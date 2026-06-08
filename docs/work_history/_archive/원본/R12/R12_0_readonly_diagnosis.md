# R12-0 — Read-Only 진단 보고서 (RAG 흐름 + Guard 조건 + b_dataset 카드 분포)

> 라운드 성격: **read-only**. 소스/Chroma 무변경. 산출물은 본 보고서 + 재사용 가능한
> 읽기전용 probe 스크립트(`scripts/diagnostics/r12_0_probe_rag.py`)뿐이다.
> 측정(run_eval) 미실행 — 모든 수치는 R11 결과 JSON과 Chroma 조회·코드 인용에서만 도출.

## 0. 게이트 / 제약 재확인

- 수정 금지: `app/`·`scripts/`(probe 제외)·`eval/`·`prompts.py`·`graph.py`·`model_utils.py`.
- `run_eval.py` / `build_b_dataset_rag.py` 실행 금지 — 미실행.
- Chroma: `get`/`query`(읽기)만. `add/upsert/update/delete/modify` 미호출.
- §C.2 top_10은 사용자 승인 하에 **프로덕션 재현(EN) 임베딩 probe**로 측정
  (gpt-4o-mini 번역 + ada-002 임베딩, Gemini 0건). 상세는 §C.2 참조.

### §6 시작 전 확인 결과
| 항목 | 결과 |
|---|---|
| 브랜치 / tip | `main` / `9797463` (ACC-fix2 보존) — R11-post 상태 ✅ |
| `eval/after_acc_r10_v2_rag_ok.json` | 존재(untracked). **R11 v2 재측정 산출물** = §C 입력 ✅ |
| `eval/after_acc_r7_dry_guard.json` | 존재 — R8 앵커 ✅ |
| 무효 R11 `after_acc_r10_analyze_generate.json` | 부재(삭제 완료) ✅ |

R11 v2가 존재한다는 것은 **사용자가 이미 R11 재측정을 Gemini 과금으로 수행**했고, fix2의
RAG 자가점검(#4)을 통과해 b_dataset_rag가 정상 적재된 상태에서 측정됐음을 뜻한다(rag_source에
b 출처 카드가 실제로 등장 — §C.2). 따라서 본 진단은 "RAG 사망 무효 측정"이 아닌 **정상 RAG 위에서의
R10 프롬프트 결과**를 분석한다.

---

## 영역 A — graph.py RAG 호출 흐름

### A.1 흐름도

```
analyze (Gemini)                  keyword_node                         retrieve_node
observed_symptoms(한국어 명사구) ─► dedup + [:RAG_SYMPTOM_KEYWORD_MAX(5)]  ─► query_en 우선
                                  = keywords_ko                          (mq = query_en or query_ko)
                                       │                                      │
                                       ├─ generate_english_keywords          ├─ b_dataset_rag  top_k=7
                                       │   (gpt-4o-mini, 1콜) = keywords_en   ├─ a_dataset_rag  top_k=3
                                       │                                      ▼
                                       ├─ query_ko = plant_name + keywords_ko   merge(가중) → raw cosine ≥0.65 필터
                                       └─ query_en = " ".join(keywords_en)      → 식물필터(generic 0.9·match +0.1) 재정렬
                                                                                ▼
                                                       top_3 → problem_type 가중 다수결(distribution)
                                                       전체 filtered docs에 [problem_type] prefix
                                                                                ▼
                                                                          generate_node
                       context_summary(묘사+관찰정보+타입분포 텍스트) + rag_chunks(prefix 카드 본문) → gpt-4o-mini
```

### A.2 단계별 코드 인용

