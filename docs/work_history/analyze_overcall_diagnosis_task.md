# [analyze 정밀화 사전] 과민 책임 단계 진단 (read-only) — 작업 프롬프트

## 0. 맥락 + 목적

새 기준점 확정 후(`after_acc_r12d1_relabeled.json`, 62.86%, FP 13). FP 13건 중 **개선 가능 10건**은 "명백히 건강한 사진을 병해/영양/건조로 과민 판정"한 것. 이걸 줄이려면 어디를 고쳐야 하는지 먼저 확정해야 한다.

**핵심 질문: 과민의 책임이 어느 단계인가?**
- (가) **analyze 과장**: Gemini가 증상 추출 단계에서 정상 변이(윤기·무늬·꽃대·자연 흠집·경미 갈변)를 "병반·이상"으로 **과장 추출** → 입력부터 오염
- (나) **generate 비약**: analyze는 "경미한 잎끝 갈변" 정도로 정확히 추출했는데, generate가 그걸 "병해 의심"으로 **과하게 판정**

→ (가)면 analyze 프롬프트, (나)면 generate 프롬프트가 정밀화 타깃. 혼합이면 비율 파악. 이 진단 없이 프롬프트 손대면 헛발질.

⚠ **read-only. 코드·프롬프트·평가셋 일절 변경 금지. 측정(Gemini 호출) 금지.** 기존 모델 출력 `eval/after_acc_r12d1_remove_surface.json` raw 분석만 (observed_symptoms·cause 등 상세는 이 원본에 있음. relabeled는 라벨만 바뀐 재채점본).

---

## PART A — 개선 가능 10건 풀 파이프라인 추출

대상 10건 (드라세나 hard 3은 제외 — 종 인지 영역):
- pred=건조(2): `chlorophytum_comosum_003`, `spathiphyllum_001`
- pred=병해 의심(6): `haengun_001`·`004`, `chlorophytum_comosum_001`, `epipremnum_aureum_001`, `ficus_elastica_002`, `sansevieria_trifasciata_002`
- pred=영양 부족(2): `aglaonema_003`, `spathiphyllum_003`

각 케이스마다 추출:
- case_id, 종
- **observed_symptoms** (analyze 출력 — 가장 중요)
- top_3 problem_type
- pred_status
- **cause / 설명문** (generate 출력)

참고 — 웹에서 확인한 **실제 이미지 소견** (analyze 추출과 대조용):

| case | 실제 이미지 소견 |
|---|---|
| chlorophytum_003 | 바위틈 접란, 잎 녹색 살아있음, 마른 꽃대 일부 |
| spathiphyllum_001 | 잎 진녹색 윤기 — 매우 건강 |
| haengun_001 | 잎 본체 진녹색, 잎끝만 미세 갈변 |
| haengun_004 | 새순 녹색, 끝부분만 약간 마름 |
| chlorophytum_001 | 야외 조경, 잎 싱싱·무늬 양호, 끝 약간 갈변 |
| epipremnum_001 | 황금 스킨답서스, 무늬 좋음, 자연 흠집·구멍 |
| ficus_002 | 고무나무, 진녹색 윤기 — 거의 완벽 |
| sansevieria_002 | 개화 꽃대 여러 개, 잎 건강 |
| aglaonema_003 | 은녹 무늬, 하부 잎 일부 노화 |
| spathiphyllum_003 | 꽃 3개 개화, 잎 진녹색 |

---

## PART B — 과장 패턴 분석

각 케이스에서 **analyze가 추출한 증상 vs 실제 이미지 소견**을 대조:
- analyze 추출이 실제보다 과장됐나? (예: 윤기/무늬/꽃대를 "병반·반점"으로, 자연 흠집을 "병징"으로)
- 정상 변이 유형 분류: 품종 무늬 / 꽃대(개화) / 윤기 / 자연 흠집·구멍 / 경미 말단 갈변 / 하부 노화
- 어떤 유형이 어떤 증상 문장으로 둔갑했는지 표로

---

## PART C — 책임 단계 진단 (핵심 산출)

각 10건을 **(가) analyze 과장 / (나) generate 비약 / (다) 혼합** 중 하나로 분류:
- observed_symptoms가 이미 과장됐으면 → (가) analyze
- observed_symptoms는 경미·정확한데 pred_status가 비건강으로 튀었으면 → (나) generate
- 둘 다면 → (다)

**최종 결론**: 10건의 (가)/(나)/(다) 분포 → 정밀화 1순위 타깃이 analyze인지 generate인지 명시. 각 분류에 case_id + observed_symptoms + cause 근거 첨부.

---

## PART D — 보고 (chat)

1. PART A 10건 풀 파이프라인 표
2. PART B 과장 패턴 (정상 변이 유형 → 둔갑한 증상 문장)
3. PART C 책임 단계 분포 + 정밀화 1순위 타깃 결론
4. 진단 보고서 경로: `docs/work_history/analyze_overcall_diagnosis.md` (작성, 커밋·푸시 보류)

---

## 주의사항

- ⚠ **read-only** — 코드·프롬프트·평가셋·baseline 무변경. 측정(Gemini) 금지.
- 비교 기준은 새 앵커 `after_acc_r12d1_relabeled.json`(62.86%)이나, **상세 추출은 원본 `after_acc_r12d1_remove_surface.json`** 에서.
- 모든 분류에 case_id·증상·cause 근거. 추측 배제.
- 보고서 작성까지만, 커밋 보류.
