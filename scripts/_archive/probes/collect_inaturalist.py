"""iNaturalist 관찰 사진 자동 수집 (메인 평가셋 후보 5장).

사양: docs/eval_collection_spec.md §2

실행 예 (프로젝트 루트에서)::

    python scripts/collect_inaturalist.py \\
        --output-dir test_data/inaturalist_candidates \\
        --per-taxon 5 \\
        --min-short-side 400

각 사진은 medium → large → original 순으로 시도해 짧은 변이
`--min-short-side` 이상인 첫 variant를 채택한다.

이미지·라이선스·관찰 메타데이터까지만 수집하며,
plant_name_korean/is_healthy/symptoms/diagnosis 같은 ground_truth는
사람이 후보 풀에서 검수·수동 라벨링 단계에서 채운다 (자동 라벨링 금지).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "test_data"))
import labeling_vocab as lv  # noqa: E402

INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
INAT_TAXA_URL = "https://api.inaturalist.org/v1/taxa"

TAXA_LIST: list[str] = [
    "Monstera deliciosa",
    "Epipremnum aureum",
    "Sansevieria trifasciata",
    "Ficus elastica",
    "Spathiphyllum",
    "Zamioculcas zamiifolia",
    "Chlorophytum comosum",
    "Pilea peperomioides",
]

LICENSE_CODE_MAP: dict[str, str] = {
    "cc0": "CC0",
    "cc-by": "CC BY 4.0",
    "cc-by-sa": "CC BY-SA 4.0",
}

VARIANT_ORDER: tuple[str, ...] = ("medium", "large", "original")

REQUEST_TIMEOUT = 30.0
SLEEP_BETWEEN_TAXA = 1.0
DEFAULT_MIN_SHORT_SIDE = 400
KST = timezone(timedelta(hours=9))


def _taxon_slug(scientific_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", scientific_name.lower()).strip("_")


def _kst_now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def _variant_url(square_url: str, variant: str) -> str:
    return square_url.replace("/square.", f"/{variant}.")


def _license_to_name(code: str | None) -> str | None:
    if not code:
        return None
    return LICENSE_CODE_MAP.get(code.lower())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="iNaturalist 관찰 사진 자동 수집")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_data/inaturalist_candidates"),
        help="출력 디렉토리 (기본 test_data/inaturalist_candidates)",
    )
    p.add_argument("--per-taxon", type=int, default=5, help="종당 수집 사진 수 (기본 5)")
    p.add_argument(
        "--min-short-side",
        type=int,
        default=DEFAULT_MIN_SHORT_SIDE,
        help=(
            "이미지 짧은 변의 최소 픽셀 (기본 400). "
            "medium → large → original 순으로 첫 통과 variant를 채택."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출 없이 파라미터와 예상 호출 수만 출력",
    )
    p.add_argument(
        "--taxa-only",
        type=str,
        default=None,
        help='특정 종만 수집 (콤마 구분, 예: "Monstera deliciosa,Epipremnum aureum")',
    )
    return p.parse_args()


def _select_taxa(taxa_only: str | None) -> list[str]:
    if not taxa_only:
        return TAXA_LIST
    return [t.strip() for t in taxa_only.split(",") if t.strip()]


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


async def _fetch_observations(
    client: httpx.AsyncClient,
    taxon_name: str | None = None,
    taxon_id: int | None = None,
) -> list[dict]:
    params: dict[str, str | int] = {
        "photo_license": "cc0,cc-by",
        "quality_grade": "research",
        "photos": "true",
        "per_page": 30,
        "order_by": "votes",
    }
    if taxon_id is not None:
        params["taxon_id"] = taxon_id
    elif taxon_name is not None:
        params["taxon_name"] = taxon_name
    else:
        return []

    response = await _request_with_retry(client, "GET", INAT_OBSERVATIONS_URL, params=params)
    if response is None:
        return []
    payload = response.json()
    return payload.get("results", []) or []


async def _fetch_fallback_taxon_id(
    client: httpx.AsyncClient, scientific_name: str
) -> int | None:
    params = {"q": scientific_name, "rank": "species,genus", "per_page": 1}
    response = await _request_with_retry(client, "GET", INAT_TAXA_URL, params=params)
    if response is None:
        return None
    payload = response.json()
    results = payload.get("results") or []
    if not results:
        return None
    return results[0].get("id")


async def _download_to_path(
    client: httpx.AsyncClient, url: str, dest: Path
) -> tuple[int, int] | None:
    """단일 URL 다운로드 + PIL 크기 측정. 실패 시 dest 삭제 후 None."""
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
    return width, height


async def _download_with_variant_fallback(
    client: httpx.AsyncClient,
    square_url: str,
    dest: Path,
    min_short_side: int,
) -> tuple[int, int, str] | None:
    """medium → large → original 순서로 시도, 짧은 변이 min_short_side 이상인 첫 variant 채택."""
    for variant in VARIANT_ORDER:
        url = _variant_url(square_url, variant)
        dims = await _download_to_path(client, url, dest)
        if dims is None:
            continue
        width, height = dims
        short_side = min(width, height)
        if short_side >= min_short_side:
            return width, height, variant
        print(
            f"    variant={variant} 크기 미달 ({width}x{height}, short={short_side}) → 다음 variant"
        )
        dest.unlink(missing_ok=True)
    return None


def _extract_first_photo(observation: dict) -> tuple[str, str, str | None] | None:
    """observation -> (square_url, license_name, photographer). 라이선스 누락/불허 시 None."""
    photos = observation.get("photos") or []
    if not photos:
        return None
    photo = photos[0]
    url = photo.get("url")
    if not url:
        return None
    license_code = photo.get("license_code")
    license_name = _license_to_name(license_code)
    if not license_name:
        return None
    if license_name not in lv.ALLOWED_LICENSES:
        return None
    user = observation.get("user") or {}
    photographer = user.get("login") or user.get("name")
    return url, license_name, photographer


async def _collect_for_taxon(
    client: httpx.AsyncClient,
    scientific_name: str,
    per_taxon: int,
    images_dir: Path,
    min_short_side: int,
) -> list[dict]:
    print(f"[1] 학명={scientific_name!r} 수집 시작")
    observations = await _fetch_observations(client, taxon_name=scientific_name)
    print(f"    taxon_name 결과 {len(observations)}건")
    if not observations:
        print("    fallback: taxa 검색 -> taxon_id 재호출")
        taxon_id = await _fetch_fallback_taxon_id(client, scientific_name)
        if taxon_id is None:
            print(f"    경고: {scientific_name} taxon 미발견, 스킵")
            return []
        observations = await _fetch_observations(client, taxon_id=taxon_id)
        print(f"    taxon_id={taxon_id} 결과 {len(observations)}건")
        if not observations:
            print(f"    경고: {scientific_name} 관찰 0건, 다음 종으로")
            return []

    slug = _taxon_slug(scientific_name)
    common_guess = lv.PLANT_NAME_KO_MAP.get(scientific_name)
    if common_guess is None:
        genus = scientific_name.split()[0]
        common_guess = lv.PLANT_NAME_KO_MAP.get(genus)

    items: list[dict] = []
    sequence = 1

    for obs in observations:
        if len(items) >= per_taxon:
            break
        extracted = _extract_first_photo(obs)
        if extracted is None:
            continue
        square_url, license_name, photographer = extracted

        candidate_id = f"inat_{slug}_{sequence:03d}"
        image_path = images_dir / f"{candidate_id}.jpg"

        resolved = await _download_with_variant_fallback(
            client, square_url, image_path, min_short_side
        )
        if resolved is None:
            print(f"    obs={obs.get('id')} 모든 variant 크기 미달 → 스킵")
            continue
        width, height, variant = resolved

        obs_id = obs.get("id")
        obs_url = (
            f"https://www.inaturalist.org/observations/{obs_id}" if obs_id else square_url
        )

        items.append({
            "candidate_id": candidate_id,
            "image_path": image_path.as_posix(),
            "source": {
                "site": "iNaturalist",
                "url": obs_url,
                "photographer": photographer or "Unknown",
                "license": license_name,
            },
            "hints": {
                "scientific_name": scientific_name,
                "common_name_guess": common_guess,
                "observation_location": obs.get("place_guess"),
                "image_dimensions": [width, height],
                "resolved_size": [width, height],
                "resolved_variant": variant,
            },
        })
        sequence += 1

    if len(items) < per_taxon:
        print(f"    경고: {scientific_name} 목표 {per_taxon}장 중 {len(items)}장만 수집")
    else:
        print(f"    {scientific_name} 수집 완료 ({len(items)}장)")
    return items


def _dry_run_report(
    taxa: list[str], per_taxon: int, min_short_side: int, output_dir: Path
) -> None:
    print("[DRY-RUN] iNaturalist 수집 파라미터")
    print(f"    output_dir       = {output_dir}")
    print(f"    per_taxon        = {per_taxon}")
    print(f"    min_short_side   = {min_short_side}")
    print(f"    variant_order    = {list(VARIANT_ORDER)}")
    print(f"    taxa ({len(taxa)}): {taxa}")
    print(f"    photo_license    = cc0,cc-by")
    print(f"    quality_grade    = research")
    print(f"    per_page         = 30 (후보 풀)")
    print(f"    예상 API 호출 수 = 본 {len(taxa)}건 (+ fallback 최대 {len(taxa)}건)")
    print(
        f"    예상 다운로드 수 = 최대 {len(taxa) * per_taxon}장 "
        f"(채택 variant당 1회, 미달 시 다음 variant까지 최대 {len(VARIANT_ORDER)}회/사진)"
    )


async def async_main(args: argparse.Namespace) -> None:
    taxa = _select_taxa(args.taxa_only)
    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    metadata_path = output_dir / "metadata.json"

    if args.dry_run:
        _dry_run_report(taxa, args.per_taxon, args.min_short_side, output_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    async with httpx.AsyncClient(headers={"User-Agent": "plant-diagnosis-eval/0.1"}) as client:
        for i, scientific_name in enumerate(taxa):
            taxon_items = await _collect_for_taxon(
                client,
                scientific_name,
                args.per_taxon,
                images_dir,
                args.min_short_side,
            )
            all_items.extend(taxon_items)
            if i < len(taxa) - 1:
                await asyncio.sleep(SLEEP_BETWEEN_TAXA)

    metadata = {
        "collected_at": _kst_now_iso(),
        "source_site": "iNaturalist",
        "search_params": {
            "license_filter": ["cc0", "cc-by"],
            "quality_grade": "research",
            "per_taxon": args.per_taxon,
            "min_short_side": args.min_short_side,
            "variant_order": list(VARIANT_ORDER),
        },
        "items": all_items,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[2] 저장 대상 이미지: {len(all_items)} / 목표 {len(taxa) * args.per_taxon}")
    print(f"[2] metadata.json 작성: {metadata_path}")

    lv.validate_metadata(all_items)


def main() -> None:
    args = _parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
