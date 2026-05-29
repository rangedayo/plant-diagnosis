"""
Plant.id · OpenAI 유틸 — CPU·비동기만 사용 (GPU/Torch 미사용)
모든 GPT 호출은 이 모듈에서 수행합니다.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger("plant_api")

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from PIL import Image

from app import prompts

load_dotenv()

PLANT_ID_IDENTIFICATION_URL = "https://api.plant.id/v3/identification"


def get_plant_id_api_key() -> Optional[str]:
    return os.getenv("PLANT_ID_API_KEY")


def get_plant_id_health_mode() -> str | None:
    """
    Plant.id v3 `health` 폼 필드: auto | all | only.
    PLANT_ID_HEALTH 미설정 시 auto. none/off/0 이면 health 미전송(식별만).
    """
    raw = os.getenv("PLANT_ID_HEALTH")
    if raw is None:
        return "auto"
    s = raw.strip().lower()
    if s in ("", "none", "off", "0"):
        return None
    if s in ("auto", "all", "only"):
        return s
    return "auto"


def _first_classification_suggestion(
    suggestions: Any,
) -> tuple[str | None, float | None]:
    """v3 classification.suggestions[0] — name(또는 구버전 plant_name), probability."""
    if not isinstance(suggestions, list) or not suggestions:
        return None, None
    s0 = suggestions[0]
    if not isinstance(s0, dict):
        return None, None
    raw_name = s0.get("name")
    if raw_name is None:
        raw_name = s0.get("plant_name")
    plant_name: str | None = None
    if raw_name is not None:
        ps = str(raw_name).strip()
        plant_name = ps if ps else None
    confidence: float | None = None
    prob = s0.get("probability")
    if prob is not None:
        try:
            confidence = float(prob)
        except (TypeError, ValueError):
            confidence = None
    return plant_name, confidence


def _first_disease_suggestion_name(suggestions: Any) -> str | None:
    """v3 result.disease.suggestions[0].name"""
    if not isinstance(suggestions, list) or not suggestions:
        return None
    s0 = suggestions[0]
    if not isinstance(s0, dict):
        return None
    n = s0.get("name")
    if n is None:
        return None
    s = str(n).strip()
    return s if s else None


def _is_healthy_probability_from_result(result: Any) -> float | None:
    """v3 result.is_healthy.probability (이미지에 건강한 식물일 확률)."""
    if not isinstance(result, dict):
        return None
    ih = result.get("is_healthy")
    if not isinstance(ih, dict):
        return None
    p = ih.get("probability")
    if p is None:
        return None
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


def _top_n_classification_candidates(
    suggestions: Any, n: int = 3
) -> list[dict[str, Any]]:
    """classification.suggestions 상위 n개 — name, probability."""
    out: list[dict[str, Any]] = []
    if not isinstance(suggestions, list):
        return out
    for s in suggestions[:n]:
        if not isinstance(s, dict):
            continue
        raw_name = s.get("name")
        if raw_name is None:
            raw_name = s.get("plant_name")
        name: str | None = None
        if raw_name is not None:
            ps = str(raw_name).strip()
            name = ps if ps else None
        prob: float | None = None
        if s.get("probability") is not None:
            try:
                prob = float(s["probability"])
            except (TypeError, ValueError):
                prob = None
        if name is not None or prob is not None:
            out.append({"name": name, "probability": prob})
    return out


def get_openai_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def get_rda_api_key() -> Optional[str]:
    return os.getenv("RDA_API_KEY")


def get_gemini_api_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY")


def decode_base64_image(image_base64: str) -> bytes:
    """Base64 문자열을 바이트로 디코딩 (블로킹 — 호출부에서 run_in_executor 권장)."""
    return base64.b64decode(image_base64, validate=True)


def image_bytes_to_rgb_size(image_bytes: bytes) -> tuple[Image.Image, tuple[int, int]]:
    """바이트에서 PIL RGB 이미지와 (width, height) 반환 (블로킹 — executor용)."""
    with Image.open(io.BytesIO(image_bytes)) as im:
        rgb = im.convert("RGB")
        return rgb.copy(), rgb.size


def _image_bytes_to_jpeg_base64_sync(image_bytes: bytes) -> str:
    """PIL로 RGB JPEG 정규화 후 base64 ASCII 문자열 (블로킹)."""
    with Image.open(io.BytesIO(image_bytes)) as im:
        rgb = im.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _parse_identification_json(body: dict[str, Any]) -> dict[str, Any]:
    """
    v3: result.classification.suggestions[0].name, .probability
    v3 질병: result.disease.suggestions[0].name
    v3: result.is_healthy.probability, classification 상위 3 후보
    구버전 호환: 최상위 suggestions + plant_name
    """
    plant_name: str | None = None
    disease_name: str | None = None
    confidence: float | None = None
    is_healthy_prob: float | None = None
    top_candidates: list[dict[str, Any]] = []

    result = body.get("result")
    if isinstance(result, dict):
        is_healthy_prob = _is_healthy_probability_from_result(result)
        cls = result.get("classification")
        if isinstance(cls, dict):
            sug = cls.get("suggestions")
            plant_name, confidence = _first_classification_suggestion(sug)
            top_candidates = _top_n_classification_candidates(sug, n=3)
        dis = result.get("disease")
        if isinstance(dis, dict):
            disease_name = _first_disease_suggestion_name(dis.get("suggestions"))

    if plant_name is None:
        legacy_sug = body.get("suggestions")
        plant_name, confidence = _first_classification_suggestion(legacy_sug)
        if not top_candidates:
            top_candidates = _top_n_classification_candidates(legacy_sug, n=3)

    return {
        "plant_name": plant_name,
        "disease_name": disease_name,
        "confidence": confidence,
        "is_healthy_prob": is_healthy_prob,
        "top_candidates": top_candidates,
    }


def parse_identification_response(body: dict[str, Any]) -> dict[str, Any]:
    """Plant.id JSON 응답 파싱 (테스트·디버그용). 식별·건강·상위 후보 포함."""
    return _parse_identification_json(body)


def format_top_candidates_for_prompt(
    top_candidates: list[dict[str, Any]] | None,
) -> str:
    """프롬프트용 한 줄 요약 (없으면 '없음')."""
    if not top_candidates:
        return "없음"
    parts: list[str] = []
    for c in top_candidates[:3]:
        if not isinstance(c, dict):
            continue
        n = c.get("name")
        p = c.get("probability")
        if n is not None and str(n).strip():
            if p is not None:
                try:
                    parts.append(f"{n} ({float(p):.4f})")
                except (TypeError, ValueError):
                    parts.append(str(n))
            else:
                parts.append(str(n))
    return "; ".join(parts) if parts else "없음"


def format_is_healthy_for_prompt(value: float | None) -> str:
    if value is None:
        return "없음"
    return f"{value:.4f}"


async def fetch_plant_identification_json(
    client: httpx.AsyncClient,
    image_bytes: bytes,
) -> dict[str, Any]:
    """
    Plant.id v3 POST /identification 전체 JSON (result.is_healthy 등 포함).
    """
    api_key = get_plant_id_api_key()
    if not api_key:
        raise RuntimeError("PLANT_ID_API_KEY가 설정되지 않았습니다.")

    headers = {"Api-Key": api_key}
    files = {"images": ("image.jpg", image_bytes, "image/jpeg")}
    data: dict[str, str] = {"similar_images": "true"}
    hm = get_plant_id_health_mode()
    if hm is not None:
        data["health"] = hm

    response = await client.post(
        PLANT_ID_IDENTIFICATION_URL,
        headers=headers,
        files=files,
        data=data,
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


async def identify_plant_disease_api(
    client: httpx.AsyncClient,
    image_bytes: bytes,
) -> dict[str, Any]:
    """
    Plant.id v3 POST /identification — Api-Key, multipart `images`,
    similar_images, 선택적 health(auto|all|only, 기본 auto → `get_plant_id_health_mode`).
    """
    body = await fetch_plant_identification_json(client, image_bytes)
    return parse_identification_response(body)


async def describe_image_with_gpt(image_bytes: bytes) -> str:
    """
    gpt-4o-mini 비전 — prompts.DESCRIBE_IMAGE_SYSTEM / USER 사용.
    """
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    loop = asyncio.get_running_loop()
    b64 = await loop.run_in_executor(
        None,
        _image_bytes_to_jpeg_base64_sync,
        image_bytes,
    )

    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.DESCRIBE_IMAGE_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompts.DESCRIBE_IMAGE_USER_TEMPLATE},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                        },
                    },
                ],
            },
        ],
        max_tokens=512,
    )
    text = resp.choices[0].message.content
    return (text or "").strip()


async def extract_keywords_with_gpt(
    description: str,
    plant_name: str | None,
    disease_name: str | None,
    confidence: float | None,
    *,
    is_healthy_prob: float | None = None,
    top_candidates: list[dict[str, Any]] | None = None,
) -> list[str]:
    """KEYWORD_SYSTEM / KEYWORD_USER_TEMPLATE — 쉼표 구분 키워드 리스트."""
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    user = prompts.KEYWORD_USER_TEMPLATE.format(
        description=description,
        plant_name=plant_name or "",
        disease_name=disease_name or "",
        confidence=confidence if confidence is not None else "",
        is_healthy_prob=format_is_healthy_for_prompt(is_healthy_prob),
        top_candidates=format_top_candidates_for_prompt(top_candidates),
    )
    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.KEYWORD_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=256,
    )
    text = (resp.choices[0].message.content or "").strip()
    parts: list[str] = []
    for p in text.replace("，", ",").split(","):
        s = p.strip()
        if s:
            parts.append(s)
    return parts


async def generate_english_keywords(keywords_ko: list[str]) -> list[str]:
    """
    한국어 키워드 리스트와 동일한 길이의 영어 검색 키워드 생성 (main_rag 등 영어 코퍼스용).
    """
    if not keywords_ko:
        return []
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    n = len(keywords_ko)
    user = prompts.ENGLISH_KEYWORD_USER_TEMPLATE.format(
        n=n,
        keywords=", ".join(keywords_ko),
    )
    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.ENGLISH_KEYWORD_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=128,
    )
    text = (resp.choices[0].message.content or "").strip()
    parts: list[str] = []
    for p in text.replace("，", ",").split(","):
        s = p.strip()
        if s:
            parts.append(s)
    if len(parts) < n:
        while len(parts) < n and parts:
            parts.append(parts[-1])
        while len(parts) < n:
            parts.append("")
    elif len(parts) > n:
        parts = parts[:n]
    return parts


RAG_QUERY_MAX_WORDS = 14
RAG_SYMPTOM_KEYWORD_MAX = 5


def _symptom_token_allowed(t: str) -> bool:
    s = t.strip()
    if not s:
        return False
    if s in ("건강", "정상", "깨끗"):
        return False
    banned_phrases = ("이상 없음", "문제 없음", "갈변 없음")
    if any(p in s for p in banned_phrases):
        return False
    if s.endswith("없음") or " 없음" in s:
        return False
    if "없다" in s or "아님" in s:
        return False
    if "건강" in s or "깨끗" in s:
        return False
    return True


def _parse_symptom_keywords_from_llm(text: str) -> list[str]:
    out: list[str] = []
    for p in text.replace("，", ",").split(","):
        s = p.strip()
        if s and _symptom_token_allowed(s):
            out.append(s)
    out = out[:RAG_SYMPTOM_KEYWORD_MAX]
    if len(out) < 3 and text:
        logger.warning(
            "symptom_keywords: LLM 출력이 3개 미만(%d개) — 검색 품질 저하 가능",
            len(out),
        )
    return out


def _sanitize_fallback_plant_line(text: str) -> str:
    line = (text or "").split("\n", 1)[0].strip()
    words = line.split()
    return " ".join(words[:10])


async def estimate_fallback_plant_with_gpt(description: str) -> str:
    """Plant.id 실패 시 묘사 기반 넓은 범주 식물 유형(검색 범위용). 빈 문자열 가능."""
    if not (description or "").strip():
        return ""
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    user = prompts.FALLBACK_PLANT_USER_TEMPLATE.format(description=description)
    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.FALLBACK_PLANT_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=120,
    )
    raw = (resp.choices[0].message.content or "").strip()
    line = _sanitize_fallback_plant_line(raw)
    if line:
        wc = len(line.split())
        if wc < 2:
            logger.warning(
                "fallback_plant: 단어 수 부족(%d) — 랭킹 힌트 약함",
                wc,
            )
    return line


async def build_rag_search_query_with_gpt(
    description: str,
    plant_name: str | None,
    disease_name: str | None,
    confidence: float | None,
    fallback_plant_name: str | None = None,
    *,
    is_healthy_prob: float | None = None,
    top_candidates: list[dict[str, Any]] | None = None,
    plant_filter_mode: str = "strict",
) -> str:
    """
    RAG 검색어: [plant 또는 relaxed일 때만 fallback_plant] + [disease_name?] + [증상 키워드], 최대 6단어.
    strict + plant_name 없음: 식물명 없이 증상·질병 키워드만 (fallback을 식물 대체로 사용하지 않음).
    """
    _ = confidence  # 시그니처 유지 (프롬프트 확장용)
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    symptom_tokens: list[str] = []
    if (description or "").strip():
        user = prompts.RAG_QUERY_SYMPTOM_USER_TEMPLATE.format(
            description=description,
            is_healthy_prob=format_is_healthy_for_prompt(is_healthy_prob),
            top_candidates=format_top_candidates_for_prompt(top_candidates),
        )
        oai = AsyncOpenAI(api_key=api_key)
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.RAG_QUERY_SYMPTOM_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=256,
        )
        raw = (resp.choices[0].message.content or "").strip()
        symptom_tokens = _parse_symptom_keywords_from_llm(raw)

    mode = (plant_filter_mode or "strict").lower()
    effective_plant = ""
    if plant_name and str(plant_name).strip():
        effective_plant = str(plant_name).strip()
    elif mode != "strict" and fallback_plant_name and str(fallback_plant_name).strip():
        effective_plant = str(fallback_plant_name).strip()

    parts: list[str] = []
    if effective_plant:
        parts.append(effective_plant)
    if disease_name and str(disease_name).strip():
        parts.append(str(disease_name).strip())
    parts.extend(symptom_tokens)

    core = " ".join(parts).strip()
    words = core.split()
    if len(words) > RAG_QUERY_MAX_WORDS:
        words = words[:RAG_QUERY_MAX_WORDS]
    return " ".join(words)


REQUIRED_RAG_FAILED_PHRASE = "제공된 정보만으로는 정확한 진단이 어렵습니다"
REQUIRED_WEAK_EVIDENCE_PHRASE = "정확도가 낮을 수 있습니다"

ALLOWED_STRUCT_STATUS = frozenset(
    {"건강", "과습", "건조", "병해 의심", "영양 부족"}
)


def default_structured_fallback(*, rag_failed: bool = False) -> dict[str, Any]:
    if rag_failed:
        return {
            "summary": REQUIRED_RAG_FAILED_PHRASE,
            "current_state": "도감 검색 시스템에 접근하지 못했습니다.",
            "cause": "시스템 오류로 참고 자료를 불러올 수 없습니다.",
            "action_plan": [
                "농업기술상담(1544-8572) 등 전문가 상담을 권장합니다.",
                "잠시 후 이미지를 다시 촬영해 재시도해 보세요.",
            ],
            "status": "병해 의심",
        }
    return {
        "summary": "관찰 정보를 바탕으로 요약했습니다.",
        "current_state": "이미지 묘사를 바탕으로 상태를 정리했습니다.",
        "cause": "정보가 제한적일 수 있어 원인은 여러 가지일 수 있습니다.",
        "action_plan": [
            "환경(빛·물·통풍·습도)을 점검하세요.",
            "지속적으로 관찰하세요.",
        ],
        # [1-7] decision #5: JSON 파싱 완전 실패 시에도 점검 행동 유도 ("건강" 디폴트 폐기).
        "status": "병해 의심",
    }


def _parse_json_object_from_llm(text: str) -> dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if m:
        t = m.group(1).strip()
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def normalize_structured_result(
    data: dict[str, Any],
    *,
    rag_failed: bool,
) -> dict[str, Any]:
    summary = str(data.get("summary", "")).strip()
    current_state = str(data.get("current_state", "")).strip()
    cause = str(data.get("cause", "")).strip()
    plan_raw = data.get("action_plan")
    if isinstance(plan_raw, list):
        plan = [str(x).strip() for x in plan_raw if str(x).strip()]
    else:
        plan = []
    _pad = ["지속적으로 관찰하세요.", "빛·물·통풍·습도 환경을 점검하세요."]
    while len(plan) < 2:
        plan.append(_pad[len(plan) % 2])
    status = str(data.get("status", "")).strip()
    if status not in ALLOWED_STRUCT_STATUS:
        # [1-7] decision #5: 불확실 시 사용자 점검 행동을 유도하는 "병해 의심"으로 (보수화 메커니즘 3 대응).
        status = "병해 의심"
    if not summary:
        summary = "상태를 요약했습니다."
    if not current_state:
        current_state = "묘사를 참고해 주세요."
    if not cause:
        cause = "원인은 여러 요인이 겹칠 수 있습니다."
    return {
        "summary": summary,
        "current_state": current_state,
        "cause": cause,
        "action_plan": plan,
        "status": status,
    }


async def generate_structured_diagnosis_with_gpt(
    context_summary: str,
    rag_chunks: str,
    *,
    rag_failed: bool = False,
    rag_no_docs: bool = False,
    rag_weak_evidence: bool = False,
) -> dict[str, Any]:
    """generate 단계: JSON 구조만. 실패 시 fallback dict."""
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    if rag_failed:
        user = prompts.STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_USER_TEMPLATE.format(
            context_summary=context_summary,
        )
        system = prompts.STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM
    else:
        weak_instruction = ""
        if rag_weak_evidence:
            weak_instruction = (
                "[중요] 검색 참고 자료의 임베딩 유사도가 높지 않습니다. "
                f"summary에 반드시 '{REQUIRED_WEAK_EVIDENCE_PHRASE}'를 자연스럽게 포함하세요. "
                "병명을 단정하지 마세요."
            )
        no_rag_block = (
            prompts.STRUCTURED_DIAGNOSIS_NO_RAG_DOCS_BLOCK if rag_no_docs else ""
        )
        user = prompts.STRUCTURED_DIAGNOSIS_JSON_USER_TEMPLATE.format(
            context_summary=context_summary,
            no_rag_block=no_rag_block,
            rag_chunks=rag_chunks if rag_chunks.strip() else "(참고 자료 없음)",
            weak_instruction=weak_instruction,
        )
        system = prompts.STRUCTURED_DIAGNOSIS_JSON_SYSTEM

    oai = AsyncOpenAI(api_key=api_key)
    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw_text = (resp.choices[0].message.content or "").strip()
        parsed = _parse_json_object_from_llm(raw_text)
        if parsed is None:
            logger.warning(
                "structured_diagnosis: JSON 파싱 실패, fallback 사용. preview=%r",
                raw_text[:200],
            )
            return normalize_structured_result(
                default_structured_fallback(rag_failed=rag_failed),
                rag_failed=rag_failed,
            )
        out = normalize_structured_result(parsed, rag_failed=rag_failed)
    except Exception:
        logger.exception("structured_diagnosis: API 호출 또는 처리 실패, fallback 사용")
        return normalize_structured_result(
            default_structured_fallback(rag_failed=rag_failed),
            rag_failed=rag_failed,
        )

    if rag_failed and REQUIRED_RAG_FAILED_PHRASE not in (out.get("summary") or ""):
        out["summary"] = f"{REQUIRED_RAG_FAILED_PHRASE}\n\n{out['summary']}"
    elif rag_weak_evidence and not rag_failed:
        if REQUIRED_WEAK_EVIDENCE_PHRASE not in (out.get("summary") or ""):
            out["summary"] = f"{REQUIRED_WEAK_EVIDENCE_PHRASE}\n\n{out['summary']}"

    return out


async def identify_plant_async(
    client: httpx.AsyncClient,
    image_bytes: bytes,
) -> dict[str, Any]:
    """하위 호환: identify_plant_disease_api와 동일."""
    return await identify_plant_disease_api(client, image_bytes)
