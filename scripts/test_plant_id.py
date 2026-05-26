"""
Plant.id만 호출해 식물명(name)·건강(질병 상위 후보)을 확인합니다.
LangGraph·OpenAI는 사용하지 않습니다.

사용법 (프로젝트 루트에서):
  .venv\\Scripts\\python.exe scripts\\test_plant_id.py path\\to\\photo.jpg
  .venv\\Scripts\\python.exe scripts\\test_plant_id.py path\\to\\photo.jpg --verbose

필요: .env 의 PLANT_ID_API_KEY
선택: PLANT_ID_HEALTH (auto | all | only | none)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.model_utils import (  # noqa: E402
    fetch_plant_identification_json,
    get_plant_id_api_key,
    parse_identification_response,
)


def _print_verbose(body: dict) -> None:
    result = body.get("result")
    if not isinstance(result, dict):
        print("\n[verbose] result 없음 또는 비정상")
        return
    ih = result.get("is_healthy")
    if isinstance(ih, dict):
        print(
            "\n[verbose] is_healthy:",
            "binary=", ih.get("binary"),
            "probability=", ih.get("probability"),
        )
    dis = result.get("disease")
    if isinstance(dis, dict):
        sug = dis.get("suggestions")
        if isinstance(sug, list) and sug:
            print("[verbose] disease 상위 3개:")
            for i, s in enumerate(sug[:3]):
                if isinstance(s, dict):
                    print(
                        f"  {i+1}. name={s.get('name')!r} "
                        f"p={s.get('probability')!r}"
                    )
    cls = result.get("classification")
    if isinstance(cls, dict):
        sug = cls.get("suggestions")
        if isinstance(sug, list) and sug:
            print("[verbose] classification 상위 3개:")
            for i, s in enumerate(sug[:3]):
                if isinstance(s, dict):
                    print(
                        f"  {i+1}. name={s.get('name')!r} "
                        f"p={s.get('probability')!r}"
                    )


async def main() -> int:
    p = argparse.ArgumentParser(description="Plant.id 식별·건강 단독 테스트")
    p.add_argument("image", type=Path, help="JPEG/PNG 등 식물 사진 경로")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="is_healthy·상위 후보 요약 출력",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="응답 JSON 전체 출력(매우 김)",
    )
    args = p.parse_args()

    if not get_plant_id_api_key():
        print("PLANT_ID_API_KEY가 없습니다. .env 를 확인하세요.", file=sys.stderr)
        return 1

    path: Path = args.image
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1

    data = path.read_bytes()

    async with httpx.AsyncClient() as client:
        body = await fetch_plant_identification_json(client, data)

    if args.raw:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return 0

    parsed = parse_identification_response(body)
    print("--- Plant.id 요약 (파싱 결과) ---")
    print("plant_name (classification 1위):", parsed.get("plant_name"))
    print("confidence:", parsed.get("confidence"))
    print("disease_name (disease 1위):", parsed.get("disease_name"))
    print("is_healthy_prob:", parsed.get("is_healthy_prob"))
    print("top_candidates:", parsed.get("top_candidates"))

    if args.verbose:
        _print_verbose(body)

    print(
        "\n※ health=auto 이면 API가 '건강'으로 보면 disease 블록이 비어 있을 수 있습니다."
        " 항상 질병 후보를 보려면 PLANT_ID_HEALTH=all"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
