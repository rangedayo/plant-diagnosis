"""여러 serviceCode로 상세 응답 시도 (sickKey 고정)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

URL = "http://ncpms.rda.go.kr/npmsAPI/service"


async def main() -> None:
    key = (os.getenv("RDA_API_KEY") or "").strip()
    if not key:
        print("NO KEY", file=sys.stderr)
        sys.exit(1)
    sick_key = "D00000007"
    async with httpx.AsyncClient() as client:
        for svc in [
            "SVC02",
            "SVC03",
            "SVC04",
            "SVC05",
            "SVC42",
            "SVC43",
        ]:
            r = await client.get(
                URL,
                params={
                    "apiKey": key,
                    "serviceCode": svc,
                    "serviceType": "AA001",
                    "sickKey": sick_key,
                },
                timeout=60.0,
            )
            head = r.text[:800].replace("\n", " ")
            print(svc, r.status_code, len(r.text), head)


if __name__ == "__main__":
    asyncio.run(main())
