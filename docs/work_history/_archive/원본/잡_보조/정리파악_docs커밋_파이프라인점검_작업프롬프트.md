# [정리·파악 라운드] docs 이력 커밋 + 현재 파이프라인 구조 점검 — 작업 프롬프트

## 0. 맥락 (먼저 읽을 것)

status guard 라운드 종료(b493e7c, 푸시 완료). 다음 큰 작업(main_rag→a_dataset_rag 명명 정합 / (b) 케어 가이드 / 모델 업그레이드) **우선순위를 정하려면 현재 파이프라인 현황 파악이 선결**. 후보들이 전부 파이프라인 구조 위에서 돌기 때문.

이번 라운드 = **(A) 미뤄둔 docs 이력 커밋**(가벼운 실행) + **(B) 파이프라인 구조 read-only 점검 보고**(다음 우선순위 결정 근거).

---

## PART A — docs 이력 커밋

- **대상**: `docs/work_history/*.md`, `docs/context_dumps/` 미커밋분.
- ⚠ **커밋 전 민감값 점검**: `context_dumps`에 **API 키·인증값·`.env` 값 등 민감정보가 없는지 확인.** 있으면 **커밋 중단·보고**(`.gitignore` 처리 논의). work_history md는 작업 지시라 보통 안전하나 같이 훑을 것.
- ⚠ 커밋 전 `git status` — `eval/baseline.json` **안 떠야 정상**.
- 메시지:
  ```
  docs: 작업 이력 정리 — B-1~status guard 작업프롬프트·컨텍스트
  ```
- **푸시**: 커밋 후 `origin/main` 푸시까지 (단계 B'·status guard 푸시와 같은 흐름). 푸시 후 clean·unpushed 0 확인.

---

## PART B — 현재 파이프라인 구조 점검 (read-only, 변경 없음)

점검·보고만. 코드 변경·커밋 금지.

1. **진단 그래프 노드 흐름** (`app/graph.py`) — 노드 순서와 각 노드 역할 (Vision → analyze → retrieve → generate → status guard 인지, 다른 구성인지).
2. **단계별 모델·API 맵** — 각 노드가 호출하는 모델/API:
   - vision/analyze: Gemini? (어느 모델)
   - generate: gpt-4o-mini (확인됨)
   - 재생성: gpt-4o-mini (확인됨)
   - 임베딩: 어느 모델 (OpenAI? )
3. **외부 의존 현황** — `Plant.id` API를 **아직 쓰는지**, 아니면 Gemini로 통합·제거됐는지. analyze가 **Gemini 단일 호출**인지 여러 단계인지.
4. **목표 대비 현황** — 사용자 노트의 목표:
   - 기존(추정): `Plant.id + GPT-4o-mini 묘사 + GPT 키워드 + RAG + 최종 LLM` (5단계)
   - 목표: `Gemini 단일 호출 + RAG + 최종 LLM` (3단계)
   - **현재 어디인가** — 이미 3단계로 단순화됐나, 5단계 잔재(Plant.id·별도 묘사·별도 키워드 단계)가 남았나. 남았으면 무엇인지 구체적으로.
5. **gpt-4o-mini 사용처 전수** — `model_utils.py` 3곳 외에 더 있는지 (전체 grep).

**보고 형식**: 노드 흐름도(텍스트) + 단계별 모델 맵 + 5→3단계 목표 대비 현황 + 단순화 잔여 항목(있으면).

---

## 환경 주의사항

- ⚠ `eval/baseline.json` 절대 덮어쓰기 금지.
- Bash로 `$env:` 금지(사고 전례) → 필요 시 PowerShell 툴.
- GateGuard 훅: Bash/Edit/Write 전 "사실 명시".
- PART B는 **read-only** — grep·파일 view만, 코드 변경·실행 측정 불필요.

---

## 산출물 요약

- PART A: docs 커밋 1개 → origin/main 푸시 (민감값 없을 시)
- PART B: 파이프라인 구조 점검 보고 (chat) — 노드 흐름·모델 맵·5→3단계 현황·잔여
