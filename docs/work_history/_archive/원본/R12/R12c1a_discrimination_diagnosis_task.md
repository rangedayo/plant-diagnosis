# [R12c-1-α 사전] FP/TP 변별 진단 (read-only) — 작업 프롬프트

## 0. 맥락 + 목적

R12d-1에서 healthy→건조 FP의 진짜 범인이 abiotic-water 카드 본문으로 확정됨. 다음 라운드 후보는 카드에 **negative(정상 감별) 신호**를 추가해 healthy FP를 줄이는 R12c-1-α. 하지만 위험이 있음:

- 진짜 건조(TP)와 정상 노화 오진(FP)의 **증상 텍스트가 거의 동일한 케이스**가 존재 (예: TP haengun_008 "여러 잎 잎끝 갈변 및 마름" ↔ FP dracaena_003 "여러 잎 잎끝 갈변 및 마름").
- TP·FP가 **같은 abiotic-water 카드를 검색**해 올리므로, 카드에 넣은 negative 신호가 TP에도 전달 → **FN 위험(recall 게이트 위반)**.
- dracaena_004·006은 "고사"·"전체 고사"까지 있는데 GT가 healthy → 종 특이적 정상 패턴일 가능성.

**이번 작업의 목적**: 카드를 건드리기 전에, "TP엔 없고 FP에만 있는 변별 신호가 실재하는가"를 데이터로 확인. negative 신호 설계가 안전하게 가능한지/얼마나 효과 볼지 판정.

⚠ **read-only. 코드·카드·프롬프트·Chroma 일절 변경 금지. 측정(Gemini 호출) 금지. 기존 `eval/after_acc_r12d1_remove_surface.json` raw 분석만.**

---

## PART A — 데이터 전수 추출

`eval/after_acc_r12d1_remove_surface.json` raw에서 두 그룹을 **전수** 추출 (요약본의 일부 표본 말고 전부):

1. **healthy→건조 FP 그룹** (true_status=건강 AND pred_status=건조) — 혼동표상 6건
2. **건조 TP 그룹** (true_status=건조 AND pred=비건강) — 5건

각 케이스별로:
- case_id, 종(gt 종명 + pred_sci)
- observed_symptoms (전체 문장)
- top_3 problem_type
- pred_status, true_status

---

## PART B — 변별 축 분석

두 그룹을 4개 축으로 코딩해서 **TP vs FP가 분리되는 축이 있는지** 확인:

| 축 | 코딩 기준 |
|---|---|
| 분포 | "여러 잎/전체" vs "일부/소수/국소" |
| 부위 | 말단("잎끝·가장자리") vs 전면("아래잎 전체·전체적") |
| 진행성 | 경미("갈변·변색") vs 진행성("고사·마름·처짐·말림·종이같은") |
| 종 | 드라세나 / 행운목 / 접란 / 스킨답서스 / 기타 |

각 축에서 TP 분포 vs FP 분포를 표로. **"TP에는 거의 없고 FP에만 몰리는" 신호가 있으면 그게 negative 후보.** 반대로 TP·FP에 고루 퍼진 신호는 negative로 쓰면 FN 유발.

특히 카운트할 것:
- **텍스트 동일/근사 쌍**: TP와 observed_symptoms가 사실상 같은 FP가 몇 건인지 (이건 카드로 변별 불가 → FN 위험군)
- **"고사"류가 있는데 healthy인 FP**: dracaena_004·006 외에 더 있는지 (종 특이 정상 패턴 후보)

---

## PART C — 3유형 분류 + 결론

FP 6건을 분류:

| 유형 | 정의 | 카드 negative 가능성 |
|---|---|---|
| (가) 경미·국소 단독 | TP엔 없는 "국소 단독" 신호만 | ✅ 안전 공략 가능 |
| (나) TP와 텍스트 동일 | 변별 신호 없음 | ❌ FN 위험 |
| (다) 종 특이 정상 | 하엽 고사 등 종 정상 패턴 | ❌ 종 지식 필요 |

**최종 결론은 셋 중 하나로 명시:**
- (A) 변별 축 실재 → 안전한 negative 신호 후보를 영어 문구로 2~3개 제시 + 영향받는 FP/TP 케이스 매핑
- (B) 부분적 → (가) 유형 N건만 공략 가능, 예상 FP 감소폭 추정 + 잔여 (나)·(다) 명시
- (C) 변별 축 없음 → 카드 negative 한계, 대안(종 메타 활용 / 평가셋 라벨 점검) 제시

추측 금지. 모든 분류에 case_id + 증상 근거 첨부.

---

## PART D — 보고 (chat)

1. PART A 전수 추출 표 (FP 6 + TP 5)
2. PART B 4축 분석 표 + 텍스트 동일 쌍 카운트 + "고사 있는데 healthy" 케이스
3. PART C 3유형 분류 + 최종 결론 (A/B/C 중 하나)
4. (결론이 A/B면) negative 신호 영어 후보 + 영향 케이스 매핑
5. 진단 보고서 경로: `docs/work_history/R12c1a_discrimination_diagnosis.md` (작성하되 커밋·푸시는 보류, 사용자 검토 후)

---

## 주의사항

- ⚠ **read-only** — 코드/카드/프롬프트/Chroma/baseline 일절 무변경.
- ⚠ 측정(run_eval, Gemini 호출) 금지 — 기존 JSON 분석만.
- 보고서 작성까지만, 커밋·푸시 보류.
- 모든 주장에 case_id·증상 근거. 추측 배제.
