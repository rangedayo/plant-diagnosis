# ACC-R3-labels: labels.json 6건 추가 (사용자 ground_truth 박기)

## 컨텍스트

`context_v24_accuracy_track_R1_datahygiene_done.md` + ACC-R3 + ACC-R3-followup(명명 통일·candidates 신설) 직후 상태에서 진행.

- R3에서 이미지 6장 + SOURCE.md 신설 완료
- R3-followup에서 명명을 `inat_epipremnum_aureum_004~009.jpg`로 통일 완료
- 사용자가 6장에 대한 `symptoms` / `diagnosis` / `true_status` 결정 완료 (§9 사람 ground_truth 룰 준수)
- **이번 라운드 = CC가 사용자 제공값을 받아 labels.json에 6건 항목 추가**. 추론·수정 금지, 단순 매핑·박기 작업

## 작업 범위

### 수정 대상

- `test_data/main_eval/labels.json` — 6건 항목 추가 (33건 → 39건)

### 금지 (가드)

- §9 자동화 금지 — 사용자 제공 ground_truth 값(`symptoms`/`diagnosis`/`true_status`)을 **글자 그대로 박기**. CC가 표현 다듬기·번역·축약·확장 일체 금지
- 기존 33건 일체 무변경 (필드 순서·들여쓰기·내용 전부)
- 기존 `inat_epipremnum_aureum_001~003` 일체 무변경 (별건)
- `test_data/main_eval/SOURCE.md` 무변경 (R3-followup에서 갱신 완료)
- `test_data/main_eval/images/` 무변경 (R3-followup에서 rename 완료)
- `test_data/inaturalist_candidates/` 무변경
- `moneyplant_candidates/` · `plantvillage_50` · RAG DB · `eval/baseline*.json` 무변경
- `main_rag` 명명 변경 ([B-2] 보류)
- `test_data/labeling_vocab.py` · `scripts/validate_main_eval.py` 무변경

## 사용자 제공 ground_truth (6건, 그대로 박을 데이터)

각 항목 공통:
- `plant_name_korean: "스킨답서스"`
- `is_healthy: false`

개별:

### inat_epipremnum_aureum_004
- symptoms: `["leaf_edge_dry", "leaf_browning"]`
- diagnosis: `"잎 가장자리와 절개 부위 주변에 갈색으로 마른 조직이 넓게 나타난다. 강한 직사광선이나 일시적인 수분 부족으로 인한 조직 손상 흔적으로 보이며, 전반적인 잎 색은 비교적 양호하다."`
- true_status: `"건조"`

### inat_epipremnum_aureum_005
- symptoms: `["leaf_spots", "leaf_browning"]`
- diagnosis: `"잎 표면에 다수의 검은색 및 갈색 반점이 분포하며 일부 조직이 괴사한 모습이 관찰된다. 노화 외에도 곰팡이성 또는 세균성 잎 반점 증상이 의심된다."`
- true_status: `"병해 의심"`

### inat_epipremnum_aureum_006
- symptoms: `["leaf_pale", "leaf_yellowing"]`
- diagnosis: `"전체적으로 연한 녹색과 황록색 잎이 많으며 색이 다소 옅어 보인다. 생육은 양호하지만 광량 부족이나 영양 결핍으로 인한 엽색 저하 가능성이 있다."`
- true_status: `"ambiguous"` ⚠ **diagnosis는 영양 부족 언급하지만 true_status는 ambiguous로 확정** — 'Epipremnum aureum Neon' cultivar 가능성 때문에 사용자가 평가 제외 결정. 진단 텍스트는 1차 관찰 기록 그대로 보존.

### inat_epipremnum_aureum_007
- symptoms: `["leaf_holes", "leaf_browning"]`
- diagnosis: `"여러 잎에서 구멍과 가장자리 손상이 확인되며 일부 부위는 갈변이 진행되어 있다. 물리적 손상 또는 해충 가해 흔적이 혼재된 상태로 보인다."`
- true_status: `"ambiguous"`

### inat_epipremnum_aureum_008
- symptoms: `["leaf_browning", "leaf_spots"]`
- diagnosis: `"무성하게 자란 개체 중 일부 잎에 갈색 괴사 부위와 반점이 관찰된다. 전반적인 생육은 양호하지만 국소적인 잎 손상과 병반이 존재한다."`
- true_status: `"병해 의심"`

### inat_epipremnum_aureum_009
- symptoms: `["leaf_yellowing", "leaf_browning"]`
- diagnosis: `"중앙 좌측의 대형 잎에서 전반적인 황변 현상과 중심부 갈색 괴사 반점이 관찰되며, 우측 후면의 잎은 심하게 갈변하여 고사 중입니다. 자생지 환경 특성상 수분 과다 또는 잎의 노화로 인한 손상이 의심됩니다."`
- true_status: `"ambiguous"`

## 메타 매핑 (image_path / source 블록 자동 채움)

각 항목 메타데이터는 다음 매핑으로 박기:

