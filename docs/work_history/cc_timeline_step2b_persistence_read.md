# [시계열 2-B] 영속화 — 읽기 UI (내 식물 + 타임라인)

## 참조
- 설계 정본: `docs/design/design_timeline_firebase.md` (§3 데이터 모델, §4 저장 흐름).
- 이전 작업: 1단계(인증), 2-A(쓰기) — 완료/푸시됨. `lib/firebase.ts`·`lib/auth.tsx`·`lib/db.ts`·`components/SaveDiagnosisModal.tsx` 가용. Firestore에 `users/{uid}/plants/{plantId}/diagnoses/{dxId}` 문서 + Storage 이미지 저장 확인됨.
- 본 작업 = Slice 1의 **읽기 UI**: 내 식물 목록 + 진단 타임라인 + 과거 진단 상세 보기(ResultView 재사용). **비교(`/compare`)는 3단계, 본 라운드 범위 밖.**

---

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)

변경 전 다음을 **view**로 확인하고 보고:

1. **`pages/index.tsx`** 현 상태머신 — Screen 타입(`"home"|"loading"|"result"|"care"`), screen 전환 분기, `result`/`file`/`previewUrl`/`showSave`/`savedMsg` state, 저장 흐름. 본 라운드에 새로 추가될 state(`selectedPlantId`, `viewMode` 또는 `historyDiagnosis`, history용 care_guide) 슬롯을 어디에 둘지 제안.
2. **`lib/db.ts`** — `listPlants` 현 시그니처, 추가할 읽기 함수(`listDiagnoses`) 시그니처 제안. Firestore `Timestamp` → JS `Date` 변환 방식.
3. **`components/ResultView.tsx`** props(`onReset`, `onSave`, `onViewCare`, `result`, `imageUrl`) 현황. history 모드 도입 시 변경 필요한 최소 항목 정리(권장: `mode?: "fresh"|"history"` 추가 + 하단 액션 버튼 텍스트/아이콘 분기. 저장 버튼은 `onSave` 미제공으로 이미 숨김).
4. **`components/HomeView.tsx`** — 현재 탭바 구조(홈 active, 나머지 disabled). 탭바를 공용 컴포넌트(`BottomTabBar`)로 추출 가능 여부. 추출 시 props 시그니처 제안(`activeTab`·`onTabChange`).
5. **`components/CareGuideView.tsx`** — `careGuide` prop 출처. history 모드에서 진입 시 어느 careGuide를 전달할지(권장: history 분기 시 `historyDiagnosis.careGuide`).
6. **미로그인 사용자가 "내 식물" 탭 진입 시 처리 방안** — 권장: 탭 자체는 active, 진입 후 화면 안에서 로그인 유도 카드 표시(SaveDiagnosisModal의 로그인 게이트와 동일 톤).

보고 후 진행.

---

## 1. 범위 (이번 라운드만)

- `Screen` 타입 확장: `"myPlants"` + `"timeline"` 2개 추가.
- 데이터 레이어 확장(읽기): `listDiagnoses(uid, plantId)` 신규, `listPlants`는 각 식물의 마지막 진단 메타(status/summary/createdAt)를 포함하도록 확장(N+1 + `Promise.all`).
- 신규 화면 2개: `components/MyPlantsView.tsx`, `components/TimelineView.tsx`.
- `ResultView` 미세 확장: `mode?: "fresh"|"history"` prop. history일 때 하단 액션 우측 버튼 → "타임라인으로 돌아가기"(아이콘 `ti-chevron-left`) + 헤더 뒤로가기도 동일 액션.
- 탭바 공용 추출: `components/BottomTabBar.tsx`. **home·myPlants 화면에만 표시**(나머지 화면 미표시 = R4 정책 유지).
- **불변**: FastAPI·`/diagnose`·비교 기능·새 디자인 시안 도입 없음. 2-A 코드(`saveDiagnosis` 등) 무변경 — denormalized 메타는 미도입(N+1로 대체).

---

## 2. 작업

### 2.1 데이터 레이어 — `lib/db.ts` 확장

#### 2.1.1 `listPlants` 확장

`PlantSummary`에 마지막 진단 메타 추가:

