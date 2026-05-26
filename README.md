# Plant Diagnosis API

식물 이미지를 받아 **Plant.id**로 식별하고, **LangGraph** 파이프라인으로 설명·키워드·**NCPMS(SVC01) RAG** 검색·최종 답변을 생성하는 **FastAPI** 서버입니다. CPU 및 외부 API만 사용합니다(GPU 미사용).

## 구성

| 구분 | 내용 |
|------|------|
| API | FastAPI |
| 파이프라인 | LangGraph: `identify → describe → keyword → retrieve → generate` |
| 식별 | Plant.id API v3 |
| RAG | Chroma (`data/vector_db`), NCPMS npmsAPI SVC01 기반 청크 |
| LLM / 임베딩 | OpenAI (langchain-openai) |

## 요구 사항

- Python **3.12** (`.python-version` 참고)
- [Plant.id](https://plant.id/) API 키
- [OpenAI](https://platform.openai.com/) API 키
- RAG DB를 새로 구축하거나 갱신할 때: 농촌진흥청 NCPMS **RDA_API_KEY** (공공데이터포털 등에서 발급)

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
|------|------|
| `PLANT_ID_API_KEY` | Plant.id 식별 |
| `OPENAI_API_KEY` | GPT 호출·텍스트 임베딩(Chroma 검색) |
| `RDA_API_KEY` | `scripts/build_rag_db.py`로 NCPMS 데이터 수집 시에만 필요 |

## RAG 벡터 DB 구축 (선택)

NCPMS 병해 정보를 Chroma에 넣을 때:

```bash
python scripts/build_rag_db.py
```

결과는 `data/vector_db` 아래에 저장됩니다. API는 기존 DB가 있으면 검색에 사용하고, 없거나 로드에 실패하면 로그만 남기고 동작합니다.

## 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 문서: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 상태 및 `PLANT_ID` / `OPENAI` 키 설정 여부 |
| `POST` | `/diagnose` | 요청 본문에 `image_base64`(필수), `return_debug`(선택) — Base64 이미지 진단 |

### `/diagnose` 요청 예 (필드)

- `image_base64`: 진단할 이미지의 Base64 문자열
- `return_debug`: `true`이면 `keywords`, `sick_keys` 등 디버그 필드 포함

## 개발 시 참고

- 이미지 디코딩·PIL 처리는 이벤트 루프를 막지 않도록 스레드 풀에서 실행합니다.
- Plant.id·OpenAI 등 외부 호출은 `httpx.AsyncClient` 및 비동기 클라이언트를 사용합니다.

## 라이선스 / 데이터

Plant.id·OpenAI·NCPMS 이용 약관 및 API 정책을 각 서비스 기준으로 준수하세요.
