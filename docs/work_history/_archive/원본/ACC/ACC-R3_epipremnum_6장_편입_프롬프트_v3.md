# ACC-R3: Epipremnum aureum 6장 메인 평가셋 편입 (이진 FP/FN 보강) — v3

> v2 대비 변경: 5번 사진(`Epipremnum_aureum5.jpg`)의 인물 크롭이 사용자에 의해 **사전 완료됨** → Step 1 #4 게이트의 옵션 C 자동 선택. 005 분기·보류 로직 제거. SOURCE.md 005 메모에 "인물 영역 크롭 (CC-BY derivative work)" 명시. 6장 동시 편입.

## 컨텍스트

`context_v24_accuracy_track_R1_datahygiene_done.md` §3, §5, §8, §9 + R2 완료 상태에서 진행.

- **R1 (라벨 스키마) + R2 (행운목 5장 건조 라벨링) 완료** — labels.json 33/33 valid, 28 건강 + 5 건조.
- 이번 R3 = iNaturalist에서 종·라이선스·등급 검증 완료한 **Epipremnum aureum 6장 편입**. (스킨답서스 = 행운목 다음으로 흔한 실내 관엽종)
- 6장 편입의 의의 = **§4 1차 목표 ① 이진 FP/FN 보강** + 종 다양성 시작 (행운목 단일 종 탈피). 5-status 혼동표 활성화는 표본 부족으로 보류 — 미측정 칸 빈칸 유지.

> 라벨링은 §9 "라벨링 자동화 금지" 원칙대로 본인이 직접 채움. CC는 사진 편입 + `true_status: "TODO"` 마커만.

## 작업 범위 (scope)

### 수정 대상

- `test_data/main_eval/labels.json` — 6건 항목 추가 (`true_status: "TODO"`, `is_healthy: false`, `species: "Epipremnum aureum"`)
- `test_data/main_eval/images/` — 사진 6장 파일명 규칙 적용 후 이동
- `test_data/main_eval/SOURCE.md` — **신설**, 외부 출처 사진의 URL·관찰자·라이선스·등급 기록

### 금지 (가드)

- `main_rag` 명명 변경 ([B-2] 보류, §7)
- `test_data/moneyplant_candidates/` 폴더 일체 수정·이동·삭제 (별도 design 패치 라운드에서 폐기 처리 예정)
- 다른 평가셋(`plantvillage_50` 등)·RAG DB·`eval/baseline*.json` 수정
- 기존 33건 라벨·필드 변경
- `test_data/labeling_vocab.py`·`scripts/validate_main_eval.py`·`scripts/migrate_labels_add_status.py` 변경
- §9 자동화 금지 — `true_status` 값은 `"TODO"` 마커만, 임의 추정·자동 매핑·종 기반 추론 금지

## 입력 자원 (사용자 준비 완료)

사용자가 새 대화 시작 시 이미 제공함:

### 1. 사진 6장 파일 (업로드 위치: `/mnt/user-data/uploads/`)

- `Epipremnum_aureum1.jpeg`
- `Epipremnum_aureum2.jpeg`
- `Epipremnum_aureum3.jpg`
- `Epipremnum_aureum4.jpg`
- `Epipremnum_aureum5.jpg` ⚠ **사용자가 원본에서 인물 영역을 사전 크롭한 버전**
- `Epipremnum_aureum6.jpeg`

### 2. 메타데이터 표 (URL·관찰자·라이선스·등급)

| 업로드 파일명 | iNaturalist URL | 관찰자명 | 라이선스 | 등급 |
|---|---|---|---|---|
| `Epipremnum_aureum1.jpeg` | https://www.inaturalist.org/observations/263764838 | reishisagnik | CC-BY | Research Grade |
| `Epipremnum_aureum2.jpeg` | https://www.inaturalist.org/observations/271084401 | lexgo | CC-BY | Research Grade |
| `Epipremnum_aureum3.jpg`  | https://www.inaturalist.org/observations/354291669 | chinchu_c | CC-BY | Research Grade |
| `Epipremnum_aureum4.jpg`  | https://www.inaturalist.org/observations/351610111 | ash2016 | CC-BY | Needs ID |
| `Epipremnum_aureum5.jpg`  | https://www.inaturalist.org/observations/330973710 | der-naturforscher | CC-BY | Research Grade |
| `Epipremnum_aureum6.jpeg` | https://www.inaturalist.org/observations/253263062 | michaelbakkerpaiva | CC-BY | Research Grade |

> ⚠ Step 1 read-only 게이트에서 위 메타데이터 표를 사용자에게 다시 확인받기. URL·관찰자·라이선스·등급의 1:1 매칭이 맞는지 점검.

### 3. 라이선스 버전

iNaturalist 기본 CC-BY는 4.0. 별도 명시 없으면 모두 **CC-BY 4.0**으로 기록.

