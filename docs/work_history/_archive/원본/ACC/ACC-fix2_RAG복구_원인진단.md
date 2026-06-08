# [ACC-fix2] b_dataset_rag 검색 실패 — 원인 진단(read-only) + 조건부 복구

> **목적**: R11 측정에서 `b_dataset_rag`(질병 카드 RAG)의 모든 검색이 실패했다 (`Error creating hnsw segment reader: Nothing found on disk`, b_docs=0). R8까지 정상이었으므로 "왜 갑자기 죽었는지" **근본 원인을 먼저 확정**하고(재발 방지), 원인이 확정된 뒤에만 복구한다. 원인 모른 채 재적재하면 같은 사고가 반복될 수 있다.
>
> **성격**: Phase 1 = 순수 read-only 원인 진단 (사용자 보고 후 멈춤). Phase 2 = 원인 확정·사용자 승인 후에만 복구. R10 코드(prompts.py)는 **무관·무변경** — analyze 보강은 R11 텍스트에서 작동 확인됨, 코드를 의심할 단계 아님.
>
> **선행**: R10(`6d3179c`/`09fa1f3`) + R11 측정(RAG 죽은 채 측정 → 무효). **후행**: RAG 복구 후 R11 재측정.

---

## 1. 확정된 증상 (R11 로그)

- `b_dataset_rag` 검색이 **전 케이스 실패**. 에러: `chromadb.errors.InternalError: Error executing plan: Internal error: Error creating hnsw segment reader: Nothing found on disk` (`app/graph.py:168` `_chroma_query_sync`).
- 결과: `b_docs: 0`, FP/TP 분석 `top_3 majority: {'(empty)'}` — 검색 결과 전무.
- **`main_rag`(또는 main 컬렉션)는 정상** — `main_docs: 3`, `merged_docs: 3`. 즉 b만 죽고 main은 삶.
- **R8까진 정상이었음** (R8 로그에 haengun_003 RAG 1위 nutrient 0.872, haengun_005 disease 0.873). R9(docs만)·R10(prompts.py만)은 Chroma 무관 → **코드 변경이 원인 아님, 환경/저장소 사고로 추정**.

### 사전 가설 (CC가 코드로 확정)

| 가설 | 내용 | 확인 방법 |
|---|---|---|
| (1) chromadb 버전 업 | 패키지가 Rust 기반 신버전으로 올라가며 구 HNSW 인덱스 포맷을 못 읽음 (스택의 `rust.py`가 정황) | 버전 + 적재 시점 대조 |
| (2) 컬렉션 비워짐/손상 | b_dataset_rag 세그먼트 파일이 사라지거나 0건 | persist 디렉토리 + count() |
| (3) 경로 불일치 | PERSIST_DIR이 빈 디렉토리를 가리킴 | 경로 + 실제 파일 |
| (4) b/main 적재 차이 | main은 살고 b만 죽은 이유 — 적재 방식·위치 차이 | 두 컬렉션 생성 코드 비교 |

---

## 2. Phase 1 — 원인 진단 (read-only, 끝나면 보고하고 멈춤)

### Step 0 — 게이트
1. `git status` 확인. R10 커밋 상태.
2. `app/graph.py`에서 Chroma 클라이언트 생성·PERSIST_DIR·`b_dataset_rag`/`main_rag` 컬렉션 접근 코드 위치 확인.

### Step 1 — Chroma 저장소 실태 (가설 2·3)
- PERSIST_DIR 실제 경로 출력 + 그 디렉토리 `ls -la` (세그먼트/sqlite 파일 존재 여부).
- Chroma 클라이언트로 **컬렉션 목록** + 각 `collection.count()` 조회 (read-only). 특히 `b_dataset_rag.count()`가 0인지, 존재는 하는지.
- b_dataset_rag의 HNSW 세그먼트 디렉토리가 디스크에 있는지 (에러가 "Nothing found on disk"이므로 핵심).

### Step 2 — 패키지 버전 (가설 1)
- `.venv\Scripts\python.exe -m pip show chromadb` 로 현재 버전.
- `requirements.txt`(또는 lock)의 chromadb 핀 버전 + git log로 **최근 변경 시점** 확인 — R8 이후 버전이 바뀌었는지.
- 현재 chromadb가 Rust 기반(0.5+)인지 확인. 구 인덱스가 신버전과 호환 안 되는 정황인지.

### Step 3 — b는 죽고 main은 산 이유 (가설 4)
- `b_dataset_rag`와 `main_rag` 두 컬렉션의 **생성·적재 코드 비교**: 같은 클라이언트/persist인지, 적재 시점·방식이 다른지.
- main이 살아있는 이유가 (재적재가 최근이었다 / 다른 저장 방식 / in-memory 폴백) 중 무엇인지.

### Step 4 — 원인 판정 + 재발 방지
- 가설 1~4 중 **무엇이 원인인지 확정** + 코드/파일 근거.
- **재발 방지책** 제시: 버전 핀 고정 / 적재 검증 스텝 / persist 백업 등.
- ⚠ Phase 1은 여기까지. **복구 실행 전에 보고하고 멈춘다.**

---

## 3. Phase 2 — 복구 (원인 확정 + 사용자 승인 후에만)

원인별 복구안을 제시하되, **실행은 사용자 승인 후**:

- **버전 불일치(가설 1)면**: chromadb 버전을 적재 시점과 맞추거나, 신버전 기준으로 **전체 재적재**. 재발 방지로 버전 핀.
- **컬렉션 비워짐/손상(가설 2·3)이면**: b_dataset_rag **재적재** (원본 카드 데이터 → 임베딩 → Chroma).

⚠ **재적재 = 임베딩 API 과금** (메모리 기준 ~$0.01). eval 풀런과 동일하게 **사용자 PowerShell 실행**. CC는 재적재 스크립트 준비·검증(dry-run)까지, 실제 적재는 사용자가.
⚠ 재적재 후 **`b_dataset_rag.count() > 0` + 샘플 쿼리 1건 성공** 확인 필수.

---

## 4. 제약 (불변)

- **Phase 1은 read-only.** 진단만, Chroma 쓰기·재적재·삭제 금지.
- **[B-2] `main_rag` 명명 변경 금지** — 살아있는 컬렉션, 손대지 말 것. 이번 작업은 `b_dataset_rag` 복구만.
- `eval/baseline.json` 보호. `app/prompts.py`(R10) 무변경 — RAG 문제와 무관.
- 재적재는 사용자 승인·실행 (과금).
- R11 측정 결과(`after_acc_r10_analyze_generate.json`)는 **RAG 죽은 채 측정돼 무효** — 비교 앵커로 쓰지 말 것. 복구 후 재측정분을 앵커로.

---

## 5. 보고 형식

**Phase 1 (먼저, 멈춤):**
1. Step 0 — Chroma 코드 위치.
2. Step 1 — PERSIST_DIR 경로 + 디렉토리 내용 + b_dataset_rag count/세그먼트 존재.
3. Step 2 — chromadb 현재 버전 + 최근 변경 시점 + Rust 정황.
4. Step 3 — b/main 적재 차이, main이 산 이유.
5. **Step 4 — 원인 확정(가설 1~4 중) + 근거 + 재발 방지책.** → 여기서 멈추고 사용자 승인 대기.

**Phase 2 (승인 후):** 원인별 복구 실행안 + 재적재 스크립트(사용자 실행용) + 복구 검증(count>0, 샘플 쿼리).
