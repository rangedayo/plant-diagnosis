# CC Task — R14 롤백 + 음성 결과 기록

> 시점: 2026-06-09. R14 측정 결과 = 게이트 C(FN 0→1) + FP 안 줄고 오름(10→11) = 순 후퇴. 사전 등록대로 generate 프롬프트 변경(`bccac9b`)을 되돌리고, R14를 **기록된 음성 결과**로 남긴다.
> **변수 없음(코드 동작 원복) + 문서화.** 새 기능·새 측정 없음.

## 0. 한 줄 요약
`bccac9b`(R14 generate 프롬프트 두 불릿 추가)를 되돌려 `app/prompts.py`를 그 이전 상태로 복원하고, R14 task md·결과 json·결과 요약·CLAUDE.md 갱신을 커밋한다. 활성 앵커는 **그대로**(R14 기각이므로 변경 없음).

## 1. 안전 제약 (필독)
- **과금 측정 금지.** 무과금(파일·git만). 회귀 점검은 `-m "not integration"`.
- 되돌린 뒤 `app/prompts.py`가 `bccac9b` **직전 상태와 정확히 동일**해야 함(diff로 확인).
- 활성 앵커 `eval/after_acc_armC_3p5flash_relabeled.json`·`baseline.json`·old 앵커 **무접촉**(읽기만).
- 커밋까지. **푸시 보류**.

## 2. 변수 & 동결
- 동작 변경 = `app/prompts.py`를 R14 이전으로 원복(=`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에서 추가했던 두 불릿 제거)뿐.
- 동결: 그 외 모든 코드·스키마·GT·앵커.

## 3. 절차
1. **원복**: `git revert bccac9b` (음성 결과 감사 추적 유지 = 추천). 미푸시이므로 repo 컨벤션상 `reset`으로 커밋 제거를 선호하면 그것도 가능 — 단 어느 쪽이든 **최종 `app/prompts.py` = R14 이전과 동일**함을 diff로 보고.
2. **검증**: `import app.prompts` OK + `pytest -m "not integration"` 통과(Gemini 0) 확인.
3. **R14 task md 추적**: `docs/work_history/`의 R14 task md(현재 untracked) 추가.
4. **결과 요약 작성**: `docs/work_history/R14_result.md`를 아래 §4 내용 그대로 생성.
5. **결과 json 보존**: `eval/after_acc_r14_generate_wholeplant.json`을 기록으로 추가(repo의 eval/ 추적 컨벤션 따름. 무시 대상이면 보고만).
6. **CLAUDE.md 갱신**: 아래 §5.

## 4. `docs/work_history/R14_result.md` 내용 (그대로 작성)
```
# R14 결과 — generate 개체-전체 판단 + 겸손 프레이밍 (기각, 게이트 C)

## 가설
generate 프롬프트에 "개체 전체 활력 판단 + 활성 병변 부재 시 cosmetic 관용 + 겸손 프레이밍"을 추가하면, 잔여 FP(미용 손상 과대판정)를 recall 손실 없이 줄일 수 있다.

## 변경 (bccac9b, 되돌림)
`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에 두 불릿 추가(개체 전체 판단 / 겸손 프레이밍). 활성 병변 신호(확산·비대칭·중앙부·무름·곰팡이) 부재를 recall 방어선으로 설정.

## 측정 (정량, 사용자 PowerShell, analyze=3.5-flash/global)
출력: eval/after_acc_r14_generate_wholeplant.json. 비교 앵커: after_acc_armC_3p5flash_relabeled.json.

| 지표 | 앵커 | R14 | 판정 |
|---|---|---|---|
| FN | 0 | 1 | 🔴 게이트 C |
| FP | 10 | 11 | 안 줄고 오름 |
| TP | 13 | 12 | |
| TN | 12 | 11 | |
| recall | 1.0 | 0.923 | |
| precision | 0.565 | 0.522 | 하락 |
| accuracy | 71.4% | 65.7% | 하락 |

AUX(PlantVillage 50, 뚜렷한 병해): recall 100%·FP 3 — 일반 recall은 건재. 실패는 "경미 미용 vs 경미 병" 경계에 국한.

## 결론 (원리적 실패)
1. **증상 층 비분리**: FP(건강) 케이스(드라세나 등 "잎끝 갈변·바삭 마름")와 FN 케이스(spathiphyllum_003, GT 과습, "잎 가장자리 국소 갈변·황색 반점")가 모델 입력(observed_symptoms)에서 거의 동일. cosmetic 관용을 켜면 FP는 못 줄이고 FN만 발생 → 프롬프트 규칙으로 분리 불가능. §6 가설 입증.
2. **프레이밍은 status 하류에서 못 고침**: status가 비건강(건조 등)으로 정해지면 cause–status 정합 룰이 cause를 "수분 부족" 등으로 강제 → 겸손 톤이 들어갈 자리 없음. 겸손 프레이밍은 status="건강"일 때만 성립.
3. **진짜 병목 = 이진 healthy/5-status 스키마**: "건강하지만 경미한 미용 손상" 출력 칸이 없어, 모델이 잎끝 마름을 "건조(비건강)"로 욱여넣음.

## 판정
generate 프롬프트 레버 = 이진 FP·프레이밍 둘 다 소진. bccac9b 롤백. 활성 앵커 불변.

## 다음 트랙
출력 스키마 확장(심각도·범위 또는 "건강-경미" 차원). GT 라벨 차원 추가(사람 결정, §8.1) 동반. 정성 평가는 스키마 확장 이후 의미.
```

## 5. CLAUDE.md 갱신
- **§2** "FP의 진짜 레버는 미용 vs 병리 임계값(generate/guard)" 류 문장에 한 줄 보강: *"R14에서 generate 프롬프트 레버는 기각(증상 층 비분리 + 프레이밍이 status 하류라 불가). 진짜 병목 = 이진 healthy/5-status 스키마."* (활성 앵커 수치·경로는 **변경 금지**, R14 기각이므로 그대로.)
- **§9 보류** "스키마 확장 (b)"를 보류에서 **다음 트랙으로 승격** 한 줄: *"R14 결과로 동기 확정 — generate/프레이밍으로 FP·톤 개선 불가, 출력 칸(심각도·범위) 부재가 병목."*
- **footer**: *"2026-06-09 — R14 generate 개체-전체+프레이밍 기각(게이트 C, FN 0→1, FP 10→11). 증상 층 비분리·프레이밍 status 하류 한계 확인 → 다음 트랙=출력 스키마 확장."*
- 다음 업데이트 트리거: *"스키마 확장 라운드 설계·결과 보고 시."*

## 6. 커밋 (atomic, 푸시 보류)
1. `revert: R14 generate 프롬프트 (게이트 C, 순 후퇴)` — bccac9b 원복 (또는 reset 시 이 단계 없음).
2. `docs: R14 음성 결과 기록 (result md + task md + 결과 json + CLAUDE.md)`.
- 해시·`git status` 보고.

## 7. 보고 형식
1. 원복 방식(revert/reset) + `app/prompts.py` diff = R14 이전과 동일 확인.
2. import OK + `not integration` 결과.
3. 추가/생성 파일 목록 + CLAUDE.md 갱신 요지.
4. 커밋 해시 + `git status`.

## 8. 금지 사항
- 과금 측정.
- 활성 앵커·baseline·old 앵커 수정/삭제.
- prompts.py 외 코드·스키마·GT 변경.
- 자동 푸시.
