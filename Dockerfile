# Plantia 백엔드(FastAPI) — Cloud Run 배포용 이미지.
#
# 담는 것: app/ 코드 + 런타임 의존성 + RAG 자산(data/vector_db, data/care_guide.json).
# 빼는 것: 평가셋·테스트·문서·원본 데이터·시크릿(.env*) — .dockerignore/.gcloudignore 참조.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성 레이어를 먼저 굳혀, 코드만 바뀔 때 재빌드가 빨라지게 분리.
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# 진단 파이프라인이 런타임에 읽는 자산.
#   data/vector_db/       <- app/graph.py:_vector_db_path() (Chroma: a_dataset_rag/b_dataset_rag)
#   data/care_guide.json  <- app/care_guide.py:_CARE_GUIDE_REL
# 코드가 '<프로젝트 루트>/data/...'로 경로를 계산하므로 WORKDIR 아래 같은 구조를 유지한다.
COPY data/vector_db/ ./data/vector_db/
COPY data/care_guide.json ./data/care_guide.json

COPY app/ ./app/

# Cloud Run이 PORT env를 주입한다(기본 8080). 로컬 docker run에서도 같은 기본값으로 뜨게 둔다.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