### 4. 005 사전 처리 사항 (v3 추가)

`Epipremnum_aureum5.jpg`는 사용자가 iNaturalist 원본에서 **인물 영역을 크롭한 derivative**임. CC-BY 4.0은 derivative work 허용 + 원작자 표기 의무만 있으므로 라이선스 준수에는 SOURCE.md에 원작자 + 원본 URL + "인물 영역 크롭 사용" 메모만 적으면 충족됨. CC는 추가 처리 불필요, 그대로 사용.

## 절차

### Step 1 — Read-only 선결 게이트 (§8)

변경 전 다음을 **읽기 전용으로 보고**. 불일치·예상 외 상태 시 중단·질의.

1. 현재 `labels.json` 분포 (33건, 28 건강 + 5 건조 예상) 출력 — `species`·`is_healthy`·`true_status` 분포 요약
2. `/mnt/user-data/uploads/`에서 6장 파일 존재·포맷·해상도·EXIF 유무 보고
3. 메타데이터 표 사용자 재확인 — 위 표 그대로 보고 + "맞으면 진행, 틀리면 정정" 질의
4. **인물 크롭 확인** — `Epipremnum_aureum5.jpg`에 인물이 보이지 않는지 (사용자 사전 크롭 결과) 시각 확인 후 사용자에게 보고. 인물이 보이지 않으면 그대로 진행. 만에 하나 인물이 남아 있다면 사용자에게 알리고 중단·질의.
5. `test_data/main_eval/SOURCE.md` 존재 여부 (신설 예정이라 부재 예상)
6. 파일명 규칙 충돌 검사 — `inat_epipremnum_001` ~ `006`와 동일한 기존 파일 부재 확인

### Step 2 — 사진 파일 이동 및 파일명 규칙 적용

Step 1 검증 통과 후:

- `/mnt/user-data/uploads/Epipremnum_aureum{N}.{jpeg|jpg}` → `test_data/main_eval/images/inat_epipremnum_00{N}.jpg`로 이동
- 파일명 매핑 (1:1 순서):
  - `Epipremnum_aureum1.jpeg` → `inat_epipremnum_001.jpg`
  - `Epipremnum_aureum2.jpeg` → `inat_epipremnum_002.jpg`
  - `Epipremnum_aureum3.jpg`  → `inat_epipremnum_003.jpg`
  - `Epipremnum_aureum4.jpg`  → `inat_epipremnum_004.jpg`
  - `Epipremnum_aureum5.jpg`  → `inat_epipremnum_005.jpg`
  - `Epipremnum_aureum6.jpeg` → `inat_epipremnum_006.jpg`
- **확장자 통일 정책**: 원본이 `.jpeg`든 `.jpg`든 결과는 모두 `.jpg`로 통일 (확장자만 변경, **재인코딩 금지** — 원본 바이트 보존, 단순 파일 rename). PIL로 열어 다시 저장하지 말 것.
- **EXIF 처리**: EXIF에 GPS·기기 정보 있을 시 제거 권장. 다만 재인코딩 없는 EXIF 제거가 가능한 도구(`piexif.remove` 등) 사용. 원본 픽셀 데이터는 변경 금지. 처리가 까다로우면 사용자에게 보고 후 그대로 두기.
- 원본 별도 백업 불필요 (iNaturalist에 원본 존재).

### Step 3 — labels.json 6건 항목 추가

각 항목 다음 구조 (기존 `self_haengun_*` 항목과 동일한 필드 셋 유지):

```json
{
  "image": "test_data/main_eval/images/inat_epipremnum_001.jpg",
  "is_healthy": false,
  "true_status": "TODO",
  "species": "Epipremnum aureum"
  // 기존 항목의 다른 필드가 있다면 동일 구조 유지
}
```

- `is_healthy`: 6건 모두 `false`
- `true_status`: 6건 모두 `"TODO"` — **사용자가 R3 후 직접 채울 자리**
- `species`: 6건 모두 `"Epipremnum aureum"`
- 기존 항목 필드 순서·스타일·들여쓰기 동일하게 유지. BOM 없는 UTF-8.
- 추가 위치: labels.json 배열 말미에 6건 순서대로 (001 → 006).

### Step 4 — SOURCE.md 신설

새 파일 `test_data/main_eval/SOURCE.md` 생성. 구조:

```markdown
# 외부 출처 사진 — 라이선스·출처 추적

본 평가셋(`test_data/main_eval/`)에 포함된 외부 출처 사진의 라이선스 및 원출처 기록.
`self_*` 사진은 본인 촬영이라 출처 기록 불필요. `inat_*` 등 외부 사진만 본 문서에 기록.

§9 데이터 범위 원칙 — "외부 데이터셋 라이선스 준수 (CC BY = 출처 표기)" 의무에 따라 작성.

---

## inat_epipremnum_001.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_001.jpg`
- 출처: iNaturalist 관찰 #263764838
- URL: https://www.inaturalist.org/observations/263764838
- 저작권자: reishisagnik (iNaturalist 사용자명)
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Research Grade