```ts
export type LastDiagnosisMeta = {
  status: string;
  summary: string;
  createdAt: Date | null; // Firestore Timestamp → JS Date (toDate())
};

export type PlantSummary = {
  id: string;
  name: string;
  speciesKey: string | null;
  coverImageUrl: string | null;
  lastDiagnosis: LastDiagnosisMeta | null; // 진단 0건일 수도 있음(현 흐름상 거의 없지만 방어)
};
```

구현:
- 기존대로 plants 컬렉션을 `orderBy("createdAt","desc")`로 조회.
- 각 plant에 대해 `diagnoses`를 `orderBy("createdAt","desc")` + `limit(1)`로 조회(병렬: `Promise.all`).
- 결과 없으면 `lastDiagnosis: null`.

> **주의**: N+1이지만 사용자 식물 수가 적은 현 단계에선 OK. 향후 denormalized 최적화(plant 문서에 `lastStatus`·`lastDxAt` 갱신) 여지는 남겨두되 본 라운드에서 도입 안 함.

#### 2.1.2 `listDiagnoses(uid, plantId)` 신규

```ts
export type DiagnosisRecord = {
  id: string;
  createdAt: Date | null;
  imageUrl: string;
  status: string;
  isHealthy: boolean;
  summary: string;
  currentState: string;
  cause: string;
  actionPlan: string[];
  careGuide: CareGuide | null;
  observedSymptoms: string[];
};

export async function listDiagnoses(uid: string, plantId: string): Promise<DiagnosisRecord[]>;
```

- `users/{uid}/plants/{plantId}/diagnoses` 컬렉션, `orderBy("createdAt","desc")`.
- Firestore Timestamp → `Date`(`.toDate()`), 누락 시 `null`.
- 저장 시 누락 가능한 필드는 방어적 기본값(`""`/`[]`/`null`).

#### 2.1.3 `diagnosisRecordToResponse(record, plant)` 신규 (헬퍼)

Firestore `DiagnosisRecord` → ResultView가 기대하는 `DiagnosisResponse`로 변환. **새 파일 `lib/historyAdapter.ts` 권장** (db.ts에 두지 말 것 — 표시 계층 변환은 분리).

```ts
import { DiagnosisRecord, PlantSummary } from "./db";
import { DiagnosisResponse } from "../types/diagnosis";

export function diagnosisRecordToResponse(
  record: DiagnosisRecord,
  plant: Pick<PlantSummary, "name">,
): DiagnosisResponse;
```

매핑:
- `structured_result.summary` ← `record.summary`
- `structured_result.current_state` ← `record.currentState`
- `structured_result.cause` ← `record.cause`
- `structured_result.action_plan` ← `record.actionPlan`
- `structured_result.status` ← `record.status`
- `care_guide` ← `record.careGuide`
- `analysis` ← 부분 mock: `{ plant_name: null, plant_name_korean: plant.name, plant_confidence: null, alt_candidates: [], visual_description: "", observed_symptoms: record.observedSymptoms }`
  - **이유**: ResultView가 `analysis?.plant_name_korean`으로 식물명을 표시. 저장 시 `plant_name`은 보존 안 했고, 사용자 별칭(`plant.name`)이 더 안정적이고 의미 있음. 학명/일반명 매번 다를 수 있는 AI 식별 결과보다 별칭이 적합.
- `message` ← `""` (사용처 없음).

> ⚠ analysis mock은 표시 전용. 추후 saveDiagnosis가 plant_name을 직접 저장하게 되면 변환에서 제거.

---

### 2.2 화면 — `Screen` 확장 + 라우팅 — `pages/index.tsx`

#### 2.2.1 Screen 타입

```ts
type Screen = "home" | "loading" | "result" | "care" | "myPlants" | "timeline";
```

#### 2.2.2 추가 state

```ts
const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null);
const [selectedPlantName, setSelectedPlantName] = useState<string>(""); // ResultView 헤더/식물명 mock용
const [historyDiagnosis, setHistoryDiagnosis] = useState<DiagnosisRecord | null>(null);
```

- `historyDiagnosis !== null`이면 `screen === "result"` 또는 `"care"`는 **history 모드**.
- 신규 진단 흐름은 기존 `result` state 그대로(historyDiagnosis는 null 유지).

