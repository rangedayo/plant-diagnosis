"""R12a run3 위생 진단(read-only·무과금): 파싱 실패 3건 429 vs 진짜 파싱실패 분류."""
import json

RUNS = {
    "run1": "eval/eval/after_acc_r12a_veto_run1.json",
    "run2": "eval/eval/after_acc_r12a_veto_run2.json",
    "run3": "eval/eval/after_acc_r12a_veto_run3.json",
}
TARGETS = (
    "self_haengun_006",
    "inat_chlorophytum_comosum_002",
    "inat_sansevieria_trifasciata_002",
)
KNOWN = {
    "image_id", "gt_plant", "pred_plant_scientific", "pred_plant_ko",
    "plant_match", "gt_is_healthy", "gt_true_status", "pred_status",
    "pred_is_healthy", "healthy_match", "latency_sec", "json_ok",
    "care_attached", "care_species_key", "expected_care_key",
    "care_link_correct", "observed_symptoms", "top_3_rag",
    "species_normal_species", "species_normal_card_count", "guard_fired",
    "guard_reason", "guard_pre_status", "pred_cause", "guard_pre_cause",
    "guard_cause_regenerated",
}

for name, path in RUNS.items():
    d = json.load(open(path, encoding="utf-8"))
    print(f"=== {name} | total={d.get('total')} | "
          f"json_parse_success_rate={d.get('json_parse_success_rate')} | "
          f"failed_ids={d.get('json_parse_failed_ids')} ===")
    print(f"    latency: {json.dumps(d.get('latency_sec') or {}, ensure_ascii=False)}")

print("\n=== run3 target case full records ===")
d3 = json.load(open(RUNS["run3"], encoding="utf-8"))
pc3 = {c.get("image_id"): c for c in (d3.get("per_case") or [])}
for tid in TARGETS:
    c = pc3.get(tid)
    print(f"\n--- {tid} ---")
    if c is None:
        print("   (per_case에 레코드 없음)")
        continue
    for k in ("json_ok", "pred_status", "pred_is_healthy", "guard_pre_status",
              "observed_symptoms", "pred_cause", "latency_sec",
              "error", "exception", "raw", "json_error"):
        if k in c:
            print(f"   {k}: {c.get(k)!r}")
    extra = [k for k in c if k not in KNOWN]
    if extra:
        print(f"   [추가 키] {extra}")
        for k in extra:
            print(f"      {k}: {c.get(k)!r}")
