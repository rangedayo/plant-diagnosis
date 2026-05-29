# """
# SVC01 RAG + LangGraph 파이프라인 오프라인 평가 (SVC42 미사용)
# """
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from datasets import Dataset
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app import prompts  # noqa: E402
from app.graph import build_diagnosis_graph  # noqa: E402
from app.vision.gemini import GeminiProvider  # noqa: E402

NODE_NAMES = ("analyze", "keyword", "retrieve", "generate")


def _ensure_sample_image(path: Path) -> None:
    """평가용 최소 JPEG이 없으면 생성 (Pillow)."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    img = Image.new("RGB", (64, 64), color=(34, 139, 34))
    img.save(path, format="JPEG", quality=85)


def _load_cases(dataset_path: Path) -> list[dict]:
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) < 20:
        raise SystemExit(f"test_dataset.json은 20개 이상 항목이 필요합니다. 현재: {len(data) if isinstance(data, list) else 0}")
    return data


def _image_to_bytes_via_base64(raw: bytes) -> bytes:
    """API 경로와 동일하게 base64 라운드트립."""
    b64 = base64.b64encode(raw).decode("ascii")
    return base64.b64decode(b64)


def _initial_state(image_bytes: bytes) -> dict:
    return {
        "image_bytes": image_bytes,
        "plant_filter_mode": "strict",
        "plant_name": None,
        "plant_name_korean": None,
        "plant_confidence": None,
        "alt_candidates": [],
        "visual_description": "",
        "observed_symptoms": [],
        "disease_name": None,
        "confidence": None,
        "is_healthy_prob": None,
        "top_candidates": [],
        "description": "",
        "keywords": [],
        "rag_query": "",
        "fallback_plant_name": None,
        "rag_docs": [],
        "sick_keys": [],
        "rag_doc_sick_pairs": [],
        "structured_result": {},
    }


def _merged_to_ragas_row(merged: dict[str, Any], expected_disease: str) -> dict[str, Any]:
    sr = merged.get("structured_result")
    if isinstance(sr, dict):
        answer_str = json.dumps(sr, ensure_ascii=False)
    else:
        answer_str = str(sr or "")
    rag_docs = merged.get("rag_docs") or []
    if not isinstance(rag_docs, list):
        rag_docs = []
    desc = (merged.get("description") or "").strip()
    rq = (merged.get("rag_query") or "").strip()
    question = desc or rq
    return {
        "question": question,
        "answer": answer_str,
        "contexts": rag_docs,
        "ground_truth": expected_disease,
    }


async def _run_one_case(
    graph,
    image_bytes: bytes,
    expected_disease: str,
) -> tuple[float, float, dict[str, float], dict[str, Any] | None]:
    """
    Returns: (retrieval_hit, answer_correct, node_seconds, ragas_row_or_none)
    """
    initial = _initial_state(image_bytes)
    merged = dict(initial)
    node_seconds: dict[str, float] = {n: 0.0 for n in NODE_NAMES}

    last = time.perf_counter()
    async for chunk in graph.astream(initial, stream_mode="updates"):
        now = time.perf_counter()
        delta = now - last
        if isinstance(chunk, dict):
            for node_name, upd in chunk.items():
                if isinstance(upd, dict):
                    merged.update(upd)
                if node_name in node_seconds:
                    node_seconds[node_name] += delta
        last = now

    rag_docs = merged.get("rag_docs") or []

    if isinstance(rag_docs, list):
        hit = 1.0 if any(expected_disease in doc for doc in rag_docs) else 0.0
    else:
        hit = 0.0

    sr = merged.get("structured_result") or {}
    blob = json.dumps(sr, ensure_ascii=False)
    correct = 1.0 if expected_disease in blob else 0.0

    ragas_row = _merged_to_ragas_row(merged, expected_disease)
    return hit, correct, node_seconds, ragas_row


async def async_main() -> None:
    load_dotenv(_ROOT / ".env")
    dataset_path = _ROOT / "data" / "test_dataset.json"
    sample_path = _ROOT / "data" / "test_images" / "eval_sample.jpg"

    cases = _load_cases(dataset_path)
    _ensure_sample_image(sample_path)

    hits: list[float] = []
    answers: list[float] = []
    latency_sum: dict[str, float] = {n: 0.0 for n in NODE_NAMES}
    n_ok = 0
    ragas_questions: list[str] = []
    ragas_answers: list[str] = []
    ragas_contexts: list[list[str]] = []
    ragas_ground_truths: list[str] = []

    vision_provider = GeminiProvider(system_prompt=prompts.ANALYZE_SYSTEM)
    async with httpx.AsyncClient() as client:
        graph = build_diagnosis_graph(client, vision_provider)

        for i, row in enumerate(cases):
            rel = row.get("image_path", "")
            expected = row.get("expected_disease", "")
            img_path = _ROOT / rel
            if not img_path.is_file():
                print(f"[skip] missing image: {rel}")
                continue
            raw = img_path.read_bytes()
            image_bytes = _image_to_bytes_via_base64(raw)

            try:
                h, c, node_sec, rag_row = await _run_one_case(
                    graph, image_bytes, expected
                )
            except Exception as e:
                print(f"[error] case {i} {rel}: {e}")
                continue

            hits.append(h)
            answers.append(c)
            for n in NODE_NAMES:
                latency_sum[n] += node_sec.get(n, 0.0)
            n_ok += 1
            if rag_row:
                ragas_questions.append(rag_row["question"])
                ragas_answers.append(rag_row["answer"])
                ragas_contexts.append(list(rag_row["contexts"]))
                ragas_ground_truths.append(rag_row["ground_truth"])

    if not hits:
        print("[RESULT] no successful runs")
        return

    recall = sum(hits) / len(hits)
    acc = sum(answers) / len(answers)

    print("[RESULT]")
    print(f"Recall@5: {recall:.2f}")
    print(f"Answer Accuracy: {acc:.2f}")
    print()

    if ragas_questions and os.environ.get("OPENAI_API_KEY"):
        try:
            ragas_ds = Dataset.from_dict(
                {
                    "question": ragas_questions,
                    "answer": ragas_answers,
                    "contexts": ragas_contexts,
                    "ground_truth": ragas_ground_truths,
                }
            )
            evaluator_llm = ChatOpenAI(model="gpt-4o", temperature=0)
            evaluator_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            ragas_result = evaluate(
                ragas_ds,
                metrics=[faithfulness, answer_relevancy],
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
            )
            print("[RAGAS] (faithfulness, answer_relevancy; evaluator=gpt-4o)")
            print(ragas_result)
        except Exception as e:
            print(f"[RAGAS] skipped or failed: {e}")
    elif ragas_questions:
        print("[RAGAS] skipped: OPENAI_API_KEY unset")
    print()
    print("[Latency]")
    for n in NODE_NAMES:
        avg = latency_sum[n] / max(n_ok, 1)
        print(f"{n}: {avg:.1f}s")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
