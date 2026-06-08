# [generate R1 사후] JSON 파싱 실패 6건 원인 진단 (read-only) — 작업 프롬프트

## 0. 맥락

generate 정합룰 측정(`after_acc_generate_escalation.json`)에서:
- JSON 파싱 성공률 100% → **84.6% (6건 실패)**
- 실패 6건: `dracaena_004`, `haengun_004`, `chlorophytum_comosum_003`, `sansevieria_trifasciata_002`·`003`, `spathiphyllum_001` — **전부 gt=건강**
- latency 20.1s → **31.3s (max 101초)**

표면 수치(FP 13→8, acc 72.4%)는 이 6건이 집계에서 빠진 착시일 가능성이 큼. **정합룰의 진짜 효과를 알려면 파싱 실패 원인부터 규명해야 함.**

⚠ **read-only. 측정·재호출(Gemini) 금지(과금). 코드·프롬프트·baseline 무변경.** 기존 출력 JSON + 코드 분석만.

---

## PART A — 파싱 실패 6건 raw 확인

`eval/after_acc_generate_escalation.json`에서 6건 추출:
- `run_eval.py`가 파싱 실패 시 **raw 응답/에러를 저장하는지** 먼저 확인. 저장하면 그 내용, 안 하면 어떻게 진단 가능한지 제안(재호출은 과금이라 보류).
- 각 케이스: latency, 응답 끝부분(잘렸는지), 에러 메시지/형식
- **latency max(101초)가 이 6건과 겹치는지** 대조 — 긴 응답일수록 truncation 의심

---

## PART B — 원인 분류

6건 각각을 분류:
- **truncation** (max_tokens 초과로 응답이 중간에 잘려 JSON 안 닫힘)
- **형식 오류** (정합 설명 텍스트가 JSON 밖으로 새거나 구조 깨짐)
- **빈 응답 / 기타**
- **비결정성** (무작위, 정합룰과 무관)

특히 latency가 긴 케이스 = 응답이 길다 = truncation 가능성. max_tokens 설정값도 확인.

---

## PART C — 정합룰 인과 확인 (핵심)

- 정합룰 추가가 응답 길이·구조에 영향을 줬는지.
- **6건이 전부 gt=건강**인 게 우연인지, 아니면 건강 케이스에서 "병해인지 환경인지 정합을 따져라"가 더 긴 추론을 유발해 응답이 길어졌는지.
- **기준점 대조**: `after_acc_r12d1_remove_surface.json`(정합룰 적용 전, 파싱 100%)에서 이 6건이 파싱 OK였는지 확인 → OK였다면 정합룰이 범인으로 확정.

---

## PART D — 보고 + 처방 (chat)

1. 6건 파싱 실패 양상 (truncation/형식/기타) + latency 대조
2. 정합룰이 원인인지 확정 (기준점 대조 결과)
3. 6건이 전부 gt건강인 이유
4. **처방 옵션 제시** (이번 작업 범위는 진단까지, 처방은 사용자 결정):
   - max_tokens 상향 (truncation이면)
   - 정합룰 간결화 (응답 길이 억제)
   - 출력 형식 강제 강화
   - 롤백 + 모델 교체로 전환
5. 진단 보고서 경로 (작성, 커밋 보류)

---

## 주의사항

- ⚠ **read-only** — 측정·재호출·코드·프롬프트·baseline 무변경.
- 추측 금지 — raw/JSON 근거. raw가 없으면 "없음"을 명시하고 진단 가능 범위만.
- 보고만, 커밋·푸시 보류.