#### 2.2.3 전환 로직

| 출발 | 트리거 | 도착 | 부수 효과 |
|---|---|---|---|
| home | 탭 "내 식물" | myPlants | — |
| myPlants | 탭 "홈" | home | selectedPlantId 등 정리(optional) |
| myPlants | 식물 카드 클릭 | timeline | `setSelectedPlantId(p.id)` + `setSelectedPlantName(p.name)` |
| timeline | 헤더 뒤로 | myPlants | — |
| timeline | 진단 카드 클릭 | result (history) | `setHistoryDiagnosis(record)` |
| result (history) | "타임라인으로 돌아가기" or 헤더 뒤로 | timeline | `setHistoryDiagnosis(null)` |
| result (history) | "케어 가이드 보기" | care (history) | historyDiagnosis 유지 |
| care (history) | 헤더 뒤로 | result (history) | — |
| result (fresh) | 헤더 뒤로 or "홈으로 돌아가기" | home | 기존 `handleReset` 그대로 |
| care (fresh) | 헤더 뒤로 | result (fresh) | 기존 동작 |

#### 2.2.4 렌더 분기

`screen === "result"` 처리:
```tsx
if (screen === "result") {
  if (historyDiagnosis) {
    // history 모드
    const historyResp = diagnosisRecordToResponse(historyDiagnosis, { name: selectedPlantName });
    return (
      <ResultView
        result={historyResp}
        imageUrl={historyDiagnosis.imageUrl}
        mode="history"
        onReset={() => { setHistoryDiagnosis(null); setScreen("timeline"); }}
        onViewCare={historyDiagnosis.careGuide ? () => setScreen("care") : undefined}
        // onSave 미제공 → 저장 버튼 숨김
      />
    );
  }
  // fresh 모드 (기존 그대로)
  return <ResultView result={result!} ... mode="fresh" or undefined ... />;
}
```

`screen === "care"` 처리:
```tsx
if (screen === "care") {
  const cg = historyDiagnosis ? historyDiagnosis.careGuide : result?.care_guide;
  if (!cg) return null; // 방어
  return <CareGuideView careGuide={cg} onBack={() => setScreen("result")} />;
}
```

---

### 2.3 `components/MyPlantsView.tsx` 신규

#### Props
```ts
type Props = {
  onPickPlant: (plant: PlantSummary) => void;
  onGoDiagnose: () => void; // empty state에서 진단 시작 유도 (home으로 이동)
};
```

#### 동작
- `useAuth()`로 `user`·`loading` 확인.
- **미로그인**: 카드 하나 — "로그인하고 내 식물 기록을 확인하세요" + "Google로 로그인" 버튼(`signInWithGoogle`). 디자인 시트 토큰 사용.
- **로그인**: `useEffect`로 `listPlants(uid)` 호출. 로딩 중 스피너/문구.
- **식물 0개 (empty state)**: 안내 문구 — "아직 등록된 식물이 없어요" + 부제 "첫 진단을 저장해 식물을 등록해보세요" + 행동 버튼 "진단 시작" → `onGoDiagnose()`.
- **식물 N개**: 카드 리스트(세로 1열). 각 카드:
  - 좌측: 64×64 정사각 썸네일(`coverImageUrl` 없으면 leaf 아이콘 placeholder, 디자인 시트 `--bg-icon-circle` 톤).
  - 우측 상단: 식물 이름(별칭).
  - 우측 중간: `lastDiagnosis`가 있으면 status 배지(`statusBadge`) + 상대시간(예: "3일 전" / 정확한 헬퍼 없으면 ISO 날짜 짧게).
  - 우측 하단: `lastDiagnosis.summary` 1줄 트런케이트(없으면 미표시 — 빈 라벨 노출 금지).
  - 카드 전체 클릭 → `onPickPlant(plant)`.

#### 헤더
- 화면 상단에 "내 식물" 타이틀(R5 톤, `var(--green-dark)`).
- 우측에 `<AuthControl />` 재사용(헤더 일관성 — 홈과 동일 위치 슬롯). 미로그인 상태에서도 자연스럽게 로그인 진입 가능.

