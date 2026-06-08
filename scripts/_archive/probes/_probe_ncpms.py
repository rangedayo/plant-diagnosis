"""NCPMS URL 프로브 — 공공데이터 serviceKey는 .env의 RDA_API_KEY 사용."""

# from __future__ import annotations

# import os
# import sys

# import httpx
# from dotenv import load_dotenv

# _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load_dotenv(os.path.join(_ROOT, ".env"))


# def _service_key() -> str:
#     key = os.getenv("RDA_API_KEY", "").strip()
#     if not key:
#         print("오류: .env에 RDA_API_KEY가 없습니다.", file=sys.stderr)
#         sys.exit(1)
#     return key


# def main() -> None:
#     service_key = _service_key()
#     urls = [
#         "http://apis.data.go.kr/1400000/SVC01/getSickBaDetail",
#         "http://apis.data.go.kr/1400000/NCPMS01/getSickBaDetail",
#         "http://apis.data.go.kr/1400000/NCPMS01/getSickBaDetailList",
#     ]
#     for u in urls:
#         try:
#             r = httpx.get(
#                 u,
#                 params={
#                     "serviceKey": service_key,
#                     "pageNo": 1,
#                     "numOfRows": 10
#                 },
#                 timeout=15,
#             )
#             print(u, r.status_code, r.text[:400].replace("\n", " "))
#         except Exception as e:
#             print(u, e)


# if __name__ == "__main__":
#     main()

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("RDA_API_KEY")

url = "http://ncpms.rda.go.kr/npmsAPI/service"

params = {
    "apiKey": key,
    "serviceCode": "SVC01",
    "serviceType": "AA001",
    "displayCount": 10,
    "startPoint": 1,
    "cropName": "벼"  # 필수 조건 (중요)
}

r = httpx.get(url, params=params)

print(r.status_code)
print(r.text[:500])