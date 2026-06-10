# 작업: 챗봇 단계 2 — 프론트 질문 UI + 2차 보정 진단 연결

> 사양: 「챗봇 2차진단 A안 설계」(§3 UX 계약 / §6 질문 세트). 단계 1 백엔드(`/diagnose/refine`·`RefineRequest`·`RefineContext`·`FollowupAnswer`·`run_generate`) 푸시 완료.
> 워크플로우: CLAUDE.md §5·§10 준수. recon-first, 변수 격리, 푸시 보류→검토. git·커밋은 PowerShell(§3.1).

---

## 1. 이번 변수 (변수 격리)
**프론트엔드에 객관식 질문 UI + 2차 보정 진단 연결을 신설**한다 — fresh 진단 결과 화면에 질문을 띄우고, 답변을 `/diagnose/refine`에 보내 2차 결과로 갱신. **백엔드는 무변경(단계 1에서 완료, 동결).** 진단 파이프라인·게이트·1차 진단 흐름 무접촉.

## 2. 선결 게이트 (READ-ONLY, 보고 후 진행 — §5.1)
변경 전 다음을 확인·보고. 예상 외 상태면 중단·질의.
1. 현재 브랜치/tip — 단계 1 푸시 반영 상태.
2. **단계 1 백엔드 시그니처 확인:** `app/schemas.py`의 `RefineRequest`/`RefineContext`/`FollowupAnswer` 필드, `app/main.py`의 `/diagnose/refine` 입출력 계약. 프론트 타입·페이로드를 여기에 정확히 맞춤.
3. **프론트 구조 확인:**
   - `pages/index.tsx` — 상태머신(screen)·result 분기(history vs fresh)·`runDiagnosis`·`handleReset`·result state 흐름.
   - `components/ResultView.tsx` — props(`result`·`imageUrl`·`mode`·`onReset` 등)·결과 카드 렌더 구조.
   - `lib/api.ts` — `diagnosePlant` 패턴(상대경로 fetch).
   - `types/diagnosis.ts` — `DiagnosisResponse` 타입 (refine_context·analysis 포함 여부).
   - `next.config.ts` — `/diagnose`·`/compare` rewrite 패턴(`/diagnose/refine` 추가 지점).

## 3. 구현 항목 (선결 게이트 통과 후)
1. **프록시 rewrite:** `next.config.ts`에 `/diagnose/refine` → 백엔드 rewrite 추가 (기존 `/compare` 패턴 동일).
2. **타입 추가:** `types/diagnosis.ts`에 `RefineContext`·`FollowupAnswer`·`RefineRequest` 대응 타입 + `DiagnosisResponse`에 `refine_context?` (단계 1 `app/schemas.py`와 1:1 정합).
3. **API 함수:** `lib/api.ts`에 `refineDiagnosis(req): Promise<DiagnosisResponse>` — `POST /diagnose/refine`. `diagnosePlant`와 동일 fetch·에러 처리 패턴.
4. **질문 데이터(정적 상수):** 설계 §6의 5문항을 상수로 정의(예: `lib/followupQuestions.ts`).
   - 마지막 물 준 시점: 1일 이내 / 3일 이내 / 일주일 / 그 이상 / 모름
   - 주로 두는 위치: 남향창 / 북향창 / 거실 안쪽 / 화장실 / 모름
   - 최근 변화: 분갈이 / 자리 옮김 / 영양제 / 없음
   - 화분 밑 배수구: 있음 / 없음 / 모름
   - 최근 환기: 자주 / 가끔 / 거의 안 함 / 모름
5. **질문 UI 컴포넌트:** 객관식 5문항 + "더 정확한 진단 받기" 제출 버튼. **기존 ResultView 카드·디자인 시스템 스타일을 따른다**(새 디자인 임의 도입 금지). 미답 문항은 제출 시 무시(전부 선택 강제 X — 이탈 부담 최소화).
6. **state·연결(`pages/index.tsx`):**
   - 1차 응답에서 `refine_context`(+ `analysis`)를 보관.
   - `refinedResult` **별도 state** 신설.
   - 제출 핸들러: 답변 + 1차 `analysis` + `refine_context`로 `RefineRequest` 조립 → `refineDiagnosis` 호출 → `refinedResult` 갱신. 호출 중 로딩 표시, 실패 시 1차 결과 유지 + 에러 메시지.
   - ResultView가 표시할 결과 = `refinedResult ?? result`(2차 있으면 2차).
7. **노출 조건:** 질문 UI는 **fresh 모드 + 1차 결과 존재 시에만**. `mode==="history"`(과거 진단 조회)에선 숨김. 2차 완료 후엔 질문 UI를 숨기거나 "보정됨" 상태 표시.

## 4. UX 계약 준수 (설계 §3 — 깨면 안 됨)
- 2차 결과도 동일 ResultView로 렌더 → 3단 출력·[진단 요약]/[이렇게 판단했어요]/[처방] 레이아웃·hedged 톤 **자동 유지**. ResultView 렌더 로직 변경 금지.
- 질문 UI는 결과를 가리지 않게 결과 카드 **하단**에 배치(1차 가치 먼저 전달 — 설계 의도).

## 5. 게이트·불변 보존 (프론트 측 책임)
- **echo-back 무결성:** 1차 응답의 `analysis`(특히 `observed_symptoms`)와 `refine_context`를 **변형 없이 그대로** `RefineRequest`에 실어 보낸다. 프론트가 증상·RAG 컨텍스트를 가공·재계산하지 않는다 → 2차가 1차와 동일 guard 입력을 받아 cardinal_miss=0 보존(백엔드가 보장하되, 프론트가 입력을 더럽히면 안 됨).
- 백엔드·진단 파이프라인·게이트 채점·labels·RAG 무접촉.

## 6. 합성 검증 (§5.2)
- 타입체크(`tsc`/빌드) 통과, lint 통과.
- 1차 진단 흐름 회귀 없음(질문 UI·refinedResult 추가가 기존 fresh/history 경로를 안 깨는지).
- 2차 연결은 mock 또는 로컬 백엔드로 sanity(답변 제출 → /diagnose/refine 호출 → 결과 갱신, history 모드 질문 미노출). 실 LLM E2E는 사용자 로컬 확인 가능.

## 7. 커밋·푸시
- Atomic 분리(§5.4): 예) `feat(web):` rewrite·타입·api / `feat(web):` 질문 UI 컴포넌트 / `feat(web):` index state 연결. 한 커밋 = 한 의도.
- **푸시 보류 → 변경 diff 보고 후 사용자 검토.**

## 8. 금지 사항
- 백엔드 변경(단계 1 동결).
- ResultView 렌더 로직·디자인 시스템 임의 변경(질문 UI는 기존 스타일 재사용).
- 동적 질문 분기(답변에 따라 다음 질문 변경)·2차 진단 저장/타임라인 반영 — 범위 밖(설계 §7).
- baseline·앵커·labels·status enum·RAG·run_eval 채점 무접촉.
- 측정(run_eval) CC 임의 실행 금지.
