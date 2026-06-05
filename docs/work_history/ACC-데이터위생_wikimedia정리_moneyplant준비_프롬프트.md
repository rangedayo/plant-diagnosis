# [정확도 트랙] 데이터 위생 — Wikimedia 폐기 정리 + Money Plant 보관 준비

> 트랙: 1차 진단 정확도 — 데이터 위생/준비 미니 라운드
> 성격: 디렉토리·.gitignore 정리 + 보관 구조 생성. 코드 로직 무변경.
> 설계 근거: `docs/design/design_accuracy_track.md` §4 결정1(웹 수집 데이터셋으로 전환, Wikimedia 폐기)
> 주의: 이 라운드는 **데이터 편입(labels 매핑·run_eval 연결)을 하지 않는다.** 보관·정리까지만. 편입은 별도 후속 라운드.

---

## 0. 배경

- Wikimedia 수집은 **폐기**(실측 수율 0 — 일러스트·책 페이지뿐). `wikimedia_candidates/` 및 관련 흔적 정리.
- 병해 표본은 공개 데이터셋으로 전환. 1차 대상: **Money Plant 데이터셋**(스킨답서스 = 평가셋 종, CC BY 4.0).
- 사용자가 Money Plant `original`을 직접 받아 `test_data/moneyplant_candidates/`에 넣을 예정. CC는 **받을 자리(디렉토리·gitignore·출처 메모)를 준비**한다.

---

## 1. read-only 선결 게이트 (변경 전 먼저 보고)

1. `test_data/` 하위 현재 디렉토리 목록 — 특히 `wikimedia_candidates/`의 존재·내용(이미지 수, `metadata.json` 유무).
2. `wikimedia_candidates/metadata.json`이 **git에 추적 중인지**(`git ls-files`로 확인).
3. `.gitignore`의 `test_data` 관련 라인 — 특히 이미지 와일드카드(`test_data/**/*.jpg` 등)와 후보 디렉토리 제외 라인.
4. `scripts/collect_wikimedia.py`의 존재.

**보고 형식**: 위 4개 1~2줄 요약. 특히 (a) `wikimedia_candidates/`에 git 추적 파일이 있는지, (b) 이미지 와일드카드 제외가 이미 `moneyplant_candidates`까지 커버하는지.

---

## 2. 작업 A — Wikimedia 흔적 정리

- `test_data/wikimedia_candidates/` 디렉토리 제거.
  - git 추적 파일(`metadata.json` 등)이 있으면 `git rm -r`로 추적 해제 + 삭제.
  - 추적 파일이 없으면(전부 gitignore) 디렉토리만 삭제.
- `.gitignore`에서 `test_data/wikimedia_candidates/images/` 라인이 있으면 **그대로 둔다**(제거해도 무방하나, 잔여 무해 라인 정리는 선택). 판단 보고 후 진행.
- `scripts/collect_wikimedia.py` — **이번 라운드에서는 삭제하지 않는다.** 제거 여부는 사용자 결정 사항이므로 보고만 하고 남겨둔다.

> `plantvillage_source/`는 사용자가 로컬에서 직접 삭제하므로 **CC는 건드리지 않는다.**

---

## 3. 작업 B — Money Plant 보관 자리 준비

### 디렉토리 생성

```
test_data/moneyplant_candidates/
├── images/                # 사용자가 original 이미지를 여기에 넣음 (클래스 폴더 구조 유지)
│   ├── healthy/           # (사용자가 채움)
│   ├── bacterial_wilt/    # (사용자가 채움)
│   └── manganese_toxicity/# (사용자가 채움)
└── SOURCE.md              # 출처·라이선스·사용 방침 메모 (git 추적)
```

- `images/` 및 하위 3개 클래스 폴더는 **빈 디렉토리로 생성**(필요 시 `.gitkeep`). 이미지는 사용자가 직접 채운다.
- CC는 **이미지를 다운로드하지 않는다**(사용자가 Mendeley에서 직접 수령).

### `SOURCE.md` 내용 (생성)

```markdown
# Money Plant Disease Dataset (보관)

- 종: Epipremnum aureum (스킨답서스 / 골든포토스)
- 출처: https://data.mendeley.com/datasets/rzjww3vdxt/3
- 라이선스: CC BY 4.0 (출처 표기 의무)
- 논문: Money plant disease atlas, Data in Brief 2024, DOI 10.1016/j.dib.2024.111216
- 클래스(original): healthy 700 / bacterial_wilt 576 / manganese_toxicity 596
- 사용 방침:
  - **original 폴더만 사용** (augmented 제외 — 평가셋 부적합).
  - 평가셋 편입 후보는 우선 **bacterial_wilt → true_status="병해 의심"**.
  - healthy·manganese_toxicity는 **현재 보관만**. 편입 안 함.
    - manganese_toxicity는 영양 "과잉"(독성)이라 현 5-status에 매핑 칸 없음 → 보류.
      (향후 "영양 과잉" status 신설 시 활용 — 백로그.)
  - 잎 위주 크롭·224 리사이즈본이라 메인(실사용 폰 원본) 분포와 차이 → 편입 시 사람 검수 필요.
- 편입(labels 매핑·run_eval 연결)은 별도 후속 라운드에서 진행.
```

### `.gitignore` 갱신

- `test_data/moneyplant_candidates/images/`를 이미지 제외 대상에 추가.
  - 기존 와일드카드(`test_data/**/*.jpg` 등)가 이미 커버하면 **중복이라도 의도 명시용으로 디렉토리 라인 1줄 추가**(가독성).
- `SOURCE.md`와 (있다면) 향후 매핑 json은 **추적 대상**(이미지만 제외).

---

## 4. 제약

- **변경 가능**: `test_data/wikimedia_candidates/`(삭제), `.gitignore`, 신규 `test_data/moneyplant_candidates/` 디렉토리 + `SOURCE.md`(+`.gitkeep`).
- **절대 무변경**: `scripts/*`(collect_wikimedia.py 포함 — 삭제 금지), `app/*`, 프론트, `test_data/main_eval/*`, `test_data/plantvillage_50/*`, `test_data/labeling_vocab.py`, `eval/*`.
- 이미지 다운로드 금지(사용자 수령). LLM/Vision 호출 없음.

---

## 5. 검증

```bash
# 1) wikimedia_candidates 제거 확인
ls test_data/ | grep -i wikimedia || echo "removed OK"

# 2) moneyplant 보관 구조 확인
ls -R test_data/moneyplant_candidates/
# 기대: images/{healthy,bacterial_wilt,manganese_toxicity}/ + SOURCE.md

# 3) gitignore에 moneyplant 이미지 제외 반영 확인
grep -n moneyplant .gitignore

# 4) git 상태 — 추적 대상이 SOURCE.md(+.gitkeep)뿐인지, 이미지가 안 잡히는지
git status --short
```

---

## 6. 커밋 (atomic 분리)

- **커밋 1 (chore)**: Wikimedia 흔적 제거
  - 예: `chore: wikimedia_candidates 제거 (수집 채널 폐기)`
- **커밋 2 (chore)**: Money Plant 보관 자리 준비
  - 예: `chore: moneyplant_candidates 보관 구조 + SOURCE.md + gitignore`

---

## 7. 완료 보고에 포함할 것

- §1 read-only 보고.
- 변경/삭제 파일 목록.
- `collect_wikimedia.py` 존치 사실(삭제 안 함) 명시.
- `git status`로 이미지가 추적되지 않고 `SOURCE.md`만 추적되는지 확인 결과.