#### 스타일
- `styled-jsx scoped`. `globals.css` `var(--*)` 토큰.
- 카드 디자인은 시안 정본 없음 → 디자인 시트 일관성으로 자작. 가짜 정량 금지(SVG 일러스트 같은 더미 미사용 — `coverImageUrl` 또는 아이콘 placeholder만).

#### 하단
- `<BottomTabBar activeTab="myPlants" onTabChange={...} />` (2.6 참조).

---

### 2.4 `components/TimelineView.tsx` 신규

#### Props
```ts
type Props = {
  uid: string;
  plant: PlantSummary;       // 헤더에 이름 표시 + 진단 카드 클릭 시 변환 컨텍스트
  onBack: () => void;        // → myPlants
  onPickDiagnosis: (record: DiagnosisRecord) => void;
};
```

#### 동작
- `useEffect`로 `listDiagnoses(uid, plant.id)` 호출. 로딩/에러 처리.
- **빈 상태(0건)**: 방어용 — 현재 흐름상 plant가 있으면 진단도 ≥1건. "진단 이력이 없습니다" 안내만(액션 버튼 불필요).
- **N건**: 카드 리스트(세로 1열, 최신순). 각 카드:
  - 좌측: 64×64 썸네일(`imageUrl`).
  - 우측 상단: status 배지(`statusBadge`) + 날짜(`createdAt` Date → 짧은 포맷, 예: "2026.06.01").
  - 우측 하단: `summary` 1-2줄 트런케이트(`-webkit-line-clamp: 2`).
  - 카드 전체 클릭 → `onPickDiagnosis(record)`.

#### 헤더
- 좌측: 뒤로가기(`ti-chevron-left`, `var(--text-primary)`) → `onBack()`.
- 중앙: `plant.name` (식물 별칭).
- 우측: `<AuthControl />` (일관성).

#### 스타일
- `styled-jsx scoped`. 디자인 시트 토큰.
- 탭바 미표시(sub 화면).

---

### 2.5 `components/ResultView.tsx` 미세 확장

추가 prop:

```ts
type ResultViewProps = {
  // ... 기존
  mode?: "fresh" | "history"; // 미제공 = "fresh" (기존 동작)
};
```

변경 사항(최소):
- `mode === "history"`일 때 **하단 액션 우측 버튼**:
  - 텍스트: "타임라인으로 돌아가기"
  - 아이콘: `ti-chevron-left`(또는 `ti-list`)
  - `onClick`: `onReset` (호출부에서 timeline 복귀 핸들러로 주입)
- 헤더 좌측 뒤로가기(`onReset`)는 기존 동작 유지 — `onReset`의 의미가 호출부에서 분기되므로 ResultView 내부 분기 불필요.
- 저장 버튼: `onSave` 미제공 시 자동 숨김(기존 가드 유지 — history 모드에서 호출부가 onSave를 안 넘기므로 OK).
- 케어 버튼: 그대로 유지(`onViewCare`).

> ⚠ 기존 props·기존 동작 보존이 최우선. `mode` 분기는 하단 우측 버튼 텍스트/아이콘 정도로 최소화.

---

### 2.6 `components/BottomTabBar.tsx` 공용 추출

현재 `HomeView` 내부의 탭바를 떼어내 공용 컴포넌트화.

```ts
export type TabKey = "home" | "diagnose" | "myPlants" | "settings";

type Props = {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
};
```

- "diagnose"·"settings"는 여전히 disabled(클릭 무반응).
- "home"·"myPlants" 클릭 시 `onTabChange` 호출.
- 시각 스타일·SVG·아이콘은 기존 HomeView 탭바와 1:1 유지(시안 변경 없음).
- `HomeView`에서 탭바 JSX 제거하고 `<BottomTabBar activeTab="home" onTabChange={...} />`로 교체.
- `MyPlantsView`도 동일 컴포넌트 사용(`activeTab="myPlants"`).
- 다른 화면(loading/result/care/timeline)은 탭바 미사용.

탭 전환은 상위(`pages/index.tsx`)에서 처리:
```ts
const handleTabChange = (tab: TabKey) => {
  if (tab === "home") setScreen("home");
  else if (tab === "myPlants") setScreen("myPlants");
  // diagnose/settings는 disabled
};
```

