# Plant Diagnosis API

식물 이미지를 받아 **Gemini 2.5 Pro**로 종을 식별·관찰하고, **LangGraph** 파이프라인으로 키워드 추출·**RAG** 검색·최종 진단 답변을 생성하는 **FastAPI** 서버입니다. CPU 및 외부 API만 사용 (GPU 미사용).

**현재 단계**: **1단계(Plant.id 폐기 + RAG 정직화) 완전 종료** ([1-10b]까지). 다음은 B 묶음(RAG 데이터셋 교체). 최신 진행 상태는 [`docs/refactoring_log.md`](docs/refactoring_log.md) 참조.

---

## 무엇을 만들고 있나

기존 시스템은 한 번 진단에 외부 API를 7회(Plant.id·OpenAI×6) 호출하고, 프롬프트에 "병명 추정 금지·진단 금지·처방 금지" 같은 강제 규칙이 누적돼 모호한 답만 반복했고, RAG 검색 실패 시 가짜 답변을 만들어 사용자에게 보여줬다.

1단계는 그 7회 호출을 4회로 줄이면서(Gemini 2.5 Pro로 식별·묘사·증상 관찰 통합) 프롬프트의 강제 규칙을 풀어 자연스러운 진단으로 전환하는 작업.

```
Before: identify(Plant.id) → describe(OpenAI) → keyword → retrieve → generate
After:  analyze(Gemini)    →                     keyword → retrieve → generate
```

## 핵심 의사결정

| 결정 | 근거 |
|---|---|
| analyze는 "관찰" 6필드(`plant_name`·`plant_name_korean`·`plant_confidence`·`alt_candidates`·`visual_description`·`observed_symptoms`), generate는 "진단"(`status` enum) — 책임 분리 | analyze의 `is_healthy`와 generate의 `status` 모순은 RAG가 새 정보를 가져온 정상 동작. 강제로 일치시키면 RAG 의미가 깎임 |
| 강제 = JSON 형식·status enum·언어(한국어) 3개만. 나머지는 권장 톤 | 강제 규칙 누적이 모호한 답의 원인. AI에게 자연스러운 답 여유 확보 |
| 회귀 임계 -5%p. 매 단계 측정→통과 후 머지 | 직관 평가 대신 데이터로 회귀 차단 |
| Vision Provider 추상화(Protocol + Provider) | 추후 Claude·OpenAI Vision 등 교체 시 1줄 변경 |
| 평가셋 이미지는 git에서 제외 | 토큰·용량·라이선스(CC BY-SA 등) — `labels.json`의 `image_path`만 공유 |

전체 결정 12개는 [`docs/phase2_decisions.md`](docs/phase2_decisions.md).

## 진행 현황 (1단계 — 완전 종료)

| 단계 | 작업 | 상태 |
|---|---|---|
| [1-1]~[1-4] | Protocol·GeminiProvider·프롬프트·factory | ✅ |
| **[1-5]** | **graph 와이어링** 🔴 1차 게이트 | ✅ 통과 |
| [1-7] | generate 재설계 | ✅ recall 20→100% |
| [1-6] | keyword_node 축소 | ✅ latency 32.4→25.5s (-21%) |
| [1-2.5] | Vertex ADC 전환 | ✅ latency →21.4s |
| [1-7.5] | generate status 경로 | ✅ 영양부족 FP -92% |
| [1-8] | retrieve_node 정비 | ✅ 死 fallback 제거 |
| **[1-9]** | **state/schema 슬림화** 🔴 2차 게이트 | ✅ 통과 |
| [1-10a] | RAG_FAILED 폐기 + Plant.id sweep | ✅ |
| [1-10b] | temperature 튜닝(0.0 채택) + 최종 측정 | ✅ |

### 1단계 결과 (v8 baseline → after_phase1, 2회 평균)

| 지표 | v8 | after_phase1 |
|---|---|---|
| 외부 API 호출 | 7회 (Plant.id + OpenAI×6) | **4회** (Gemini + OpenAI×3) — **-43%** |
| recall (아픈 식물 검출) | 60.0% | **100%** (한 장도 안 놓침) |
| precision | 23.08% | 23.27% (B 묶음에서 본질 해소 예정) |
| 식물명(plant_korean) | 90.0% | 88.58% |
| latency 평균 | 21.07s | **19.05s** |
| JSON 파싱 | 100% | 100% (유지) |

