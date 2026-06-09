# CC Task — R13: 3.5 Flash 채택 (기본값 전환 + 앵커 교체 + 문서)

> 시점: 2026-06-09. Arm C 측정 완료(FP 13→14 = 1케이스, 사실상 동등·recall 100%·속도 이점). 결정 = **3.5-flash/global 채택.**
> 이 task는 **코드·설정·문서·커밋만 — 과금 측정 없음.**

## 0. 한 줄 요약
analyze 기본을 `gemini-3.5-flash` / `global`로 영구 전환(코드 fallback + `.env` 정합), 새 앵커 = `eval/after_acc_armC_3p5flash.json` 지정, CLAUDE.md 갱신.

## 1. 안전 제약 (필독)
- **과금 호출 금지.** 회귀 점검 시 `-m "not integration"`.
- 이번엔 baseline 동작을 **의도적으로 변경**함(채택). 단 **env override 메커니즘 보존** — 필요시 2.5-pro/asia-northeast1로 되돌릴 수 있어야 함.
- **`.env` 편집은 `GOOGLE_CLOUD_LOCATION` 한 줄만.** 다른 줄·시크릿(`GEMINI_API_KEY`·`GOOGLE_CLOUD_PROJECT` 등) **절대 건드리지·출력하지 말 것.**
- 앵커·`baseline.json`·old 앵커 파일 **삭제 금지(보존).**
- generate/guard 로직·`prompts.py`·RAG·`run_eval.py` 채점 로직 **무변경** (이번은 모델 전환만).

## 2. ① 코드 기본값 전환 (`app/vision/gemini.py`)
- `ANALYZE_MODEL` fallback: `"gemini-2.5-pro"` → `"gemini-3.5-flash"`.
- location fallback (L108-109 `... or "asia-northeast1"`): `"asia-northeast1"` → `"global"`.
- 인자/env 우선순위·override 동작·`print` 라인 **그대로 보존.**

## 3. ② `.env` 정합 — shadowing 차단 (중요)
- 배경: `load_dotenv(override=False)`라 `.env`의 `GOOGLE_CLOUD_LOCATION=asia-northeast1`이 코드 fallback(`"global"`)을 **가린다.** 코드만 바꾸면 세션 env 미설정 시 여전히 asia-northeast1 → 404.
- 조치: `.env`의 `GOOGLE_CLOUD_LOCATION` 값을 `asia-northeast1` → `global`로 변경 (그 한 줄만, 시크릿 무접촉·무출력).
- `ANALYZE_MODEL`은 `.env`에 없음 → 코드 fallback(3.5-flash) 적용. **`.env`에 추가하지 말 것** (모델 기본값의 진실원은 버전관리되는 코드. location만 `.env`에 기존 충돌값이 있어 정합하는 비대칭임).

## 4. ③ 비측정 검증 (과금 0 — genai.Client mock 패치)
- 세션 env 미설정 상태에서 GeminiProvider 해석값이 **model=`gemini-3.5-flash`, location=`global`** 인지 확인(실호출 X). `print` 라인 + 해석된 location 보고.
- override 보존 확인: `ANALYZE_MODEL=gemini-2.5-pro` → 해석 2.5-pro / 세션 `GOOGLE_CLOUD_LOCATION` 세팅 시 그 값 우선.

## 5. ④ 앵커 교체 + 문서 (CLAUDE.md)
- **새 앵커 지정**: `eval/after_acc_armC_3p5flash.json` (3.5-flash/global, acc 60.0% · FP14 · FN0 · 분모35) = 이후 generate/guard 트랙의 비교 기준점. **재측정 없음** (이미 깨끗·비교가능).
- old 앵커 `after_acc_r12d1_relabeled.json` = 참고·보존 (2.5-pro 기준, 비교 금지·삭제 금지).
- CLAUDE.md 갱신:
  - (a) analyze 기본 모델/엔드포인트 = **3.5-flash / global** (was 2.5-pro / asia-northeast1).
  - (b) 현 앵커 = `eval/after_acc_armC_3p5flash.json` (수치 포함). old 앵커는 참고로 강등.
  - (c) R13 Arm C 결론 한 줄: 모델 교체 = FP 중립(13→14, 1케이스)·recall 유지 → **속도 근거로 채택**. FP의 진짜 레버는 "미용 vs 병리" 임계값(generate/guard) → 다음 트랙.
  - (d) global 엔드포인트 = **데이터 레지던시 미보장** (식물 사진이라 수용).

## 6. 커밋
- 코드 전환(`gemini.py`) **isolated 커밋.** 제안 메시지 예: `feat: analyze 기본 모델 3.5-flash/global 채택 (R13 Arm C)`.
- CLAUDE.md 갱신 = **별도 docs 커밋.**
- `.env`는 gitignore(미커밋) — 변경 사실만 보고.
- 커밋 해시·`git log -1 --oneline` 보고. **푸시는 사용자 재량.**

## 7. 보고 형식 (CC → 웹)
1. `gemini.py` diff (fallback 2개).
2. `.env` 변경 확인 (값만: location=global, 시크릿 무출력).
3. 비측정 검증: no-env 해석 model/location + override 보존.
4. CLAUDE.md 갱신 요지 + 커밋 해시 2개.

## 8. 금지 사항
- 과금 측정.
- `.env` 시크릿 접근/출력, location 외 줄 변경.
- 앵커·old 앵커·`baseline.json` 삭제.
- generate/guard/`prompts.py`/RAG/채점 로직 변경.
- `prompts.py` 동시 커밋.
