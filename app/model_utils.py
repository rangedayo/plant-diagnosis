"""
OpenAI 유틸 — CPU·비동기만 사용 (GPU/Torch 미사용)
모든 GPT 호출은 이 모듈에서 수행합니다.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger("plant_api")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from PIL import Image

from app import prompts

load_dotenv()


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


REQUIRED_WEAK_EVIDENCE_PHRASE = "정확도가 낮을 수 있습니다"

ALLOWED_STRUCT_STATUS = frozenset(
    {"건강", "과습", "건조", "병해 의심", "영양 부족"}
)


def default_structured_fallback(*, rag_failed: bool = False) -> dict[str, Any]:
    if rag_failed:
        # [1-10a] decision #3: RAG 시스템 실패 시 LLM 호출 없이 정직한 정적 안내를 반환.
        return {
            "summary": "근거 자료가 부족해 정확한 진단을 제시하기 어려워요. 사진을 다시 촬영하거나 환경을 점검해 보세요.",
            "current_state": "이미지의 관찰 묘사만으로는 상태를 단정하기 어렵습니다.",
            "cause": "참고할 수 있는 근거 자료가 충분하지 않아 원인을 특정하기 어렵습니다.",
            "action_plan": [
                "환경(빛·물·통풍·습도)을 점검해 주세요.",
                "잎의 변화를 며칠 더 관찰한 뒤 다시 촬영해 주세요.",
            ],
            "status": "병해 의심",  # 안전망 — 사용자 점검 행동 유도
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


def normalize_structured_result(data: dict[str, Any]) -> dict[str, Any]:
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
    if rag_failed:
        # [1-10a] decision #3: RAG 시스템 실패 시 LLM 호출을 폐기하고 정적 안내로 즉시 반환.
        return default_structured_fallback(rag_failed=True)

    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

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
            return normalize_structured_result(default_structured_fallback())
        out = normalize_structured_result(parsed)
    except Exception:
        logger.exception("structured_diagnosis: API 호출 또는 처리 실패, fallback 사용")
        return normalize_structured_result(default_structured_fallback())

    if rag_weak_evidence and REQUIRED_WEAK_EVIDENCE_PHRASE not in (
        out.get("summary") or ""
    ):
        out["summary"] = f"{REQUIRED_WEAK_EVIDENCE_PHRASE}\n\n{out['summary']}"

    return out
