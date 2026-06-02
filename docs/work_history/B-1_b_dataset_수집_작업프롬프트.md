# [B-1] b_dataset raw 수집 — 작업 프롬프트

> Claude Code 의뢰용. B 묶음(영문 5자료 ~75 청크) **raw 수집 단일 단계**. 청크화·임베딩·적재는 [B-2] 별도, 측정은 [B-3] 별도.
> 결정 확정: F 옵션(단계 분리 + 새 메트릭) — `docs/work_history/v14_컨텍스트.md` 참조. 진단 매핑이 본질, NCPMS 도메인 미스매치 해소 목적.
> 1단계 종료(93abbaa) 후 첫 작업. 회귀 게이트 대상 아님(코퍼스 적재 전이라 측정 변화 0).

---

## 1. 컨텍스트 (한 줄)

[1-10b] 1단계 완전 종료(93abbaa) → **B 묶음 자료 발견 단계 완료(영문 5자료 풀 확정) → [B-1] raw 수집**. 사용자 로컬 3자료(PSU.pdf · PSU txt · MU Trinklein PDF) + Mobot 2페이지 스크래핑 → `data/raw/b_dataset/` 아래 원본 + JSON 카드.

핵심 성격:
- **raw 수집만** — 청크화·임베딩·DB 적재는 [B-2]. 본 작업에서 절대 손대지 않음.
- **변수 격리** — `app/`·`scripts/run_eval.py`·`scripts/build_rag_db.py`·`data/vector_db/` 손대지 않음.
- **사용자 로컬 자료 우선** — 3자료는 `data/source/`에 사전 배치되어 있음 (사용자가 본인 로컬 프로젝트 루트에 미리 둠). 재다운로드 시도 X.
- **스크래핑 매너** — Mobot 2페이지만, robots.txt 확인, 페이지 간 3초 sleep, User-Agent 박기.
- **라이선스 메타 박기** — 각 자료 JSON에 `fair_use_personal_educational` 명시 (decision #10).

원칙:
- **단일 커밋** — 5자료 수집 전부 한 번에 커밋. 부분 성공도 전체 롤백 후 재실행.
- **자료별 디버깅 격리** — 스크립트 4개 분할 (collect_psu_ucanr / collect_psu_indoor / collect_mu_trinklein / collect_mobot).
- **검증 게이트 = 카드 수 + 필수 키워드** — fetch에서 본 카드 수가 ground truth. 어긋나면 파서 버그.

---

## 2. 사전 확인 (작업 시작 전 필수)

### 2.1 환경

```bash
git status              # 작업 트리 clean
git log -1 --oneline    # HEAD가 93abbaa ([1-10b] 푸시 커밋)인지 확인
git branch --show-current
```

작업 트리 dirty이거나 HEAD가 다르면 **즉시 중단·보고**.

### 2.2 입력 파일 확인

```bash
ls -la data/source/
# 기대: 다음 3개 파일 존재
#  - PSU.pdf
#  - Pest_and_Disease_Problems_of_Indo.txt
#  - Missouri_Environment_Garden.pdf

md5sum data/source/PSU.pdf
md5sum data/source/Pest_and_Disease_Problems_of_Indo.txt
md5sum data/source/Missouri_Environment_Garden.pdf
```

3개 중 하나라도 없으면 **즉시 중단·보고**. 사용자가 본인 로컬 프로젝트 루트의 `data/source/`에 3자료를 사전 배치 누락한 자리. `data/source/`는 `.gitignore`의 `data/` 패턴에 포함 — git 추적 X.

### 2.3 Dependency 확인

```bash
python -c "import pdfplumber; print(pdfplumber.__version__)" 2>&1
python -c "import pypdf; print(pypdf.__version__)" 2>&1
python -c "import bs4; print(bs4.__version__)" 2>&1
python -c "import httpx; print(httpx.__version__)" 2>&1
```

미설치 패키지는 `pip install pdfplumber pypdf beautifulsoup4 httpx` 후 `requirements.txt`에 추가. **PDF 파서는 `pdfplumber` 우선 채택** — 표·공백 구조 보존 우수. 추출 결과 깨지면 `pypdf` 폴백.

### 2.4 Mobot robots.txt 확인

```bash
python -c "
import httpx
r = httpx.get('https://www.missouribotanicalgarden.org/robots.txt', timeout=20)
print(r.status_code)
print(r.text)
"
```

`/gardens-gardening/...` 또는 `/visual-guides/...` 경로 `Disallow` 여부 확인. **disallow면 즉시 중단·보고** (자료 풀 재논의 필요).

### 2.5 목표 디렉토리 확인

```bash
ls -la data/raw/ 2>/dev/null || echo "data/raw 없음"
ls -la data/raw/b_dataset/ 2>/dev/null || echo "b_dataset 없음 (정상)"
```

`data/raw/b_dataset/`이 이미 존재하면 **즉시 보고**. 본 작업이 첫 수집이라 비어 있어야 정상.

---

## 3. 작업 항목

### 3.1 디렉토리 생성

```bash
mkdir -p data/raw/b_dataset/{psu_ucanr,psu_indoor,mu_trinklein,mobot}
```

`data/`는 `.gitignore`에 포함 — git tracking 대상 아님. 결과물은 로컬 디스크에만 남고, 측정 보고에서 디렉토리 트리·JSON 샘플로 공유.

### 3.2 `scripts/collect_psu_ucanr.py` — 자료 1 (PSU UCANR)

- **입력**: `data/source/PSU.pdf`
- **출력**:
  - `data/raw/b_dataset/psu_ucanr/PSU.pdf` (원본 카피, 무변형)
  - `data/raw/b_dataset/psu_ucanr/psu_ucanr.json` (파싱 카드)
- **파싱 흐름**:
  1. pdfplumber로 전체 페이지 텍스트 추출
  2. 섹션 분리: **Pest Problems** / **Disease Problems** / **Abiotic Problems** 3 섹션. 헤더 패턴 grep으로 인덱스 잡기
  3. 각 섹션 안에서 problem 항목 단위로 분할 (각 항목 = 증상 + 원인 + 해결책 묶음 = 카드 1개)
  4. 카드 ID: `psu_ucanr_001`, `psu_ucanr_002`, ...
- **본질 (변경 금지)**: **Abiotic Problems 테이블이 1단계 FP 본질 직격**. 황화·잎끝 갈변을 환경 원인으로 명시 매핑. Abiotic 섹션 누락 시 검증 실패.

### 3.3 `scripts/collect_psu_indoor.py` — 자료 2 (PSU Indoor txt)

- **입력**: `data/source/Pest_and_Disease_Problems_of_Indo.txt`
- **출력**:
  - `data/raw/b_dataset/psu_indoor/pest_and_disease_problems.txt` (원본 카피)
  - `data/raw/b_dataset/psu_indoor/psu_indoor.json`
- **파싱 흐름**:
  1. txt 헤더 패턴 식별 (Pest 7 + Disease 4 = 11 카드 예상). Pest 이름은 대개 첫 줄에 대문자/제목 케이스로 등장
  2. 각 problem 헤더 사이 본문 = 1 카드
  3. **honeydew → sooty mold 매핑 본문에 명시되어 있어야 함** — 1단계 "병해 의심" FP 일부 케이스 직격 자리

### 3.4 `scripts/collect_mu_trinklein.py` — 자료 3 (MU Trinklein PDF, page 1만)

- **입력**: `data/source/Missouri_Environment_Garden.pdf` (10페이지)
- **출력**:
  - `data/raw/b_dataset/mu_trinklein/trinklein_2018.pdf` (원본 전체 보존)
  - `data/raw/b_dataset/mu_trinklein/trinklein_2018_page1.txt` (page 1만 텍스트)
  - `data/raw/b_dataset/mu_trinklein/mu_trinklein.json`
- **파싱 흐름**:
  1. pdfplumber로 **page 1만** 추출. **page 2 이후는 폐기**
  2. page 1 본문에서 disease vs disorder 프레임 기준으로 카드 분할
  3. 카드 수 5 미만이어도 자료 본질이 "프레임 정의"라 OK. 카드 짧아도 보존
- **본질 (변경 금지)**: **"disease는 전염되지만 disorder는 안 됨" 프레임 + abiotic 손상 진단 패턴 명시**. 1단계 FP 본질 직격 자리 ⭐⭐⭐.

### 3.5 `scripts/collect_mobot.py` — 자료 4 + 5 (Mobot 2페이지 HTML)

- **입력 URL** (확정):
  - Mobot Indoor: `https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/problems-common-to-many-indoor-plants`
  - Mobot Herb: `https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/herb-problems-indoors`
- **출력**:
  - `data/raw/b_dataset/mobot/problems-common-to-many-indoor-plants.html` (raw HTML)
  - `data/raw/b_dataset/mobot/problems-common-to-many-indoor-plants.json` (카드 21 예상)
  - `data/raw/b_dataset/mobot/herb-problems-indoors.html`
  - `data/raw/b_dataset/mobot/herb-problems-indoors.json` (카드 12 예상)
- **스크래핑 매너 (필수)**:
  - User-Agent: `"plant-diagnosis-research/0.1 (educational; rangedayo@naver.com; +https://github.com/rangedayo)"`
  - 페이지 간 `time.sleep(3)`
  - timeout 30초, 재시도 1회만
- **파싱 흐름**:
  1. BeautifulSoup로 HTML 파싱. 섹션 구조 식별:
     - Indoor: Environmental Conditions(8) / Insects(7) / Diseases(4) / Nutrients(2) = 21
     - Herb: 비슷한 카테고리(herb 특이 + winter overwintering계) = 12
  2. 각 problem 카드 = `<div>` 또는 `<section>` 블록. 셀렉터는 실제 HTML 확인 후 결정 — Claude Code가 첫 fetch 후 보고하고 사용자 확정받은 후 진행
  3. `lookalikes` 필드: 카드 본문에 "may indicate ... or ..." 같은 모호성 표현이 명시되어 있으면 추출. 없으면 `null`. Herb의 "Wet and water-logged soil" 카드에는 박혀있음 — 그 패턴 기준

### 3.6 `data/raw/b_dataset/metadata.json` 작성

```json
{
  "stage": "B-1",
  "fetched_at": "<ISO 8601>",
  "sources": [
    {"id": "psu_ucanr",    "type": "pdf",         "license": "fair_use_personal_educational", "origin": "user_upload", "card_count": <N1>},
    {"id": "psu_indoor",   "type": "txt",         "license": "fair_use_personal_educational", "origin": "user_upload", "card_count": <N2>},
    {"id": "mu_trinklein", "type": "pdf_page1",   "license": "fair_use_personal_educational", "origin": "user_upload", "card_count": <N3>},
    {"id": "mobot_indoor", "type": "html_scrape", "license": "fair_use_personal_educational", "url": "https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/problems-common-to-many-indoor-plants", "card_count": <N4>},
    {"id": "mobot_herb",   "type": "html_scrape", "license": "fair_use_personal_educational", "url": "https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/herb-problems-indoors", "card_count": <N5>}
  ],
  "total_cards": <합계>
}
```

### 3.7 JSON 카드 공통 스키마 (5자료 동일)

```json
{
  "source": "<source_id>",
  "page": "<page_name>",
  "license": "fair_use_personal_educational",
  "fetched_at": "<ISO 8601>",
  "card_count": <N>,
  "cards": [
    {
      "id": "<source_id>_<3자리 번호>",
      "section": "<섹션 이름>",
      "title": "<카드 제목>",
      "body": "<카드 본문 전체, 무변형>",
      "lookalikes": "<오인 가능 다른 원인 — 없으면 null>",
      "external_link": "<있으면 URL, 없으면 null>"
    }
  ]
}
```

스키마 변경 금지. [B-2] 청크화 단계에서 이 스키마를 입력으로 받음.

---

## 4. 검증 게이트

각 자료별 **카드 수 + 필수 키워드** 체크. 어긋나면 파서 버그 — 본 단계 통과 실패.

| 자료 | 카드 수 최소 | 필수 키워드 (본문 또는 섹션명에 1+회) |
|---|---|---|
| PSU UCANR | ≥18 | "Abiotic" (섹션명 또는 단어) |
| PSU Indoor | ≥10 | "honeydew" |
| MU Trinklein | ≥3 | "disorder" |
| Mobot Indoor | ≥19 (21 예상) | "Environmental Conditions" |
| Mobot Herb | ≥10 (12 예상) | "winter" 또는 "overwintering" |

`scripts/validate_b_dataset.py` 작성·실행:

```bash
python scripts/validate_b_dataset.py
```

기대 출력 예:
```
[PASS] psu_ucanr   : 20 cards (>=18), 'Abiotic' found
[PASS] psu_indoor  : 12 cards (>=10), 'honeydew' found
[PASS] mu_trinklein:  5 cards (>=3) , 'disorder' found
[PASS] mobot_indoor: 21 cards (>=19), 'Environmental Conditions' found
[PASS] mobot_herb  : 12 cards (>=10), 'winter' found
[PASS] total: 70 cards
```

하나라도 FAIL이면 **즉시 보고·중단**. 디버그 모드(`--dump-bodies`)로 카드 본문 첫 80자 dump 옵션 박을 것.

---

## 5. 결과 보고 (사용자 확정 대기)

다음 항목 모두 보고에 포함:

5.1. **디렉토리 트리** (`tree data/raw/b_dataset/` 출력 그대로).

5.2. **각 JSON 첫 카드 샘플** (5개) — `jq '.cards[0]' data/raw/b_dataset/.../X.json`.

5.3. **카드 수 + 키워드 게이트 표** (§4 그대로).

5.4. **라이브러리·환경 보고**:
- 채택 PDF 파서 (`pdfplumber` vs `pypdf` 폴백 여부)
- `requirements.txt` 갱신 여부 + diff
- robots.txt 결과 요약

5.5. **Mobot 스크래핑 메타**:
- HTTP 응답 상태 코드 (2개 페이지)
- 페이지 간 sleep 실측 시간
- User-Agent 실제 사용값

5.6. **발견된 이슈** — 예: 특정 카드 `lookalikes` 추출 어려움, HTML 셀렉터 분기 케이스, PDF 표 텍스트 깨짐 등. 박힌 그대로 명시.

5.7. **다음 단계 제안** — [B-2] 청크화·임베딩·적재 작업의 입력으로 본 결과를 그대로 쓸 수 있는지, 또는 본 단계에서 카드 본문 정제(공백·줄바꿈) 추가 필요한지 의견.

---

## 6. 롤백

검증 실패 또는 사용자 거부 시:

```bash
# raw 자료 폐기
rm -rf data/raw/b_dataset/

# 생성된 스크립트 (커밋 전이면)
git status              # collect_*.py · validate_b_dataset.py 추적 여부 확인
git checkout -- scripts/  # 또는 rm -f scripts/collect_psu_ucanr.py scripts/collect_psu_indoor.py scripts/collect_mu_trinklein.py scripts/collect_mobot.py scripts/validate_b_dataset.py
```

`data/raw/b_dataset/`는 `.gitignore`의 `data/` 패턴에 포함 → 작업 디렉토리만 정리하면 됨.

**부분 성공 자료가 있어도 전체 재실행 원칙**. 부분 커밋 절대 금지.

---

## 7. 주의 사항 (재강조)

- **변수 격리**: `app/`·`scripts/run_eval.py`·`scripts/build_rag_db.py`·`scripts/eval_rag.py`·`data/vector_db/` 절대 손대지 않음. 본 작업은 `data/raw/b_dataset/` + `scripts/collect_*.py` + `scripts/validate_b_dataset.py`만 신규 작성.
- **NCPMS 처리 결정 보류**: NCPMS 폐기 vs 별도 컬렉션 보존은 [B-2] 청크화·적재 단계에서 결정. 본 작업 무영향.
- **농진청 자료 단계 B'**: 농진청 API 승인 대기 중. 단계 B'(종 메타 + 새 메트릭) 진입 자리로 본 단계와 분리. 본 작업에서 농진청 자료 절대 적재 X.
- **사용자 로컬 자료 변형 금지**: PSU.pdf · PSU txt · MU PDF는 `data/source/`의 원본을 **카피만**. 수정·압축·인코딩 변환 X. 원본 파일은 1차 디렉토리 `data/raw/b_dataset/<source_id>/`에 그대로 복제.
- **카드 ID 일관성**: `<source_id>_<3자리 번호>` 패턴 (`psu_ucanr_001`, `mobot_indoor_001` 등). source_id prefix로 자료 간 충돌 방지.
- **카드 본문 trim 금지**: HTML/PDF에서 추출한 본문을 임의 자르지 말 것. lookalikes·external_link 추출 외엔 원본 유지. 공백 정리(`\s+` → ` `)는 허용, 의미 단어 삭제 X.
- **`fetched_at`**: 각 자료 JSON에 ISO 8601 박기. 동일 실행 내 자료들은 동일 timestamp 허용.
- **스크래핑 거절 응답**: Mobot이 4xx/5xx 응답하면 sleep 후 1회 재시도. 두 번째도 실패하면 **즉시 중단·보고**. 강제 fetch 시도 금지.
- **HTML 구조 변경 대응**: Mobot 페이지의 HTML 셀렉터가 예상과 다르면 첫 fetch 직후 raw HTML을 dump해 보고. 사용자 확정 후 셀렉터 결정. 추측으로 파싱 강행 금지.

---

## 8. 작업 순서 요약

1. **사전 확인** §2 — git · 입력 파일 md5 · dependency · robots.txt · 목표 디렉토리. 이상 시 중단·보고.
2. **디렉토리 생성** §3.1.
3. **PSU UCANR 수집** §3.2 — `collect_psu_ucanr.py` 작성·실행.
4. **PSU Indoor 수집** §3.3 — `collect_psu_indoor.py`.
5. **MU Trinklein 수집** §3.4 — `collect_mu_trinklein.py` (page 1만).
6. **Mobot 수집** §3.5 — `collect_mobot.py` (3초 sleep, User-Agent 박기). 첫 fetch 후 HTML 셀렉터 사용자 확정받기.
7. **메타 파일 작성** §3.6.
8. **검증** §4 — `validate_b_dataset.py` 실행. 카드 수 + 키워드 게이트.
9. **결과 보고** §5 — 사용자 확정 대기.
10. 사용자 OK 후 **단일 커밋** (`scripts/collect_*.py` + `scripts/validate_b_dataset.py` + `requirements.txt` 갱신).

총 스크립트 5개 (collect 4 + validate 1) + 디렉토리 트리 + 메타 1개. 다음 단계([B-2] 청크화·임베딩·적재)는 본 단계 보고 후 별도 진단·작업 프롬프트로 진입.
