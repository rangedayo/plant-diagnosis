# 정확도 트랙 설계 — 1차 진단 FP/FN 측정 정비

> 작성: 2026-06-05 · 상태: 합의 초안 (검토 후 `docs/design/`에 커밋)
> 선행: 시계열 기능 완료 · L0 기준선(`eval/baseline_current_postguard_avg.json`) 캡처됨
> 후속: 라벨 스키마 마이그레이션 → status 리라벨링 → 병해 표본 수집 → run_eval 확장 → L0' 재측정

---

## 0. 한 줄 요약

1차 진단 정확도 트랙의 **목표는 현 9종 평가셋에 대한 FP/FN을 제대로 측정**하는 것이며, 그 핵심 병목은 **병해(증상) 표본 부족**과 **5-status 정답 라벨 부재**다. 본 문서는 그 두 병목을 푸는 방식을 합의한다.

---

## 1. 배경 — 현황과 갭

### 실측 평가셋 (run_eval이 실제 소비)

- 단일 소스: `test_data/main_eval/labels.json`, **9종 33장**.
- 구성: 정상 28 / 증상 5.
  - self_captured: 행운목(2/5), 드라세나 송오브인디아(5/0)
  - iNaturalist(수동 큐레이션) 7종: 아글라오네마·접란·스킨답서스·고무나무·몬스테라·산세베리아·스파티필름 — 각 3/0 (전부 정상)
- L0 기준선은 이미 이 9종 33장 위에서 측정됨.

### 두 개의 갭

1. **병해(FN) 표본 빈약** — 증상 5장이 전부 행운목 단일종. FP/precision 축은 9종으로 튼튼하나, **FN·recall 측정은 단일종에 묶여 사실상 불능**.
2. **5-status 정답 라벨 부재** — 현 라벨은 `is_healthy`(이진) + `symptoms` + 자유서술 `diagnosis`뿐. status 5종(`건강`·`과습`·`건조`·`병해 의심`·`영양 부족`) 정답이 없어 **status별 under-detection을 점수화할 수 없음**.

### 놀고 있는 자산

- **PlantVillage 50장** — 병해 라벨까지 완료(`test_data/plantvillage_50/labels.json`)됐으나 run_eval이 미연결. 단 작물(토마토·감자·사과) 도메인이라 메인 부적합.
- **Wikimedia 0장** — `scripts/collect_wikimedia.py` 존재(병징 검색어 12개 내장)하나 미실행·미검증.

---

## 2. 1차 목표 (이번 트랙의 스코프)

- **9종 평가셋에 대한 FP/FN을 제대로 측정**한다.
- 이를 위해 (a) 다종 병해 표본을 확충하고, (b) 5-status 정답 라벨을 추가하며, (c) run_eval을 status confusion까지 측정하도록 확장한다.
- **스코프 밖(후속 축)**: 9종을 넘어선 넓은 종 일반화 신뢰. 이는 더 많은 종의 표본이 필요한 별개 작업으로, 본 트랙에서 측정 대상이 아님.

---

## 3. 평가셋 대표성 — 명시와 한계

### 현 9종이 대표하는 것

식집사 입문 단골 인기종 핵심(몬스테라·스킨답서스·산세베리아·스파티필름·고무나무)을 포함. **"흔한 입문 관엽"은 잘 대표**한다.

### 대표 못 하는 것 (미측정 영역 — 정직 표기)

- 누락된 흔한 종: 금전수(ZZ)·야자류(테이블야자·아레카야자)·필로덴드론·싱고니움·페페로미아·호야·칼라데아·고사리류.
- 형태 공백: **야자류(깃털잎)·고사리류(섬세잎) 형태가 평가셋에 전무.**
- 속 편중: Dracaena 속 2종(행운목·드라세나) 중복.

→ **원칙**: 위 미커버 부류에 대한 진단 성능은 9종 점수로 **외삽하지 않는다**. "측정됨 = 9종 범위 내"임을 모든 리포트에 명시.

---

## 4. 핵심 결정 사항

### 결정 1 — 병해 표본 확보: 웹 수집 위주

- **본인/지인 식물 직접 촬영은 접음** (자연 발생 의존·한계 명확).
- **1순위 채널: Wikimedia** — 텍스트 검색이라 병징("yellowing"·"root rot"·"powdery mildew" 등)을 의도적으로 노릴 수 있음. 단 0장·미검증 → **dry-run 먼저** 수율 확인 후 소량 실수집.
- **iNaturalist 증상/종 확장은 접음** — 자연 관찰 기록 특성상 건강 개체 편향, 병해 수율 낮음. ("증상 annotation 필터"는 iNat에 사실상 존재하지 않음.)

### 결정 2 — 종 다양성: 느슨한 확장

- 병해 수집 과정에서 **누락된 흔한 종 중 병해 사진을 구하기 쉬운 것(금전수·필로덴드론 등)이 걸리면 자연스럽게 추가**.
- **강제 종 목표 없음** — 병해 표본 확보가 우선, 종 확장은 보너스.
- 최종 커버 종 목록을 본 문서 §3에 갱신·명시.

