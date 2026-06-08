# R12c-1-α 사전 — FP/TP 변별 진단 (read-only)

> 목적: 카드 negative(정상 감별) 신호 추가가 안전한지 판정. "TP엔 없고 FP에만 있는 변별 신호가 실재하는가"를 데이터로 확인.
> 입력: `eval/after_acc_r12d1_remove_surface.json` raw (R12d-1 단일 run). **측정·코드·카드 무변경(read-only).**
> **최종 결론: (C) 카드 텍스트 negative로 안전 공략 가능한 변별 축 없음.** 깨끗하게 분리되는 유일 축은 *종(species)* 이며 일반 카드는 종을 모름. 대안 2종(종 메타 / 라벨 점검) 제시.

## PART A — 전수 추출

### A-1. healthy→건조 FP 그룹 (true_status=건강 ∧ pred=건조) — 6건

| case_id | gt 종 | pred_sci | observed_symptoms | top_3 problem_type |
|---|---|---|---|---|
| self_dracaena_003 | 드라세나 송 오브 인디아 | Cordyline fruticosa | 여러 잎의 잎끝 갈변 및 마름 | abiotic-water · abiotic-water · abiotic |
| self_dracaena_004 | 드라세나 송 오브 인디아 | Dracaena deremensis | 여러 잎의 잎끝이 바삭하게 갈변 / 일부 잎의 **황화 및 고사** | abiotic-water · abiotic · "" |
| self_dracaena_006 | 드라세나 송 오브 인디아 | Dracaena reflexa 'Song of India' | 여러 잎의 잎끝 갈변 및 마름 / 일부 잎의 **전체 고사** / 잎의 **세로 말림** | abiotic-water · abiotic-water · abiotic |
| inat_chlorophytum_comosum_003 | 접란 | Chlorophytum comosum | 일부 잎끝 갈변 및 마름 | abiotic-water · abiotic · "" |
| inat_spathiphyllum_001 | 스파티필름 | Spathiphyllum wallisii | 잎끝 미세한 황화 / 잎 가장자리 갈변 및 마름 | abiotic-water · abiotic-water · abiotic |
| inat_spathiphyllum_002 | 스파티필름 | Spathiphyllum wallisii | 다수의 아래잎 갈변 및 **고사** | abiotic-water · "" · "" |

### A-2. 건조 TP 그룹 (true_status=건조 ∧ pred=건조) — 5건

| case_id | gt 종 | pred_sci | observed_symptoms | top_3 problem_type |
|---|---|---|---|---|
| self_haengun_002 | 행운목 | Dracaena fragrans | 아래쪽 잎의 종이 같은 마름 / 잎 표면 미세 황색 반점·주름 / 일부 잎끝 갈변 | abiotic-water · abiotic-water · frame |
| self_haengun_003 | 행운목 | Dracaena fragrans | 아래잎 전체가 갈색으로 마름 / 새순 잎 끝부분 마름 | abiotic · abiotic-water · abiotic-water |
| self_haengun_006 | 행운목 | Dracaena fragrans | 아래잎 일부 황화 / 일부 잎끝 갈변 및 마름 | abiotic-water · abiotic-water · nutrient |
| self_haengun_008 | 행운목 | Dracaena fragrans | 여러 잎의 잎끝 갈변 및 마름 / 전체적인 잎 처짐 | abiotic-water · abiotic · abiotic-water |
| inat_epipremnum_aureum_004 | 스킨답서스 | Epipremnum aureum | 잎 가장자리와 중앙부에 넓고 불규칙한 갈색 마름 | general · abiotic-water · general |

> 참고: true=건조인데 pred=**병해 의심**으로 빠진 `self_haengun_005`("잎끝 바삭한 마름" + "잎 표면 불규칙 노란 반점", top3 ["",abiotic,""])는 "건조로 끌려간" 그룹이 아니므로 dry-negative 신호의 FN 위험 대상에서 제외. 단 변별 분석엔 참고로 둠.

## PART B — 4축 변별 분석

