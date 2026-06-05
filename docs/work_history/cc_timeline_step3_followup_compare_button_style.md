# [시계열 3단계 후속] 비교 버튼 시각 개선

## 참조
- 본 작업 = **3단계(`/compare` + 비교 UI) 후속 fix 미니 라운드**. 3단계 검증 중 발견된 UI 개선 사항 처리.
- 범위: `TimelineView`의 "이전 진단과 비교" 버튼 시각만 변경. 기능·이벤트 처리·인덱싱 무변경.

---

## 발견된 개선 사항 (3단계 수동 E2E 중 시각 확인)

현재 비교 버튼 모습:
- 텍스트 링크 톤(작은 글씨 + 아이콘), 카드 우측 정렬, 좌우 양방향 화살표(↔) 아이콘.

문제 인식:
- 텍스트 링크는 클릭 가능성이 약함(눈에 잘 안 띄어 인지율 ↓).
- 좌우 화살표(↔)는 세로 타임라인의 두 카드를 비교하는 의미와 시각적으로 어색함(좌우 비교 같은 느낌).
- 우측 정렬은 직전 카드에 종속된 인상 → 두 카드를 잇는 의미가 안 살아남.

개선 방향:
1. **버튼 형식** — pill 형태 outline 버튼(테두리 + 투명/연한 배경). 텍스트 링크보다 명확.
2. **아이콘 변경** — 좌우 양방향(↔) → **위아래 양방향(↕)**. 세로 타임라인에서 위 카드(이전) ↔ 아래 카드(현재 진단의 직전) 비교 의미 강화.
3. **가운데 정렬** — 두 카드 사이 중앙에 위치. 두 카드를 잇는 시각 위치.

---

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)

변경 전 다음을 view로 확인하고 보고:

1. **`components/TimelineView.tsx`** — 현재 비교 버튼 JSX 구조·className·인라인 스타일·아이콘. styled-jsx scoped 영역에서 변경할 셀렉터 위치.
2. **현재 사용 중인 아이콘 이름** (Tabler Icons) — 예: `ti-arrows-exchange` 또는 유사. 위아래 양방향(↕) 대체 후보 제안(`ti-arrows-vertical`·`ti-arrows-up-down`·`ti-arrow-up-down` 등 Tabler에서 실재하는 것). 디자인 시트에 등록된 아이콘 규칙(_document.tsx에서 로드) 충돌 없는지 확인.
3. **디자인 시트 토큰** — outline 버튼 톤 만들 때 사용할 색·테두리·반지름 토큰(예: `--green-medium` 보더, `--green-dark` 텍스트, `--radius-button` 반지름). 기존 다른 버튼(`SaveDiagnosisModal`의 "취소" outline 버튼 등)과의 일관성 확인.
4. **레이아웃 영향** — 현재 카드 형제로 배치된 버튼이 정렬 변경 시 다른 카드 간격에 영향을 주는지 미리 점검(margin/padding 조정 필요 여부).

보고 후 진행.

---

## 1. 범위 (이번 라운드만)

- `components/TimelineView.tsx` 비교 버튼의 **스타일·아이콘·정렬**만 변경.
- 버튼 클릭 동작·`stopPropagation`·`compareTarget` state·인덱싱(`records[i+1]` vs `records[i]`)·가장 오래된 카드 숨김 로직 **무변경**.
- `/compare` 엔드포인트·`CompareModal`·기타 시계열 코드 무변경.

---

## 2. 작업

### 2.1 아이콘 교체

좌우 양방향(↔) → **위아래 양방향(↕)** 아이콘. Tabler Icons에서 실재 아이콘 이름 사용(권장 후보: `ti-arrows-vertical` · `ti-arrows-up-down`. 게이트에서 검증된 이름으로 확정).

### 2.2 버튼 스타일 — pill outline

권장 스타일(디자인 시트 토큰 활용):

```css
.compare-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;             /* 카드보다 작게 — 시각적 hierarchy */
  padding: 0 16px;
  border-radius: 999px;     /* pill */
  border: 1.5px solid var(--green-medium);
  background: var(--bg-card);  /* 또는 transparent */
  color: var(--green-dark);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: -0.01em;
}
.compare-btn:hover {
  background: var(--bg-icon-circle);  /* 미세 hover, 토큰 활용 */
}
.compare-btn i {
  font-size: 15px;
}
```

> `SaveDiagnosisModal`의 outline "취소" 버튼과 톤 일관성. 단 height는 더 작게(36px) — 카드 사이 보조 액션이라 시각 비중 낮게.

### 2.3 정렬 — 가운데

현재 우측 정렬을 **가운데 정렬**로:

```css
.compare-btn-wrap {
  display: flex;
  justify-content: center;     /* 가운데 */
  margin: 8px 0;               /* 카드 간격에 맞춰 미세 조정 */
}
```

