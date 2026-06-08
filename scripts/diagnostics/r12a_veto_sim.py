"""R12a read-only 시뮬: 위치 veto 트레이드오프 추정. 측정·코드·baseline 무변경."""
import json

PATH = "eval/after_acc_generate_escalation_v2.json"
LOCATION_VETO = ("아래", "하엽", "하부", "기부", "아래쪽", "오래된 잎", "묵은 잎")

d = json.load(open(PATH, encoding="utf-8"))
pc = d["per_case"]

print("=== haengun_006 ===")
for c in pc:
    iid = str(c["image_id"]).lower()
    if "haengun" in iid and "006" in iid:
        for k in ["image_id", "gt_is_healthy", "gt_true_status", "pred_status",
                  "pred_is_healthy", "healthy_match", "guard_fired", "guard_reason",
                  "guard_pre_status", "observed_symptoms"]:
            print(f"  {k}: {c.get(k)}")

print("\n=== guard fired cases (all) ===")
for c in pc:
    if c.get("guard_fired"):
        print(f'  {c["image_id"]} | reason={c.get("guard_reason")} '
              f'| gt_healthy={c.get("gt_is_healthy")} '
              f'| pre={c.get("guard_pre_status")} -> post={c.get("pred_status")} '
              f'| healthy_match={c.get("healthy_match")}')
        print(f'     syms={c.get("observed_symptoms")}')

print("\n=== veto simulation (location token present in ANY symptom) ===")
fn_prevented = []  # guard fired -> 건강, but gt 비건강 (FN), and has location token
fp_new = []        # guard fired -> 건강 correctly (gt healthy), but veto would block -> FP
for c in pc:
    if not c.get("guard_fired"):
        continue
    if c.get("guard_reason") != "all_cosmetic_nondisease_top1":
        continue  # veto only targets cosmetic correction
    syms = c.get("observed_symptoms") or []
    joined = " ".join(str(s) for s in syms)
    has_loc = any(tok in joined for tok in LOCATION_VETO)
    if not has_loc:
        continue
    gt_healthy = c.get("gt_is_healthy")
    iid = c["image_id"]
    if gt_healthy is False:
        fn_prevented.append((iid, syms))
    elif gt_healthy is True:
        fp_new.append((iid, syms))

print(f"FN prevented (gt 비건강, veto blocks bad 건강 교정): {len(fn_prevented)}")
for iid, syms in fn_prevented:
    print(f"   {iid}: {syms}")
print(f"FP newly retained (gt 건강, veto blocks good 건강 교정): {len(fp_new)}")
for iid, syms in fp_new:
    print(f"   {iid}: {syms}")
