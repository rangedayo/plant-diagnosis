"""평가셋 라벨링 공통 모듈.

- Task 1, 2 수집 스크립트의 metadata.json 검증 (`validate_metadata`)
- Task 3 PlantVillage 사전 매핑 라벨 / 메인 평가셋 라벨 검증
  (`validate_label`, `validate_dataset`)
- 증상/식물명/라이선스 공통 어휘

수동 라벨링과 자동 수집 스크립트 모두에서 import 해 쓴다.
"""
from __future__ import annotations

SYMPTOM_VOCAB: list[str] = [
    "leaf_yellowing",   # 잎 황변
    "leaf_browning",    # 잎 갈변
    "leaf_droop",       # 잎 처짐
    "leaf_spots",       # 잎 반점
    "leaf_holes",       # 잎 구멍
    "leaf_edge_dry",    # 잎 끝 마름
    "wet_soil",         # 흙 과습
    "dry_soil",         # 흙 건조
    "pests_visible",    # 해충
    "white_powder",     # 흰가루병
    "leggy_growth",     # 웃자람
    "leaf_pale",        # 잎 색 옅음
]

PLANT_NAME_KO_MAP: dict[str, str] = {
    "Monstera deliciosa": "몬스테라",
    "Epipremnum aureum": "스킨답서스",
    "Sansevieria trifasciata": "산세베리아",
    "Dracaena trifasciata": "산세베리아",  # 산세베리아 현재 학명(=Sansevieria trifasciata)
    "Ficus elastica": "고무나무",
    "Spathiphyllum": "스파티필름",
    "Spathiphyllum wallisii": "스파티필름",
    "Zamioculcas zamiifolia": "금전수",
    "Chlorophytum comosum": "접란",
    "Pilea peperomioides": "필레아",
    "Aglaonema modestum": "아글라오네마",
    "Aglaonema commutatum": "아글라오네마",
    "Dracaena fragrans": "행운목",
    "Dracaena reflexa": "드라세나 송 오브 인디아",
    "Dracaena": "드라세나",
}

ALLOWED_LICENSES: set[str] = {
    "CC0", "Public domain", "self_owned",
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
}


def validate_label(label: dict) -> None:
    """단건 라벨 검증, 위반 시 ValueError."""
    if "image_id" not in label or "ground_truth" not in label:
        raise ValueError(f"필수 필드 누락: {label}")

    gt = label["ground_truth"]
    required = {"plant_name_korean", "is_healthy", "symptoms", "diagnosis"}
    missing = required - gt.keys()
    if missing:
        raise ValueError(f"{label['image_id']}: ground_truth 누락 필드 {missing}")

    if not gt["is_healthy"] and not gt["symptoms"]:
        raise ValueError(f"{label['image_id']}: unhealthy인데 symptoms 없음")

    for s in gt["symptoms"]:
        if s not in SYMPTOM_VOCAB:
            raise ValueError(f"{label['image_id']}: 알 수 없는 증상 {s}")


def validate_dataset(labels: list[dict]) -> dict:
    """전체 데이터셋 검증 + 통계 리포트 출력."""
    for label in labels:
        validate_label(label)

    n = len(labels)
    n_healthy = sum(1 for label in labels if label["ground_truth"]["is_healthy"])
    symptom_counts: dict[str, int] = {}
    plant_counts: dict[str, int] = {}
    for label in labels:
        for s in label["ground_truth"]["symptoms"]:
            symptom_counts[s] = symptom_counts.get(s, 0) + 1
        p = label["ground_truth"]["plant_name_korean"]
        plant_counts[p] = plant_counts.get(p, 0) + 1

    report = {
        "total": n,
        "healthy_ratio": n_healthy / n if n else 0,
        "symptom_distribution": symptom_counts,
        "plant_distribution": plant_counts,
    }
    print("=== Dataset validation passed ===")
    print(f"Total: {n}, Healthy: {n_healthy} ({report['healthy_ratio']:.1%})")
    print(f"Plant distribution: {plant_counts}")
    print(f"Symptom distribution: {symptom_counts}")
    return report


def validate_metadata(items: list[dict]) -> None:
    """수집 단계(Task 1, 2)의 metadata.json 검증."""
    seen_ids: set[str] = set()
    for item in items:
        cid = item.get("candidate_id")
        if not cid:
            raise ValueError(f"candidate_id 누락: {item}")
        if cid in seen_ids:
            raise ValueError(f"중복 candidate_id: {cid}")
        seen_ids.add(cid)

        path = item.get("image_path")
        if not path:
            raise ValueError(f"{cid}: image_path 누락")

        src = item.get("source", {})
        license_name = src.get("license")
        if not license_name:
            raise ValueError(f"{cid}: license 누락")
        if license_name not in ALLOWED_LICENSES:
            raise ValueError(f"{cid}: 허용되지 않은 라이선스 {license_name}")

    print(f"=== Metadata validation passed: {len(items)} items ===")
