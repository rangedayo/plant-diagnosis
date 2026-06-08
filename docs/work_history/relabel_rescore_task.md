# [라벨 정정 + 재채점] FP 재검 반영 — 재측정 없이 점수 재계산 — 작업 프롬프트

## 0. 맥락

FP 15건 전수 재검(사진 단위 기준) 완료. 최종 판정:

**건강 유지 13건** (현 GT=건강이 맞음 → 라벨 변경 없음. 모델 과민반응 = 진짜 FP):
- hard case 3 (텍스트 변별 불가, 건조 오판): `dracaena_003`·`004`·`006`
- 개선 가능 10 (명백히 건강한 사진을 병해/영양/건조로 과민 판정): `haengun_001`·`004`, `chlorophytum_001`·`003`, `epipremnum_001`, `ficus_002`, `sansevieria_002`, `aglaonema_003`, `spathiphyllum_001`·`003`

**비건강 정정 1건**: `spathiphyllum_002` — 아래쪽 잎 광범위 시듦, 원인 미상

**ambiguous 제외 1건**: `monstera_deliciosa_001` — 병해(halo 반점) vs 환경/물리 손상 단정 불가. 모델의 "병해 의심"은 정당한 의심이라 FP 아님 → 측정 제외

⚠ **라벨 정정은 2건뿐.** 13건은 라벨이 맞고 모델 잘못이라 정정 효과 없음 → 재계산해도 정확도 소폭 상승(~63% 예상). 13건 FP는 별도 모델 개선(analyze 정밀화) 대상. 이번 작업은 baseline을 정확히 만드는 것.

⚠ **재측정(Gemini 호출) 절대 금지.** 기존 모델 출력으로 라벨만 바꿔 점수를 재계산.

---

## PART A — labels.json 정정 (2건)

대상: `test_data/main_eval/labels.json`

1. **백업 먼저**: `labels.json` → `.bak` (타임스탬프 포함).
2. **spathiphyllum_002**: `ground_truth.is_healthy` true→**false** (확정).
   - `true_status`는 **원인 미상** (사진상 비건강은 확실하나 과습/건조 등 원인 단정 불가). labels.json 구조와 채점 로직을 확인한 뒤, 5-status 혼동표에서 이걸 어떻게 다룰지 **방안을 제안**할 것 (예: is_healthy 평가엔 포함하되 5-status 매칭에선 중립 처리). is_healthy=false만 먼저 확정 반영.
3. **monstera_deliciosa_001**: **ambiguous** 처리 — 기존 ambiguous 3건과 동일한 메커니즘으로 is_healthy 평가 분모에서 제외.
4. `scripts/validate_main_eval.py`로 검증.

⚠ 나머지 13건은 **건드리지 말 것** (라벨 정확).

---

## PART B — 재채점 (재측정 없이)

- 입력: 기존 모델 출력 `eval/after_acc_r12d1_remove_surface.json` + 정정된 `labels.json`
- **점수/집계만 재계산.** Gemini·gpt-4o-mini·임베딩 등 모델 호출 일절 금지.
- `run_eval.py` 구조상 measure 단계와 score 단계가 분리 안 되면, **출력 JSON을 입력으로 점수만 내는 방법**을 확인하고 제안(별도 재채점 함수/스크립트 가능 여부). 분리 불가하면 보고하고 멈춤 — 임의로 전체 재실행하지 말 것.

---

## PART C — 보고 (chat)

1. **정정 전후 비교**: 건강여부 accuracy 58.3% → ? (분모 36→35 예상, monstera 제외)
2. 새 TP/TN/FP/FN (분모 35 기준)
3. **FP 잔존 내역** — 13건 전부 나열, **hard case 3(드라세나) vs 개선 가능 10** 명확히 구분
4. spath_002 `true_status` 처리 방안 제안
5. labels.json 백업·검증 결과

---

## 주의사항

- ⚠ `eval/baseline.json` 무접촉.
- ⚠ **재측정(Gemini 호출) 금지** — 라벨 정정 + 재채점만.
- labels.json 백업 필수, validate 통과 확인.
- 13건(건강 유지) 라벨 변경 금지.
- 커밋·푸시 보류 (사용자 검토 후).

---

## 다음 단계 (참고 — 이 작업 범위 X)

재채점 baseline 확정 후 → **① analyze(증상 추출) 정밀화** 설계. FP 13건 중 개선 가능 10건이 타깃 (정상 변이를 병징으로 과장 추출하는 걸 줄이되 FN 안 건드리게). 드라세나 hard 3건은 종 인지 영역으로 별도.
