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

# [1-10b] decision #6: 모든 LLM 호출에 동일 temperature 적용 (영역 1 A — Vision + GPT 동시 동일 값).
# 결정성(run1==run2) 확보가 목적. gemini.GeminiProvider 생성자 기본값과
# generate_structured_diagnosis_with_gpt가 이 상수를 참조한다.
LLM_TEMPERATURE: float = 0.0

# [시계열 3단계] 비교 서술 전용 temperature. 진단 결정성(LLM_TEMPERATURE=0.0) 정책에서
# 의도적 예외: 정성 비교는 결정성 의무가 약하고, 약간의 표현 다양성이 과장 억제·자연스러움에
# 유리(작업 프롬프트 §3.1.2 권장 0.3~0.5). 진단 경로(0.0)는 무영향.
COMPARE_TEMPERATURE: float = 0.3


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
    한국어 키워드 리스트와 동일한 길이의 영어 검색 키워드 생성 (a_dataset_rag 등 영어 코퍼스용).
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
    {"건강", "경미", "과습", "건조", "병해 의심", "영양 부족"}
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
            temperature=LLM_TEMPERATURE,
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


# [status guard] guard가 status를 비건강→"건강"으로 교정한 케이스 전용 cause 경량 재생성.
# generate가 쓴 "병해 의심" cause와 교정된 status="건강"의 모순을 해소한다(cause만 교체).
# 호출부(graph.generate_node)는 응답의 cause만 취하고 status는 guard 확정값으로 고정한다.
_STATUS_GUARD_CAUSE_FALLBACK = (
    "관찰된 증상은 해당 식물에서 흔한 경미한 변색·자연 범위로 보이며, "
    "건강 이상 신호로 보기는 어렵습니다. 빛·물·통풍 등 평소 관리를 유지해 주세요."
)


async def regenerate_healthy_cause(
    plant_name: str | None,
    observed_symptoms: list[str] | None,
) -> str:
    """status guard가 '건강'으로 교정한 케이스의 cause를 건강 전제로 다시 쓴다.

    cause 텍스트(한국어)만 반환. status는 호출부에서 guard 값으로 고정하므로 여기서
    재판정하지 않는다. API 키 부재·호출 실패·파싱 실패 시 안전한 정적 cause로 폴백한다.
    """
    syms = [str(s) for s in (observed_symptoms or []) if str(s).strip()]
    api_key = get_openai_api_key()
    if not api_key:
        return _STATUS_GUARD_CAUSE_FALLBACK

    user = prompts.STATUS_GUARD_CAUSE_REGEN_USER_TEMPLATE.format(
        plant_name=str(plant_name or "알 수 없음"),
        symptoms="\n".join(f"- {s}" for s in syms) if syms else "- (없음)",
    )
    oai = AsyncOpenAI(api_key=api_key)
    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.STATUS_GUARD_CAUSE_REGEN_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=512,
            response_format={"type": "json_object"},
            temperature=LLM_TEMPERATURE,
        )
        raw_text = (resp.choices[0].message.content or "").strip()
        parsed = _parse_json_object_from_llm(raw_text)
        cause = str((parsed or {}).get("cause", "")).strip()
        return cause or _STATUS_GUARD_CAUSE_FALLBACK
    except Exception:
        logger.exception("regenerate_healthy_cause: 호출 실패, 정적 cause 폴백")
        return _STATUS_GUARD_CAUSE_FALLBACK


def _format_symptoms(symptoms: list[str] | None) -> str:
    syms = [str(s).strip() for s in (symptoms or []) if str(s).strip()]
    return ", ".join(syms) if syms else "특이사항 없음"


async def generate_diagnosis_comparison(prev: Any, curr: Any) -> str:
    """[시계열 3단계] 같은 식물의 두 진단 스냅샷을 받아 정성 비교 서술(한국어)을 생성.

    prev·curr는 app.schemas.DiagnosisSnapshot (date/status/summary/current_state/
    cause/action_plan/observed_symptoms 속성). 진단 경로와 달리 폴백을 두지 않고,
    API 키 부재·호출 실패 시 예외를 그대로 올려 호출부(main.compare)가 502로 매핑한다.
    """
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    user = prompts.COMPARE_USER_TEMPLATE.format(
        prev_date=prev.date or "(날짜 미상)",
        prev_status=prev.status or "(미상)",
        prev_summary=prev.summary or "(요약 없음)",
        prev_current_state=prev.current_state or "(서술 없음)",
        prev_cause=prev.cause or "(원인 미상)",
        prev_symptoms=_format_symptoms(prev.observed_symptoms),
        curr_date=curr.date or "(날짜 미상)",
        curr_status=curr.status or "(미상)",
        curr_summary=curr.summary or "(요약 없음)",
        curr_current_state=curr.current_state or "(서술 없음)",
        curr_cause=curr.cause or "(원인 미상)",
        curr_symptoms=_format_symptoms(curr.observed_symptoms),
    )

    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.COMPARE_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=512,
        temperature=COMPARE_TEMPERATURE,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("비교 서술 생성 실패: 빈 응답")
    return text


def _format_trend_entry(idx: int, total: int, snap: Any) -> str:
    """추이 요약 프롬프트용 단일 스냅샷 블록(시간순 인덱스 기준 최초/최신 태그)."""
    if idx == 0:
        tag = "최초"
    elif idx == total - 1:
        tag = "최신"
    else:
        tag = f"{idx + 1}회차"
    return (
        f"[{idx + 1}/{total} · {tag} — {snap.date or '(날짜 미상)'}]\n"
        f"- 상태: {snap.status or '(미상)'}\n"
        f"- 요약: {snap.summary or '(요약 없음)'}\n"
        f"- 원인: {snap.cause or '(원인 미상)'}\n"
        f"- 관찰된 증상: {_format_symptoms(snap.observed_symptoms)}"
    )


async def generate_diagnosis_trend(snaps: list[Any]) -> str:
    """[추이 요약] 같은 식물의 진단 이력(시간순 오래된→최신)을 받아 전반 흐름 요약(한국어)을 생성.

    snaps는 app.schemas.DiagnosisSnapshot 리스트. generate_diagnosis_comparison과 동일하게
    폴백 없이 API 키 부재·호출 실패 시 예외를 그대로 올려 호출부(main.summarize_trend)가 매핑한다.
    """
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    if len(snaps) < 2:
        raise RuntimeError("추이 요약에는 2건 이상의 진단이 필요합니다.")

    total = len(snaps)
    entries = "\n\n".join(_format_trend_entry(i, total, s) for i, s in enumerate(snaps))
    user = prompts.TREND_USER_TEMPLATE.format(count=total, entries=entries)

    oai = AsyncOpenAI(api_key=api_key)
    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompts.TREND_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=400,
        temperature=COMPARE_TEMPERATURE,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("추이 요약 생성 실패: 빈 응답")
    return text
