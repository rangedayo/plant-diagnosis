# R12a 사전 — 가드 위치 veto 진단 (read-only)

> ⚠ read-only 진단. 측정·코드·프롬프트·baseline **무변경**. 기존 코드(`app/graph.py`) +
> 측정 JSON 4종(`v2`/`relabeled`/`escalation`/`antifab`) 분석만. 커밋·푸시 보류.

---

## PART A — 가드 cosmetic 판정 로직 + 위치 토큰 현재 취급

### A.1 cosmetic 판정 함수 (graph.py L76-82)

```python
def _symptom_is_cosmetic(symptom: str) -> bool:
    """끝·가장자리·소수 잎 국한 변색만인 cosmetic 증상인지 (병변 단어 없을 때만)."""
    if _symptom_has_lesion(symptom):
        return False
    has_loc = any(tok in symptom for tok in STATUS_GUARD_COSMETIC_LOCATION)
    has_disc = any(tok in symptom for tok in STATUS_GUARD_COSMETIC_DISCOLOR)
    return has_loc and has_disc
```

cosmetic = **병변 토큰 없음 AND (cosmetic 위치 토큰 1+) AND (변색 토큰 1+)**.

### A.2 토큰 리스트 현황 (graph.py L55-67)

| 리스트 | 내용 |
|---|---|
| `STATUS_GUARD_LESION_TOKENS` | 고사·마름·마른·시들·시듦·위조·**황화**·반점·괴사·부패·썩·무름·처짐·주름·손상·절단·찢·구멍·뚫·확산·번짐·줄기·부착·물질·백색·흰·검은·흑색·곰팡 |
| `STATUS_GUARD_COSMETIC_LOCATION` | 잎끝·잎 끝·끝부분·끝 부분·**가장자리**·일부·자루·엽초·잎집·불염포·꽃 |
| `STATUS_GUARD_COSMETIC_DISCOLOR` | 갈변·변색·갈색 |
| `STATUS_GUARD_DISEASE_TOP1` | disease·pest |

### A.3 "아래/하엽/하부/기부/아래쪽" 위치 토큰의 현재 취급 — **어느 리스트에도 없음**

- `COSMETIC_LOCATION`에는 잎의 **끝·가장자리**(말단부)만 있고, **하부 위치(아래/하엽)는 없음**.
- `LESION_TOKENS`에도 위치 토큰 없음.
- 결과: 하부 위치 신호는 **판정에 전혀 반영되지 않고 통째로 무시**된다.
  `"아래쪽 잎의 끝과 가장자리 갈변"`은 `"끝"·"가장자리"`(COSMETIC_LOCATION) + `"갈변"`(DISCOLOR)
  매칭으로 **cosmetic=True**가 되고, `"아래쪽"`은 평가에 0 기여.

### A.4 가드 발동 조건 `all_cosmetic_nondisease_top1` (graph.py L105-110)

```python
# 규칙 3: 전 증상 cosmetic + 비-disease/pest top_1 → 건강 교정 (핵심)
if all(_symptom_is_cosmetic(s) for s in syms):
    top1 = str(top_1_problem_type or "").strip().lower()
    if top1 not in STATUS_GUARD_DISEASE_TOP1:
        return GUARD_HEALTHY_STATUS, "all_cosmetic_nondisease_top1"
    return cur, None  # disease/pest top_1 → 보수적 유지
```

= **모든 observed_symptoms가 cosmetic** AND **top_1 problem_type이 disease/pest 아님** →
비건강→**건강**으로 over-correct. 이게 haengun_006을 건강으로 뒤집은 경로.

---

## PART B — haengun_006 FN 메커니즘 (`after_acc_generate_escalation_v2.json`)

```
image_id:           self_haengun_006
gt_is_healthy:      False         (gt_true_status: 건조)
guard_pre_status:   건조           ← generate는 옳게 비건강(건조) 판정
pred_status:        건강           ← 가드가 뒤집음
guard_fired:        True
guard_reason:       all_cosmetic_nondisease_top1
observed_symptoms:  ['아래쪽 잎의 끝과 가장자리 갈변']   ← 단일 증상
→ healthy_match: False = FN
```

**무시 지점 정확히**: 유일 증상 `"아래쪽 잎의 끝과 가장자리 갈변"`에서
`"끝"`·`"가장자리"`+`"갈변"`이 cosmetic 매칭을 성립시켜 `_symptom_is_cosmetic=True`.
병변 토큰 없음 → 규칙 2 통과 → 규칙 3에서 top_1≠disease/pest → **건강 교정 = FN**.
위치 신호 `"아래쪽"`이 A.3대로 어디에도 안 걸려서, **하엽 갈변(건조의 전형 신호)을
말단 cosmetic과 구별하지 못한 것**이 FN의 직접 원인. ← veto를 끼울 자리.

---

## PART C — 위치 veto 설계 + 영향 시뮬레이션

### C.1 veto 규칙

규칙 3에서 건강 교정을 반환하기 **직전**, observed_symptoms 중 하나라도 위치 veto 토큰을
포함하면 교정을 **차단**(비건강 유지). 병변 veto(규칙 2)와 같은 철학 — cosmetic 판정 위에
얹는 보수적 안전판.

**토큰 후보(보수적 최소 집합)**: `("아래", "하엽", "하부")`
— `"아래"`가 `아래쪽·아래잎·아래 잎`을 모두 substring 커버. haengun_006(`"아래쪽"`)을 잡기엔
이 3개로 충분. `오래된 잎·묵은 잎·기부`는 과포함(FP↑) 소지 → **1차 제외 권고**(C.4).

### C.2 시뮬레이션 (v2 run, guard 발동 4건 전수)

