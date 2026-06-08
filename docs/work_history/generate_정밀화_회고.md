# generate 정밀화 회고

- **기간/라운드**: 2026-06-08 전후, generate 출력 정밀화 라인 (antifab · escalation · FP15 relabel).
- **목적**: analyze/generate의 환각·과escalation(is_healthy FP)과 cause-status 모순을 입력(프롬프트)·라벨 측에서 교정 시도하고 본질 기여를 측정. 결과적으로 입력 측 교정이 한계임이 분명 → 모델 교체로 이관됨.

## 1. antifab — analyze 날조 억제 (실패·롤백, CLOSED)
- 시도: analyze 프롬프트에 "관찰 충실성" 원칙 추가.
- 실측: FP 13→16, acc→54.3%, latency +24% → 전반 악화.
- 결론: 환각은 모델이 자기 환각을 인지하지 못해 프롬프트 훈계로 안 잡힘. → **롤백 완료(CLOSED).** 입력 측 교정의 첫 실패 사례.

## 2. generate cause-status 정합 (escalation) — neutral·롤백, CLOSED
- 시도: R12b 기본 정합룰 위에 **③ 강화분**(병해는 cause가 병징을 직접 지목할 때만 → loophole 봉합).
- v1: API 429(쿼터 소진)로 측정 오염 → **무효**. "파싱 실패 6건"이 실제로 429라 generate 미실행(정합룰 무관)이었음.
- v2: `analyze.py` max_attempts 2→3 상향 후 재측정(`after_acc_generate_escalation_v2.json`). JSON 100% 정상 통과. **is_healthy FP 13→13 무영향 확정**(정합룰은 비건강 내부 이동 병해→건조라 is_healthy 불변). FN=1 발생했으나 정합룰 무관.
- 결론: **정합룰은 is_healthy FP를 두 번 못 잡음.** → R12a 매뉴얼에서 **③ 강화분만 롤백(restore) 완료(CLOSED)**, R12b 기본 정합룰은 앵커 코드에 유지. 입력 측 교정의 두 번째 결과(중립).

## 3. FP15 relabel (rescore, 현 앵커 정의)
- FP15 전수 재검 인벤토리·워크시트 → labels 2건 정정(spath_002 비건강-원인미상 · monstera ambiguous).
- 측정(Gemini 호출) 없이 `rescore_from_output.py`로 점수 재계산 → 현 앵커 `after_acc_r12d1_relabeled.json`(acc 62.86% / FP 13 / FN 0).

## 4. 결론 — 입력·출력 우회 한계 → 모델 교체로
- antifab(프롬프트 훈계)·escalation(정합 룰)은 둘 다 **입력 측 교정**인데 환각·is_healthy FP를 못 잡음(실패/중립).
- **출력 측 우회**(R12a 가드 위치 veto)도 효과 미입증(`R12_트랙_회고.md`·`R12a_result.md` 참조).
- ⇒ 근본 원인 = analyze 비결정성·환각. **다음 트랙 = ⇒ 모델 교체**(Gemini 3.5 Flash A/B 후보, agentic vision이 필요). 입력·출력 우회를 다 시도한 뒤 "모델 자체로 간다"는 근거가 이 트랙에서 확정됨.

## 5. 트랙 상태
- **CLOSED**: antifab(실패·롤백) · escalation ③ 강화(neutral·롤백) · FP15 relabel(앵커 확정).
- **OPEN/후보**: analyze_overcall(과호출 진단) · json_parse 분리 집계(429 vs 진짜 파싱 실패, `run_eval.py` L836 → R12a run3에서 429를 파싱 실패로 오분류한 사례 재현, 위생 개선 후보).
- 교훈: 라벨 정정은 측정 없이 rescore로 가능. **환각은 입력 측에서 안 잡힌다**(antifab·escalation 모두 입증) → 모델 교체가 근본책.

## 원본 파일
- → `_archive/원본/generate_정밀화/`: FP15_relabel_inventory_task.md · FP15_relabel_worksheet.md
- ACTIVE 유지(work_history 루트, 미아카이브): analyze_antifab_task.md · generate_escalation_task.md · analyze_overcall_diagnosis(.md+_task.md) · json_parse_failure_diagnosis(.md+_task.md)
- 관련 측정 JSON: `eval/_archive/superseded/after_acc_analyze_antifab.json` · `eval/_archive/invalid/after_acc_generate_escalation.json`(v1 429 무효) · `eval/_archive/r12/after_acc_generate_escalation_v2.json`