또는 부모 컨테이너 정렬 변경. 게이트에서 본 현 구조에 맞춰 최소 변경 경로 선택.

### 2.4 텍스트 유지

"이전 진단과 비교" 텍스트는 그대로 유지.

---

## 3. 제약 (불변)

- `/compare` 백엔드·`CompareModal`·`comparePlantDiagnoses` 무변경.
- 비교 버튼의 동작 로직(`stopPropagation`·클릭 핸들러·`compareTarget` state·가장 오래된 카드 숨김 조건) 무변경.
- 카드 본체 클릭 동작(ResultView 진입) 무변경.
- 다른 화면(`MyPlantsView`·`ResultView`·`CareGuideView`·`HomeView`) 무변경.
- 디자인 시트 토큰 신설 금지(기존 토큰 재사용).
- `eval/`·`scripts/`·백엔드 무변경.
- 명명 정합 변경(`main_rag`) 금지(B-2 보류 중).

---

## 4. 검증

### 4.1 정적
- `npx tsc --noEmit` 통과.
- `npm run build` 성공.

### 4.2 수동 시각 확인

전제: 타임라인에 진단 ≥2건 있는 식물 보유.

1. **버튼 모습** — 타임라인 진입 → 카드 사이에 pill outline 버튼이 가운데 정렬되어 표시되는지. 아이콘이 위아래 양방향(↕)인지.
2. **숨김 유지** — 가장 오래된(타임라인 최하단) 카드 다음엔 비교 버튼이 여전히 표시되지 않아야.
3. **클릭 동작 유지** — 버튼 클릭 → `CompareModal` 정상 오픈. 카드 본체 클릭과 격리 유지(stopPropagation 동작).
4. **호버 톤** — 마우스 올렸을 때 미세 배경 변화(권장 스타일대로 적용 시).
5. **다른 화면 무영향** — 홈·내 식물·결과·케어 화면 시각 변화 없음.

각 항목 결과 + 스크린샷(권장: 1) + 콘솔 에러 0 확인.

---

## 5. 커밋 (분리·푸시 보류)

- `docs:` — 본 프롬프트(`docs/work_history/cc_timeline_step3_followup_compare_button_style.md`).
- `style:` — `components/TimelineView.tsx` 시각 변경.

> `style:` 커밋 타입 사용(`feat:`·`fix:` 아님 — 시각 보정만, 기능·버그 변경 없음).

커밋 메시지 안(사용자 확정 후):
```
style: [시계열 3단계 후속] 비교 버튼 시각 개선

- 텍스트 링크 → pill outline 버튼 (--green-medium 보더, --green-dark 텍스트)
- 좌우 양방향 화살표(↔) → 위아래 양방향 화살표(↕). 세로 타임라인의
  두 카드를 잇는 의미 시각화.
- 우측 정렬 → 가운데 정렬. 두 카드 사이 중앙 위치.
- 클릭 동작·stopPropagation·가장 오래된 카드 숨김 로직 무변경.
- 디자인 시트 토큰 재사용(신설 없음).

범위: TimelineView 비교 버튼 시각만. 기능·다른 컴포넌트 무영향.
3단계 검증 중 발견된 UX 개선 사항 처리.
```

---

## 보고

- 0번 게이트 결과(현 JSX 구조·아이콘 이름·토큰 후보·레이아웃 영향).
- 변경 파일(`components/TimelineView.tsx` 단일 예상).
- `tsc`·`npm run build` 결과.
- 시각 확인 5개 결과 + 스크린샷.
- 의외 발견(예: 토큰 부족·아이콘 폰트 미로드·레이아웃 깨짐 등) 즉시 보고.

`eval/`·백엔드·다른 컴포넌트 add 금지.

---

## 6. 주의

- **클릭 핸들러 유지**: `stopPropagation` 호출이 새 JSX에서도 그대로 작동해야 함. 시각 변경하면서 핸들러 누락 없도록.
- **가장 오래된 카드 숨김 조건 유지**: `i === records.length - 1` 가드 그대로.
- **아이콘 폰트 의존**: Tabler Icons 웹폰트는 `_document.tsx`에서 로드됨. 새 아이콘 이름이 그 폰트에 실재하는지 확인(없는 이름 쓰면 빈 원 표시).
- **height 차별화**: 36px 권장(카드보다 작게) — 카드 본체 액션과 시각 비중 차이를 둬서 보조 액션임을 명시.
- **eval/baseline.json 절대 손대지 말 것**.
- **다음 작업 후보** (3단계 완전 종료 후):
  - 정확도 트랙 — 종 다양 환자 표본 + status GT 라벨 구축.
  - 인증 통합 — `/diagnose`·`/compare`에 Firebase ID 토큰 인증 적용(별건 백로그).
  - 명명 정합 변경 — `main_rag` → `a_dataset_rag` ([B-2] 보류 해제 시).
