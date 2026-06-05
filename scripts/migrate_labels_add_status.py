"""main_eval 라벨에 true_status(5-status 정답) 키를 추가하는 마이그레이션.

설계: docs/design/design_accuracy_track.md §4 결정4 · §7-1
성격: 평가셋 라벨 스키마 R1 — true_status 추가 (진단/프론트 무관).

동작:
    - is_healthy == True  → true_status = "건강"  (정합성 규칙상 유일 해, 자동 채움)
    - is_healthy == False → true_status = "TODO"  (사람이 다음 라운드에 채움. 추론 금지)
    - 이미 true_status가 있는 항목은 건너뜀(멱등, 재실행 안전).
    - 덮어쓰기 전 타임스탬프 백업(`labels.<ts>.bak.json`, gitignore 대상) 생성.

자동화 경계:
    - is_healthy=False 항목의 true_status를 symptoms/diagnosis/이미지로부터 추론하지 않는다.
    - LLM/Vision API 호출 없음.

실행 예 (프로젝트 루트에서)::

    python scripts/migrate_labels_add_status.py --dry-run
    python scripts/migrate_labels_add_status.py
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = _ROOT / "test_data" / "main_eval" / "labels.json"

HEALTHY_STATUS = "건강"
TODO_STATUS = "TODO"


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"labels.json 형식 오류 또는 빈 배열: {path}")
    return data


def migrate(labels: list[dict]) -> tuple[list[dict], int, list[str], int]:
    """true_status를 채운 새 리스트를 반환(원본 비파괴).

    Returns:
        (updated, auto_filled, todo_ids, skipped)
        - updated: true_status가 채워진 라벨 리스트
        - auto_filled: is_healthy=True → "건강" 자동 채움 건수
        - todo_ids: is_healthy=False → "TODO"가 된 image_id 목록(사람이 채울 대상)
        - skipped: 이미 true_status가 있어 건너뛴 건수
    """
    auto_filled = 0
    todo_ids: list[str] = []
    skipped = 0
    updated: list[dict] = []

    for label in labels:
        gt = label["ground_truth"]
        if "true_status" in gt:
            skipped += 1
            updated.append(label)
            continue

        new_gt = dict(gt)
        if gt["is_healthy"]:
            new_gt["true_status"] = HEALTHY_STATUS
            auto_filled += 1
        else:
            new_gt["true_status"] = TODO_STATUS
            todo_ids.append(label["image_id"])

        new_label = dict(label)
        new_label["ground_truth"] = new_gt
        updated.append(new_label)

    return updated, auto_filled, todo_ids, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="main_eval 라벨에 true_status(5-status 정답) 추가"
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
    updated, auto_filled, todo_ids, skipped = migrate(labels)

    mode = "dry-run" if args.dry_run else "WRITE"
    print(f"=== migrate_labels_add_status ({mode}) ===")
    print(f"대상: {args.labels} (총 {len(labels)}장)")
    print(f"자동 채움(건강): {auto_filled}")
    print(f"TODO(비건강, 사람이 채울 자리): {len(todo_ids)}")
    for tid in todo_ids:
        print(f"  - {tid}")
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
