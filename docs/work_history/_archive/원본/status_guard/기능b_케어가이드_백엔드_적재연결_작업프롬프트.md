# [기능 (b)] 케어 가이드 — garden 케어 필드 적재 + 진단 응답 첨부 (백엔드) — 작업 프롬프트

## 0. 맥락·스코프 (먼저 읽을 것)

진단 파이프라인 안정화(FP 7.5~8·FN 0·임베딩 토대 검증) 후 **첫 기능 확장**. 단계 B' 탐색에서 garden API의 케어 필드가 풍부함을 확인했고((b) 용도), 이번에 실제 적재·연결한다.

**제품 결정 (사용자 확정)**:
- **status 무관 항상 케어 가이드 첨부** — 건강일 때도 지속 관리법 포함, 무조건 노출.
- **커버: 평가셋 9종부터** (작게 시작).

**설계 핵심**:
- (a) `species_normal_rag`(RAG, 자유서술 정상화 텍스트)와 **별개**. (b)는 **구조화 케어 필드**라 RAG/cosine이 아니라 **종명 키 lookup**(json/딕셔너리). 종이 정해지면 직접 조회.
- analyze `plant_name` → **단계 B' 종명 정규화 매핑 재사용·확장** → garden 종 키 → 케어 카드.

**이번 라운드 범위**: 백엔드 (적재 → 종 연결 → 응답 첨부 → 진단 회귀 확인). **프론트(ResultView.tsx) 표시는 다음 라운드** (응답 구조 확정 후).

⚠ **진단 로직(status·cause·status guard) 무변경.** 케어 가이드는 진단 결과에 **첨부만** 한다.

---

## PART A — 평가셋 9종 garden 커버 + 케어 필드 적재

### A-1. 9종 커버 확인

평가셋 9종 (PART B 점검 보고 기준):
- 단계 B'에서 확인됨(4종): 드라세나, 행운목(Dracaena fragrans), 스파티필룸, 산세베리아
- **미확인(5종)**: 아글라오네마, 접란, 스킨답서스, 고무나무, 몬스테라 — `gardenList`로 검색해 cntntsNo 확보, garden 표기 매핑. (흔한 실내식물이라 커버 가능성 높음)
- **종명 정규화 매핑 확장**: 단계 B' `species_mapping.json`에 5종 추가. 평가셋표기 → garden표기 → cntntsNo.
- garden에 없는 종은 **미커버로 기록**(케어 카드 없음 처리, 보고에 명시).

### A-2. 케어 필드 추출·적재

`gardenDtl`에서 **케어 필드** 추출 (단계 B' 보고에서 풍부 확인):
- `soilInfo`(토양), `watercycle{Sprng/Summer/Autumn/Winter}CodeNm`(계절별 물주기 4), `lighttdemanddoCodeNm`(광량), `grwhTpCodeNm`(생육적온), `hdCodeNm`(습도), `frtlzrInfo`(비료), `postngplaceCodeNm`(배치장소), `managelevelCodeNm`(관리난이도), `winterLwetTpCodeNm`(겨울최저온), `growthHgInfo`/`AraInfo`(생육크기).
- 코드값+한글명 쌍 → **한글명 위주 카드화**.
- **저장**: 종명 키 구조화 json (`scripts/build_care_guide.py` 신규 → `data/care_guide.json` 등 적절 위치). **RAG 아님** — 종 lookup용 딕셔너리.
- 품종 레벨(드라세나 12품종 등)은 **종 레벨 대표 카드**로 우선(같은 종은 케어 유사). 품종별 차이는 후속.

**보고**: 9종 중 케어 카드 확보 수 / 미커버 종.

---

## PART B — 종 연결 + 응답 첨부

1. **종 연결**: analyze `plant_name`(korean) → 종명 정규화 매핑 → garden 종 키 → 케어 카드 lookup.
   - 매핑 실패(미등록·오타·미커버): care_guide **빈 값/null** (진단엔 영향 없음).
2. **응답 첨부**: `graph.py` generate_node(+guard) 후, plant_name으로 케어 카드 조회 → 진단 응답에 `care_guide` 첨부. **status 무관 항상**.
3. **schemas.py**: 응답에 `care_guide` 필드 추가 (구조화 — 토양·계절별 물주기·광량·온습도·비료·배치·관리난이도 등).
4. ⚠ **진단 필드(status·cause·observed_symptoms·guard) 무변경** — care_guide는 별도 필드로 첨부만.

---

## PART C — 검증

1. ⚠ **진단 회귀 없음 (핵심)** — FP/FN/healthy_acc가 `979f63a`(FP 8.0/FN 0/healthy 0.758) 대비 **불변**. 케어 첨부가 진단을 안 건드려야 정상. 변하면 첨부 로직이 진단에 샌 것.
   - e2e 2회 평균.
2. **케어 커버리지** — 평가셋 33장 중 care_guide가 붙은 비율, 미커버 케이스.
3. **종 연결 정확도** — 33장 plant_name → 올바른 종 케어 카드 매칭되나 (오연결 = 엉뚱한 케어 점검).
4. **케어 카드 샘플** — 2~3종 raw (필드·한글명 확인).

⚠ `eval/baseline.json` 절대 덮어쓰기 금지.

---

## PART D — 보고 (커밋 전, 변경 보존)

1. 9종 garden 커버 + 미커버 종.
2. 케어 카드 구조 + 샘플(2~3종).
3. 종 연결 정확도 (오연결 유무).
4. **진단 회귀 불변 확인** (FP/FN/healthy).
5. care_guide 응답 구조 (다음 프론트 라운드 입력).
6. 판정 + 프론트 표시 라운드 권고.

---

## 환경 주의사항 (반드시 준수)

- garden API 키: `.env` `RDA_API_KEY` (농사로, 인증 정상 확인됨).
- `$env:RUN_EVAL_OUT`에 **`eval/` 접두 금지**. **Bash로 `$env:` 금지** → 측정은 **PowerShell 툴**.
- ⚠ **`eval/baseline.json` 절대 덮어쓰기 금지.**
- run_eval 콘솔 **cp949 깨짐** → 값은 **JSON UTF-8 읽기**.
- **2회 평균 패턴**, analyze 비결정성 FP ±1.
- GateGuard 훅: Bash/Edit/Write 전 "사실 명시".
- **커밋은 진단 회귀 통과(FP/FN 불변) 확인 후** — 백엔드 care_guide 첨부는 API 레벨로 완결적이라 커밋 가능하나, 측정·보고 후 사용자 결정.

---

## 산출물 요약

- `scripts/build_care_guide.py` + `data/care_guide.json` (종명 키 케어 카드)
- `species_mapping.json` 확장 (9종)
- `graph.py`(케어 lookup·첨부) + `schemas.py`(care_guide 필드) — 진단 로직 무변경
- `eval/after_phase_care_guide_{run1,run2,avg}.json` — 진단 회귀 불변 확인
- PART D 보고 (chat)