| image_id | image_path | iNaturalist URL | 관찰자 | 라이선스 | 등급 |
|---|---|---|---|---|---|
| `inat_epipremnum_aureum_004` | `test_data/main_eval/images/inat_epipremnum_aureum_004.jpg` | https://www.inaturalist.org/observations/263764838 | reishisagnik | CC-BY 4.0 | Research Grade |
| `inat_epipremnum_aureum_005` | `test_data/main_eval/images/inat_epipremnum_aureum_005.jpg` | https://www.inaturalist.org/observations/271084401 | lexgo | CC-BY 4.0 | Research Grade |
| `inat_epipremnum_aureum_006` | `test_data/main_eval/images/inat_epipremnum_aureum_006.jpg` | https://www.inaturalist.org/observations/354291669 | chinchu_c | CC-BY 4.0 | Research Grade |
| `inat_epipremnum_aureum_007` | `test_data/main_eval/images/inat_epipremnum_aureum_007.jpg` | https://www.inaturalist.org/observations/351610111 | ash2016 | CC-BY 4.0 | Needs ID |
| `inat_epipremnum_aureum_008` | `test_data/main_eval/images/inat_epipremnum_aureum_008.jpg` | https://www.inaturalist.org/observations/330973710 | der-naturforscher | CC-BY 4.0 | Research Grade |
| `inat_epipremnum_aureum_009` | `test_data/main_eval/images/inat_epipremnum_aureum_009.jpg` | https://www.inaturalist.org/observations/253263062 | michaelbakkerpaiva | CC-BY 4.0 | Research Grade |

008 메모(원본에서 인물 영역 크롭한 derivative)는 main_eval/SOURCE.md에 이미 명시되어 있으므로 labels.json의 source 블록에 별도로 박을 필요는 없음. 단 기존 `inat_epipremnum_aureum_001~003`의 source 블록 구조가 `note` 같은 필드를 갖고 있다면 그 자리에 derivative 메모 한 줄 추가 (스키마 일관성 차원).

## 절차

### Step 1 — Read-only 선결 게이트 (§8)

변경 전 다음을 **읽기 전용으로 보고**. 불일치 시 중단·질의.

1. 현재 `labels.json` 33건 — `species` (`plant_name_korean`) · `is_healthy` · `true_status` 분포 보고
2. **기존 `inat_epipremnum_aureum_001~003`의 source 블록 정확한 스키마** 보고 — 어떤 필드들이 있고, URL·관찰자·라이선스·등급 정보가 어떻게 박혀 있는지. 이번 6건도 동일 스키마로 따라갈 것
3. `test_data/main_eval/images/`에 `inat_epipremnum_aureum_004~009.jpg` 6장 존재 확인 (R3-followup 결과)
4. `test_data/main_eval/SOURCE.md`에 6개 항목(004~009) 정상 존재 확인
5. labels.json에 `inat_epipremnum_aureum_004~009` 이미 존재하지 않음 확인 (중복 가드)
6. `scripts/validate_main_eval.py` 현 상태 exit 코드 — 33건 valid (exit 0) 확인

### Step 2 — labels.json 6건 항목 추가

Step 1 검증 통과 후:

- 기존 항목 스키마(특히 `inat_epipremnum_aureum_001~003`)를 **그대로** 따라 신규 6건 작성
- ground_truth 블록은 위 "사용자 제공 ground_truth" 섹션의 값을 **글자 그대로 복사** — 표현 수정·다듬기 금지
- source 블록은 기존 3건 구조를 따라 위 메타 매핑 표의 정보를 채워 넣음
- 추가 위치: labels.json 배열 말미에 6건 순서대로 (004 → 009)
- 필드 순서·들여쓰기·인용부호 스타일 기존 항목과 동일
- BOM 없는 UTF-8

### Step 3 — 전체 검증

`python scripts/validate_main_eval.py` 실행:

- 총 항목 수 = **39** (33 + 6)
- 모든 항목 `validate_label` 통과 (ValueError 0)
- **TODO 0건** (이번 라운드에서 모든 항목이 valid status로 확정됨)
- enum 위반 0
- `is_healthy ↔ true_status` 정합성 충족 — 신규 6건 전부 `is_healthy=false`, true_status는 `건조`(1) / `병해 의심`(2) / `ambiguous`(3) 분포
- 이미지 파일 존재 확인 — 6건의 `image_path`가 실제 파일과 매칭
- **exit 0** 필수

분포 보고:
- status별: 28 건강 + 5 건조(self_haengun) + 1 건조(neu) + 2 병해 의심 + 3 ambiguous → 정확한 카운트는 CC가 실측 보고
- species별: 기존 종 + Epipremnum aureum 9건(기존 3 + 신규 6)
- is_healthy별: 28 true + 11 false

### Step 4 — Atomic 커밋 (푸시 보류)

검증 통과 후:

1. `feat(eval): ACC-R3-labels Epipremnum 6장 labels.json 항목 추가 (ground_truth 확정)` — labels.json
2. `docs(work_history): ACC-R3-labels 작업 프롬프트 보존` — 본 .md 파일을 `docs/work_history/`로 복사

푸시는 사용자가 검토 후 직접.

## 완료 보고

- before/after 분포 표 (33 → 39, status별·species별·is_healthy별)
- 6건의 `image_id` / `true_status` 매핑 표
- validate exit 코드
- 변경 파일·라인 수
- 커밋 해시(들)
- 기존 33건 무변경 확인
- **다음 라운드 후보 (컨텍스트 §6)**:
  - **R4** [CC]: `run_eval.py` 확장 — status 혼동표(미측정 칸 명시) + `--aux`(PlantVillage). prepare_plantvillage 부작용 처리 포함(§7)
  - **R5** [사용자]: 새 평가셋(39건)으로 L0' 재측정 (Gemini 과금, PowerShell)