| case | 분포 | 부위 | 진행성 | 종 |
|---|---|---|---|---|
| **FP** dracaena_003 | 여러 | 말단(잎끝) | 마름 | 드라세나 |
| **FP** dracaena_004 | 여러+일부 | 말단(잎끝) | **고사**·바삭 | 드라세나 |
| **FP** dracaena_006 | 여러+일부 | 말단(잎끝) | **전체 고사**·세로 말림 | 드라세나 |
| **FP** chloro_003 | 일부 | 말단(잎끝) | 마름 | 접란 |
| **FP** spath_001 | (무표기) | 말단(잎끝·가장자리) | 마름(+미세 황화) | 스파티필름 |
| **FP** spath_002 | 다수 | 전면(아래잎) | **고사** | 스파티필름 |
| **TP** haengun_002 | 일부 | 아래+말단 | 종이같은 마름 | 행운목 |
| **TP** haengun_003 | 전체 | 아래 전면+말단 | 마름 | 행운목 |
| **TP** haengun_006 | 일부 | 아래+말단 | 마름 | 행운목 |
| **TP** haengun_008 | 여러 | 말단+전면 | 마름·처짐 | 행운목 |
| **TP** epipremnum_004 | 단일 | 말단+**중앙부** | 마름(넓고 불규칙) | 스킨답서스 |

### 축별 분리 판정

| 축 | FP 분포 | TP 분포 | 분리? |
|---|---|---|---|
| 분포 | 여러/전체 4 · 일부/국소 2 | 여러/전체 2 · 일부/단일 3 | ❌ 양쪽 혼재 |
| 부위 | 말단(잎끝) 5 · 아래전면 1 | 아래/전면 동반 4 · 말단단독 1 | △ 약함(겹침) |
| 진행성 | 마름/고사 **6/6** (고사 3) | 마름 5/5 | ❌ 분리 안 됨 — FP가 오히려 더 심함 |
| **종** | 드라세나3·접란1·스파티필름2 | **행운목4·스킨답서스1** | ✅ **완전 분리(교집합 0)** |

### 텍스트 동일/근사 쌍 (카드로 변별 불가 → FN 위험군)
- **dracaena_003 "여러 잎의 잎끝 갈변 및 마름" ≡ haengun_008 "여러 잎의 잎끝 갈변 및 마름"** — 사실상 동일(haengun_008은 "전체적 처짐" 추가). **완전 동일 쌍.**
- **chloro_003 "일부 잎끝 갈변 및 마름" ≈ haengun_006 "일부 잎끝 갈변 및 마름"** — 근사 쌍(haengun_006은 "아래잎 일부 황화" 추가).
- dracaena_006 "여러 잎의 잎끝 갈변 및 마름"도 haengun_008과 앞부분 동일.
→ **텍스트 동일/근사 = 최소 3 FP가 TP 쌍둥이 보유.** 이들에 negative를 걸면 TP도 동시에 눌림.

### "고사"가 있는데 healthy인 FP
- dracaena_004("일부 잎의 황화 및 고사"), dracaena_006("일부 잎의 전체 고사"), spath_002("다수의 아래잎 갈변 및 고사") — **3건.**
→ 진행성 최상위 신호인 "고사"가 GT 건강에 존재. **진행성 축이 변별 불가인 결정적 증거**이며, 종 특이 정상(하엽 노화) 패턴 후보.

## PART C — 3유형 분류 + 결론

| case | 유형 | 근거 |
|---|---|---|
| dracaena_003 | **(나) TP와 텍스트 동일** | haengun_008과 증상 문구 동일 |
| dracaena_004 | **(다) 종 특이 정상** | "황화 및 고사" 동반, 건강 드라세나 |
| dracaena_006 | **(다) 종 특이 정상** | "전체 고사"·"세로 말림", 건강 드라세나 (텍스트도 TP와 겹침) |
| chloro_003 | **(나) TP와 텍스트 동일** | haengun_006과 근사 |
| spath_001 | (나)/(가) 경계 | "미세 황화"(경미)는 (가)성이나 "갈변 및 마름"이 TP와 겹침 → 안전 공략 불가 |
| spath_002 | **(다) 종 특이 정상** | "아래잎 고사" = 하엽 자연 노화, 건강 스파티필름 |