**(1) keyword_node — observed_symptoms 채택 + 영문 번역** [graph.py:448-479](../../app/graph.py#L448-L479)
```python
symptoms = [s.strip() for s in (state.get("observed_symptoms") or []) if s and str(s).strip()]
keywords_ko = list(dict.fromkeys(symptoms))[:RAG_SYMPTOM_KEYWORD_MAX]   # 가공=dedup+truncate(5)뿐
keywords_en = await model_utils.generate_english_keywords(keywords_ko) if keywords_ko else []
...
query_ko = " ".join(parts)            # parts = [plant_name] + keywords_ko
```
- 가공 단계: **요약/재추출 없음**. analyze의 한국어 명사구를 그대로 dedup→최대 5개로 자르고,
  `generate_english_keywords`(gpt-4o-mini)로 **같은 길이의 영어 키워드로 번역**.
- `RAG_SYMPTOM_KEYWORD_MAX = 5` 정의 위치 [graph.py:43](../../app/graph.py#L43) — RAG 쿼리에 쓰는
  observed_symptoms 명사구 최대 개수를 통제.

**(2) retrieve_node — 쿼리 텍스트 결정 + 컬렉션 호출** [graph.py:540-547](../../app/graph.py#L540-L547)
```python
mq = (query_en or query_ko).strip()           # ★ 영문 쿼리 우선, query_ko는 폴백
docs_b, metas_b, sims_b, err_b = _chroma_query_sync(mq, db_path, B_DATASET_TOP_K, "b_dataset_rag")  # top_k=7
docs_main, ... = _chroma_query_sync(mq, db_path, MAIN_TOP_K, "a_dataset_rag")                        # top_k=3
```
- `B_DATASET_TOP_K = 7`(메인), `MAIN_TOP_K = 3`(보조 a_dataset_rag) [graph.py:28-29](../../app/graph.py#L28-L29).
- **두 컬렉션 모두 동일한 `mq`(영문)로 호출**. plant_name은 query_en에 포함되지 않음 → 실제 쿼리는
  순수 영어 증상 키워드.

**(3) 결과 후처리** [graph.py:603-734](../../app/graph.py#L603-L734)
- merge: `_merge_rag_triples` — b 상위 7 + main 상위 3 가중정렬 후 doc 기준 dedup
  (B_DATASET_SIM_WEIGHT=1.0, main의 source==UC_IPM만 0.85 페널티).
- 필터: raw cosine `≥ RAG_MIN_COSINE_SIMILARITY(0.65)` [graph.py:641](../../app/graph.py#L641).
- 식물 필터: 문서 제거 없이 generic 페널티(0.9)·식물명 매칭 부스트(+0.1) 재정렬 [graph.py:298-320](../../app/graph.py#L298-L320).
- **top_3로 좁히는 지점**: `_weighted_problem_type_majority(filtered_metas[:3], filtered_sims[:3])`
  [graph.py:709-711](../../app/graph.py#L709-L711) — top_3의 problem_type을 raw cosine 가중 다수결.
  단 카드 본문(rag_docs)은 top_3가 아니라 **필터 통과 전체**가 generate로 전달된다.
- 메타데이터: `card_id, problem_type, source, title, source_id, section` (§C.1 확인). 각 카드 본문 앞에
  `[problem_type]` prefix를 박아 generate에 타입 노출 [graph.py:418-425](../../app/graph.py#L418-L425).

**(4) generate 입력** [graph.py:761-774](../../app/graph.py#L761-L774)
- `context_summary`: 묘사 + 관찰정보(식물명/신뢰도/대안/증상) + **검색 타입 분포 텍스트**
  (우세 타입 / 1위 카드 타입 / 분포). `rag_chunks`: prefix 박은 카드 본문 join.

### A.3 검토자 가설 검증

| 검토자 가설 | 판정 | 근거 |
|---|---|---|
| "observed_symptoms가 keyword 단계에서 **그대로** 검색 키워드가 된다" | **절반만 참** | 한국어 키워드 선택은 그대로(dedup+5개 자르기만). 그러나 실제 RAG 쿼리는 그 키워드를 **gpt-4o-mini로 영어 번역한 `query_en`** ([graph.py:541](../../app/graph.py#L541)). 한국어 원문이 직접 쿼리되지 않는다. |
| 한국어 쿼리 → 영어 카드 매칭 (cross-lingual 임베딩?) | **아니오 — 번역으로 해결** | ada-002는 cross-lingual이 아니다. `keyword_node`가 영어로 번역(`generate_english_keywords` [model_utils.py:61](../../app/model_utils.py#L61))한 뒤 영어 카드를 영어 쿼리로 매칭. `query_ko`는 query_en이 빈 경우의 폴백뿐. |

**A 시사점**: 번역 단계(gpt-4o-mini)가 RAG 정확도의 숨은 의존점이다. "잎끝 갈변·바삭한 마름"이
`brown leaf tip / crispy desiccation`으로 번역되면 임베딩상 **"Brown leaf tips • Chemical"·
disease 카드와 더 가깝게** 매칭된다(§C.2). 즉 번역 자체는 충실하나, 번역된 영어 표현이 건조 카드보다
화학손상/병해 카드에 임베딩 근접한다.

---

## 영역 B — Guard 조건

### B.1 가드 발동 사유 전체 목록

`apply_status_guard` [graph.py:85-112](../../app/graph.py#L85-L112)는 **이진 게이트**(비건강→건강)만 교정한다.
relabel을 발생시키는 `by_reason` 키는 **단 2종**:

| reason | 트리거 조건 | 결과 |
|---|---|---|
| `empty_symptoms` | observed_symptoms가 빈 리스트 | → 건강 |
| `all_cosmetic_nondisease_top1` | 전 증상이 cosmetic **AND** top_1 problem_type ∉ {disease, pest} | → 건강 |
| (None) 이미 건강 | cur == "건강" | 무변경 |
| (None) 병변 veto | 증상 중 1개라도 LESION 토큰 포함 | 무변경(비건강 유지·FN0 안전판) |
| (None) cosmetic+disease top1 | 전 증상 cosmetic이나 top_1 ∈ {disease,pest} | 무변경(보수적) |
| (None) 혼재 | cosmetic도 병변도 아닌 증상 혼재 | 무변경 |

**가드가 reroute할 수 있는 status: 「임의의 비건강 → 건강」 한 방향뿐.** 비건강 enum끼리
(건조↔병해 의심↔영양 부족↔과습)의 교정은 **구조적으로 불가능**하다. 따라서 "건조를 병해로
오분류"한 케이스를 가드가 "건조로" 되돌리는 일은 설계상 없다.

### B.2 `_symptom_is_cosmetic()` 흐름 [graph.py:76-82](../../app/graph.py#L76-L82)
```
if 증상에 LESION 토큰 1개라도 → return False        # 병변 veto 우선
has_loc  = COSMETIC_LOCATION 토큰 중 1개라도 매칭
has_disc = COSMETIC_DISCOLOR 토큰 중 1개라도 매칭
return has_loc AND has_disc                          # 위치 AND 변색 동시 충족 시에만 cosmetic
```

### B.3 토큰 리스트 (코드 그대로) [graph.py:55-67](../../app/graph.py#L55-L67)
```python
STATUS_GUARD_LESION_TOKENS = (
    "고사","마름","마른","시들","시듦","위조","황화","반점","괴사","부패","썩","무름",
    "처짐","주름","손상","절단","찢","구멍","뚫","확산","번짐","줄기","부착","물질",
    "백색","흰","검은","흑색","곰팡")
STATUS_GUARD_COSMETIC_LOCATION = (
    "잎끝","잎 끝","끝부분","끝 부분","가장자리","일부","자루","엽초","잎집","불염포","꽃")
STATUS_GUARD_COSMETIC_DISCOLOR = ("갈변","변색","갈색")
STATUS_GUARD_DISEASE_TOP1 = ("disease","pest")
```

### B.4 haengun_006 추적 (FN=1의 정확한 경로)

입력: `observed_symptoms = ["아래쪽 잎의 끝과 가장자리 갈변"]`, top_1 problem_type = `abiotic`,
pre_status = `병해 의심`.

1. `_symptom_has_lesion("아래쪽 잎의 끝과 가장자리 갈변")` → LESION 토큰 어느 것도 미포함
   (갈변은 DISCOLOR이지 LESION 아님) → **False**. 병변 veto 통과.
2. `has_loc`: `"가장자리"` ∈ COSMETIC_LOCATION → **True**.
3. `has_disc`: `"갈변"` ∈ COSMETIC_DISCOLOR → **True**.
4. → `_symptom_is_cosmetic = True`. 증상 1개이므로 `all(...)` True.
5. top_1 = `"abiotic"` ∉ {disease, pest} → 규칙 3 발동 → **건강 교정 + `all_cosmetic_nondisease_top1`**.
6. cause 재생성(regenerate_healthy_cause) → "…흔히 나타나는 자연스러운 현상…". **GT=건조(비건강)인데
   건강으로 over-correct → 이 케이스가 R11 recall=0.875의 FN=1.**

### B.5 가드가 "진행성/범위 토큰"을 보는가?

- **진행성 토큰은 대부분 본다**: `고사·마름·처짐·주름·확산·괴사·시듦`은 전부 LESION에 존재 →
  실제로 건조 6건 중 5건(002·003·005·008·epipremnum_004)은 LESION 토큰을 동반해 **병변 veto로
  비건강 유지**된다(가드가 건강으로 깎지 않음). 검토자의 "진행성 토큰 미관측" 우려는 이 부분에선 반증.
- **순수 범위 quantifier는 안 본다**: `전체·여러·넓은·다수·전반·광범위`는 어느 리스트에도 없다.
- **결정적 사각**: 006이 빠진 이유는 진행성/범위 토큰 부재가 아니라, **위치 토큰 `아래쪽`(하엽=
  계통적 신호)을 cosmetic 정의가 무시**하기 때문. cosmetic은 "끝·가장자리 국한 변색"으로만 정의돼
  있어, 하엽 전반의 끝·가장자리 갈변(전형적 건조/계통 신호)을 국소 미용 손상과 구분하지 못한다.
  `아래/아래쪽/하엽`은 토큰 리스트 어디에도 없다.

---

## 영역 C — b_dataset_rag 카드 분포

### C.1 컬렉션 메타 통계 (Chroma read-only)

- **총 카드 수: 82** (컨텍스트 82와 일치 ✅).
- problem_type 분포: `pest 28 · general 18 · disease 14 · abiotic 10 · env 8 · frame 2 · nutrient 2`.
  → **건조/물부족 전용 타입 없음.** abiotic 10이 최근접 우산이나 내용은 화학·염류·일소 등 혼재.
  병해(disease)+해충(pest) = 42/82(51%)로 **코퍼스가 생물 피해 쪽으로 편향**.
- source 분포: `mobot_indoor 21 · psu_ucanr 20 · mu_trinklein 15 · psu_indoor 14 · mobot_herb 12`.
- 메타 키: `title·card_id·problem_type·source·source_id·section` (82 전수). **`body`·`sickKey` 없음** →
  graph.py의 sick_keys("D" 접두) 추출은 b_dataset에서 0건(a_dataset 전용 경로).

### C.1 건조 관련 카드 존재 — **약하게 있음 (sparse·비특이)**

documents+metadata 텍스트 매칭(영어):
| 키워드 | 카드 수 | 대표 ID |
|---|---|---|
| underwatering / dehydration / water stress / low humidity / crispy / leaf scorch | **0** | (없음) |
| drought | 2 | mobot_indoor_001, mobot_indoor_006 |
| dry soil | 1 | mu_trinklein_012 |
| drying | 1 | mobot_indoor_009 |
| scorch | 1 | psu_ucanr_015 |
| wilting / wilt | 5~7 | psu_ucanr_019, psu_indoor_013, mobot_indoor_001/008 … |
| "dry"(부분문자열) | 11 | (다수는 타 맥락) |

→ **건조 "전용" 카드는 사실상 `mobot_indoor_001`("Too dry", problem_type=`env`) 한 장**.
나머지는 generic/abiotic 본문에 dry/drought가 스쳐 언급되는 수준. underwatering·crispy·leaf scorch
같은 핵심 건조 어휘 카드는 **0건**. 한국어 키워드(건조·수분 부족 등) 0건은 영어 코퍼스라 당연.

### C.2 건조 6건 실제 검색 깊이

> 입력: R11 JSON의 observed_symptoms 재사용(analyze 재실행 0). 쿼리는 **프로덕션 재현**:
> dedup→`generate_english_keywords`(gpt-4o-mini)→`query_en`→ada-002→`b_dataset_rag` top_10.

**stored top_3 (R11 실측 — 영문 쿼리)와 재현 top_10이 일관**. 핵심: 건조 전용 카드
("Too dry"/"Wilting plant")가 **6건 중 1건(003)에서만 top_10(rank 7)에 진입**, 나머지 5건은
top_10에도 없음. 상위는 일관되게 **"Brown leaf tips • Chemical"(abiotic) + generic(frame/general)
+ disease/pest** 가 점령.

| case | gt | pred | top_3(실측) 우세 | 재현 top_10 내 건조카드 |
|---|---|---|---|---|
| haengun_002 | 건조 | 병해 의심 | frame / pest(Whiteflies) / '' | **없음** (Chemical·Yellowing·N-def·해충 위주) |
| haengun_003 | 건조 | 병해 의심 | general(저온) / '' / abiotic(Chemical) | **rank7 mobot_indoor_001 "Too dry"(env)**, rank5 "Wilting plant"(abiotic) |
| haengun_005 | 건조 | 병해 의심 | abiotic(Chemical) / '' / pest | **없음** (Chemical·Leaf spot·Anthracnose·Scale·Spider mites) |
| haengun_006 | 건조 | **건강(FN)** | abiotic(Chemical) / '' / nutrient(N-def) | **없음** (Chemical·저온·N-def·Salt build-up·Sunburn) |
| haengun_008 | 건조 | 영양 부족 | general(저온) / '' / general | **없음** (Chemical·저광·Anthracnose·Aphids·Leaf spot) |
| epipremnum_004 | 건조 | 병해 의심 | general / general / abiotic(Chemical) | **없음** (necrosis 쿼리→Gray mold·Anthracnose·Leaf spots 점령) |

재현 top_1은 6건 중 4건이 **`psu_ucanr_016` "Brown leaf tips • Chemical"(abiotic)** 또는
generic mu_trinklein. "Brown leaf tip"이라는 영어 번역이 화학손상 카드 제목과 거의 동일해
임베딩이 그쪽으로 쏠린다.

### C.3 결론적 분류 — **복합 (층위 B·C 지배, 층위 A 약점 동반)**

- **층위 A (약점)**: 건조 전용 카드가 코퍼스에 사실상 1장("Too dry", 게다가 `env`로 분류).
  underwatering/crispy/leaf scorch 핵심 어휘 카드 0건 → 검색이 잡을 "건조 정답 카드" 자체가 빈약.
- **층위 B (지배)**: 그 한 장조차 검색에서 밀린다. 6건 중 5건은 top_10 미진입, 1건(003)은 rank7로
  "Chemical"·generic 아래. 번역된 영어 증상("brown tip","crispy desiccation","necrosis")이 건조
  카드보다 화학손상/병해 카드에 임베딩 근접.
- **층위 C (지배)**: 상위 점령 카드의 problem_type이 `abiotic`(=Chemical)·`disease`·`pest`·`general`
  뿐 — generate가 status 건조로 옮길 앵커(`물 부족/건조` 타입)가 없다. 유일한 건조 카드도 `env`라
  건조 enum과 직결 안 됨.

→ **R12c는 "카드 추가"만으로 부족.** ①underwatering 전용 카드 신설(+명확한 water-stress
problem_type/status hint) ②검색에서 건조 카드가 Chemical/병해를 이기도록(쿼리 분리 또는 부스트)
③problem_type 택소노미에 건조 앵커 추가 — 세 개가 함께 필요.

### C.4 (교차 발견) cause–status 모순 — generate가 건조를 "알면서" enum을 안 고른다

R11 JSON의 pred_cause 인용:
| case | pred_status(enum) | pred_cause(자유서술) |
|---|---|---|
| haengun_003 | **병해 의심** | "**수분 부족** 또는 환경적 요인으로 인한 스트레스일 수 있습니다." |
| haengun_008 | **영양 부족** | "온도가 너무 낮거나, **과도한 건조**, 영양 부족 또는 과비 가능성…" |
| haengun_005 | 병해 의심 | "과습 또는 영양 부족일 수 있습니다." |
| haengun_006 | 건강(가드) | (가드 재생성된 건강 cause) |

→ **003·008은 자유서술에서 수분 부족/과도한 건조를 명시했는데 enum은 병해 의심/영양 부족.**
generate는 건조 신호를 인지하고도 enum 커밋에서 더 "강한"(병해) 또는 디폴트(영양) 카테고리로
빠진다. 이는 R9의 "analyze 상류 정보손실" 단독 결론을 **부분 수정**한다: 적어도 일부 케이스는
하류(generate)가 충분한 단서를 받고도 enum-prose 정합에 실패한다 → **R12b 레버리지 실재**.

---

## 종합 시사점 — R12a / R12b / R12c 설계 입력

### R12a (guard hotfix)
- FN=1(006)의 단일 원인: cosmetic 정의가 **하엽 위치(`아래/아래쪽/하엽`)를 무시**하고 끝·가장자리
  변색을 무조건 미용으로 본 것. 진행성/범위 토큰 추가로는 006이 안 잡힌다(006엔 그런 단어가 없음).
- 후보: cosmetic 판정에서 **위치 단서 `아래/아래쪽/하엽/하부` 동반 시 cosmetic 제외**(non-cosmetic
  veto). 추가로 순수 범위 quantifier `전체/여러/넓/다수/전반`도 veto 후보. 단 healthy 케이스의
  "아래쪽 잎 약간 갈변"류가 FP로 돌아설 위험 → 측정 필수.

### R12b (generate 단순화 + cause–status 일관성)
- §C.4가 직접 입력: generate가 cause에 "수분 부족/과도한 건조"를 쓰고도 enum=병해/영양. **enum을
  cause 텍스트와 정합시키는 제약**(예: cause가 수분/건조를 지목하면 status=건조 우선)이 003·008을
  바로 교정할 수 있다. 입력 설득 5회 실패와 달리, 여기선 generate가 이미 정답을 prose로 말하고 있다.
- 동시에 "약한 단서로 병해 의심 escalate" 경향 완화(005·epipremnum_004는 disease 카드 다수에 끌려감).

### R12c (RAG 보강)
- 층위 A+B+C 복합(§C.3). 최소: underwatering/물부족 전용 카드 2~3장 신설 + water-stress problem_type
  (또는 metadata `status_hint="건조"`) + "Too dry" 재분류(env→abiotic-water). 그리고 건조 쿼리가
  Chemical/병해 카드를 이기게 쿼리 분리 또는 problem_type 기반 부스트.

---

## 확정된 사실 vs 남은 불확실성

| 확정(코드/DB/JSON 근거) | 남은 불확실성(측정 필요) |
|---|---|
| RAG 쿼리는 영문(query_en) — 한국어 직접 쿼리 아님 (A.2) | R12a 위치-veto가 healthy FP를 얼마나 늘리는가 |
| 가드 relabel은 비건강→건강 1방향뿐, 비건강 간 교정 불가 (B.1) | R12b cause-status 제약이 003·008 외 케이스에 미치는 부수효과 |
| 006 FN의 정확 경로: 가장자리+갈변→cosmetic, top1=abiotic→건강 (B.4) | R12c 카드 추가 시 건조 카드가 실제 top_3에 진입하는 최소 부스트량 |
| 건조 전용 카드 사실상 1장(Too dry/env), 핵심 어휘 0건 (C.1) | 번역(gpt-4o-mini) 표현 변동이 검색 순위에 주는 분산 |
| 건조 6건 중 5건 top_10에 건조카드 미진입 (C.2) | generate enum 선택의 비결정성(temperature) 기여분 |
| generate가 003·008 cause에 건조 명시·enum 불일치 (C.4) | — |

---

## 다음 라운드 추천 — R12a 설계 (구체 후보)

1. **우선순위: R12b > R12a > R12c** 로 제안.
   - R12b가 가장 저비용·고확률: generate가 이미 cause에 정답을 쓰는 케이스(003·008)를 enum 정합만으로
     건조로 끌어올린다. recall 위험 낮음(비건강→비건강 이동).
   - R12a는 recall=FN0 사수에 직결하나 FP 증가 위험 → 단독 변경 + 즉시 측정 권장.
   - R12c는 적재/임베딩 과금·재발방지 비용 큼 → B·A 효과 측정 후 잔여분에 한정.
2. **R12a 구체 후보(택1 측정)**:
   - (a) `_symptom_is_cosmetic`에 위치 veto: 증상에 `아래/아래쪽/하엽/하부` 포함 시 cosmetic=False.
   - (b) 범위 quantifier veto 추가: `전체/여러/넓/다수/전반/광범위`.
   - (a)만으로 006 교정 가능. (b)는 002·008류 보강이나 이미 LESION veto로 비건강 유지 중 → 순효과 작을 것.
3. **게이트(측정 시)**: post.fn=0 사수(깨지면 즉시 revert) · post.fp ≤ R11 14 · 건조 발화 > 0 ·
   건강행 pred건조=0. 앵커 = R8 `after_acc_r7_dry_guard.json`, 비교 = R11 `after_acc_r10_v2_rag_ok.json`.

---

## 변경 파일 명시

이 라운드에서 변경한 파일:
- `docs/work_history/R12_0_readonly_diagnosis.md` (본 보고서)
- `scripts/diagnostics/r12_0_probe_rag.py` (읽기전용 Chroma probe, 다음 라운드 재사용)

그 외 **어떤 소스/Chroma/eval 파일도 변경하지 않았다.** `run_eval.py`·`build_b_dataset_rag.py` 미실행,
Chroma 컬렉션 무변경(`get`/`query`만). §C.2 임베딩 probe는 사용자 승인 하의 gpt-4o-mini+ada-002 호출
(Gemini 0건)이며 Chroma 쓰기 없음.
