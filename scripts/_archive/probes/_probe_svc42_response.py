"""SVC42 실제 응답 로그 출력 (1회성 프로브 — build_rag_db 설계용)."""

from __future__ import annotations

import asyncio
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

NCPMS_SERVICE_URL = "http://ncpms.rda.go.kr/npmsAPI/service"


def _local_tag(tag: str | None) -> str:
    if not tag:
        return ""
    return tag.split("}", 1)[1] if "}" in tag else tag


async def main() -> None:
    key = (os.getenv("RDA_API_KEY") or "").strip()
    if not key:
        print("오류: RDA_API_KEY 없음", file=sys.stderr)
        sys.exit(1)

    async with httpx.AsyncClient() as client:
        r1 = await client.get(
            NCPMS_SERVICE_URL,
            params={
                "apiKey": key,
                "serviceCode": "SVC01",
                "serviceType": "AA001",
                "sickNameKor": "병",
            },
            timeout=120.0,
        )
        print("=== SVC01 HTTP", r1.status_code, "bytes", len(r1.text))
        print("=== SVC01 (처음 2000자) ===")
        print(r1.text[:2000])
        r1.raise_for_status()

        root = ET.fromstring(r1.text)
        sick_key: str | None = None
        for el in root.iter():
            if _local_tag(el.tag) == "sickKey" and el.text and el.text.strip():
                sick_key = el.text.strip()
                break
        print("=== 첫 sickKey ===", sick_key)
        if not sick_key:
            sys.exit(1)

        for st in ("AA001", "AA002"):
            r42 = await client.get(
                NCPMS_SERVICE_URL,
                params={
                    "apiKey": key,
                    "serviceCode": "SVC42",
                    "serviceType": st,
                    "sickKey": sick_key,
                },
                timeout=120.0,
            )
            print(f"\n=== SVC42 serviceType={st!r} HTTP {r42.status_code} bytes {len(r42.text)} ===")
            print(r42.text)


if __name__ == "__main__":
    asyncio.run(main())
