"""Wikimedia Commons 식물·증상 사진 자동 수집 (메인 평가셋 후보 5장).

사양: docs/eval_collection_spec.md §3

실행 예 (프로젝트 루트에서)::

    python scripts/collect_wikimedia.py \\
        --output-dir test_data/wikimedia_candidates \\
        --per-query 5

라이선스(`extmetadata.LicenseShortName`)는 CC0 / CC BY / CC BY-SA만 허용,
NC·ND·Fair use·non-free 패턴은 제외. ground_truth는 자동 추론하지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "test_data"))
import labeling_vocab as lv  # noqa: E402

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"

WIKIMEDIA_QUERIES: list[str] = [
    "Monstera deliciosa yellowing",
    "Monstera deliciosa root rot",
    "Epipremnum aureum yellow leaves",
    "Epipremnum aureum leaf spot",
    "Sansevieria overwatering",
    "Sansevieria root rot",
    "Ficus elastica leaf drop",
    "Spathiphyllum brown tips",
    "Zamioculcas yellowing",
    "houseplant leaf scorch",
    "houseplant spider mite damage",
    "houseplant powdery mildew leaf",
]

ALLOWED_WIKI_LICENSE_NAMES: set[str] = {
    "CC0", "Public domain",
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
}
EXCLUDED_LICENSE_PATTERNS: tuple[str, ...] = ("NC", "ND", "Fair use", "non-free")

USER_AGENT = (
    "plant-diagnosis-eval/0.1 "
    "(https://github.com/rangedayo/plant-diagnosis; contact via github)"
)

REQUEST_TIMEOUT = 30.0
SLEEP_BETWEEN_CALLS = 0.5
MIN_IMAGE_DIMENSION = 400
SEARCH_LIMIT = 20
THUMB_WIDTH = 800
KST = timezone(timedelta(hours=9))


def _query_slug(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")


def _kst_now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Wikimedia Commons 사진 자동 수집")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_data/wikimedia_candidates"),
        help="출력 디렉토리 (기본 test_data/wikimedia_candidates)",
    )
    p.add_argument(
        "--per-query", type=int, default=5, help="검색어당 수집 사진 수 (기본 5)"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출 없이 검색어 리스트만 출력",
    )
    return p.parse_args()


def _client_headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    token = (os.getenv("WIKIMEDIA_OAUTH_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response | None:
    """5xx -> 2초 backoff 1회 재시도, 429 -> Retry-After 우선 60초 sleep 후 재시도."""
    for attempt in range(2):
        try:
            response = await client.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        except httpx.HTTPError as exc:
            print(f"    HTTP 오류: {exc} (attempt {attempt + 1})")
            await asyncio.sleep(2.0)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() else 60.0
            print(f"    429 받음 → {wait:.0f}s sleep 후 재시도")
            await asyncio.sleep(wait)
            continue
        if 500 <= response.status_code < 600:
            print(f"    {response.status_code} 5xx → 2s backoff 후 재시도")
            await asyncio.sleep(2.0)
            continue
        if response.status_code >= 400:
            print(f"    {response.status_code} 응답 → 스킵")
            return None
        return response
    return None


async def _search_files(client: httpx.AsyncClient, query: str) -> list[str]:
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,
        "srlimit": SEARCH_LIMIT,
    }
    response = await _request_with_retry(client, "GET", WIKIMEDIA_API_URL, params=params)
    if response is None:
        return []
    payload = response.json()
    search_results = (payload.get("query") or {}).get("search") or []
    return [r.get("title", "") for r in search_results if r.get("title")]


async def _fetch_imageinfo(client: httpx.AsyncClient, title: str) -> dict | None:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|user|extmetadata|size",
        "iiurlwidth": THUMB_WIDTH,
    }
    response = await _request_with_retry(client, "GET", WIKIMEDIA_API_URL, params=params)
    if response is None:
        return None
    payload = response.json()
    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if infos:
            return infos[0]
    return None


def _extract_license_name(imageinfo: dict) -> str | None:
    ext = imageinfo.get("extmetadata") or {}
    short = (ext.get("LicenseShortName") or {}).get("value")
    if not short:
        return None
    short = str(short).strip()
    for bad in EXCLUDED_LICENSE_PATTERNS:
        if bad.lower() in short.lower():
            return None
    if short in ALLOWED_WIKI_LICENSE_NAMES:
        return short
    return None


def _extract_photographer(imageinfo: dict) -> str:
    ext = imageinfo.get("extmetadata") or {}
    artist = (ext.get("Artist") or {}).get("value")
    if artist:
        cleaned = re.sub(r"<[^>]+>", "", str(artist)).strip()
        if cleaned:
            return f"Wikimedia User: {cleaned}"
    user = imageinfo.get("user")
    if user:
        return f"Wikimedia User: {user}"
    return "Wikimedia User: Unknown"


async def _download_image(
    client: httpx.AsyncClient, url: str, dest: Path
) -> tuple[int, int] | None:
    response = await _request_with_retry(client, "GET", url)
    if response is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    try:
        with Image.open(dest) as img:
            width, height = img.size
    except Exception as exc:
        print(f"    이미지 열기 실패 ({exc}) → 삭제")
        dest.unlink(missing_ok=True)
        return None
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        print(f"    크기 미달 ({width}x{height}) → 삭제")
        dest.unlink(missing_ok=True)
        return None
    return width, height


async def _collect_for_query(
    client: httpx.AsyncClient,
    query: str,
    per_query: int,
    images_dir: Path,
) -> list[dict]:
    print(f"[1] query={query!r} 검색 시작")
    titles = await _search_files(client, query)
    print(f"    검색 결과 {len(titles)}건")
    await asyncio.sleep(SLEEP_BETWEEN_CALLS)
    if not titles:
        print(f"    경고: {query!r} 검색 결과 없음, 다음 검색어로")
        return []

    slug = _query_slug(query)
    items: list[dict] = []
    sequence = 1

    for title in titles:
        if len(items) >= per_query:
            break

        imageinfo = await _fetch_imageinfo(client, title)
        await asyncio.sleep(SLEEP_BETWEEN_CALLS)
        if imageinfo is None:
            continue

        license_name = _extract_license_name(imageinfo)
        if not license_name:
            continue
        if license_name not in lv.ALLOWED_LICENSES:
            continue

        thumb_url = imageinfo.get("thumburl") or imageinfo.get("url")
        if not thumb_url:
            continue

        descriptionurl = imageinfo.get("descriptionurl") or ""
        filename_original = title.replace("File:", "", 1)

        candidate_id = f"wiki_{slug}_{sequence:03d}"
        image_path = images_dir / f"{candidate_id}.jpg"

        dims = await _download_image(client, thumb_url, image_path)
        if dims is None:
            continue

        photographer = _extract_photographer(imageinfo)
        share_alike = "SA" in license_name

        source: dict = {
            "site": "Wikimedia Commons",
            "url": descriptionurl,
            "photographer": photographer,
            "license": license_name,
        }
        if share_alike:
            source["share_alike"] = True

        items.append({
            "candidate_id": candidate_id,
            "image_path": image_path.as_posix(),
            "source": source,
            "hints": {
                "query_used": query,
                "image_dimensions": [dims[0], dims[1]],
                "filename_original": filename_original,
            },
        })
        sequence += 1

    if len(items) < per_query:
        print(f"    경고: {query!r} 목표 {per_query}장 중 {len(items)}장만 수집")
    else:
        print(f"    {query!r} 수집 완료 ({len(items)}장)")
    return items


def _dry_run_report(per_query: int, output_dir: Path) -> None:
    print("[DRY-RUN] Wikimedia Commons 수집 파라미터")
    print(f"    output_dir = {output_dir}")
    print(f"    per_query  = {per_query}")
    print(f"    queries ({len(WIKIMEDIA_QUERIES)}):")
    for q in WIKIMEDIA_QUERIES:
        print(f"      - {q}")
    print(f"    예상 검색 API 호출 = {len(WIKIMEDIA_QUERIES)}건")
    print(f"    예상 imageinfo 호출 최대 = {len(WIKIMEDIA_QUERIES) * SEARCH_LIMIT}건")
    print(f"    예상 다운로드 최대 = {len(WIKIMEDIA_QUERIES) * per_query}장")


async def async_main(args: argparse.Namespace) -> None:
    load_dotenv()
    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    metadata_path = output_dir / "metadata.json"

    if args.dry_run:
        _dry_run_report(args.per_query, output_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    async with httpx.AsyncClient(headers=_client_headers()) as client:
        for query in WIKIMEDIA_QUERIES:
            query_items = await _collect_for_query(
                client, query, args.per_query, images_dir
            )
            all_items.extend(query_items)

    metadata = {
        "collected_at": _kst_now_iso(),
        "source_site": "Wikimedia Commons",
        "search_params": {
            "queries": WIKIMEDIA_QUERIES,
            "per_query": args.per_query,
        },
        "items": all_items,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[2] 저장 대상 이미지: {len(all_items)} / 목표 {len(WIKIMEDIA_QUERIES) * args.per_query}"
    )
    print(f"[2] metadata.json 작성: {metadata_path}")

    lv.validate_metadata(all_items)


def main() -> None:
    args = _parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