is_healthy binary accuracy는 63.6%→50.0%로 내려갔는데, 이는 회귀가 아니라 **recall 우선(아픈 식물을 놓치지 않음)의 의도된 트레이드오프**다. FP의 본질 원인은 RAG 병해 코퍼스 매칭 한계이며 B 묶음(데이터셋 교체)에서 해소한다. 게이트 통과 현황·결정성 발견(temperature=0에서도 비결정)은 [`docs/refactoring_log.md`](docs/refactoring_log.md).

---

## 구성

| 구분 | 내용 |
|---|---|
| API | FastAPI |
| 파이프라인 | LangGraph: `analyze → keyword → retrieve → generate` |
| Vision | Gemini 2.5 Pro (식별·묘사·증상 관찰 통합) |
| RAG | Chroma (`data/vector_db`) — main_rag(k=7) + ncpms_rag(k=3) |
| LLM / 임베딩 | OpenAI (generate·keyword 영문 번역·임베딩) |

## 요구 사항

- Python **3.12** (`.python-version` 참고)
- [Gemini](https://aistudio.google.com/) API 키
- [OpenAI](https://platform.openai.com/) API 키
- RAG DB 구축·갱신 시: 농촌진흥청 NCPMS **RDA_API_KEY** (공공데이터포털 등에서 발급)

## 설치

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 두고 `python-dotenv`로 불러옵니다. **키는 코드에 넣지 마세요.**

| 변수 | 용도 |
|---|---|
| `GOOGLE_CLOUD_PROJECT` | analyze_node — Vertex AI 모드(권장). 설정 시 Gemini를 Vertex ADC로 호출 |
| `GOOGLE_CLOUD_LOCATION` | Vertex region. 미설정 시 `asia-northeast1`(도쿄) 기본 |
| `GEMINI_API_KEY` | analyze_node — Google AI Studio 모드(fallback). Vertex 미설정 시에만 사용 |
| `OPENAI_API_KEY` | generate(GPT-4o-mini)·keyword 영문 번역·텍스트 임베딩(Chroma) |
| `RDA_API_KEY` | `scripts/build_rag_db.py`로 NCPMS 데이터 수집 시에만 |

### Gemini 인증 — Vertex AI (권장) vs Google AI Studio (fallback)

두 모드 중 하나를 골라 환경변수에 박습니다. **Vertex 모드가 GCP 크레딧을 사용**하며,
`GeminiProvider`가 `GOOGLE_CLOUD_PROJECT` 유무로 자동 분기합니다.

**Vertex 모드 (권장)** — `.env`에 다음:

```
GOOGLE_CLOUD_PROJECT=<your-project>
GOOGLE_CLOUD_LOCATION=asia-northeast1
```

사전 인증: `gcloud auth application-default login`을 1회 실행합니다(로컬 ADC 캐시 저장).
서울(`asia-northeast3`)은 Gemini 2.5 Pro 미지원이라 도쿄(`asia-northeast1`)를 씁니다.

**AI Studio 모드 (fallback)** — `.env`에 `GEMINI_API_KEY=...`를 박습니다.
Vertex 환경변수가 비어 있을 때만 사용됩니다.

## RAG 벡터 DB 구축 (선택)

NCPMS 병해 정보 + houseplant 자료를 Chroma에 넣을 때:

```bash
python scripts/build_rag_db.py
```

결과는 `data/vector_db` 아래에 저장됩니다. API는 기존 DB가 있으면 검색에 사용하고, 없거나 로드 실패 시 로그만 남기고 동작합니다.

## 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 문서: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | 상태 및 외부 API 키 설정 여부 |
| `POST` | `/diagnose` | 요청 본문에 `image_base64`(필수), `return_debug`(선택) — Base64 이미지 진단 |

### `/diagnose` 요청

- `image_base64`: 진단할 이미지의 Base64 문자열
- `return_debug`: `true`이면 `keywords`, `sick_keys` 등 디버그 필드 포함

## 평가·측정 재현

```bash
# 33장 평가셋으로 회귀 측정
RUN_EVAL_OUT=after_phase1_keyword.json python scripts/run_eval.py
```

baseline·after_phase1_* 측정 결과는 `eval/` 아래. v8 baseline은 보존(변경 금지).

평가셋 이미지(`test_data/main_eval/images/` 33장 + 후보 100+장)는 git에서 제외 — 라이선스(iNaturalist CC BY 등)·용량·토큰 부담 고려. `labels.json`의 `image_path`로 충분하므로 본인 환경에서 같은 경로에 이미지를 배치하면 작동.

## 폴더 구조

```
plant-diagnosis/
├── app/
│   ├── vision/               # VisionProvider Protocol + GeminiProvider
│   ├── nodes/                # analyze_node factory
│   ├── graph.py              # LangGraph 4노드
│   ├── prompts.py
│   ├── model_utils.py
│   └── main.py
├── tests/                    # pytest (25건)
├── scripts/
│   ├── run_eval.py           # baseline·회귀 측정
│   └── eval_rag.py           # RAGAS 측정
├── docs/
│   ├── phase2_decisions.md   # 결정 12개 누적
│   ├── phase2_refactoring_plan.md
│   ├── refactoring_log.md    # 1단계 진행 흐름 요약
│   ├── eval_collection_spec.md
│   └── work_history/         # 각 단계 진단·작업 프롬프트 md
├── test_data/
│   ├── main_eval/
│   │   ├── labels.json
│   │   └── images/           # ⛔ git 제외 — 로컬만
│   └── labeling_vocab.py
├── eval/                     # baseline·측정 결과
└── data/vector_db/           # Chroma
```

## 의사결정 추적

| 궁금한 것 | 보는 곳 |
|---|---|
| 단일 결정 근거 | `docs/phase2_decisions.md` (#1~#12) |
| 1단계 전체 흐름·게이트 통과 현황 | `docs/refactoring_log.md` |
| 각 단계 결정 영역·옵션 비교·롤백 전략 | `docs/work_history/1-N_*.md` |
| Phase 2 전체 설계 산출물 | `docs/phase2_refactoring_plan.md` |

## 개발 시 참고

- 이미지 디코딩·PIL 처리는 이벤트 루프를 막지 않도록 스레드 풀에서 실행.
- 외부 호출은 각 SDK의 비동기 클라이언트 사용 (`genai.Client.aio`, `AsyncOpenAI`). 공용 httpx client 주입은 [1-10a]에서 제거(노드가 미사용이던 死 의존).
- temperature는 `app/model_utils.LLM_TEMPERATURE`(=0.0) 단일 상수로 Vision 생성자 기본값과 generate GPT 호출이 공유.
- 재시도: `app/nodes/analyze.py`의 `_with_retry` helper (429 60s / 5xx 2s backoff, max 2회).

## 후속 계획

1단계(Plant.id 폐기 + RAG 정직화)가 종료됐고, 다음 묶음은 다음과 같다.

- **B 묶음 — RAG 데이터셋 교체**: PennState Extension(Houseplant Problems)·Missouri Botanical Garden(Plant Finder/Problem Solver)·농촌진흥청 가정원예·『하우스플랜트 마스터 가이드』로 코퍼스를 실내식물 도메인에 맞춤. precision·병해 의심 FP의 본질 해소.
- **C 묶음 — 시계열 추적**: 같은 식물의 이전 진단 N개를 컨텍스트로 넣어 변화 추이("지난주보다 갈변 진행") 코멘트.
- **D 묶음 — 단계적 진단(객관식)**: 1차 진단 후 3~5개 객관식 질문(물 주기·위치·최근 변화)으로 2차 진단 보정.
- **E 묶음 — 속도·비용·튜닝**: 추론 속도 개선, Gemini 가격 추정, PaliGemma fine-tuning 검토.

## 라이선스 / 데이터

코드: MIT.

Gemini·OpenAI·NCPMS 이용 약관 및 API 정책을 각 서비스 기준으로 준수. 평가셋 이미지는 git 제외 (iNaturalist·Wikimedia·본인 촬영 혼재, 라이선스 별도 관리).