`HomeView`·`MyPlantsView`가 `onTabChange` prop을 받아 BottomTabBar에 전달.

---

## 3. 제약 (불변)

- `/diagnose`·`lib/api.ts`·FastAPI·`scripts/`·`eval/baseline.json` 무변경.
- `lib/db.ts`의 쓰기 함수(`createPlant`·`saveDiagnosis`·`updatePlantCover`) 시그니처·동작 무변경. 본 라운드는 **읽기만** 추가.
- R5/R6 UI 토큰·스타일 일관성 유지. 새 디자인 시안 도입 없음(시안 정본 없는 신규 화면은 디자인 시트 토큰으로 자작).
- 가짜 정량/숫자 신설 금지. 더미 카드/일러스트 금지(이미지 placeholder는 아이콘만).
- `current_state`·care 필드 타입 유지(백엔드 호환).
- 비교 기능(`/compare`) 도입 금지 — 3단계.
- denormalized 메타(plant.lastStatus 등) 도입 금지 — 본 라운드는 N+1로 충분.
- 브라우저 라우팅 도입 금지(상태머신 유지). `Screen` enum만 확장.
- 명명 정합 변경(`main_rag` 등) 금지(B-2 보류 중).

---

## 4. 검증

### 4.1 정적
- `npx tsc --noEmit` 통과.
- `npm run build` 성공(필요 시 `.next` 정리). prod 빌드 권장 — Turbopack dev 풀리로드 루프 회피.

### 4.2 수동 E2E (Firebase 콘솔에 기존 데이터 있는 상태 전제. 없으면 1번 먼저 수행)

1. **저장 흐름 유지** (regression): 로그인 → 진단 → 저장(새 식물 1건). 기존 토스트·동작 유지 확인.
2. **myPlants 진입**: 홈 탭바 "내 식물" → myPlants 화면. 식물 카드(이름·커버·status 배지·요약 스니펫) 정상 표시. `lastDiagnosis` 메타 노출 확인.
3. **식물 선택 → timeline**: 카드 클릭 → timeline 화면. 헤더에 식물 별칭, 진단 카드 리스트(썸네일·status·날짜·summary) 최신순 표시.
4. **진단 상세 (history 모드)**: 진단 카드 클릭 → ResultView 진입. 식물명에 별칭 표시, status·summary·cause·action_plan 정상 렌더. **저장 버튼 없음**. 하단 우측 버튼 = "타임라인으로 돌아가기".
5. **케어 (history 모드)**: history result에서 "지속 관리법 보기" → CareGuideView 진입. careGuide 필드 정상 렌더. 헤더 뒤로 → history result 복귀.
6. **타임라인 복귀**: history result에서 "타임라인으로 돌아가기" 또는 헤더 뒤로 → timeline 복귀. 헤더 뒤로 한 번 더 → myPlants.
7. **홈 복귀**: myPlants 탭바 "홈" → home.
8. **fresh 흐름 무영향** (regression): 홈에서 새 진단 → result(fresh) → 헤더 뒤로 또는 "홈으로 돌아가기" → home. "지속 관리법 보기" → care → 뒤로 → result(fresh). 저장 → 토스트.
9. **미로그인 상태**: 로그아웃 후 "내 식물" 탭 → 로그인 유도 카드 표시. "Google로 로그인" → 팝업 → 로그인 → 자동 식물 목록 표시.
10. **식물 0개 (empty state)**: 새 계정으로 로그인 후 "내 식물" → empty state 안내 + "진단 시작" 버튼 → home으로 이동.

각 케이스 결과(스크린샷 권장 4·5·9·10) + 콘솔 에러 0 확인.

---

## 5. 커밋 (분리·푸시 보류)

- `docs:` — 본 프롬프트(`docs/work_history/cc_timeline_step2b_persistence_read.md`).
- `feat:` — 코드 변경:
  - `lib/db.ts` 확장 (`listPlants` 메타 추가, `listDiagnoses` 신규, 타입 추가).
  - `lib/historyAdapter.ts` 신규.
  - `components/BottomTabBar.tsx` 신규(공용 추출).
  - `components/MyPlantsView.tsx` 신규.
  - `components/TimelineView.tsx` 신규.
  - `components/ResultView.tsx` 미세 확장(`mode` prop).
  - `components/HomeView.tsx` 탭바 분리(JSX 교체).
  - `pages/index.tsx` Screen 확장 + 라우팅.