- **(가) 경미·국소 단독 = 0건.** 6건 전부 "갈변·마름" 이상의 진행성 어휘를 포함 → 순수 cosmetic 단독 신호가 없음.
- **(나) TP와 텍스트 동일 = 2~3건** (dracaena_003·chloro_003 + spath_001 경계).
- **(다) 종 특이 정상 = 3건** (dracaena_004·006·spath_002).

### 최종 결론: **(C) 카드 텍스트 negative로 안전 공략 가능한 변별 축 없음**

근거 3종:
1. **(가) 유형 0건** — 카드 negative가 안전하게 누를 "TP엔 없는 경미·국소 단독" FP가 존재하지 않음.
2. **진행성 축 실패** — "고사"가 healthy FP 3건에 존재, TP보다 오히려 심함. 증상 텍스트 강도로는 정상/건조를 못 가름.
3. **텍스트 동일 쌍 ≥3** — FP에 negative를 걸면 동일 문구 TP(haengun_008·006)가 같이 눌려 **FN(recall 게이트) 위반**.

→ 깨끗하게 분리되는 유일 축은 **종(species)**(FP=드라세나·접란·스파티필름 / TP=행운목·스킨답서스, 교집합 0). 그러나 b_dataset 카드는 종 비특이(generic)라 카드 본문에 종 변별을 넣을 수 없음. **카드 negative 신호는 본 문제에 부적합.**

### 대안 2종 (카드 우회)

**대안 1 — 종 메타 활용 (선례 有).**
드라세나·스파티필름·접란의 "잎끝 갈변·하엽 고사"를 *종별 정상 노화 패턴*으로 주입. 이미 `species_normal_rag` + graph.py 종 주입 경로가 존재(메모리 `phase-b-prime-species-meta-null-effect` — 단 그때 순효과 0·FN 리스크 관찰됨). eval JSON의 `species_normal_diagnosis`도 드라세나·스파티필룸·행운목을 covered로 추적 중. **단 과거 종 메타가 generate를 못 설득한 이력**이 있어, 입력 경로(RAG/메타)보다 **출력 우회(가드 종-aware 화이트리스트)** 가 더 유망할 수 있음 — 별도 설계 라운드 필요.

**대안 2 — 평가셋 라벨 점검.**
dracaena_004("황화 및 고사")·006("전체 고사"·"세로 말림")·spath_002("아래잎 고사")가 *정말 건강*인지 GT 재검 후보. "전체 고사"·"세로 말림"은 건강 라벨과 긴장. 실제 경증 하엽 노화면 라벨 유지(→ 종 메타로 처리), 실제 수분 손상이면 라벨 정정으로 이 FP들이 TP로 전환되어 FP 자체가 사라짐. **저비용 read-only 검토**(이미지 재확인)로 분기 가능.

## PART D 요약 — 권고

- **R12c-1-α(카드 negative)는 권하지 않음.** (가) 유형 0건, 텍스트 동일 쌍 ≥3으로 FN 위험이 이득을 초과.
- 우선순위: **대안 2(라벨 점검, 무과금)** 선행 → 종 특이 정상 3건의 GT 확정 → 그 결과로 **대안 1(종-aware 가드)** 또는 **R12a(가드 위치 veto)** 결정.
- R12a(가드 위치 veto `아래/하엽/하부`)는 본 FP 중 spath_002("아래잎")·일부 하엽 케이스에 부분 효과 가능하나, 잎끝(말단) FP(003·chloro_003·spath_001)에는 무효 — 별도 변수.

> 모든 분류에 case_id·증상 근거 첨부. 추측 배제. 단일 run 기반(analyze 비결정 ±1~2)이므로 종 축 분리는 견고하나 개별 케이스 증상 문구는 run마다 변동 가능.
