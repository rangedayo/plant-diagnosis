"""R12b 합성 검증 — cause–status 정합 룰의 문법/sanity 점검 (gpt-4o-mini, Gemini 0건).

§3.1 4케이스를 generate_structured_diagnosis_with_gpt에 통과시켜, 새 정합 룰 하에서
cause 주원인과 status enum이 일치하는지 본다. graph.py generate_node의 context_summary·
rag_chunks 구성을 재현하고, top 카드 본문은 b_dataset_rag에서 read-only로 가져온다.

한계(§3.2): generate는 LLM 결정이라 합성으로 100% 보장 불가. 단일 호출·temperature 비결정.
"프롬프트 문법 + 명백한 매핑 표 작동" 수준만 검증. 실효 검증은 사용자 run_eval 실측.

읽기 전용: Chroma get만. 쓰기 없음.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import graph as graph_mod  # noqa: E402
from app import model_utils  # noqa: E402

VECTOR_DB = ROOT / "data" / "vector_db"


def _fetch_cards(card_ids: list[str]) -> dict[str, tuple[str, str]]:
    """card_id → (problem_type, document) 본문, read-only."""
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    coll = client.get_collection("b_dataset_rag")
    got = coll.get(where={"card_id": {"$in": card_ids}},
                   include=["documents", "metadatas"])
    out: dict[str, tuple[str, str]] = {}
    for doc, meta in zip(got.get("documents") or [], got.get("metadatas") or []):
        cid = str((meta or {}).get("card_id") or "")
        pt = str((meta or {}).get("problem_type") or "")
        out[cid] = (pt, str(doc or ""))
    return out


def _build_context(*, plant_ko: str, confidence: str, symptoms: list[str],
                   majority: str, top_pt: str, dist_str: str) -> str:
    symptoms_str = ", ".join(symptoms) if symptoms else "관찰된 이상 없음"
    return (
        f"묘사:\n실내 화분 식물. 잎 상태 관찰.\n\n"
        f"[관찰 정보]\n"
        f"- 식물명(학명 1위): {plant_ko}\n"
        f"- 식물명(통명): {plant_ko}\n"
        f"- 식별 신뢰도: {confidence}\n"
        f"- 대안 후보: 없음\n"
        f"- 관찰된 증상: {symptoms_str}\n\n"
        f"[검색된 자료의 타입 분포 (top_3 sim 가중)]\n"
        f"- 우세 타입: {majority}\n"
        f"- 1위 카드 타입: {top_pt}\n"
        f"- 분포: {dist_str}\n"
    )


# (가)건조 (나)과습 (다)영양 (라)병해 — cause 텍스트 → 기대 enum 매핑 키워드
CAUSE_TO_STATUS = {
    "건조": ["수분 부족", "물 부족", "과도한 건조", "건조", "토양 건조", "수분"],
    "과습": ["과습", "물 과다", "물주기 과다", "뿌리 무름"],
    "영양 부족": ["영양 부족", "비료 부족", "결핍", "질소"],
    "병해 의심": ["곰팡이", "세균", "바이러스", "진균", "해충", "흰가루", "잎점무늬", "병해", "감염"],
}


def _infer_status_from_cause(cause: str) -> set[str]:
    hit = set()
    for status, kws in CAUSE_TO_STATUS.items():
        if any(k in cause for k in kws):
            hit.add(status)
    return hit


CASES = [
    {
        "name": "haengun_003 시뮬 (건조 기대)",
        "plant_ko": "행운목",
        "confidence": "med",
        "symptoms": ["아래잎 전체의 바삭한 마름 및 고사", "새순 끝부분 마름"],
        "cards": ["mu_trinklein_012", "psu_ucanr_016"],
        "majority": "tie", "top_pt": "general",
        "dist": "general 0.50, abiotic 0.50",
        "expect": "건조",
    },
    {
        "name": "haengun_008 시뮬 (건조 기대)",
        "plant_ko": "행운목",
        "confidence": "med",
        "symptoms": ["여러 잎의 잎끝 갈변 및 마름", "아래쪽 잎 고사", "전체적인 잎 처짐 및 주름"],
        "cards": ["mu_trinklein_012", "mu_trinklein_006"],
        "majority": "general", "top_pt": "general",
        "dist": "general 1.00",
        "expect": "건조",
    },
    {
        "name": "healthy 시뮬 (매핑 비강제 — 건조여서는 안 됨)",
        "plant_ko": "스킨답서스",
        "confidence": "low",
        "symptoms": ["일부 잎끝 갈변"],
        "cards": ["psu_ucanr_016"],
        "majority": "abiotic", "top_pt": "abiotic",
        "dist": "abiotic 0.60, env 0.40",
        "expect_not": "건조",  # 불특정 cause면 매핑 강제 X
    },
    {
        "name": "disease sanity (병해 정합)",
        "plant_ko": "스킨답서스",
        "confidence": "med",
        "symptoms": ["잎 중앙부 불규칙 갈색 반점 확산", "비대칭 괴사 병반"],
        "cards": ["psu_indoor_011", "psu_ucanr_007"],
        "majority": "disease", "top_pt": "disease",
        "dist": "disease 1.00",
        "expect": "병해 의심",
    },
]


async def main() -> None:
    all_ids = sorted({c for case in CASES for c in case["cards"]})
    cards = _fetch_cards(all_ids)
    print(f"fetched cards: {sorted(cards.keys())}\n")

    passed = 0
    for case in CASES:
        rag_chunks = "\n\n".join(
            f"[{cards[cid][0]}] {cards[cid][1]}" for cid in case["cards"] if cid in cards
        )
        ctx = _build_context(
            plant_ko=case["plant_ko"], confidence=case["confidence"],
            symptoms=case["symptoms"], majority=case["majority"],
            top_pt=case["top_pt"], dist_str=case["dist"],
        )
        res = await model_utils.generate_structured_diagnosis_with_gpt(ctx, rag_chunks)
        gen_status = str(res.get("status") or "")
        cause = str(res.get("cause") or "")
        # 프로덕션 정합: generate 출력 후 status guard 적용 (비건강→건강 교정)
        post_status, guard_reason = graph_mod.apply_status_guard(
            gen_status, case["symptoms"], case["top_pt"]
        )
        cause_status = _infer_status_from_cause(cause)
        consistent = (not cause_status) or (gen_status in cause_status)

        ok = True
        if "expect" in case:
            ok = (gen_status == case["expect"]) and consistent
        elif "expect_not" in case:
            ok = (post_status != case["expect_not"])  # 가드 후 기준

        passed += int(ok)
        print(f"== {case['name']}  → {'PASS' if ok else 'FAIL'}")
        print(f"   gen_status={gen_status!r} → post_guard={post_status!r}(reason={guard_reason})")
        print(f"   cause_infers={sorted(cause_status)}  정합={consistent}")
        print(f"   cause={cause!r}\n")

    print(f"=== 합성 {passed}/{len(CASES)} ===")


if __name__ == "__main__":
    asyncio.run(main())
