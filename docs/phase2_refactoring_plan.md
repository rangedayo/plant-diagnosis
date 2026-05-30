# Phase 2: 리팩토링 실행 계획 요청

## 컨텍스트
Phase 1 진단 보고서는 잘 받았고 전반적으로 동의해. 다만 진행 방향에 대해 몇 가지 결정사항을 먼저 알려줄게.

### 확정된 진행 순서 (이 순서대로 작업할 거야)
1. **Plant.id 제거 + Gemini 통합** (analyze_node 도입)
2. **프롬프트·후처리 강제 완화**
3. **데이터셋 교체** (NCPMS → 실내 식물 코퍼스, 추후 자료 조사 후 진행)
4. **시계열 추적 MVP** (SQLite + plant_handle)
5. **단계적 진단** (clarify_node + refine_node)

→ **데이터셋 교체보다 코드 정리(1, 2단계)를 먼저 한다.** 이유는 데이터셋 교체는 자료 수집/정제 시간이 오래 걸리고, 코드가 깔끔해진 상태에서 데이터를 넣어야 효과 측정이 가능하기 때문.

### Phase 1에서 동의한 결정사항
- analyze_node는 Gemini Flash 사용 (모델명은 gemini-2.5-flash로 시작, 추후 gemini-3.5-flash 비교 검토)
- 통합 호출 JSON 스키마: plant_name, plant_name_korean, plant_confidence(low/med/high), alt_candidates, visual_description, observed_symptoms, is_healthy(bool), health_notes
- confidence는 calibrated probability가 아닌 self-reported enum으로 재정의
- 강제 로직은 "프롬프트 강제 + 후처리 강제 이중" 패턴을 풀어내고, 출력 형식(JSON 키)·status enum·언어(한국어) 3개만 강제 유지
- 최종 답변 LLM은 일단 GPT-4o-mini 유지, 1단계 완료 시점에 Gemini와 품질 비교 후 통일 여부 결정

### Phase 1에서 보완 요청한 부분
- **평가용 이미지 셋 준비**: 1단계 시작 전 평가용 이미지 20~30장 + 정답 라벨 수집 필요 (회귀 테스트 baseline)
- **임베딩 모델 재검토**: 3단계 데이터셋 교체 시 데이터 언어에 따라 text-embedding-3-small 유지 또는 변경
- **이미지 저장 정책**: 시계열 추적용 이미지 저장 방식 (image_hash + 로컬 디렉토리 권장)

## 너에게 부탁하는 것 (Phase 2)

이번 Phase에서는 **1단계(Plant.id 제거 + Gemini 통합)와 2단계(강제 로직 완화)에 집중**해줘. 3~5단계는 큰 그림만 잡고, 본격 설계는 다음 Phase로 미루자.

여전히 **코드 직접 수정은 금지**. 계획·다이어그램·예시·인터페이스 정의만 작성해줘.

### 2-A. 새 아키텍처 다이어그램 (1, 2단계 완료 시점)

다음을 텍스트로 표현해줘:

1. **LangGraph 노드 구성도**
   - 현재: identify → describe → keyword → retrieve → generate (5노드)
   - 신규: analyze → keyword → retrieve → generate (4노드, 또는 더 단순화)
   - 각 노드의 입력/출력 state 변화
   - keyword 노드를 별도 LLM 호출로 유지할지, analyze에서 받은 observed_symptoms를 그대로 쓸지 결정 + 근거

2. **DiagnosisState 슬림화 후 필드 목록**
   - 추가/제거/타입 변경 필드 명확히
   - 각 필드가 어느 노드에서 채워지고 어느 노드에서 소비되는지

3. **외부 API 호출 흐름**
   - 1회 진단당 외부 호출 횟수 변화 (Before → After)
   - 호출 순서와 의존성

### 2-B. 단계별 리팩토링 순서 + 검증 방법

1단계와 2단계를 각각 **하위 작업 단위**로 쪼개줘. 한 작업이 너무 크면 안전하게 진행 못 하니까, 각 작업은 다음 조건을 만족해야 해:

- 한 작업당 1~3시간 분량
- 작업 후 즉시 검증 가능 (어떤 명령어/테스트로?)
- 롤백 가능 (어떤 커밋 단위로 묶을지)

예시 형식:
[1단계-작업1] Gemini SDK 추상화 계층 생성

작업: app/vision/ 디렉토리 생성, VisionProvider 인터페이스 정의, GeminiProvider 구현체 작성
검증: pytest tests/vision/test_gemini_provider.py 또는 수동 테스트 스크립트
커밋 단위: 1개 (feat: add vision provider abstraction)
위험도: 낮음 (기존 코드 안 건드림)


이런 형식으로 각 단계당 5~10개 작업 단위 나열해줘.

특히 다음 위험 지점을 명확히 표시해줘:
- 기존 동작이 일시적으로 깨지는 작업 (예: identify_node 제거 시점)
- 환경변수/스키마/DB 변경이 필요한 작업
- 프론트엔드도 같이 손봐야 하는 작업

