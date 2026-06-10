# 작업: 챗봇 단계 1 — 백엔드 2차 보정 진단 통로

> 사양: `docs/work_history/` 또는 핸드오프의 「챗봇 2차진단 A안 설계」 참조. A안(generate-only 재실행) 확정.
> 워크플로우: CLAUDE.md §5(라이프사이클)·§10(체크리스트) 준수. recon-first, 변수 격리, 푸시 보류→검토.

---

## 0. 선행 — 보류 중 recon 커밋 푸시 (사용자 승인됨)
- `docs/work_history/chatbot_recon_diagnosis.md`의 `docs:` 커밋이 보류 중이면 **먼저 푸시**. (read-only 산출물, 단계 1과 독립.)
- `git status`로 미커밋 잔재 확인 후 진행.

## 1. 이번 변수 (변수 격리)
**백엔드에 "2차 보정 진단" 경로를 신설**한다 — 1차 analyze·RAG 결과를 재사용하고 generate·guard만 다시 실행하는 통로. **프론트엔드는 이번 범위 밖(단계 2).** generate/guard의 판정 로직 자체·1차 경로 동작·프롬프트 판정 규칙·RAG·labels·게이트 채점은 **무변경(동결)**.

## 2. 선결 게이트 (READ-ONLY, 보고 후 진행 — §5.1)
변경 전 다음을 읽기 전용으로 확인·보고. 예상 외 상태면 **중단·질의.**

1. 현재 브랜치/tip — 0번 푸시 반영 상태.
2. **§4 RAG 보존 방식 확정용 recon (중요):** `DiagnosisSnapshot`(또는 진단 스냅샷 직렬화) 구조를 확인. 1차 진단 재료(rag_docs·우세 타입·rag 플래그·analyze 6필드)를 응답에 실어 2차 요청에 되돌려주는 **방식 (a)** 가 기존 패턴 재사용으로 깔끔한지 판정.
   - **(a)가 깔끔하면**: (a)로 진행.
   - **(a)에 문제**(스냅샷 선례 부적합 / 내부 RAG 데이터 클라이언트 노출이 부적절 / 페이로드 과대 등)면: **구현 멈추고** (b) 서버 캐시 포함 대안을 trade-off와 함께 보고 → **사용자 결정 대기.**
3. `app/graph.py`의 generate 노드 본문 구조 — 공유 callable로 분리 가능한지 (현재 노드가 받는 입력·내는 출력).
4. `app/graph.py`의 `context_summary` 빌더 위치 — 객관식 답변을 `[사용자 추가 입력]` 섹션으로 가산할 지점.
5. `apply_status_guard`가 `observed_symptoms`를 어떻게 키로 쓰는지 — 2차에서 이 값을 1차 그대로 두면 게이트가 보존되는지 코드로 확인.

## 3. 구현 항목 (선결 게이트 통과 후)
1. **generate 본문 공유 callable 분리:** 현재 generate 노드 본문을 순수 함수(예: `run_generate(...) -> structured_result`)로 추출. 1차 그래프 노드와 2차 경로가 **같은 함수**를 호출. (리팩터링 — 1차 동작 불변이 핵심.)
2. **1차 재료 보존((a) 확정안):** 1차 응답에 2차 재사용에 필요한 재료(RAG 컨텍스트·analyze 6필드)를 포함. 기존 스냅샷 구조 재사용 우선.
3. **`DiagnosisState` 입력 필드 추가:** 객관식 답변용 optional 필드(예: `followup_answers`). 1차엔 없음(None), 2차에만 채워짐.
4. **2차 진입 경로:** 새 엔드포인트(예: `POST /diagnose/refine`) 또는 기존 확장 — recon 결과로 더 적합한 쪽 선택. 입력 = 1차 재료(또는 진단 id) + 객관식 답변, 출력 = 2차 `DiagnosisResponse`(1차와 동일 스키마).
5. **객관식 답변 → context 가산:** `context_summary`에 `[사용자 추가 입력]` 블록으로 답변을 합류. 답변이 있을 때만 추가.

## 4. 게이트 보존 원칙 (절대 준수)
- **`observed_symptoms` 불변:** 2차는 사진에서 뽑은 증상을 1차 값 그대로 사용. 객관식 답변으로 증상 배열을 재생성·변형하지 **않는다**.
- **2차도 동일 `apply_status_guard` 통과:** 1차와 같은 guard 경로. (위 + 증상 불변 → cardinal_miss=0 게이트 구조적 보존.)
- 답변은 generate에 **참고 맥락으로만** 작용. status는 generate가 맥락 포함해 재판정하되, guard가 최종 안전 검수.

## 5. 합성 검증 (측정 전, 무과금 — §5.2)
- `import` OK.
- `pytest -m "not integration"` 회귀 없음 (실 Gemini 호출 금지 — §7.6).
- `grep`으로 변경 반영 확인.
- **1차 경로 동작 불변 확인:** generate callable 분리 후에도 1차 진단 흐름이 기존과 동일한지(합성/기존 테스트로). 1차 회귀 의심 시 사용자에게 1차 run_eval 1회 검증 제안(과금 — 사용자 PowerShell).
- 2차 경로는 평가 하니스 없음 → 동작 sanity(엔드포인트 호출 시 2차 응답 생성, 증상 불변, guard 통과)만 mock으로 확인.

## 6. 커밋·푸시
- Atomic 분리(§5.4): 예) `refactor:` generate callable 분리 / `feat:` 2차 진입 경로·state 필드 / `feat:` 객관식 답변 context 가산. 한 커밋 = 한 의도.
- **푸시 보류 → 변경 diff 보고 후 사용자 검토.**

## 7. 금지 사항
- 프론트엔드 변경(단계 2).
- generate/guard 판정 로직·프롬프트 판정 규칙·1차 경로 동작 변경.
- baseline·앵커·`labels.json`·status enum·RAG·`run_eval` 채점 무접촉.
- 측정(run_eval) CC 임의 실행 금지 — 필요 시 사용자 PowerShell.
- §4 (a)/(b) 미확정 상태에서 구현 강행 금지(선결 게이트 2번 결과 우선).
