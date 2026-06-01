# [1-10b] temperature 튜닝 + 1단계 최종 measurement + 문서 갱신 — 작업 프롬프트

> Claude Code 의뢰용. A 묶음 최종 자리. [1-10a] 완료(ad4d1e1 push) → 본 작업으로 1단계 완전 종료, B 묶음(데이터셋 교체) 진입 준비.
>
> 결정 확정: 영역 1 A (동시 동일 값) / 영역 2 A (0.0 기본 채택, ±2%p 이내 격차면) / 영역 3 (`eval/after_phase1.json` + v8 직접 비교) / 영역 4 (refactoring_log + README 갱신, git history 51594d2 참조 입력) / 영역 5 (단일 커밋) / 영역 6 (메모리 정리는 사용자 영역, 보고에 추천 항목만).

---

## 1. 컨텍스트 (한 줄)

[1-10a] 푸시 완료(ad4d1e1) → **[1-10b] A 묶음 마지막 자리**. temperature A/B/C 튜닝 + 1단계 최종 measurement + refactoring_log·README 전체 갱신을 단일 커밋으로. 통과 후 1단계 완전 종료.

핵심 성격:
- **temperature 튜닝 = 동작 변화 (코드 ~2~5줄)** — 결정성 확인이 핵심
- **measurement·문서 갱신 = 동작 무변경**
- **단일 커밋** — 채택 + 최종 measurement + refactoring_log·README

원칙:
- **0.0 기본 채택** — 1회 비교에서 plant_korean·precision·accuracy 모두 ±2%p 이내면 0.0. 격차 크면 종합 평가 후 사용자 보고.
- **참조 자료는 작업 디렉토리 무영향** — `git show 51594d2:<path>`로 stdout만 읽고 흡수. `git checkout`으로 트리 복원 안 함.
- **B 묶음 영역 절대 손대지 않음** — RAG 가중치·벡터 DB·데이터셋.

---

## 2. 사전 확인

### 2.1 환경

```bash
git status              # clean
git log -1 --oneline    # HEAD가 ad4d1e1
git branch --show-current
```

이상 시 즉시 중단·보고.

### 2.2 temperature 현재 설정 위치 확인

```bash
grep -rn "temperature\|Temperature" app/vision/ app/model_utils.py
```

