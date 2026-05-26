"""PlantVillage 50장 보조 평가셋 추출 + 사전 매핑 라벨 생성.

사양: docs/eval_collection_spec.md §4

실행 예 (프로젝트 루트에서)::

    python scripts/prepare_plantvillage.py \\
        --source-dir <PlantVillage 원본 루트> \\
        --output-dir test_data/plantvillage_50 \\
        --total 50 \\
        --seed 42

PlantVillage는 폴더명(<Plant>___<Status>) → 사람이 정의한 `PLANTVILLAGE_LABEL_MAP`
사전 매핑이므로 자동 라벨링 정책의 예외다 (LLM 추론 없음).
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "test_data"))
import labeling_vocab as lv  # noqa: E402

PRIORITY_CLASSES: list[str] = [
    "Tomato___Late_blight",
    "Tomato___Early_blight",
    "Potato___Late_blight",
    "Apple___Apple_scab",
    "Tomato___healthy",
]

PLANTVILLAGE_LABEL_MAP: dict[str, dict] = {
    "Tomato___Late_blight": {
        "plant_name_korean": "토마토",
        "is_healthy": False,
        "symptoms": ["leaf_spots", "leaf_browning"],
        "diagnosis": "토마토 잎마름병 (Late blight)",
    },
    "Tomato___Early_blight": {
        "plant_name_korean": "토마토",
        "is_healthy": False,
        "symptoms": ["leaf_spots"],
        "diagnosis": "토마토 겹무늬병 (Early blight)",
    },
    "Potato___Late_blight": {
        "plant_name_korean": "감자",
        "is_healthy": False,
        "symptoms": ["leaf_spots", "leaf_browning"],
        "diagnosis": "감자 잎마름병 (Late blight)",
    },
    "Apple___Apple_scab": {
        "plant_name_korean": "사과",
        "is_healthy": False,
        "symptoms": ["leaf_spots"],
        "diagnosis": "사과 검은별무늬병 (Apple scab)",
    },
    "Tomato___healthy": {
        "plant_name_korean": "토마토",
        "is_healthy": True,
        "symptoms": [],
        "diagnosis": "정상 상태",
    },
}

PLANTVILLAGE_SOURCE_URL = "https://data.mendeley.com/datasets/tywbtsjrjv/1"
IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")


def _class_slug(class_name: str) -> str:
    return class_name.lower().replace("___", "_")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PlantVillage 50장 추출 + 사전 매핑 라벨링")
    p.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="PlantVillage 데이터셋 루트 (사용자가 Kaggle에서 별도 다운로드)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_data/plantvillage_50"),
        help="출력 디렉토리 (기본 test_data/plantvillage_50)",
    )
    p.add_argument("--total", type=int, default=50, help="추출 총 장수 (기본 50)")
    p.add_argument(
        "--seed", type=int, default=42, help="랜덤 시드 (기본 42, 재현성)"
    )
    return p.parse_args()


def _find_class_dir(source_dir: Path, class_name: str) -> Path | None:
    """source_dir 아래에서 <class_name> 디렉토리를 재귀 탐색."""
    direct = source_dir / class_name
    if direct.is_dir():
        return direct
    for path in source_dir.rglob(class_name):
        if path.is_dir():
            return path
    return None


def _list_images(class_dir: Path) -> list[Path]:
    seen: set[Path] = set()
    for ext in IMAGE_EXTENSIONS:
        for p in class_dir.glob(f"*{ext}"):
            seen.add(p.resolve())
    return sorted(seen)


def _allocate_per_class(total: int, n_classes: int) -> list[int]:
    """클래스별 균등 분배. 나머지는 앞쪽 클래스에 +1."""
    base, rem = divmod(total, n_classes)
    return [base + (1 if i < rem else 0) for i in range(n_classes)]


def _build_label(image_id: str, image_path: Path, class_name: str) -> dict:
    gt_template = PLANTVILLAGE_LABEL_MAP[class_name]
    return {
        "image_id": image_id,
        "image_path": image_path.as_posix(),
        "ground_truth": {
            "plant_name_korean": gt_template["plant_name_korean"],
            "is_healthy": gt_template["is_healthy"],
            "symptoms": list(gt_template["symptoms"]),
            "diagnosis": gt_template["diagnosis"],
        },
        "source": {
            "site": "PlantVillage",
            "url": PLANTVILLAGE_SOURCE_URL,
            "photographer": "PlantVillage Dataset",
            "license": "CC0",
        },
    }


def _sample_for_class(
    source_dir: Path,
    class_name: str,
    target: int,
    rng: random.Random,
    images_dir: Path,
) -> list[dict]:
    class_dir = _find_class_dir(source_dir, class_name)
    if class_dir is None:
        print(f"    경고: 클래스 디렉토리 미발견 → {class_name}")
        return []

    images = _list_images(class_dir)
    if not images:
        print(f"    경고: {class_name} 이미지 0개")
        return []

    if len(images) < target:
        print(f"    경고: {class_name} 가용 {len(images)}장 < 목표 {target}장")
        target = len(images)

    sampled = rng.sample(images, target)
    slug = _class_slug(class_name)
    labels: list[dict] = []
    for offset, src_path in enumerate(sampled, start=1):
        image_id = f"pv_{slug}_{offset:03d}"
        dst_path = images_dir / f"{image_id}.jpg"
        shutil.copyfile(src_path, dst_path)
        labels.append(_build_label(image_id, dst_path, class_name))
    print(f"    {class_name}: {len(labels)}장 복사")
    return labels


def _redistribute_shortfall(
    quota: list[int], available_per_class: list[int]
) -> list[int]:
    """클래스 N의 가용량이 부족하면 다른 클래스로 라운드로빈 재분배."""
    adjusted = list(quota)
    for i, avail in enumerate(available_per_class):
        if adjusted[i] > avail:
            shortfall = adjusted[i] - avail
            adjusted[i] = avail
            j = 0
            guard = len(adjusted) * 100
            while shortfall > 0 and j < guard:
                idx = j % len(adjusted)
                if idx != i and adjusted[idx] < available_per_class[idx]:
                    adjusted[idx] += 1
                    shortfall -= 1
                j += 1
            if shortfall > 0:
                print(
                    f"    경고: 재분배 후에도 {shortfall}장 부족 (총 가용량 부족)"
                )
    return adjusted


def main() -> None:
    args = _parse_args()
    source_dir: Path = args.source_dir
    output_dir: Path = args.output_dir
    total: int = args.total
    seed: int = args.seed

    if not source_dir.is_dir():
        print(
            f"오류: --source-dir 경로가 디렉토리가 아닙니다: {source_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    images_dir = output_dir / "images"
    labels_path = output_dir / "labels.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    print(f"[1] PlantVillage 추출 (seed={seed}, total={total})")
    print(f"    우선순위 클래스 {len(PRIORITY_CLASSES)}개: {PRIORITY_CLASSES}")

    available: list[int] = []
    for cls in PRIORITY_CLASSES:
        d = _find_class_dir(source_dir, cls)
        n = len(_list_images(d)) if d else 0
        available.append(n)
        print(f"    가용 {cls}: {n}장")

    quota = _allocate_per_class(total, len(PRIORITY_CLASSES))
    print(f"    초기 분배: {dict(zip(PRIORITY_CLASSES, quota))}")
    quota = _redistribute_shortfall(quota, available)
    print(f"    조정 분배: {dict(zip(PRIORITY_CLASSES, quota))}")

    all_labels: list[dict] = []
    for cls, target in zip(PRIORITY_CLASSES, quota):
        if target <= 0:
            continue
        labels = _sample_for_class(source_dir, cls, target, rng, images_dir)
        all_labels.extend(labels)

    labels_path.write_text(
        json.dumps(all_labels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[2] labels.json 작성: {labels_path}")
    print(f"[2] 총 라벨 수: {len(all_labels)} (목표 {total})")

    lv.validate_dataset(all_labels)


if __name__ == "__main__":
    main()