커밋 메시지 안(사용자 확정 후):
```
feat: [시계열 2-B] 영속화 — 읽기 UI (내 식물 + 타임라인)

- lib/db.ts: listPlants에 lastDiagnosis 메타 추가(N+1, Promise.all),
  listDiagnoses 신규 (users/{uid}/plants/{plantId}/diagnoses, 최신순).
- lib/historyAdapter.ts: Firestore DiagnosisRecord → ResultView가 기대하는
  DiagnosisResponse 변환. 식물명은 사용자 별칭(plant.name)을
  analysis.plant_name_korean에 mock 주입(저장 시 plant_name 미보존, 별칭이 안정).
- components/BottomTabBar.tsx: 탭바 공용 추출(home/myPlants 활성, 나머지 disabled 유지).
- components/MyPlantsView.tsx: 식물 카드 리스트, 미로그인/empty state.
- components/TimelineView.tsx: 선택 식물의 진단 이력 카드 리스트(최신순).
- components/ResultView.tsx: mode prop ("fresh"|"history") — history일 때
  하단 우측 버튼 "타임라인으로 돌아가기"(아이콘 변경). 저장 버튼은
  onSave 미제공으로 기존 가드대로 자동 숨김.
- pages/index.tsx: Screen에 "myPlants"·"timeline" 추가, history 모드 분기
  (selectedPlantId·selectedPlantName·historyDiagnosis state),
  ResultView/CareGuideView가 fresh/history에 따라 다른 데이터 소스 사용.

범위: 읽기 UI 전용. 쓰기 경로(2-A) 무변경, 비교(/compare)는 3단계.
가짜 정량/숫자 금지·더미 금지 원칙 유지.
```

---

## 보고

- 0번 게이트 결과(파일별 현황 + 제안한 슬롯/시그니처/매핑).
- 변경/신규 파일 목록, `tsc`·`npm run build` 결과.
- 10개 E2E 케이스 결과(스크린샷 권장: 4·5·9·10).
- 콘솔 에러 0 확인.
- 비정상 동작·설계 위반 의심 발견 시 즉시 보고(예: ResultView analysis mock으로 인한 부작용, Firestore 권한 거부, lastDiagnosis 메타 누락 식물 발견 등).

`eval/`·`data/`·백엔드·`SaveDiagnosisModal`·`AuthControl`·`CareGuideView` 코드 add 금지. mock 데이터 커밋 금지.

---

## 7. 주의

- **R4 정책 유지**: 탭바는 home·myPlants에만 표시. loading/result/care/timeline은 미표시.
- **fresh/history 격리**: history 모드 진입 시 `result` state는 건드리지 말 것(신규 진단 데이터 보존). 별도 `historyDiagnosis` state로 격리.
- **analysis mock 부작용 주의**: ResultView 외 다른 곳에서 `analysis`를 사용하면 mock이 새는 위험. 본 라운드 history 변환은 ResultView 입력 전용으로만 사용(외부 노출 금지).
- **N+1 쿼리**: 식물 수가 크게 늘면 listPlants 지연 가능. 향후 denormalized로 최적화 여지 메모(본 라운드는 무리 없음).
- **Firebase 권한**: owner-only 규칙 게시 완료. 본인 데이터 외 접근 시도하면 거부됨 — 정상 동작.
- **Firestore 명명 DB**: `plant-diagnosis` (NOT `(default)`). `lib/firebase.ts` 핫픽스로 처리됨. 본 라운드에서 손대지 말 것.
- **명명 정합 변경(`main_rag`) 금지**: B-2 보류 중. 본 라운드와 무관.
- **eval/baseline.json 절대 손대지 말 것**.
- **다음 라운드(3단계)**: FastAPI `/compare` 엔드포인트 + 타임라인의 "이전 진단과 비교" UI. 정성 비교 서술만(가짜 정량 금지).
