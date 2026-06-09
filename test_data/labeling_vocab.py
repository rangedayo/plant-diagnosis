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

# 3단 심각도 tier (건강/경미/비건강). is_healthy 이진 위에 얹는 차원으로,
# R15에서 도입. 건강·경미 → is_healthy=True, 비건강 → is_healthy=False.
TIER_VOCAB: list[str] = ["건강", "경미", "비건강"]

# 5-status 정답 라벨용 enum (app/model_utils.py ALLOWED_STRUCT_STATUS와 동일 5종)
STATUS_VOCAB: list[str] = ["건강", "과습", "건조", "병해 의심", "영양 부족"]

# 경미 tier 전용 true_status. STATUS_VOCAB(5종) 밖이라 run_eval 5-status 혼동표에서
# 자동 skip되고(build_status_confusion_matrix), 이진에선 is_healthy=True → 건강 취급.
# STATUS_VOCAB 5종 계약(= ALLOWED_STRUCT_STATUS)을 깨지 않기 위해 분리 상수로 둔다.
STATUS_MILD: str = "경미"

# 사람이 잎 사진만으로 5종 판정이 곤란한 케이스 → 평가에서 제외
STATUS_AMBIGUOUS: str = "ambiguous"

# 비건강은 확실하나 잎 사진만으로 원인(과습/건조/병해/영양) 단정이 곤란한 케이스.
# is_healthy 평가엔 비건강으로 포함하되, 5-status 혼동표에서는 중립 제외된다
# (STATUS_VOCAB 밖이라 build_status_confusion_matrix가 자동 skip). 건강/비건강 자체가
# 불명한 STATUS_AMBIGUOUS와 구분된다(이쪽은 비건강이 확실).
STATUS_UNKNOWN_CAUSE: str = "비건강-원인미상"

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
    required = {"plant_name_korean", "is_healthy", "symptoms", "diagnosis", "true_status", "tier"}
    missing = required - gt.keys()
    if missing:
        raise ValueError(f"{label['image_id']}: ground_truth 누락 필드 {missing}")

    if not gt["is_healthy"] and not gt["symptoms"]:
        raise ValueError(f"{label['image_id']}: unhealthy인데 symptoms 없음")

    for s in gt["symptoms"]:
        if s not in SYMPTOM_VOCAB:
            raise ValueError(f"{label['image_id']}: 알 수 없는 증상 {s}")

    # tier enum 검증
    tier = gt["tier"]
    if tier not in TIER_VOCAB:
        raise ValueError(f"{label['image_id']}: 알 수 없는 tier {tier!r} (허용: {TIER_VOCAB})")

    # true_status enum 검증 (TODO 등 미기입 값은 여기서 ValueError → "사람이 채울 자리" 게이트)
    true_status = gt["true_status"]
    if true_status not in STATUS_VOCAB and true_status not in (
        STATUS_MILD,
        STATUS_AMBIGUOUS,
        STATUS_UNKNOWN_CAUSE,
    ):
        allowed = STATUS_VOCAB + [STATUS_MILD, STATUS_AMBIGUOUS, STATUS_UNKNOWN_CAUSE]
        raise ValueError(
            f"{label['image_id']}: 알 수 없는 true_status {true_status!r} (허용: {allowed})"
        )

    # tier ↔ is_healthy 정합성: 비건강만 is_healthy=False, 건강·경미는 True.
    if tier == "비건강" and gt["is_healthy"]:
        raise ValueError(f"{label['image_id']}: tier='비건강'인데 is_healthy=True (정합성 위반)")
    if tier in ("건강", "경미") and not gt["is_healthy"]:
        raise ValueError(f"{label['image_id']}: tier={tier!r}인데 is_healthy=False (정합성 위반)")

    # tier ↔ true_status 정합성: 건강→"건강", 경미→경미, 비건강→원인(5종 중 건강 제외)·원인미상.
    if tier == "건강" and true_status != "건강":
        raise ValueError(
            f"{label['image_id']}: tier='건강'인데 true_status={true_status!r} (정합성 위반)"
        )
    if tier == "경미" and true_status != STATUS_MILD:
        raise ValueError(
            f"{label['image_id']}: tier='경미'인데 true_status={true_status!r} (정합성 위반)"
        )
    if tier == "비건강":
        unhealthy_causes = [s for s in STATUS_VOCAB if s != "건강"] + [STATUS_UNKNOWN_CAUSE]
        if true_status not in unhealthy_causes:
            raise ValueError(
                f"{label['image_id']}: tier='비건강'인데 true_status={true_status!r} "
                f"(허용 원인: {unhealthy_causes})"
            )


def validate_dataset(labels: list[dict]) -> dict:
    """전체 데이터셋 검증 + 통계 리포트 출력.

    단건 ValueError를 모아 어떤 image_id가 실패했는지 함께 보여준다
    (true_status 미기입/TODO 항목을 한 번에 드러내는 게이트). 실패가 하나라도
    있으면 분포 리포트를 출력한 뒤 ValueError를 던진다.
    """
    errors: list[str] = []
    for label in labels:
        try:
            validate_label(label)
        except ValueError as e:
            errors.append(str(e))

    n = len(labels)
    n_healthy = sum(1 for label in labels if label["ground_truth"]["is_healthy"])
    symptom_counts: dict[str, int] = {}
    plant_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for label in labels:
        gt = label["ground_truth"]
        for s in gt.get("symptoms", []):
            symptom_counts[s] = symptom_counts.get(s, 0) + 1
        p = gt.get("plant_name_korean", "(없음)")
        plant_counts[p] = plant_counts.get(p, 0) + 1
        ts = gt.get("true_status", "(없음)")
        status_counts[ts] = status_counts.get(ts, 0) + 1

    report = {
        "total": n,
        "healthy_ratio": n_healthy / n if n else 0,
        "symptom_distribution": symptom_counts,
        "plant_distribution": plant_counts,
        "true_status_distribution": status_counts,
    }
    print("=== Dataset validation report ===")
    print(f"Total: {n}, Healthy: {n_healthy} ({report['healthy_ratio']:.1%})")
    print(f"Plant distribution: {plant_counts}")
    print(f"Symptom distribution: {symptom_counts}")
    print(f"true_status distribution: {status_counts}")

    if errors:
        print(f"=== Validation FAILED: {len(errors)} label(s) ===")
        for msg in errors:
            print(f"  - {msg}")
        raise ValueError(f"{len(errors)} label(s) failed validation: " + "; ".join(errors))

    print("=== All labels valid ===")
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