## inat_epipremnum_002.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_002.jpg`
- 출처: iNaturalist 관찰 #271084401
- URL: https://www.inaturalist.org/observations/271084401
- 저작권자: lexgo
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Research Grade

## inat_epipremnum_003.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_003.jpg`
- 출처: iNaturalist 관찰 #354291669
- URL: https://www.inaturalist.org/observations/354291669
- 저작권자: chinchu_c
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Research Grade

## inat_epipremnum_004.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_004.jpg`
- 출처: iNaturalist 관찰 #351610111
- URL: https://www.inaturalist.org/observations/351610111
- 저작권자: ash2016
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Needs ID

## inat_epipremnum_005.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_005.jpg`
- 출처: iNaturalist 관찰 #330973710
- URL: https://www.inaturalist.org/observations/330973710
- 저작권자: der-naturforscher
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Research Grade
- 메모: 원본에서 인물 영역을 크롭한 derivative. CC-BY 4.0의 derivative work 허용 범위 내 사용.

## inat_epipremnum_006.jpg

- 파일: `test_data/main_eval/images/inat_epipremnum_006.jpg`
- 출처: iNaturalist 관찰 #253263062
- URL: https://www.inaturalist.org/observations/253263062
- 저작권자: michaelbakkerpaiva
- 라이선스: CC-BY 4.0
- 종: Epipremnum aureum
- 등급: Research Grade
```

라이선스 버전은 iNaturalist 기본인 CC-BY 4.0으로 통일.

### Step 5 — 전체 검증

`scripts/validate_main_eval.py` 실행:

- 검증 항목:
  - 모든 항목 `validate_label` 통과 (ValueError 0)
  - **`true_status: "TODO"` 항목 6개 존재** (R3 진입 시점이라 TODO가 사라지면 안 됨)
  - enum 위반 0 (`STATUS_VOCAB ∪ STATUS_AMBIGUOUS ∪ {"TODO"}` 외 값 0)
  - `is_healthy ↔ true_status` 정합성 — TODO 항목은 정합성 검증에서 정상적으로 통과해야 함 (R1·R2에서 동작 확인됨)
- 출력:
  - 총 항목 수 = 39 (33 기존 + 6 신규)
  - status별 분포 — 28 건강 + 5 건조 + 6 TODO
  - species별 분포 — 기존 종 X건 + Epipremnum aureum 6건
  - **사용자에게 명확히 표시: "true_status TODO 6건은 사용자 직접 라벨링 대기"**
- 파일 존재 검증:
  - labels.json의 신규 `image` 경로가 실제 `images/` 폴더에 존재하는지 확인
  - SOURCE.md의 6개 항목이 labels.json의 6개 신규 항목과 1:1 매칭되는지 확인

### Step 6 — Atomic 커밋 (R2 패턴)

검증 모두 통과 후 atomic 커밋 (푸시 보류 — 사용자 검토 후 직접):

1. `feat(eval): ACC-R3 Epipremnum 6장 이미지 편입` — `images/inat_epipremnum_*.jpg` 추가
2. `feat(eval): ACC-R3 Epipremnum 6장 labels.json 항목 추가 (true_status TODO)` — labels.json 변경
3. `docs(eval): ACC-R3 SOURCE.md 신설 (외부 출처 라이선스 추적)` — SOURCE.md 신설
4. `docs(work_history): ACC-R3 작업 프롬프트 보존` — 본 .md 파일을 `docs/work_history/`로 복사

푸시는 사용자가 검토 후 직접.

## 완료 보고 (사용자에게)

- 분포 (before/after 표): 33건 → 39건, status별·species별 카운트
- 6장 파일명 매핑 표: 업로드 파일명 → `inat_epipremnum_XXX.jpg`
- 변경 파일·라인 수
- 커밋 해시(들)
- 검증 통과 여부 + TODO 6건 명시
- **Step 1 #4 인물 크롭 확인 결과** (005가 클린한지)
- **다음 사용자 작업 안내**:
  1. `true_status` 6건 결정 (병해 의심 / 건조 / 영양 부족 / 과습 / ambiguous 중)
  2. labels.json 직접 편집 (R2 패턴)
  3. `validate_main_eval.py` 재실행해 TODO 0 확인
  4. atomic 커밋 + 푸시
- **다음 라운드 후보**: design 패치 라운드 (Money Plant 폐기 + Kaggle Indoor 종결 + PlantDoc/DiaMOS 폐기 + §4 1차 목표 ① 격상 + 본인 촬영 백로그 명시)
