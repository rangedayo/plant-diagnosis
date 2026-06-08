# ACC 트랙 회고 (ACC-R1 ~ R10 + fix/위생)

- **기간/라운드**: 2026-06-05 ~ 06-06, 13 라운드.
- **목적**: 5-status(건강·과습·건조·병해 의심·영양 부족) 라벨 스키마 확립 + 평가셋 39건 구축 + 건조·영양부족 변별 시도.

## 주요 변경·결과 (medium)
- **스키마·데이터(R1~R4)**: true_status 스키마 마이그레이션(R1) → 행운목 "건조" 입력(R2) → Epipremnum 6장 편입 + labels 33→39(R3 trio) → run_eval 혼동표 + plantvillage 사전매핑(R4).
- **변별 시도(R6·R7·R9·R10)**: 건조 미발화 진단(R6, 원인=prompts 건조/과습 트리거 부재) → 건조·과습 트리거 신설(R7, 이진 순효과有/건조 발화 0) → 변별 실패 병목=**analyze 상류 정보손실 확정**(R9) → analyze 4축 + generate 황화 충돌룰(R10, 후에 R12d-1에서 빼기 대상으로 입증).
- **보조(fix·fix2·위생)**: baseline 원복(fix) · RAG transient 실패 진단·chromadb 핀(fix2) · wikimedia 폐기·moneyplant 준비(데이터위생).

## 교훈
- "입력(프롬프트) 설득"으로 status 발화는 안 풀림 — R7 건조 트리거 순효과 0. 상류(analyze) 병목이 진짜(R9).
- R10 황화 충돌룰은 효과 0으로 빼기: CLAUDE.md **§7.4** 참조.
- RAG transient 읽기 실패 재발방지(chromadb==1.5.5 핀, 측정 전 자가점검): MEMORY `phase-acc-fix2-*` 참조.

## 원본 파일 (→ `_archive/원본/ACC/`)
ACC-R1_label_schema_migration_프롬프트.md · ACC-R2_haengun_true_status_프롬프트.md · ACC-R3_epipremnum_6장_편입_프롬프트_v3.md · ACC-R3-labels_labels.json_6건추가.md · ACC-R3-followup_명명통일_candidates_프롬프트.md · ACC-R4_run_eval확장+plantvillage사전매핑.md · ACC-R6_건조status_미발화_진단.md · ACC-R7_건조과습트리거+가드확장.md · ACC-R9_건조-영양부족_변별실패_진단.md · ACC-R10_analyze4축+generate충돌룰.md · ACC-fix_baseline원복+R5보존.md · ACC-fix2_RAG복구_원인진단.md · ACC-데이터위생_wikimedia정리_moneyplant준비_프롬프트.md