### 2-C. 새 프롬프트 설계 가이드라인 + 예시

1. **프롬프트 작성 원칙** (1~2단계 방향 반영)
   - 무엇을 강제하고 무엇을 풀어줄지의 판단 기준
   - "강제 = 출력 형식·status enum·언어"만 유지하는 구체적 의미

2. **새 프롬프트 예시 2개 (Before → After)**
   - 예시 1: DESCRIBE_IMAGE_SYSTEM → analyze_node용 새 프롬프트
     - 현재 "진단 X, 병명 추정 X, 처방 X" 3중 금지를 어떻게 풀어주는지
     - JSON 스키마를 어떻게 명시하는지
     - Korean 출력 보장 방법
   - 예시 2: STRUCTURED_DIAGNOSIS_JSON_SYSTEM → 완화된 버전
     - REQUIRED_WEAK_EVIDENCE_PHRASE 같은 강제 문구를 어떻게 더 자연스럽게 처리할지
     - action_plan 패딩 같은 후처리를 제거하면서도 안정성 유지하는 방법

각 예시에 **왜 이렇게 바꿨는지 설명**도 포함.

### 2-D. Vision 모델 추상화 인터페이스

향후 Gemini → Claude/GPT/PaliGemma 등으로 갈아끼울 수 있는 구조:

1. **인터페이스 정의** (Python ABC 또는 Protocol)
   - 입력: image_bytes, optional prompt context
   - 출력: 표준화된 dict 또는 Pydantic 모델 (1-B의 JSON 스키마)
   - 에러 처리 방식 (rate limit, timeout, invalid response)

2. **GeminiProvider 구현 스케치**
   - google-generativeai SDK 호출 패턴
   - JSON mode 활용 방법
   - 비동기 처리 (현재 코드의 AsyncOpenAI 패턴과 일관성)

3. **테스트 전략**
   - 실제 API 안 부르고 mock으로 테스트하는 방법
   - 통합 테스트는 별도 marker로 분리

### 2-E. 3~5단계 큰 그림 (스케치만)

이번 Phase에서 본격 설계는 안 해도 되지만, 다음 사항만 미리 결정해두면 좋겠어:

1. **데이터셋 교체 (3단계)**
   - 어떤 출처를 우선 검토할지 추천 (UC IPM Home, PennState, RHS 등)
   - 청크 형식 권장사항 (현재 houseplant.txt 구조 유지? 새로 설계?)
   - 메타데이터 필드 (출처, 식물 종류, 증상 카테고리 등)

2. **시계열 추적 (4단계)**
   - SQLite 스키마 초안 (테이블 2~3개)
   - plant_handle을 어떻게 발급할지 (UUID? 사용자 지정 nickname?)
   - load_history_node가 graph 어느 위치에 들어갈지

3. **단계적 진단 (5단계)**
   - clarify_node가 어느 조건에서 활성화될지 (conditional edge)
   - 객관식 질문을 LLM 생성으로 할지, 고정 질문 풀에서 선택할지 + 근거

### 2-F. 평가 인프라 보완

Phase 1에서 RAGAS는 있다고 했지만, 1~2단계 리팩토링의 효과를 측정하려면 추가가 필요해.

1. **회귀 테스트 셋 정의**
   - 평가용 이미지 20~30장에 어떤 라벨이 필요한지 (식물명, 정답 진단, 권장 해결책 등)
   - 라벨 포맷 (JSON 권장)
   - 어떻게 측정할지: 정확도, 일관성, 답변 품질

2. **각 단계 완료 시점의 측정 지표**
   - 1단계 완료: 외부 호출 횟수, 평균 응답 시간, baseline RAGAS 점수
   - 2단계 완료: 강제 로직 제거 후 RAGAS 변화, 답변 자연스러움 (정성 평가)

## 작업 방식 (중요)

- **출력은 섹션별로 명확히 구분** (2-A, 2-B, 2-C, 2-D, 2-E, 2-F)
- **각 섹션 끝에 "핵심 요약 3줄"** 유지
- **추정 부분은 "(추정)" 표시**
- **Phase 1과 마찬가지로 코드 직접 수정 금지**
- 내 결정에 동의 안 되는 부분 있으면 솔직히 말해줘 (특히 코드 정리 우선 결정에 대해)
- 분량이 길어질 것 같으면 **2-A부터 순차적으로 출력**해도 됨. 한 섹션 끝나면 "다음 섹션 진행할까?" 물어봐줘.

## 추가 컨텍스트 (Phase 1과 동일하지만 재확인)

- 포트폴리오 + 학습용 프로젝트
- 4~6주 내 마무리 목표
- 면접에서 의사결정 과정 설명 가능해야 함
- 백엔드: Python 3.12, FastAPI, LangGraph, Chroma
- 프론트엔드: Next.js (별도 작업)
- Phase 1에서 식별한 모든 즉시 삭제 / 단순화 / 강제 완화 영역은 1~2단계 작업에 반영

Phase 2 시작해줘.