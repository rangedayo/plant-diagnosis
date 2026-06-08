# [R12a 사전] 가드 위치 veto 진단 (read-only) — 작업 프롬프트

## 0. 맥락

- **recall 불안정 발견**: FN=0이 운에 의존. haengun_006이 analyze 비결정성으로 "아래쪽 잎 갈변"(cosmetic-only)으로 추출되면, 가드가 `all_cosmetic_nondisease_top1`로 건강 over-correct → **FN**. (`after_acc_generate_escalation_v2.json`에서 실제 발현)
- **R12a 목표**: 가드 cosmetic 판정에 **위치 veto** 추가 — "아래/하엽/하부" 등 위치 신호가 있으면 cosmetic 교정(비건강→건강)을 차단해 FN 방지.
- ⚠ **가드 본체를 처음 수정하는 라운드.** 가드는 FN=0의 마지막 안전판이라, 구현 전 진단 필수 (날조·정합룰 두 번 실패 교훈: 관찰 먼저).

⚠ **read-only. 측정·코드·프롬프트·baseline 무변경.** 기존 코드 + 측정 JSON 분석만.

---

## PART A — 가드 cosmetic 판정 로직 파악

- status guard의 cosmetic 판정 함수(`_symptom_is_cosmetic` 등) **전체 로직** 인용.
- 토큰 리스트 현황: `COSMETIC_LOCATION` / `COSMETIC_DISCOLOR` / `LESION` 등 — 각 리스트 내용.
- **"아래/하엽/하부/기부/아래쪽" 등 위치 토큰**이 현재 어떻게 취급되나 — cosmetic으로 묶이나, 무시되나, 아예 없나.
- 가드 발동 조건(`all_cosmetic_nondisease_top1`)이 정확히 무엇인지.

---

## PART B — haengun_006 FN 메커니즘

- `after_acc_generate_escalation_v2.json`에서 haengun_006의 observed_symptoms + 가드 판정 경로 추적.
- "아래쪽 잎의 끝과 가장자리 갈변"이 왜 `all_cosmetic_nondisease_top1`로 판정됐나 — 어떤 토큰에 매칭됐는지.
- **위치 신호("아래쪽")가 무시된 지점** 정확히 식별 — 여기가 veto를 끼울 자리.

---

## PART C — 위치 veto 설계 + 영향 시뮬레이션 (핵심)

veto 규칙 후보: observed_symptoms(특히 top_1)에 위치 토큰(아래/하엽/하부 등)이 있으면 cosmetic 교정 **차단**(비건강 유지).

가용한 기존 측정 JSON(`relabeled`, `v2` 등)에서 observed_symptoms가 저장돼 있으면, 이 veto 적용 시:
- **FN 방지되는 케이스** (haengun_006 등) — 몇 건
- **새로 FP로 남는 케이스** — 건강인데 위치 토큰이 있어 건강 교정을 못 받는 경우 몇 건
- 즉 **FN↓ vs FP↑ 트레이드오프** 추정치

⚠ JSON에 케이스별 observed_symptoms가 없으면 "시뮬 불가"를 명시하고, 가능한 범위(요약 리포트의 가드 발동 4건 등)만으로 추정. 추측 금지.

위치 토큰 후보 리스트 제안 (과포함 시 FP↑, 과소 시 FN 못 막음 — 보수적 설계).

---

## PART D — 보고 + 처방 (chat)

1. 가드 cosmetic 판정 로직 요약 + 위치 토큰 현재 취급
2. haengun_006 FN 메커니즘 (어디서 위치 신호가 무시됐나)
3. veto 설계안 (토큰 리스트 + 적용 위치)
4. **트레이드오프 추정**: FN 방지 N건 vs FP 증가 M건 (시뮬 가능 범위)
5. 구현 권고 + 리스크 (가드 안전판을 건드리는 만큼 보수적 제안)
6. 진단 보고서 경로 (작성, 커밋 보류)

---

## 주의사항

- ⚠ **read-only** — 측정·재호출·코드·프롬프트·baseline 무변경.
- 추측 금지 — 코드/JSON 근거. observed_symptoms 없으면 "없음" 명시.
- 보고만, 커밋·푸시 보류.

---

## 다음 단계 (참고 — 범위 X)

진단 후 → **정합룰 롤백 + R12a veto 구현 + 측정** (별도 task). 측정 변수 = veto 하나(롤백은 기준점 복귀). 게이트: 🔴 FN 복구(haengun_006 잡힘) + FP 과증가 없음.
