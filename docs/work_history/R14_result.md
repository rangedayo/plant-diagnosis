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
