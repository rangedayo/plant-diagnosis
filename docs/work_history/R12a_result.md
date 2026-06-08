# R12a — status guard 위치 veto: 결과

## 1. 가설
analyze가 haengun_006을 "아래쪽 잎 가장자리"(cosmetic-only)으로 추출하면 status guard가 비건강→건강으로 over-correct하여 FN이 발생한다. 하부 위치 토큰("아래쪽" 등)을 진행성 신호로 보고 강도가 건강 교정을 veto하면 recall이 안정화될 것이다.

## 2. 변경사항
- 정합룰 롤백: generate cause-status 정합룰 ③ 강화분(미커밋 working-tree 수정)을 `git restore`로 폐기 → `app/prompts.py` 앵커 상태(기본 정합룰 유지) 복귀. 변수 격리상 측정 변수는 veto 하나.
- veto 구현(fb52fc1, `app/graph.py`): `STATUS_GUARD_PROGRESSIVE_LOCATION = ("아래쪽","하엽","하부","하단")` 상수 + `_symptom_has_progressive_location()` 함수. 규칙 3 all_cosmetic 통과 직전·건강 교정 직접 layer(lesion veto에 대응). 부분일치. `_symptom_is_cosmetic` 불변. veto 시 `(cur, None)` 반환(cause 재생성 미발동).

## 3. 측정 (3-run, 앵커 = after_acc_r12d1_relabeled.json: acc 62.86% · FP 13 · FN 0 · 분모 35)

| run | 상태 | FP(가드후/분석) | FN | acc | haengun_006 | "아래쪽" 토큰 매칭 |
|---|---|---|---|---|---|---|
| 1 | clean (39/39) | 12 / 13 | 0 | 65.7% | TP (증상 "아래가 황화") | haengun_002 1건 |
| 2 | clean (39/39) | 11 / 12 | 0 | 68.6% | TP (증상 "아래쪽 일부 황화") | 0건 |
| 3 | 429 드롭 3건 (36/39) | 12 / 13 | 0 | 62.5% | 미측정(429) | 0건 |

- FP는 두 가지로 보고됨(가드후 / FP분석, 일관된 약 1 offset); 앵커 "FP 13"은 FP분석 쪽과 정렬. 어느 쪽이든 모든 run에서 ≤14.
- run3: 3건(haengun_006 포함)이 429(RESOURCE_EXHAUSTED)로 드롭. 모델 파싱 실패 아님 → 인프라(쿼터) 사유. 게이트는 clean한 run1·run2 기준, run3는 분모 제외.

## 4. 게이트 판정: 🟡 부분 통과
- 안전: FP ≤14 (앵커 13 대비 과증가 없음) → 2 clean run 충족.
- recall 유지: FN=0 → 2 clean run 충족.
- veto 효과 **미입증**: 타깃 haengun_006이 어느 run에서도 veto 토큰("아래쪽")을 추출하지 않음 → 전부 "아래가". 3 run 통틀어 "아래쪽" 매칭은 run1 haengun_002 1건뿐(그마저 바뀔 불필요한 TP). recall 안정성은 veto가 아니라 analyze 증상 내용 + 기존 가드가 만든 것.

## 5. 결론
- recall은 2 clean run에서 안정적(FN=0)이나 veto에 기인하지 않는다. veto는 v2 실패 패턴("아래쪽" + all-cosmetic) 재발에 대비한, 올바르게 좁혀진·FP-중립 안전핀으로 유지한다(제거하지 않음).
- 확인된 갭: analyze는 "아래가"를 압도적으로 사용("아래쪽"보다 훨씬). 현 토큰 셋은 "아래가"를 못 잡으므로 veto 커버리지가 표현 의존적이다.
- 근본 원인은 analyze 비결정성(같은 식물을 "아래쪽"/"아래가"/429로 다르게 처리)이다. 토큰 확장은 두더지잡기 → 근본 해결은 ② 모델 교체.

## 6. 다음 라운드 노트
- ② 모델 교체 트랙 착수 → Gemini 3 vision grounding 조사 + A/B 측정 설계.
- (후보) 토큰 셋에 "아래가"/"아래" 어간 추가 → 갭 닫기용. 단 analyze 별도 추격이라 효용 한정적.
- (후보) 쿼터 여유 시 run3 clean 재측정 → n=3 완성용. 결론 불변.
- (위생 후보) run_eval.py L836: 429와 진짜 파싱 실패 분리 집계 → 파싱률(이번 0.923) 오독 방지.
