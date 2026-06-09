# CLAUDE.md — Plantia 프로젝트 메모리

> 이 파일은 Claude Code가 세션 시작 시 자동으로 읽는 프로젝트 메모리입니다.
> 아래 규칙은 **모든 라운드·모든 작업에 무조건 적용**됩니다.
> 사용자가 매 프롬프트마다 다시 적지 않아도 CC는 이 내용을 이미 알고 있어야 합니다.

---

## 0. 프로젝트 개요

**Plantia (plant-diagnosis)** — 식물 진단 AI 프로젝트.

- **5-status 분류**: 건강 / 과습 / 건조 / 병해 의심 / 영양 부족 (+ ambiguous 평가 제외)
- **추가 라벨**: `비건강-원인미상` (is_healthy=false 확정·원인 미상, 5-status 매칭 시 중립)
- **워크플로**: Vision(analyze, **Gemini 3.5-flash/global**) → retrieve(RAG) → generate(gpt-4o-mini) → status guard
- **개발 방식**: 라운드 기반 평가 중심. 한 라운드 = 한 변수 격리 측정.

---

## 1. 절대 불변 파일 (무접촉)

다음 파일은 **어떤 경우에도 수정·이동·덮어쓰기 금지**.

| 파일 | 비고 |
|---|---|
| `eval/baseline.json` | 옛 라벨 기준. 비교 앵커 아님(보존만). |
| `test_data/main_eval/labels.json` | GT 정본. 정정 시 백업(`.bak`) 필수 + `validate_main_eval.py` 통과. |
| `test_data/labeling_vocab.py` | R1에서 확정된 라벨 스키마. |
| `test_data/main_eval/SOURCE.md` | 외부 출처·라이선스 추적. |

**가장 자주 일어나는 사고 — `baseline.json` 덮어쓰기**: `RUN_EVAL_OUT` 미설정으로 `scripts/run_eval.py`가 기본 출력 경로(`baseline.json`)를 덮어쓴 ACC-fix 사고가 실재. **모든 측정 명령 직전에 `$env:RUN_EVAL_OUT` 설정 여부 확인 의무**.

---

## 2. 현재 비교 앵커 (활성 기준점)

> **⚠️ R15 — GT가 3단(tier: 건강/경미/비건강)으로 마이그레이션됨** (분모 35→39, ambiguous 0). 아래 이진 앵커들은 전부 **옛 이진 GT 기준**이라 3단 측정과 **직접 비교 불가 = 역사적 참고**로 강등. 새 **3단 baseline은 다음 라운드(run_eval 3단 채점 확장 + 재측정) 후 확정**된다. 그 전까지는 활성 3단 앵커 없음.

- **이진 참고 앵커(R15 이전, 직접 비교 불가)**: `eval/after_acc_armC_3p5flash_relabeled.json` (R13 Arm C, analyze=**gemini-3.5-flash/global**, **GT 정정 후**)
  - acc **71.4%** (25/35), 분모 **35**, FP **10** · TP **13** · TN **12** · FN **0**, recall **1.0**, precision 0.565
  - GT 재검(FP14 방향a) → 4건 건강→비건강+status 정정(haengun_001 건조·epipremnum_001 병해 의심·spathiphyllum_001/003 과습) → FP 14→10. 무과금 재채점(`rescore_from_output.py`).
  - 잔여 10 FP = 진짜 over-call 영역(전부 유지(건강) 케이스). FP의 진짜 레버는 "미용 vs 병리" 임계값(generate/guard).
  - **R14에서 generate 프롬프트 레버는 기각**(증상 층 비분리 + 프레이밍이 status 하류라 불가, 게이트 C: FN 0→1·FP 10→11). 진짜 병목 = 이진 healthy/5-status 스키마. (앵커 수치·경로 불변 — R14 롤백 `9624889`.)
- **참고(강등)**: `eval/after_acc_armC_3p5flash.json` = 정정 전 raw 측정 (acc 60.0%·FP14·FN0). 보존(aux_plantvillage 포함). **비교 금지**(라벨 정정 전).
- **참고(강등)**: `eval/after_acc_r12d1_relabeled.json` = 2.5-pro 기준 옛 앵커 (acc 62.86%·FP13·FN0). 보존·**비교 금지**(arm 다름).
- **참고 — 옛 baseline.json은 비교 앵커 아님**: 라벨 정정 전 기준. 보존만.
- 새 라운드는 항상 이 활성 앵커 대비 게이트 설계.