| image_id | gt_healthy | reason | 위치토큰 | veto 영향 |
|---|---|---|---|---|
| self_dracaena_002 | True | cosmetic | 없음(여러 잎 끝의 바삭한 갈변) | 영향 없음 — 정상 건강 교정 유지 |
| **self_haengun_006** | **False** | cosmetic | **있음(아래쪽)** | **건강 교정 차단 → FN 복구** |
| inat_chlorophytum_003 | True | cosmetic | 없음(일부 잎끝 갈변) | 영향 없음 |
| inat_spathiphyllum_001 | True | cosmetic | 없음(잎끝·가장자리 갈변) | 영향 없음 |

**트레이드오프(v2): FN 방지 1건(haengun_006) vs 새 FP 0건.**

### C.3 교차 확인 — 잠재 FP 리스크 (relabeled/escalation/antifab 3종 추가)

위치 토큰을 가진 **gt-건강** 케이스를 4개 run 전수 스캔한 결과,
**거의 전부 동시에 병변 토큰(황화·고사·마름)을 포함** → `_symptom_is_cosmetic`이 이미
False → cosmetic 교정 규칙 자체가 발동 안 함 → **veto와 무관하게 이미 비건강/FP**:

| run | gt-건강 + 위치토큰 케이스 | 동반 병변토큰 | cosmetic 교정? |
|---|---|---|---|
| relabeled | aglaonema_003(아래잎 **황화**), spathiphyllum_003(아래잎 **황화**) | 황화 | ✗ (이미 비건강) |
| escalation | haengun_001(아래잎 **황화**), 위 2건 | 황화 | ✗ |
| antifab | dracaena_006(아래쪽 잎 **고사**), haengun_001, aglaonema_003 등 | 고사·황화 | ✗ |

→ veto가 **새 FP를 만들려면** "전 증상 cosmetic(병변 토큰 0) + 위치 토큰 동시 보유 + gt 건강"
케이스가 필요한데, **가용 4개 run에 0건**. 현 데이터 기준 veto의 FP 비용 = **0 (관측)**.

### C.4 잔존 리스크 (정직)

- **개념적 충돌**: generate 프롬프트의 cosmetic 패턴 (4) "식물 아래쪽 오래된 잎에만 국한된
  변색 = 자연 노화 = 건강"과 이 veto는 **정면 충돌**. 즉 진짜 건강한 자연 노화 개체가
  "아래쪽 잎 끝 갈변"만 보고되면 veto가 건강 교정을 막아 **FP**가 된다. 현 4개 run엔 그
  인스턴스가 없을 뿐, **비결정 analyze가 다른 run에서 만들어낼 수 있음**(FP 리스크 0 아님).
- **recall 우선 원칙(CLAUDE.md §4.2)**으로 이 트레이드오프는 정당화됨 — haengun_006의 실제
  gt가 **건조(비건강)**인 것처럼 하엽 갈변은 노화가 아닌 실제 수분 문제일 수 있고, veto는
  recall-safe 방향으로 기운다. 비용은 precision(FP), 사수 대상은 recall(FN). FN 0이 절대
  게이트이므로 recall 우선.
- **과포함 회피**: `기부·오래된 잎`을 넣으면 epipremnum_007(`잎 기부의 넓은 갈색 마름`) 류와
  맞물려 의도 외 작동 위험 → 최소 집합 `(아래, 하엽, 하부)` 권고.
- **단일 run 한계**: 시뮬은 v2 1회 + 교차 3회. analyze 비결정성으로 FN/FP 케이스 구성이 run마다
  ±1~2 흔들림. 실측으로만 확정.

---

## PART D — 처방 요약

1. **로직**: cosmetic = 병변토큰0 ∧ (말단 위치토큰) ∧ (변색토큰). 하부 위치(아래/하엽)는
   **어느 리스트에도 없어 무시됨**.
2. **haengun_006 FN**: `"아래쪽 잎의 끝과 가장자리 갈변"`의 `"끝·가장자리·갈변"`이 cosmetic 성립,
   `"아래쪽"`은 0 기여 → 건강 over-correct.
3. **veto 설계**: 규칙 3 건강 반환 직전, 위치 토큰 `(아래, 하엽, 하부)` 1+ 보유 시 교정 차단.
   병변 veto와 동형의 안전판.
4. **트레이드오프 추정**: FN 방지 **1건**(haengun_006) vs 새 FP **0건**(v2) / 교차 3 run에서도
   순수-cosmetic+위치토큰+건강 케이스 0건. 단 프롬프트 자연노화 패턴과 개념 충돌로 FP 리스크는
   **0이 아님(미관측)**.
5. **구현 권고**: ✅ 구현 권고. 단 (a) 최소 토큰 집합 `(아래, 하엽, 하부)`, (b) `_symptom_is_cosmetic`을
   건드리지 말고 **규칙 3 직전 별도 veto 함수**로 layered(병변 veto와 동형, FN-safety 추론 격리),
   (c) 측정 게이트 = **FN 복구(haengun_006 잡힘) + FP 과증가 없음(≤ 기준점)**.
6. **리스크**: 가드 안전판 최초 수정. FN을 줄이는 방향(보수적)이라 recall 게이트엔 안전.
   진짜 비용은 precision(자연노화 건강 개체 오판). 측정에서 FP 추세 감시 필수.

---

## 다음 단계 (참고 — 범위 X)

R12a 본 구현: **정합룰(prompts.py) 롤백 + 위치 veto 구현 + 측정**. 측정 변수 = veto 하나
(롤백은 기준점 `after_acc_r12d1_relabeled.json` 복귀). 게이트: 🔴 FN 복구 + FP 과증가 없음.

*시뮬 스크립트: `scripts/diagnostics/r12a_veto_sim.py` (read-only, 커밋 보류).*
