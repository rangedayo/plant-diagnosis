"""
식물 진단 API — LangGraph 파이프라인 + FastAPI
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from app import model_utils, prompts
from app.graph import get_compiled_graph, init_graph
from app.vision.gemini import GeminiProvider
from app.schemas import (
    AnalysisResult,
    DiagnosisResponse,
    HealthResponse,
)

load_dotenv()

logger = logging.getLogger("plant_api")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(_h)

ALLOWED_UPLOAD_EXT = (".jpg", ".jpeg", ".png")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_magic_number(data: bytes) -> str:
    if data.startswith(b"\xFF\xD8"):
        return "jpeg"
    if data.startswith(b"\x89PNG"):
        return "png"
    raise HTTPException(status_code=400, detail="유효하지 않은 이미지 파일")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "에러: %s: %s\n경로: %s %s\n%s",
            type(exc).__name__,
            exc,
            request.method,
            request.url,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "서버 내부 오류가 발생했습니다."},
        )


image_executor = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("앱 시작: Gemini VisionProvider · LangGraph 초기화")
    # [1-5] analyze 경로: GeminiProvider를 lifespan에서 1회 생성해 그래프에 주입 (decision #7 옵션 A).
    vision_provider = GeminiProvider(system_prompt=prompts.ANALYZE_SYSTEM)
    init_graph(vision_provider)
    yield
    logger.info("앱 종료")


app = FastAPI(
    title="Plant Diagnosis API",
    description="LangGraph + NCPMS SVC05 RAG (유사도 필터)",
    version="0.3.0",
    openapi_version="3.0.2",  # Swagger file upload UI 정상화를 위한 설정
    lifespan=lifespan,
    docs_url=None,  # 기본 Swagger 비활성화 → 최신 Swagger UI 커스텀 /docs 사용
)
# 생성자의 openapi_version은 일부 FastAPI 버전에서 extra로만 전달되므로, 스키마 버전은 속성으로 확정
app.openapi_version = "3.0.2"
register_error_handlers(app)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Plant Diagnosis API Docs",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        openai_configured=bool(model_utils.get_openai_api_key()),
    )


@app.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    file: UploadFile = File(...),
) -> DiagnosisResponse:
    """이미지 업로드 후 LangGraph 실행 (analyze→keyword→retrieve→generate)."""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail="허용되지 않는 확장자입니다. (.jpg, .jpeg, .png)",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="파일 크기 초과 (최대 5MB)",
        )
    validate_magic_number(image_bytes)

    loop = asyncio.get_running_loop()

    def process_image() -> bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            return buf.getvalue()
        except UnidentifiedImageError:
            raise HTTPException(
                status_code=400,
                detail="이미지 파일이 손상되었거나 지원되지 않는 형식입니다",
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="이미지 처리 중 오류가 발생했습니다",
            )

    image_bytes = await loop.run_in_executor(None, process_image)

    if not model_utils.get_openai_api_key():
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY 미설정 — .env를 확인하세요.",
        )

    graph = get_compiled_graph()
    try:
        out = await graph.ainvoke(
            {
                "image_bytes": image_bytes,
                "plant_name": None,
                "plant_name_korean": None,
                "plant_confidence": None,
                "alt_candidates": [],
                "visual_description": "",
                "observed_symptoms": [],
                "keywords": [],
                "rag_query": "",
                "rag_docs": [],
                "sick_keys": [],
                "rag_doc_sick_pairs": [],
                "structured_result": {},
            }
        )
    except Exception as e:
        logger.exception("LangGraph 실행 실패")
        raise HTTPException(status_code=502, detail=str(e)) from e

    analysis = AnalysisResult(
        plant_name=out.get("plant_name"),
        plant_name_korean=out.get("plant_name_korean"),
        plant_confidence=out.get("plant_confidence"),
        alt_candidates=list(out.get("alt_candidates") or []),
        visual_description=str(out.get("visual_description") or ""),
        observed_symptoms=list(out.get("observed_symptoms") or []),
    )

    sr = out.get("structured_result")

    if not isinstance(sr, dict) or not sr:
        sr = model_utils.default_structured_fallback()

    return DiagnosisResponse(
        message="diagnosis complete",
        analysis=analysis,
        structured_result=sr,
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = app._original_openapi()

    try:
        file_prop = (
            openapi_schema["components"]["schemas"]["Body_diagnose_diagnose_post"][
                "properties"
            ]["file"]
        )

        file_prop["type"] = "string"
        file_prop["format"] = "binary"

        if "contentMediaType" in file_prop:
            del file_prop["contentMediaType"]

    except Exception:
        pass

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app._original_openapi = app.openapi
app.openapi = custom_openapi  # type: ignore[method-assign]
