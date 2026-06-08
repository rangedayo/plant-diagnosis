# status_guard 회고 (전략2 + 케어가이드 + run_eval)

- **기간/라운드**: 2026-06-03 ~ 06-04, 4 작업.
- **목적**: 입력(프롬프트·RAG) 설득 3연속 실패(B 트랙) 후 **출력 우회 전략2** — generate 출력 후 status enum만 교정하는 status guard 도입. + 케어가이드 백엔드 + run_eval 도구 작성.

## 주요 변경·결과 (medium)
- **status guard 성공(전략2)**: graph.py `apply_status_guard`(병변 veto로 FN0) + 교정분 cause 경량 재생성(`regenerate_healthy_cause`, status 고정·cause만 건강전제 재작성, 모순 해소). **FP 17.5→7.5**·FN0/recall1.0·healthy_acc 0.773. 커밋 b493e7c. 입력 설득 3회 실패를 출력 우회로 돌파.
- **설명정합 경량재생성**: status=건강/cause=병해 모순 해소 정합 라운드.
- **기능b 케어가이드**: garden API 9종 케어 적재(care_guide.json) + lookup + 응답 첨부(진단 무변경).
- **run_eval 작성**: 평가 하네스 초기 작성.

## 교훈
- 입력 설득 한계 → 출력 후처리(guard)가 돌파구. CLAUDE.md 워크플로의 status guard 근간.
- MEMORY `phase-status-guard-success`·`phase-care-guide-backend-done` 참조.

## 원본 파일 (→ `_archive/원본/status_guard/`)
status_guard_전략2_단계B정리_구현_측정_작업프롬프트.md · status_guard_설명정합_경량재생성_커밋푸시_작업프롬프트.md · 기능b_케어가이드_백엔드_적재연결_작업프롬프트.md · run_eval_작성_프롬프트.md
