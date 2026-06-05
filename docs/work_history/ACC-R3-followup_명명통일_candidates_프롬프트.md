# ACC-R3-followup: 명명 통일 + inaturalist_candidates 신설

## 컨텍스트

`context_v24_accuracy_track_R1_datahygiene_done.md` + ACC-R3 직후 상태에서 진행. R3에서 6장이 `inat_epipremnum_001~006.jpg` 명명으로 들어갔는데, 기존 평가셋의 같은 종 사진은 `inat_epipremnum_aureum_001~003.jpg` 패턴이라 명명 불일치 상태. 종명 명시 패턴이 미래 다종 확장에 견고하므로 신규 6장을 그쪽으로 통일.

추가로 사용자가 iNaturalist 원본 6장(Downloads 폴더)을 리포 내 `test_data/inaturalist_candidates/`로 옮겨 라이선스 추적·원본 백업 일원화하려 함. `moneyplant_candidates`와 같은 위계로 "외부 출처 사진 보관소" 의미 통일.

**타이밍**: labels.json에 6건 아직 추가 안 함(`true_status` 라벨링 라운드 전 상태). image_path 박기 전이라 명명 변경 비용 최소.

## 작업 범위

### 수정 대상

- `test_data/main_eval/images/` — 신규 6장 rename (`inat_epipremnum_001~006.jpg` → `inat_epipremnum_aureum_004~009.jpg`)
- `test_data/main_eval/SOURCE.md` — 6개 항목 헤더 + `파일:` 경로 갱신
- `test_data/inaturalist_candidates/images/` — Downloads 원본 6장 복사 + 명명 통일
- `test_data/inaturalist_candidates/NOTE.md` — 신설, 라이선스 일원화 안내 한 줄

### 금지 (가드)

- `test_data/main_eval/labels.json` 일체 무변경 (아직 6건 추가 전 — image_path 박힐 자리 없음)
- `inat_epipremnum_aureum_001~003.jpg` (기존 3건) 일체 무변경 (별건)
- `moneyplant_candidates/` 일체 무변경
- 다른 평가셋(`plantvillage_50` 등)·RAG DB·`eval/baseline*.json` 무변경
- `docs/work_history/ACC-R3_..._프롬프트_v3.md` (이미 보존된 R3 히스토리) 무변경 — 역사 기록 보존
- Downloads의 원본 사진은 **삭제 금지**, 복사만 (사용자 영역, Downloads 정리는 사용자가 직접)
- §9 자동화 금지 — 명명 변경은 단순 매핑이라 영향 없음

## 명명 매핑 표

| 현 main_eval 명명 | 새 main_eval 명명 | Downloads 원본 → candidates 명명 |
|---|---|---|
| `inat_epipremnum_001.jpg` | `inat_epipremnum_aureum_004.jpg` | `Epipremnum aureum1.jpeg` → `inat_epipremnum_aureum_004.jpg` |
| `inat_epipremnum_002.jpg` | `inat_epipremnum_aureum_005.jpg` | `Epipremnum aureum2.jpeg` → `inat_epipremnum_aureum_005.jpg` |
| `inat_epipremnum_003.jpg` | `inat_epipremnum_aureum_006.jpg` | `Epipremnum aureum3.jpg`  → `inat_epipremnum_aureum_006.jpg` |
| `inat_epipremnum_004.jpg` | `inat_epipremnum_aureum_007.jpg` | `Epipremnum aureum4.jpg`  → `inat_epipremnum_aureum_007.jpg` |
| `inat_epipremnum_005.jpg` | `inat_epipremnum_aureum_008.jpg` | `Epipremnum aureum5.jpg`  → `inat_epipremnum_aureum_008.jpg` |
| `inat_epipremnum_006.jpg` | `inat_epipremnum_aureum_009.jpg` | `Epipremnum aureum6.jpeg` → `inat_epipremnum_aureum_009.jpg` |

> ⚠ **005 (= 신 명명 008)의 특수 사정 (프롬프트 원안)**: main_eval의 008은 사용자가 인물 영역을 크롭한 derivative. candidates의 008은 Downloads에 있는 인물 포함 원본 가정. (실제로는 아래 "진행 메모" 참조 — Downloads 008도 크롭본이었음.)

## 절차

### Step 1 — Read-only 선결 게이트

변경 전 다음을 **읽기 전용으로 보고**. 불일치 시 중단·질의.

1. main_eval/images/에 `inat_epipremnum_001~006.jpg` 6장 존재 + 크기 (R3 결과 일치)
2. main_eval/SOURCE.md의 6개 항목 헤더·경로 현 상태
3. `inat_epipremnum_aureum_004~009.jpg` 충돌 검사 (부재 확인)
4. 기존 `inat_epipremnum_aureum_001~003.jpg` 무변경 대상 — 존재 확인
5. Downloads에 원본 6장 존재 확인
6. `inaturalist_candidates/` 폴더 상태 확인
7. labels.json에 해당 경로 미등장 확인 (6건 추가 전 상태)

### Step 2 — main_eval/images/ rename

매핑 표대로 6장 rename. 단순 rename, 재인코딩 금지, 바이트 보존.

### Step 3 — main_eval/SOURCE.md 갱신

6개 항목 헤더 + `파일:` 경로 새 명명으로 갱신. URL·관찰자·라이선스·등급·메모 무변경. 008 derivative 메모 유지.

### Step 4 — inaturalist_candidates/

Downloads 6장을 복사(이동·삭제 금지) → 명명 통일. 라이선스 추적 일원화.

### Step 5 — 전체 검증

main_eval 새 명명 6장 + 구명 부재, SOURCE 구명 잔재 0, candidates 6장, Downloads 보존, validate_main_eval exit 0(labels 무변경), aureum_001~003 무변경.

### Step 6 — Atomic 커밋 (푸시 보류)

푸시는 사용자가 검토 후 직접.

## 완료 보고

- before/after 명명 매핑 표
- 변경 파일·라인 수, 커밋 해시, 검증 결과
- Downloads 원본·aureum_001~003 무변경 확인
- 다음 사용자 작업: labels.json 6건 추가 (새 명명 image_path + ground_truth 직접 작성, R2 패턴)

---

## 실제 진행 메모 (CC 추가 — 프롬프트 전제와 달랐던 점)

- **inaturalist_candidates/ 는 신설이 아니라 기존 폴더**였음(iNat 수집 후보 보관소, metadata.json 관례 + aureum_001~003 등록됨). → 사용자 결정(옵션 2): 기존 images/에 6장 추가 + **metadata.json에 6항목 등록**(NOTE.md 미신설).
- **Downloads 원본은 이미 `inat_epipremnum_aureum_004~009`로 사용자가 리네임**한 상태였고, 008은 인물 포함 원본이 아니라 **크롭본**(main_eval/008과 sha256 동일). 인물 포함 원본은 로컬에 없고 iNaturalist에만 존재. → 사용자 결정(옵션 1): 크롭본 수용, metadata.json 008 항목에 "본 폴더 파일은 크롭본 (인물 원본은 iNaturalist 페이지에만 존재, 로컬 미보관)" 메모. main_eval/SOURCE.md 008 derivative 메모는 유지.
- license 문자열은 SOURCE.md와 일치시켜 `"CC-BY 4.0"` 사용(참고: labeling_vocab.ALLOWED_LICENSES는 `"CC BY 4.0"` 하이픈 없는 형태).
