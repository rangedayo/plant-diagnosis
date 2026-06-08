# B 트랙 회고 (b_dataset RAG: B-1 ~ B-prime)

- **기간/라운드**: 2026-06-03, 7 라운드.
- **목적**: 영문 b_dataset RAG 수집·임베딩·적재 후 generate 활용으로 FP 감축 시도. 결과적으로 **FP는 generate 본질**임을 확증한 라인.

## 주요 변경·결과 (medium)
- **구축(B-1~B-3)**: 영문 5자료 82카드 수집(B-1) → 청크화·임베딩·적재(B-2, 791d469, b_dataset_rag 82) → 골든셋 본측정(B-3, Hit@10=1.0/MRR=0.9, FP 17 불변).
- **generate 활용 시도(B-4a~B-prime) — 전부 순효과 0**:
  - B-4a: empty=0 → 시나리오② 기각, generate가 RAG problem_type 무시·병해 확대 확증.
  - B-4b: problem_type 가중 다수결 → FP 17.5 불변(tie 지배).
  - B-4c: tie+cosmetic 건강룰 → FP 17.5 불변(tie 룰 발동 0건).
  - B-prime: 종메타 정상화 카드 격리 적재 → 커버4종 FP 11 완전 동일 + FN 리스크.

## 교훈
- **입력(프롬프트·RAG 사실) 설득 3연속 순효과 0** → status guard(출력 우회, 전략2)로 전환. 이 전환이 FP 17.5→7.5 성공(status_guard 트랙)으로 이어짐.
- generate는 증상 보고 시 cosmetic 면죄 거부·병해 escalate → prompts로 안 풀림. MEMORY `phase-b4*`·`phase-b-prime-*` 참조.

## 원본 파일 (→ `_archive/원본/B/`)
B-1_b_dataset_수집_작업프롬프트.md · B-2_청크화_임베딩_적재_작업프롬프트.md · B-3_골든셋_본측정_작업프롬프트.md · B-4a_FP_본질_진단_측정_작업프롬프트.md · B-4b_generate_problem_type_활용_작업프롬프트.md · B-4c_tie_cosmetic_건강룰_작업프롬프트.md · B-prime_종메타_정상화_작은적재_FP측정_작업프롬프트.md
