# L0 구현 — 측정 가독성: 가드 전/후 FP 명시 + `_avg` 요약 보강 (코드만)

## 배경

방향: 1차 진단 정확도 개선, 첫 레버 = **L0(측정 정비)**. read-only 조사 결과, 우리 목표인 **병해 의심 over-escalation(FP)** 은 현 평가셋(건강 28장)으로 **이미 측정 가능**하다. status 정답 라벨·실패모드 표본 같은 **데이터 작업(A·B)은 별도 트랙으로 미룬다.**

따라서 L0는 "이미 있는 측정을 **한눈에 보이게** 만들고, **바꾸기 전 기준선**을 새로 캡처"하는 데 그친다. `app/`·`data/`·`baseline.json` 무변경.

참고: eval 실제 실행은 Gemini 비전 N콜(비용·시간)이라 **이 환경에서 못 돌린다.** → **코드 작성은 Claude Code**, **기준선 캡처 실행은 사용자**가 한다(아래 명령 제공).

## 공통 규칙

- 변경은 **`scripts/`만**(run_eval 집계부 + `_avg` 산출부). `app/`·`data/`·`labels*.json`·`baseline.json` 무접촉(읽기만).
- **`baseline.json` 절대 덮어쓰기 금지.** `$env:RUN_EVAL_OUT` 값은 파일명만(eval/ 접두 금지).
- 새 집계는 **이미 있는 per-case 필드**(예: `guard_pre_status`, `guard_fired`, 최종 status, gt `is_healthy`) 기반으로만. **새 모델콜·새 데이터 없음.**
- **eval 풀런 금지**(비용). 검증은 합성 케이스 데이터로 집계 함수만 단위 검증(Gemini 불필요).
- 커밋 분리: `docs:`(이 프롬프트) / `fix:`(scripts 집계). 푸시는 보고 검토 후.

---

## 작업 0 (선결, read-only) — `_avg` 산출 주체 특정

- `_avg.json`(또는 `*_avg` 요약)을 **무엇이 생성하는지** 특정한다(별도 스크립트인지, run_eval 내부인지, 수동인지). 조사 보고에서 미확인으로 남았던 부분.
- 그 결과에 따라 작업 D의 대상 파일이 정해진다. 별도 스크립트가 없고 수동 산출이면 **그 사실을 보고**하고 D는 "run_eval가 avg까지 산출하도록 추가" 또는 "보류"를 제안.

## 작업 C — 가드 전/후 FP 명시 (`run_eval.py` 집계)

- `_aggregate_and_report`의 `is_healthy` confusion 블록을 **pre-guard / post-guard 두 벌**로 나란히 출력:
  - `is_healthy_post_guard`: 현재처럼 **최종 status** 기준(positive=비건강 confusion: TP/TN/FP/FN + precision/recall/accuracy).
  - `is_healthy_pre_guard`: **`guard_pre_status`** (가드 적용 전 status) 기준 동일 confusion. (가드가 안 터진 케이스는 pre=post.)
  - `guard_caught_fp = pre_guard.fp - post_guard.fp` 를 **명시 필드**로(가드가 건강 복원해 잡은 FP 수가 한 줄로 보이게).
- status→is_healthy 매핑은 **기존 규칙 재사용**(건강=healthy, 그 외 4종=비건강). 새 규칙 만들지 말 것.
- 기존 `is_healthy` 키를 깨면 다른 집계가 참조할 수 있으니, **기존 키는 유지**하고(=post_guard와 동일) pre/post·guard_caught_fp를 **추가**하는 방향 권장(호환 우선). 정확한 키 구조는 read-only로 현 출력 보고 결정·보고.

## 작업 D — `_avg` 요약에 guard·fp 블록 포함

- 작업 0에서 특정한 산출부에서, run들 평균 요약에 **`status_guard_diagnosis`·`fp_analysis`(+ 작업 C의 pre/post·guard_caught_fp)** 가 포함되도록 추가.
- 현재 `_avg`엔 guard 블록이 빠져 run1/run2 원본을 봐야만 가드 효과가 보이는 상태 → **평균 리포트만 봐도 보이게**가 목표.
- 평균이 의미 없는 항목(전수 dump 등)은 평균 말고 합산/대표값 등 적절히. 처리 방식은 제안·보고.

## 검증 (eval 풀런 없이)

- **합성 per-case 데이터**(가드 터진/안 터진, FP/TP 섞인 더미 케이스 몇 개)를 만들어 집계 함수에 넣고:
  - `pre_guard.fp`, `post_guard.fp`, `guard_caught_fp` 가 손계산과 일치하는지,
  - 기존 `is_healthy`/기타 블록이 안 깨졌는지
  단위 검증. (검증 스크립트는 커밋 제외/삭제.)
- `baseline.json` **무변경** 확인(diff 없음).

## 기준선 캡처 (사용자 실행 — Claude Code는 명령만 제공)

- `baseline.json` 안 건드리고 **새 파일**로 현재 파이프라인(가드 적용·신스키마·작업 C/D 반영) 기준선을 뜬다. 관례대로 run1/run2 + avg.
- 보고에 **정확한 PowerShell 명령**을 적어줄 것. 예시 형태(파일명만, eval/ 접두 금지):
  - `$env:RUN_EVAL_OUT="baseline_current_postguard_run1.json"; .venv\Scripts\python.exe scripts\run_eval.py`
  - run2도 동일(파일명만 변경), 그다음 avg 산출 절차.
- 이 새 파일이 **앞으로 "바꾸기 전" 작업 기준**이 된다. `baseline.json`(구·2026-05-29)은 **역사 산출물로 그대로 보존.**

## 보고 형식

1. **작업 0 결과**: `_avg` 산출 주체.
2. **변경 파일·라인**: run_eval 집계(C) / avg 산출부(D).
3. **검증**: 합성 데이터 단위검증 결과 + baseline.json 무변경 확인.
4. **사용자용 기준선 캡처 명령**(run1/run2/avg, RUN_EVAL_OUT 규약 준수).
5. **커밋 제안**(`docs:` + `fix:`) — 승인 후 푸시.