### 결정 3 — PlantVillage: 보조 sanity check (게이트 제외)

- `run_eval.py --aux`로 **메인과 완전 분리** 측정.
- 용도: "명백한 잎 병반에도 모델이 '건강'이라 하지 않는가"의 **순수 병징 인식 sanity check**.
- **점수는 메인 게이트에 절대 미포함** — 참고용 보너스 지표.
- 도메인 미스매치(작물·연구실·잎 클로즈업) 한계 명시. 본진 FN 표본의 대체재 아님.
- **현 5클래스 유지, 종 추가 안 함** (더 끌어와도 전부 작물).

### 결정 4 — status 정답 라벨: `true_status` + `ambiguous`

- ground_truth에 `true_status` 5종 enum 신규 추가 (백엔드 `ALLOWED_STRUCT_STATUS`와 동일).
- 사람이 잎만 보고 5종 판정이 어려운 케이스는 `ambiguous` → **평가에서 제외**(분모 투명 표기).
- `is_healthy ↔ true_status` 방향 정합성 검증 추가 (ambiguous는 면제).

---

## 5. 라벨 스키마 변경

### `test_data/labeling_vocab.py` 추가

```python
STATUS_VOCAB: list[str] = ["건강", "과습", "건조", "병해 의심", "영양 부족"]
STATUS_AMBIGUOUS: str = "ambiguous"  # 잎만으로 5종 판정 곤란 → 평가 제외
```

### `labels.json` ground_truth — `true_status` 한 줄 추가

```json
"ground_truth": {
  "plant_name_korean": "몬스테라",
  "is_healthy": true,
  "true_status": "건강",
  "symptoms": [],
  "diagnosis": "정상 상태"
}
```

### `validate_label` 갱신

- `true_status`를 필수 필드에 추가.
- enum 검증: `STATUS_VOCAB` ∪ `{ambiguous}` 외 값은 ValueError.
- 정합성: `true_status=="건강"`이면 `is_healthy=true`, 비건강 4종이면 `is_healthy=false` (ambiguous 면제).
- 기존 허용 유지: `is_healthy=true` + `symptoms=[...]` 조합(드라세나 잎끝 마름 등 경증)은 계속 허용.

---

## 6. run_eval 확장

- 기존 측정(식물명·is_healthy 이진·status 분포·JSON·latency)은 **불변**.
- 신규: **5×5 status confusion matrix** — `true_status` 정답 대비 예측 status. `ambiguous`는 분모 제외 + 제외 건수 별도 카운트.
- 신규: `--aux` 옵션 — PlantVillage 50장 별도 측정, 결과 JSON 분리, 메인 게이트 미반영.
- `eval/baseline_current_postguard_avg.json`(L0 앵커)·`eval/baseline.json`(구스키마)은 **무변경**.

---

## 7. 작업 라운드 흐름

```
[지금] 설계 합의 ← 본 문서
   ↓ docs/design/design_accuracy_track.md 커밋
1) [CC] 라벨 스키마 마이그레이션 — labeling_vocab.py(STATUS_VOCAB) + validate 갱신 + 기존 33장 마이그레이션 도구
   ↓
2) [본인] 기존 33장 true_status 라벨링 (애매한 건 ambiguous)
   ↓
3) [본인+CC] Wikimedia dry-run → 수율 확인 → 소량 실수집 → 후보 검수 → 메인 평가셋 병해 +N장
   ↓
4) [CC] run_eval.py 확장 — 5×5 status confusion + --aux(PlantVillage)
   ↓
5) [본인] 새 평가셋으로 L0' 재측정 (Gemini 과금, PowerShell)
```

각 라운드는 read-only 선결 게이트(변경 전 현황 보고 → 불일치 시 중단) 적용. CC 작업 프롬프트는 `.md` 파일로 전달.

---

## 8. 데이터 범위 원칙 (불변 — 상속)

- 토양습도%·일조량·성장% 등 센서/측정/정량값 금지. 가짜 숫자 금지.
- 라벨링 자동화 금지 — ground_truth는 사람이 채움 (PlantVillage 사전 매핑만 예외).
- 파일 인코딩 BOM 없는 UTF-8, Python 3.12 호환.

---

## 부록 — 결정 근거 요약

| 결정 | 채택안 | 기각안 + 사유 |
|---|---|---|
| 병해 채널 | Wikimedia dry-run 우선 + 누락종 보너스 | iNat 증상확장(병해 수율 낮음) · 본인촬영(한계) |
| 종 다양성 | 느슨한 확장 (강제 목표 없음) | 9종 고정(대표성 약점) · 적극 확장(라벨 비용) |
| PlantVillage | --aux 보조, 게이트 제외 | 메인 통합(도메인 오염) · 폐기(라벨 아까움) · 종 추가(여전히 작물) |
| status 라벨 | true_status + ambiguous | is_healthy 이진 유지(under-detection 측정 불가) |
