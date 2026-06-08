"""plantvillage_50 보조 평가셋 라벨에 true_status(5-status 정답)를 추가하는 마이그레이션.

설계: docs/work_history/ACC-R4_run_eval확장+plantvillage사전매핑.md
성격: 보조 평가셋 라벨 스키마 정비 (진단/프론트 무관, LLM/Vision 호출 없음).

동작:
    - test_data/plantvillage_50/labels.json 을 utf-8-sig 로 로드.
    - 각 항목의 image_id 슬러그(pv_<slug>_<NNN>)에서 PlantVillage 클래스를 역추출,
      prepare_plantvillage.PLANTVILLAGE_STATUS_MAP(사람 정의 사전매핑)로 true_status 결정.
    - 이미 true_status가 있는 항목은 건너뜀(멱등, 재실행 안전).
    - 매핑 표에 없는 슬러그 발견 시 즉시 중단·보고(안전망 — Step 1에서 다 잡혔어야 함).
    - 덮어쓰기 전 타임스탬프 백업(`labels.<ts>.bak.json`, gitignore 대상) 생성.

자동화 경계 (§9 예외):
    - true_status는 사람이 정의한 PLANTVILLAGE_STATUS_MAP dict에서만 온다. LLM 추론 없음.

실행 예 (프로젝트 루트에서)::

    python scripts/migrate_plantvillage_add_status.py --dry-run
    python scripts/migrate_plantvillage_add_status.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
LABELS_PATH = _ROOT / "test_data" / "plantvillage_50" / "labels.json"

# prepare_plantvillage 의 사전매핑·슬러그 규칙을 단일 출처로 재사용 (DRY).
sys.path.insert(0, str(_SCRIPTS))
from prepare_plantvillage import (  # noqa: E402
    PLANTVILLAGE_STATUS_MAP,
    _class_slug,
)

# full class명 → 슬러그(image_id에 박힌 형태)로 변환한 사전매핑.
SLUG_TO_STATUS: dict[str, str] = {
    _class_slug(cls): status for cls, status in PLANTVILLAGE_STATUS_MAP.items()
}


def _slug_from_image_id(image_id: str) -> str:
    """``pv_<slug>_<NNN>`` 에서 <slug> 추출. 접두 ``pv_`` + 말미 ``_숫자`` 제거."""
    core = image_id[3:] if image_id.startswith("pv_") else image_id
    return core.rsplit("_", 1)[0]


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"labels.json 형식 오류 또는 빈 배열: {path}")
    return data


def migrate(labels: list[dict]) -> tuple[list[dict], int, dict[str, int], int]:
    """true_status를 채운 새 리스트를 반환(원본 비파괴).

    Returns:
        (updated, filled, status_dist, skipped)
        - updated: true_status가 채워진 라벨 리스트
        - filled: 이번에 true_status를 새로 박은 건수
        - status_dist: 새로 박은 true_status 분포
        - skipped: 이미 true_status가 있어 건너뛴 건수
    Raises:
        SystemExit: 매핑 표에 없는 슬러그를 만나면 즉시 중단(안전망).
    """
    filled = 0
    skipped = 0
    status_dist: dict[str, int] = {}
    updated: list[dict] = []
    unknown: list[str] = []

    for label in labels:
        gt = label["ground_truth"]
        if "true_status" in gt:
            skipped += 1
            updated.append(label)
            continue

        slug = _slug_from_image_id(label["image_id"])
        status = SLUG_TO_STATUS.get(slug)
        if status is None:
            unknown.append(f"{label['image_id']} (slug={slug!r})")
            updated.append(label)
            continue

        new_gt = dict(gt)
        new_gt["true_status"] = status
        new_label = dict(label)
        new_label["ground_truth"] = new_gt
        updated.append(new_label)
        filled += 1
        status_dist[status] = status_dist.get(status, 0) + 1

    if unknown:
        raise SystemExit(
            "매핑 표에 없는 PlantVillage 슬러그 발견 → 중단. "
            "PLANTVILLAGE_STATUS_MAP에 추가 후 재실행:\n  - "
            + "\n  - ".join(unknown)
        )

    return updated, filled, status_dist, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="plantvillage_50 라벨에 true_status(5-status 정답) 추가"
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=LABELS_PATH,
        help=f"대상 labels.json (기본: {LABELS_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일을 쓰지 않고 통계만 출력",
    )
    args = parser.parse_args()

    labels = _load(args.labels)
    updated, filled, status_dist, skipped = migrate(labels)

    mode = "dry-run" if args.dry_run else "WRITE"
    print(f"=== migrate_plantvillage_add_status ({mode}) ===")
    print(f"대상: {args.labels} (총 {len(labels)}장)")
    print(f"새로 채움: {filled}  (분포: {status_dist})")
    print(f"건너뜀(이미 true_status 있음): {skipped}")

    if args.dry_run:
        print("[dry-run] 파일을 변경하지 않았습니다.")
        return

    if skipped == len(labels):
        print("모든 항목에 이미 true_status가 있습니다. 변경 없음.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = args.labels.with_name(f"labels.{ts}.bak.json")
    backup.write_bytes(args.labels.read_bytes())
    print(f"백업 생성: {backup}")

    with args.labels.open("w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"마이그레이션 완료: {args.labels} (true_status 추가)")


if __name__ == "__main__":
    main()