---

## 3. 환경 규칙

### 3.1 OS·셸·인터프리터

- **OS**: Windows
- **셸**: **PowerShell** (Bash 사용 금지 — `$env:` 문법이 Bash에서 잘못 해석되어 사고 전례 있음)
- **Python**: `.venv\Scripts\python.exe` (가상환경 우선)
- **인코딩**: 모든 파일 UTF-8 (BOM 없음). PowerShell `Set-Content`로 CP949 깨짐 사례 있음 → BOM·인코딩 확인 필수.

### 3.2 측정 명령 표준 (반드시 이 패턴)

```powershell
$env:RUN_EVAL_OUT="after_acc_<라운드명>.json"
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

**측정 전 자가점검**:
1. `$env:RUN_EVAL_OUT` 설정 여부 확인 (미설정이면 `baseline.json` 덮어쓰기 위험).
2. `verify_dry_top10_entry` 등 자가점검 통과 (실패 시 exit 2 → Gemini 호출 0건).
3. 측정은 **사용자 PowerShell 직접 실행**. CC가 임의로 Gemini 호출 시작 금지.

### 3.3 RAG·Chroma

- `a_dataset_rag` / `b_dataset_rag` 두 컬렉션 운용.
- 재적재: `.venv\Scripts\python.exe scripts\build_b_dataset_rag.py` — 임베딩 과금 발생.
- 메타 키: `title, card_id, problem_type, source, source_id, section, license, source_url`.
- `status_hint` 메타는 **R12d-1에서 dead code 확인 후 제거** — 다시 추가 금지.

### 3.4 analyze 모델·엔드포인트 (R13 Arm C 채택)

- **기본**: `gemini-3.5-flash` / Vertex **global** 엔드포인트 (was 2.5-pro / asia-northeast1).
- 진실원: **모델 기본값 = 버전관리 코드**(`app/vision/gemini.py` fallback). **location = `.env`의 `GOOGLE_CLOUD_LOCATION=global`** (`load_dotenv(override=False)`라 .env 기존값이 코드 fallback을 가리는 shadowing 방지 위해 정합; `ANALYZE_MODEL`은 .env에 없어 코드 fallback 적용).
- **롤백 메커니즘 보존**: env override로 2.5-pro/asia 복귀 — `$env:ANALYZE_MODEL="gemini-2.5-pro"`, `$env:GOOGLE_CLOUD_LOCATION="asia-northeast1"` (세션 env가 .env·코드 fallback보다 우선).
- **global 엔드포인트 = 데이터 레지던시 미보장** (식물 사진이라 수용).
- **R13 Arm C 결론**: 모델 교체 = FP 중립(13→14, 1케이스)·recall 1.0 유지 → **속도 근거로 채택**. FP의 진짜 레버는 "미용 vs 병리" 임계값(generate/guard) → 다음 트랙.

---

## 4. 작업 원칙 (절대 위반 금지)

### 4.1 변수 격리 (Variable Isolation)

**한 라운드 = 한 변수.** 여러 변경을 동시에 측정하면 원인 분리 불가.

- 라운드 시작 시 "이번 변수는 정확히 무엇인가"를 명시.
- 변수 외 영역은 동결 (코드·프롬프트·카드·가드·RAG 등 명시적 표기).
- 변수 외 변경이 우연히 들어가면 **변수 누수** — 측정 결과 무효.

### 4.2 FN 0 절대 사수 (Recall 게이트)

`post_guard.fn = 0` (= recall 1.0)은 **절대 사수 게이트**.

- 어떤 변경이든 FN 1+ 발생 시 즉시 revert 검토.
- "FN이 견고한가" 항상 점검 (analyze 비결정성에 의존하는 FN=0은 견고하지 않음).
- 위치 veto·가드 보수화 등 recall 사수 레버는 분리 라운드로.

### 4.3 Surface 패치 금지

다음을 프롬프트·카드·가드에 박지 마라:
- 특정 **종 이름** (드라세나·행운목·스킨답서스 등)
- 특정 **케이스 ID** (`haengun_003` 등)
- 특정 **증상 유형 목록** ("반점·괴사·병반을 만들지 마라" 식)

→ 새 종·새 증상이 들어올 때마다 목록을 늘려야 하는 패치는 일반화 실패.
→ **추상 원칙 하나**로 모든 종류를 커버 (예: "관찰되지 않는 이상 징후를 추론·날조하지 마라" — 증상 종류 불문).

### 4.4 추측 금지 (증거 기반)

모든 주장에 근거 첨부:
- 코드 변경 영향 주장 → 실제 코드 인용
- 측정 결과 해석 → JSON 원본 + case_id
- 분류·판정 → 데이터에서 추출한 표

근거 없이 단정 금지. 불명확하면 "확인 안 됨"으로 보고. 측정 vs 코드 불일치 발견 시 모순 자체를 보고.

### 4.5 추가 vs 빼기 균형

"계속 추가만 한다고 안 나아진다"는 R12d-1의 통찰. 시스템에 surface 패치·dead metadata가 누적되면 본질 기여 측정 불가. **정기적으로 빼기 라운드**로 본질/surface 분리 측정.

---

## 5. 표준 작업 라이프사이클

모든 작업은 아래 단계를 거친다.

### 5.1 Read-only 선결 게이트 (변경 전 보고)

변경 전 다음을 **읽기 전용으로 보고**. 예상 외 상태 발견 시 중단·질의:
1. 현재 브랜치/tip — 이전 라운드 푸시 완료 상태인지
2. 변경 대상 파일의 현 상태
3. 변수 격리 보증 — 동결 영역이 의도대로 동결인지
4. 알려진 잔재(`status_hint` 같은 dead code) 부재 확인

### 5.2 합성 검증 (측정 전, 무과금)

코드·프롬프트 변경 후 측정 전 점검:
- `import` OK
- `pytest` 회귀 없음 (기존 테스트 통과)
- `grep`으로 변경 의도대로 반영 확인
- 합성 케이스 sanity (LLM 결정 보장은 불가, 문법·매핑 표 작동만)

**합성 통과 ≠ 실측 통과** (전례: R10 합성 4/4 통과 후 실측 효과 0). 합성은 sanity일 뿐.

### 5.3 측정 (사용자 PowerShell, Gemini 과금)

§3.2 표준 명령으로 실행. CC가 임의로 시작 금지.

### 5.4 Atomic 커밋 분리

한 커밋 = 한 의도. 부분 revert 가능하게.

**커밋 prefix 컨벤션**:
- `feat:` 신규 기능·룰
- `fix:` 버그 수정
- `chore:` 정리·구조 변경 (코드 동작 무변경)
- `docs:` 문서·작업 프롬프트 추가
- `refactor:` 동작 동일·구조 변경 (빼기 포함)

**푸시는 사용자 검토 후.** CC가 임의 푸시 금지.

### 5.5 보고

§6 보고 형식 표준 준수.

---

## 6. 보고 형식 표준

작업 완료 보고에 다음을 포함:

### 6.1 게이트 통과·실패 표

| 지표 | 기준 | 측정값 | 판정 |
|---|---|---|---|
| 🔴 `post_guard.fn` | = 0 | ? | ✅/❌ |
| `post_guard.fp` | ≤ 이전 | ? | ✅/❌ |
| latency mean | ±10% | ? | ✅/❌ |

### 6.2 5-status 혼동표

행=GT true_status, 열=pred_status. 과습·영양 부족 독립 GT 표본 0은 unmeasured 표기.

### 6.3 비교 앵커 명시

R8 / R12b / R12c-1 / R12d-1 등 어떤 측정 결과와 비교했는지 명시.

### 6.4 측정 한계 (정직)

- 단일 run vs 다중 run
- analyze 비결정성 ±1~2 노이즈 인지
- temperature 비결정성과 변경 효과의 교락 가능성
- 표본 작음(평가셋 35건)으로 인한 noise

### 6.5 변수 격리 보증

이 라운드에서 변경하지 않은 영역을 명시. "그 외 일절 무변경(변수 격리 유지)".

### 6.6 다음 라운드 후보 (참고용, 범위 X)

분기 조건과 함께 다음 라운드 후보 1~3개. 우선순위는 사용자 결정.

---

## 7. 사고 전례 (재발 방지)

### 7.1 ACC-fix 사고

- **원인**: `RUN_EVAL_OUT` 미설정 → `run_eval.py`가 기본 경로 `baseline.json` 덮어씀
- **대책**: 모든 측정 명령 직전 `$env:RUN_EVAL_OUT` 확인 (§3.2). 가능하면 pre-commit hook으로 구조적 차단.

### 7.2 antifab (날조 억제) 실패

- **시도**: analyze 프롬프트에 "관찰 충실성" 원칙 추가
- **결과**: FP 13→16, acc 62.86→54.3, latency +24%. 환각이 프롬프트 훈계로 안 잡힘.
- **교훈**: LLM에 추상 원칙으로 환각 통제 한계. 롤백 → 다른 레버(generate escalation, 카드 본문 정교화) 시도.

### 7.3 status_hint dead metadata

- **시도**: R12c-1에서 카드별 `status_hint` enum 매핑 추가
- **결과**: `app/` 어디서도 read 되지 않는 dead code. healthy→건조 FP 7→6 (analyze 비결정 노이즈 범위).
- **교훈**: 변경물이 실제 코드에서 read 되는지 사전 검증. CC가 변경 착수 전 코드 경로 확인.

### 7.4 R10 황화 충돌룰 = 효과 0

- **시도**: generate 프롬프트에 황화·갈변 충돌 시 우선순위 룰 추가
- **결과**: R11 측정에서 효과 0 확인, R12d-1에서 안전한 빼기 대상.
- **교훈**: 가설 단계 룰은 측정으로 검증, 효과 없으면 빼기. 누적 패치 회피.

### 7.5 "추가만으로 안 나아진다"

R7~R12c-1 누적 변경 5종(R7 트리거·R10 룰·R12b 정합룰·R12c-1 카드·status_hint)이 얽혀 기여도 분리 불가. R12d-1 빼기로 본질(카드)/surface(status_hint·R10 룰) 분리.

→ **시스템에 surface 패치 누적 시 정기적 빼기 라운드 의무화**.

### 7.6 pytest integration 실 Gemini 호출 사고

- **원인**: `tests/vision/`에 실 API를 호출하는 integration 테스트 2건 존재. `skipif`는 `GOOGLE_CLOUD_PROJECT`/`GEMINI_API_KEY` 부재 시 skip이지만, `app/vision/gemini.py`→`app/model_utils.py` 모듈 레벨 `load_dotenv()`가 pytest 프로세스에 `.env` 키를 주입 → skipif 무력화 → R13에서 `pytest tests/vision/` 회귀 점검이 실 Gemini 2회 호출.
- **대책**: **모든 회귀 점검은 `-m "not integration"`(또는 `-k "not integration"`) 필수.** 비측정 검증은 `genai.Client` mock 패치(과금 0)로.

---

## 8. 데이터·라벨 규칙

### 8.1 라벨링 자동화 금지 (§9)

- `ground_truth.{plant_name_korean, is_healthy, symptoms, diagnosis, true_status, tier}`는 **사람만 결정**.
- LLM·Vision API로 라벨 추정·확장·번역·축약 금지.
- 사용자 제공값을 **글자 그대로 박기** (CC가 표현 다듬기 금지).
- 예외: PlantVillage 폴더명 → 사전 매핑(사람이 정의한 dict)은 자동화 허용.

### 8.1a 3단 tier 스키마 (R15 도입)

- 라벨 스키마에 **`tier`(건강/경미/비건강)** 차원 추가 — `is_healthy` 이진 위에 얹는 심각도 층. `labeling_vocab.TIER_VOCAB`.
- 경미 전용 status = **`STATUS_MILD="경미"`** (별도 상수). **`STATUS_VOCAB` 5종 불변**(= `ALLOWED_STRUCT_STATUS` 계약) → run_eval 5-status 혼동표는 경미를 자동 skip, 이진에선 is_healthy=True → 건강 취급.
- 정합성(`validate_label`): tier↔is_healthy(비건강↔False, {건강,경미}↔True), tier↔true_status(건강→"건강"·경미→경미·비건강→원인 4종+원인미상).
- **비대칭 게이트 원칙(3단 채점 라운드 설계 기준)**: 비건강→건강 오분류 = **0 (하드 게이트, recall 사수)**, 비건강→경미 = **추적**(완전 실패는 아니나 감점), 과대(건강/경미→비건강) = **최소화**. 이진 FN 0 사수의 3단 확장.

### 8.2 라벨 정정 절차

1. 사용자가 이미지 재검 → 판정 결정
2. `labels.json` → `.bak` 백업 (타임스탬프 포함)
3. 변경 반영
4. `scripts/validate_main_eval.py` exit 0 확인
5. `scripts/rescore_from_output.py`로 재측정 없이 점수 재계산 가능 (Gemini 호출 0)

### 8.3 외부 데이터셋 라이선스

- 신설 카드·데이터 도입 시 `license` + `source_url` 명시 필수.
- 라이선스 표기 통일 (CC-BY 4.0 형식).
- 사용자 검토 게이트: CC가 카드 신설 후 사용자 OK 받기 전 build 진행 금지.

---

## 9. 보류·백로그 (변경 금지 영역)

- **`main_rag` → `a_dataset_rag` 명명 정합**: 별도 라운드 (B-2 분리). 진행 중 라운드에서 명명 변경 금지.
- **과습·영양 부족 독립 GT 표본 확보**: 현재 0건, 5-status 혼동표 미완.
- **드라세나 hard 3 (종 인지 영역)**: 카드·프롬프트로 변별 불가. 종-aware 가드 또는 종 메타 별도 설계.
- **자동화 도입 (pre-commit hook, 라운드 라이프사이클 스크립트)**: 라운드 안정화 후 도입.
- **출력 스키마 확장 (b)**: R14 동기 확정(generate/프레이밍으로 FP·톤 개선 불가, 심각도 차원 부재가 병목). **R15에서 GT 차원(tier 건강/경미/비건강) 추가 완료**(§8.1a). 남은 단계 = run_eval 3단 채점 확장 + 재측정 → 새 3단 baseline 확정 (다음 라운드).
- **plantvillage_50 tier 반영**: `validate_label`이 plantvillage 검증과 **공유**됨(R15에서 tier required 추가). `test_data/plantvillage_50/labels.json` **재생성 시 tier 반영 필요**(현재 파일 부재라 라이브 게이트 영향 0, migrate 스크립트는 `scripts/_archive/`).

---

## 10. CC 작업 시작 전 체크리스트

매 작업 시작 시 CC가 자가 확인:

1. ☐ 현재 브랜치/tip 확인 (이전 라운드 푸시 완료 여부)
2. ☐ 이번 변수 한 가지 명시 (변수 격리 보증)
3. ☐ 동결 영역 명시 (변경하지 않을 코드·프롬프트·카드)
4. ☐ Read-only 선결 게이트 수행 후 보고
5. ☐ 측정 전 `$env:RUN_EVAL_OUT` 설정 확인 의무
6. ☐ Atomic 커밋 분리 계획
7. ☐ 푸시 보류 (사용자 검토 후)
8. ☐ FN 0 사수 게이트 의식

---

## 11. 작업 산출물 경로 컨벤션

- **작업 프롬프트**: `docs/work_history/<라운드명>_task.md`
- **결과 보고서**: `docs/work_history/<라운드명>_result.md`
- **진단 보고서** (read-only): `docs/work_history/<라운드명>_diagnosis.md`
- **측정 출력**: `eval/after_acc_<라운드명>.json` (`RUN_EVAL_OUT`으로 지정)
- **컨텍스트 덤프**: `docs/context_dumps/`

---

## 12. 이 파일의 진화

CLAUDE.md는 **살아있는 문서**. 다음 시점에 업데이트:

- 새 사고 발생 → §7 사고 전례에 추가
- 새 절대 불변 파일 생성 → §1에 추가
- 새 비교 앵커 확정 → §2 업데이트
- 새 보류 항목 → §9에 추가
- 본질로 입증된 변경 → 해당 섹션에 명시 (기여도 추적)
- Dead code·실패 시도 빼기 → §7에 빼기 근거 기록

업데이트 권한: 사용자(랑) 또는 사용자가 위임한 라운드 결과 보고 시 명시적 변경 제안.

---

*마지막 업데이트: 2026-06-10 — R15: GT 3단 스키마 반영(tier 건강16/경미7/비건강16, ambiguous 0). vocab/validate 확장(TIER_VOCAB·STATUS_MILD), 이진 앵커 역사적 참고로 강등. 다음=run_eval 3단 채점 확장 + 재측정 → 3단 baseline 확정.*
*다음 업데이트 트리거: run_eval 3단 채점 라운드 설계·결과 보고 시.*
