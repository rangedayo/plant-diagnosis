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
from app.graph import get_compiled_graph, init_graph, run_generate
from app.vision.gemini import GeminiProvider
from app.schemas import (
    AnalysisResult,
    CompareRequest,
    CompareResponse,
    DiagnosisResponse,
    HealthResponse,
    RefineContext,
    RefineRequest,
    TrendRequest,
    TrendResponse,
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
    description="LangGraph + b_dataset/main RAG (유사도 필터)",
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

    # [기능 (b)] 케어 가이드 첨부 (진단 무관, status 무관). 미커버 종은 None.
    cg = out.get("care_guide")
    care_guide = cg if isinstance(cg, dict) and cg else None

    # [챗봇 2차 보정] 2차 generate-only 재실행에 필요한 RAG 컨텍스트를 echo-back용으로 노출.
    # analyze 6필드는 이미 analysis로 노출되므로 비-analyze 재료만 담는다.
    refine_context = RefineContext(
        rag_docs=list(out.get("rag_docs") or []),
        top_3_problem_type_weighted=dict(out.get("top_3_problem_type_weighted") or {}),
        rag_failed=bool(out.get("rag_failed")),
        rag_no_docs=bool(out.get("rag_no_docs")),
        rag_weak_evidence=bool(out.get("rag_weak_evidence")),
    )

    return DiagnosisResponse(
        message="diagnosis complete",
        analysis=analysis,
        structured_result=sr,
        care_guide=care_guide,
        refine_context=refine_context,
    )


@app.post("/diagnose/refine", response_model=DiagnosisResponse)
async def diagnose_refine(req: RefineRequest) -> DiagnosisResponse:
    """[챗봇 2차 보정] 1차 analyze·RAG 결과를 재사용해 generate+guard만 재실행.

    Gemini(analyze)·임베딩(retrieve) 재호출 없음 — analysis·refine_context를 echo-back으로
    받아 객관식 답변을 참고 맥락으로 합류한다. observed_symptoms는 1차 값 불변으로 전달되어
    1차와 동일 status guard를 통과 → cardinal_miss=0 구조 보존. 무인증(/diagnose 동일 정책,
    권한은 Firestore 규칙 담당). gpt-4o-mini 1콜(+guard 교정 시 cause 재생성 1콜)만 발생.
    """
    if not model_utils.get_openai_api_key():
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY 미설정 — .env를 확인하세요.",
        )

    analysis = req.analysis
    ctx = req.refine_context
    try:
        out = await run_generate(
            visual_description=analysis.visual_description or "",
            plant_name=analysis.plant_name,
            plant_name_korean=analysis.plant_name_korean,
            plant_confidence=analysis.plant_confidence,
            alt_candidates=list(analysis.alt_candidates or []),
            observed_symptoms=list(analysis.observed_symptoms or []),
            top_3_problem_type_weighted=dict(ctx.top_3_problem_type_weighted or {}),
            rag_docs=list(ctx.rag_docs or []),
            rag_failed=bool(ctx.rag_failed),
            rag_no_docs=bool(ctx.rag_no_docs),
            rag_weak_evidence=bool(ctx.rag_weak_evidence),
            followup_answers=[
                {"question": a.question, "answer": a.answer} for a in req.answers
            ],
        )
    except Exception as e:
        logger.exception("2차 보정 진단(run_generate) 실패")
        raise HTTPException(status_code=502, detail=str(e)) from e

    sr = out.get("structured_result")
    if not isinstance(sr, dict) or not sr:
        sr = model_utils.default_structured_fallback()

    cg = out.get("care_guide")
    care_guide = cg if isinstance(cg, dict) and cg else None

    return DiagnosisResponse(
        message="refine complete",
        analysis=analysis,  # 1차 analyze 6필드 그대로 echo (불변)
        structured_result=sr,
        care_guide=care_guide,
        refine_context=ctx,  # 동일 RAG 컨텍스트 재echo (추가 보정 연쇄 대비)
    )


@app.post("/compare", response_model=CompareResponse)
async def compare_diagnoses(req: CompareRequest) -> CompareResponse:
    """[시계열 3단계] 같은 식물의 직전 vs 이번 진단 정성 비교 서술 생성.

    무인증(/diagnose와 동일 정책). 권한은 Firestore 규칙이 담당 — 프론트가 본인 진단의
    정성 필드만 페이로드로 전달. 진단 파이프라인·Gemini 비전 무관(텍스트 전용 LLM 호출).
    """
    if not model_utils.get_openai_api_key():
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY 미설정 — .env를 확인하세요.",
        )
    try:
        comparison = await model_utils.generate_diagnosis_comparison(
            req.previous, req.current
        )
    except Exception as e:
        logger.exception("진단 비교 생성 실패")
        raise HTTPException(status_code=502, detail="비교 분석에 실패했습니다.") from e
    return CompareResponse(comparison=comparison)


@app.post("/trend", response_model=TrendResponse)
async def summarize_trend(req: TrendRequest) -> TrendResponse:
    """[추이 요약] 같은 식물의 진단 이력 전체(시간순)를 받아 전반 흐름을 간결히 요약.

    /compare(2건 정성 비교)와 동일 정책: 무인증, 텍스트 전용 LLM, 진단 파이프라인·Gemini 무관.
    이력이 2건 미만이면 요약 의미가 없어 400으로 막는다(프론트도 2건 이상에서만 호출).
    """
    if len(req.diagnoses) < 2:
        raise HTTPException(
            status_code=400,
            detail="추이 요약에는 진단 이력이 2건 이상 필요합니다.",
        )
    if not model_utils.get_openai_api_key():
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY 미설정 — .env를 확인하세요.",
        )
    try:
        trend = await model_utils.generate_diagnosis_trend(req.diagnoses)
    except Exception as e:
        logger.exception("진단 추이 요약 생성 실패")
        raise HTTPException(status_code=502, detail="추이 요약에 실패했습니다.") from e
    return TrendResponse(trend=trend)


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