대상:
- `app/vision/gemini.py` — Vision API 호출의 temperature 파라미터. SDK가 `google-genai`(decision #12)라 `GenerateContentConfig(temperature=...)` 패턴 예상
- `app/model_utils.generate_structured_diagnosis_with_gpt` — OpenAI API 호출의 `temperature=` 인자

현재 값 보고. SDK 기본값(미설정)이면 명시:
- Gemini google-genai: temperature 미설정 시 SDK 기본 (~1.0 가능성, 모델별 차이)
- OpenAI: 미설정 시 1.0

### 2.3 참조 자료 읽기 (작업 디렉토리 무영향)

```bash
git show 51594d2:"docs/work_history/단계별_시도_및_수정.md"
git show 51594d2:"docs/work_history/새로운_시도.md"
```

stdout으로 읽고 refactoring_log·README 갱신 시 입력 자료로 흡수. 작업 디렉토리에 파일 생성 안 함.

`51594d2` 커밋이 git history에 있는지 사전 확인:
```bash
git rev-parse 51594d2 2>&1 | grep -i unknown
# 기대: 출력 없음 (커밋 존재)
```

---

## 3. 작업 항목

### 3.1 temperature 3 옵션 비교 측정 (1회씩)

#### A. temperature=0.0 측정

코드 변경 (Vision + GPT 동시 동일 값):

```python
# app/vision/gemini.py — google-genai SDK
# Before
response = client.models.generate_content(
    model=model,
    contents=[...],
    config=GenerateContentConfig(...),  # temperature 미설정
)

# After
response = client.models.generate_content(
    model=model,
    contents=[...],
    config=GenerateContentConfig(temperature=0.0, ...),
)
```

```python
# app/model_utils.generate_structured_diagnosis_with_gpt — OpenAI
# Before
response = client.chat.completions.create(
    model=model,
    messages=[...],
)

# After
response = client.chat.completions.create(
    model=model,
    messages=[...],
    temperature=0.0,
)
```

측정:

```bash
RUN_EVAL_OUT=after_phase1_temp_00.json python scripts/run_eval.py
```

#### B. temperature=0.2 측정

코드 변경 — 둘 다 `temperature=0.2`로:

```bash
RUN_EVAL_OUT=after_phase1_temp_02.json python scripts/run_eval.py
```

#### C. temperature=0.5 측정

코드 변경 — 둘 다 `temperature=0.5`로:

```bash
RUN_EVAL_OUT=after_phase1_temp_05.json python scripts/run_eval.py
```

산출: `eval/after_phase1_temp_{00,02,05}.json` 3개.

### 3.2 결정 기준 적용 + 채택값 결정

비교표 (보고에 박을 것):

| 지표 | temp_00 | temp_02 | temp_05 | 채택 영향 |
|---|---|---|---|---|
| plant_korean | ? | ? | ? | ±2%p 비교 |
| precision | ? | ? | ? | ±2%p 비교 |
| accuracy | ? | ? | ? | ±2%p 비교 |
| recall | ? | ? | ? | 95% 이상 유지 확인 |
| JSON | ? | ? | ? | 100% 유지 확인 |
| latency | ? | ? | ? | 참고 |

**채택 로직**:
1. plant_korean·precision·accuracy 모두 3개 옵션이 ±2%p 이내 → **0.0 자동 채택** (결정성 우선)
2. 한 지표라도 격차 큼(>2%p) → 종합 평가 보고서 작성 후 사용자 결정 대기:
   - 어느 옵션이 어느 지표에서 우위인지
   - 결정성(0.0) 가치 vs 측정값 우위(0.2/0.5) 가치 비교
   - 사용자 결정 후 채택

### 3.3 채택값 박기 + 최종 measurement 2회

채택 temperature를 `gemini.py`·`model_utils.py`에 박은 후:

```bash
RUN_EVAL_OUT=after_phase1_run1.json python scripts/run_eval.py
RUN_EVAL_OUT=after_phase1_run2.json python scripts/run_eval.py
```

`eval/after_phase1.json` 산출 (run1·run2 평균값을 박는 별도 파일):
- 형식: `eval/after_phase1_run1.json`·`_run2.json`은 측정 raw 보존
- `eval/after_phase1.json`은 2회 평균 + 메타("temperature=X 채택", "v8 대비 변화" 등)

**결정성 확인 필수**: run1과 run2의 비트 단위 동일 여부 보고. temperature=0.0 채택 시 결정적 기대.

### 3.4 v8 직접 비교표 (refactoring_log 입력용)

| 지표 | v8 (baseline) | after_phase1 | 변화 |
|---|---|---|---|
| plant_korean | ? | ? | ? |
| recall | ? | ? | ? |
| precision | ? | ? | ? |
| accuracy | ? | ? | ? |
| latency | ? | ? | ? |
| 외부 API 호출 | 7회 (Plant.id + OpenAI×6) | 4회 (Gemini + OpenAI×3) | -43% |
| 비용 추정 | ? | ? | ? |

`eval/baseline.json` (v8) 읽어서 직접 비교. 비용 추정은 가능하면 추가, 어려우면 외부 호출 수 변화만.

### 3.5 refactoring_log.md 갱신

**참조 자료 읽기** (§2.3 명령으로 stdout 출력):
- `단계별_시도_및_수정.md` (562줄) — 시행착오 이력 (1단계 시작 전·초기 작업)
- `새로운_시도.md` (36줄) — Plant.id→LLM 전환 근거

**갱신 구조** (~3000~5000자 추가, 기존 refactoring_log에 append):

```markdown
## 1단계 (Plant.id 폐기 + RAG 정직화) — 마무리

### 전체 흐름

| 단계 | 결과 | 핵심 발견 |
|---|---|---|
| [1-1]~[1-4] | 신규 파일만 | (기존 코드 무변경) |
| [1-5] graph 와이어링 | ✅ 1차 게이트 | 부작용: recall 60→20% 보수화 |
| [1-7] generate 재설계 | ✅ | recall 20→100% |
| [1-6] keyword 축소 | ✅ | latency 32.4→25.5s (-21%) |
| [1-3] v4 | ❌ revert | FP 주범 = generate(analyze 아님) 입증 |
| [1-2.5] Vertex ADC | ✅ | latency 25.5→21.4s, 2회 측정 원칙 정립 |
| [1-7.5] generate status 경로 | ✅ | 영양 부족 FP -92%, 병해 의심 FP는 RAG 데이터셋 문제 |
| [1-8] retrieve 정비 | ✅ | fallback 보너스 [1-6] 이후 작동 0 입증 |
| [1-9] state/schema 슬림화 | ✅ 2차 게이트 | Plant.id 응답 잔재 제거 + analysis sub-object |
| [1-10a] RAG_FAILED 폐기 + Plant.id sweep | ✅ | 활성 LLM 경로 폐기, decision #3 본의 실행 |
| [1-10b] temperature 튜닝 + 최종 | ✅ | 1단계 완전 종료 |

### v8 → after_phase1 직접 비교
(§3.4 비교표)

### 핵심 결정 (decision #1~#N, 누적)
(기존 phase2_decisions 12건 + [1-7.5]~[1-10b] 신규)

### 핵심 발견 (자산)
- **eval-gate-noise-and-mapping-artifact** ([1-7.5]·[1-9] 측정 노이즈 패턴)
- **fp-root-cause-generate-not-analyze** ([1-3] v4 실패 + [1-7] 재설계)
- **rag-dataset-as-fp-lever** ([1-7.5] 발견: 병해 의심 FP +19% RAG 데이터셋 원인 → B 묶음 가속 근거)

### 미해결 (B 묶음 진입 조건)
- 병해 의심 FP 잔존 → 데이터셋 교체로 해소 (PennState·Missouri·농촌진흥청 가정원예·하우스플랜트 마스터 가이드)
- precision ~23% / accuracy ~50% — RAG 데이터셋 본질 해소 후 재측정
- plant_korean 매핑 사전 아티팩트 (dracaena 누락 학명 등) — 별도 매핑 작업
```

### 3.6 README.md 갱신

**갱신 구조** (~2000자):

```markdown
## 진행 상황 (1단계 마무리)

식물 사진을 받아 한국어로 진단 결과를 돌려주는 시스템. 1단계에서 Plant.id API와 RAG 정직성 정리를 마무리했고, 다음은 데이터셋 교체(B 묶음).

### 1단계 결과 (v8 → after_phase1)
(§3.4 비교표 요약)

- 외부 API 호출: 7회 → 4회 (-43%)
- latency: ?s → ?s
- plant_korean: ?% → ?%
- recall: 100% 유지
- precision: ?% (B 묶음에서 본질 해소 예정)

### 현재 시스템 구조
1. analyze (Gemini 2.5 Pro) — 종 식별 + 시각 묘사 + 관찰 증상
2. keyword (GPT) — RAG 검색 쿼리·키워드 추출
3. retrieve (Chroma) — main_rag(k=7) + ncpms_rag(k=3)
4. generate (GPT) — structured_result JSON 생성

### 평가셋
33장, plant_korean·recall·precision·accuracy·JSON·latency 측정

### 후속 계획
- B 묶음: RAG 데이터셋 교체 (~1~2주)
- C 묶음: 시계열 추적
- D 묶음: 단계적 진단(객관식)
- E 묶음: 속도·비용·튜닝
```

기존 README의 잘못된 정보(예: "7회 호출" 등) 정정 + Plant.id 관련 모든 언급 제거. [1-10a]에서 일부 정정했지만 마무리 갱신.

---

## 4. 변경 금지 (범위 외)

- **B 묶음 영역**: RAG 가중치(`GENERIC_DOC_PENALTY`·`PLANT_NAME_MATCH_BOOST`·NCPMS 0.8·UC_IPM 0.85), 벡터 DB 컬렉션(`data/vector_db/`), 임베딩 모델
- **배포 영역**: `BACKEND_API_URL` env, docker-compose
- **C·D·E 묶음**: 시계열 추적, 단계적 진단, 속도·비용 튜닝 코드
- **analyze·keyword·retrieve·generate 본체**: temperature 외 무변경
- **프론트**: [1-10b]에서 손대지 않음 (temperature는 백엔드만)

위 중 하나라도 변경 필요 판단되면 **작업 중단 후 보고**.

---

## 5. 검증

### 5.1 정적

```bash
python -c "from app.main import app; print('ok')"
pytest tests/ -v
```

### 5.2 측정 게이트 (§3.3 최종 2회)

[1-10a] 평균 대비 -5%p 이내:

| 지표 | [1-10a] | [1-10b] 게이트 (≥) |
|---|---|---|
| plant_korean | 85.27% | 80.27% |
| recall | 100% | 95% |
| precision | (보고값) | -5%p |
| accuracy | (보고값) | -5%p |
| JSON | 100% | 100% 절대 |
| latency | 20.8s | ± |

**결정성**: temperature=0.0 채택 시 run1==run2 비트 단위 동일 기대. 같지 않으면 보고.

### 5.3 문서 검증

- refactoring_log·README 변경 후 markdown 렌더링 확인 (가능하면)
- 잘못된 정보 잔존 없는지 grep:
  ```bash
  grep -rn "Plant.id\|PLANT_ID\|7회\|plant_id" README.md docs/
  # 기대: 보존이 필요한 곳(이력 기록)만 남음
  ```

---

## 6. 게이트 ([1-10a] 대비 -5%p 이내)

§5.2 표 그대로.

**예상**: temperature 0.0 채택 시 결정성 강화 → run1==run2 동일. plant_korean noise 줄어들 가능성. 다만 analyze가 google-genai이라 temperature가 한국어 매핑에 영향 줄지 미지수.

회귀 시:
- temperature 0.0이 generate에서 답변 단조로움 유발했을 가능성 — 0.2 재시도
- 측정 스크립트 매핑 회귀일 가능성 (낮음, 본 작업 매핑 무변경)
- 케이스별 분석 후 채택값 변경

---

## 7. 롤백 전략

게이트 미통과 시:

1. **즉시 `git revert HEAD`** — 단일 커밋이라 1회 revert로 [1-10a] 푸시 상태 복원
2. 원인 진단: 어떤 옵션이 어느 지표에서 미달인지
3. 분기:
   - 0.0이 미달 → 0.2 또는 0.5로 채택값 변경, 재커밋
   - 모든 옵션 미달 → [1-10b] 보류, 사용자와 게이트 임계값 조정 논의

---

## 8. 작업 완료 후 보고

### 8.1 사전 확인 결과
- 현재 temperature 위치·값
- 51594d2 커밋 존재 확인
- 참조 자료 분량 (단계별_시도_및_수정 562줄, 새로운_시도 36줄)

### 8.2 3 옵션 비교 측정 결과

§3.2 비교표 + 채택값 + 근거 ("±2%p 이내라 0.0 자동 채택" 또는 "격차 X%p로 종합 평가 후 0.2 채택" 등).

### 8.3 채택값으로 최종 measurement 2회

| 지표 | run1 | run2 | 평균 | 결정성 |
|---|---|---|---|---|
| plant_korean | ? | ? | ? | run1==run2? |
| recall | ? | ? | ? | ? |
| precision | ? | ? | ? | ? |
| accuracy | ? | ? | ? | ? |
| JSON | ? | ? | ? | ? |
| latency | ? | ? | ? | ? |

### 8.4 v8 직접 비교표

§3.4 표 채워서.

### 8.5 refactoring_log·README 갱신 분량

- refactoring_log: 추가 라인 수, 핵심 section 미리보기
- README: 갱신된 section 미리보기

전체를 보고에 박지 말고 (분량 큼), section별 첫 줄·구조 정도 미리보기 + 사용자 검토 받기.

### 8.6 메모리 정리 추천 항목 (사용자 영역, 강제 아님)

- 보존 추천: `eval-gate-noise-and-mapping-artifact`, `fp-root-cause-generate-not-analyze`, decision #11(gemini-2.5-pro), decision #12(google-genai SDK)
- 갱신 검토: ADC quota project 메모 (단순 환경 설정, 보존 의문)
- 신규 추가 가능: "1단계 마무리: v8→after_phase1 외부 호출 7→4회, FP는 B 묶음으로"

사용자가 `memory_user_edits`로 직접 정리. 본 작업에서는 추천만.

### 8.7 커밋 메시지 (제안)

```
refactor: temperature 튜닝(0.0 채택) + 1단계 최종 measurement + 문서 갱신 ([1-10b])

temperature 튜닝 (decision #6):
- Vision(google-genai) + GPT(OpenAI) 동시 동일 값
- 3 옵션 비교: 0.0/0.2/0.5
- 채택: 0.0 (결정성 우선, ±2%p 이내 격차 또는 0.0이 우위)

1단계 최종 measurement:
- eval/after_phase1.json (2회 평균, [채택값] 적용)
- 결정성: run1==run2 [비트 단위 동일 / 1건 차이 등]
- v8 → after_phase1 비교: 외부 API 7→4회, latency Xs→Ys, plant_korean X%→Y%

문서 갱신:
- docs/refactoring_log.md: [1-1]~[1-10] 전체 흐름 + 결정 누적 + 미해결
- README.md: 1단계 마무리 상태, 잘못된 정보 정정

범위 외 (B 묶음 진입 조건):
- 병해 의심 FP 잔존 (RAG 데이터셋 본질 해소 필요)
- precision ~23% / accuracy ~50% (B 묶음에서 재측정)

measurement: eval/after_phase1_run{1,2}.json, eval/after_phase1.json
gate: -5%p 이내 통과 ([1-10a] 대비)
```

### 8.8 커밋·push (사용자 확정 후)

```bash
git add app/vision/gemini.py app/model_utils.py
git add eval/after_phase1_temp_00.json eval/after_phase1_temp_02.json eval/after_phase1_temp_05.json
git add eval/after_phase1_run1.json eval/after_phase1_run2.json eval/after_phase1.json
git add docs/refactoring_log.md README.md
git add docs/work_history/1-10b_*.md   # 작업프롬프트 md
git status                              # untracked·미스테이징 0 확인
git commit -m "..."
git push
```

---

## 9. 작업 순서

1. **사전 확인** §2 — git·temperature 위치·51594d2 존재.
2. **3 옵션 측정** §3.1 — temp_00 → temp_02 → temp_05.
3. **결정 기준 적용** §3.2 — ±2%p 자동 채택 or 종합 평가 보고.
4. **채택값 박기 + 최종 2회** §3.3.
5. **v8 비교표** §3.4.
6. **참조 자료 읽기 (git show 51594d2)** + **refactoring_log 갱신** §3.5.
7. **README 갱신** §3.6.
8. **정적 검증** §5.1 + 문서 grep §5.3.
9. **게이트 판정** §6. 미통과 시 §7 롤백.
10. **보고** §8 — 사용자 확정 대기.
11. 사용자 OK 후 **커밋·push** §8.8.

---

## 10. 주의 사항 (재강조)

- **temperature 적용은 둘 다 동시**: `gemini.py`와 `model_utils.py` 동일 값. 분리 튜닝 X (영역 1 결정).
- **결정 기준 자동/수동 분기**: ±2%p 이내면 0.0 자동, 격차 크면 사용자 결정 대기 (영역 2 결정).
- **참조 자료는 작업 디렉토리 무영향**: `git show <commit>:<path>` 사용, `checkout`으로 파일 복원 안 함.
- **51594d2 커밋 존재 사전 확인**: 만약 없으면 (rebase 등으로 사라졌으면) 사용자에게 보고 후 다른 commit hash 찾기.
- **메모리는 사용자 영역**: 보고에 추천만, 직접 `memory_user_edits` 호출 안 함.
- **단일 커밋**: temperature 채택 코드 + 측정 산출 + 문서 갱신 모두 한 커밋.
- **B 묶음 영역 절대 무변경**: RAG 가중치·벡터 DB·데이터셋.
