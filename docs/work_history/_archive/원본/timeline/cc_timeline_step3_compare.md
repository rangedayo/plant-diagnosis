# [시계열 3단계] 진단 비교 — `/compare` 엔드포인트 + 타임라인 비교 UI

## 참조
- 설계 정본: `docs/design/design_timeline_firebase.md` §5 "비교 기능". 본 라운드는 그 §5의 개요에 아래 §1 확정 디테일을 더해 구현.
- 이전 작업: 1단계 인증·2-A 쓰기·2-B 읽기 UI·1단계 후속 인증 위생 — 모두 완료/푸시됨.
- 본 작업 = 시계열 Slice 2 (마지막 슬라이스). 이후 정확도 트랙(라벨 구축 등)으로 진입 예정.

---

## 1. 확정 디테일 (본 라운드 합의 사항)

### 비교 대상 선택
- **"직전 vs 이번" 단순 비교**. 임의 2건 선택 모드는 미도입(v2 백로그).
- 타임라인 진단 카드에서 "이전 진단과 비교" 버튼 진입 → 그 카드(=current)와 한 칸 더 오래된 카드(=previous)를 비교.
- 가장 오래된 진단(타임라인 최하단)엔 비교 대상 없음 → **버튼 자체 숨김**.

### 결과 표시
- **모달**. 새 Screen 추가 없음(상태머신 무변경). 진단 결과 저장 모달(`SaveDiagnosisModal`)과 유사한 오버레이 패턴 재사용.

### 인증
- **무인증** (`/diagnose`와 동일 정책). Firebase Admin SDK·토큰 검증 도입 없음.
- 권한 보호는 Firestore 규칙이 담당(본인 데이터만 읽기 가능 → 본인 진단의 content만 페이로드로 백엔드에 전달됨).
- `/diagnose`·`/compare` 동시 인증화는 별도 백로그.

### LLM
- **GPT-4o-mini**. 텍스트 전용 비교에 적합·한국어 자연어 강함·저렴. 케어 가이드 생성에 쓰는 기존 클라이언트 재사용.

### 입력 페이로드 구조
프론트가 Firestore에서 읽은 두 `DiagnosisRecord`의 정성 필드만 백엔드에 전달:
- `previous`·`current` 각각: `date`(ISO 문자열)·`status`·`summary`·`current_state`·`cause`·`action_plan[]`·`observed_symptoms[]`.
- 이미지 URL·식물 이름 미전달(텍스트 전용 비교, 비전 안 씀).

### 출력 응답 구조
- 단일 필드 `comparison: string` — 한국어 자연어 비교 서술.
- 구조화 필드(delta_status 등)는 첫 컷 미도입(v2 여지).

### 하드 제약 (LLM 프롬프트에 명시)
- **정량·수치 신설 절대 금지** — "잎 면적 12% 증가", "성장률 30%" 같은 가짜 수치 금지. 두 진단 텍스트에 명시되지 않은 숫자 생성 금지.
- status·summary·observed_symptoms·cause의 **질적 변화만** 서술.
- 변화가 미미하면 솔직히 **"큰 변화 없음"** 으로.
- 의학적 단정·과장 금지 — "완치", "악화 확정", "치명적" 같은 단정 표현 피하기.
- 한국어 2~4문장 자연스러운 서술. 짧은 케어 조언 1문장 선택적 추가 가능.

### UI 진입점
- `TimelineView`의 진단 카드 우측 하단(또는 카드 내부 보조 영역)에 작은 텍스트 버튼 "이전 진단과 비교".
- 카드 본체 클릭은 기존대로 history result 진입 — 비교 버튼은 별도 클릭 핸들러(이벤트 버블링 차단).
- 가장 오래된 카드만 버튼 숨김.

### 에러 핸들링
- LLM 실패·네트워크 에러 시 모달 내부에 "비교 결과를 가져오지 못했어요. 잠시 후 다시 시도해주세요" 표시.
- 캐싱 미도입 — 같은 두 진단 다시 비교 요청하면 LLM 재호출.

---

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)

변경 전 다음을 view로 확인하고 보고:

1. **`app/main.py` (또는 라우터 분할 구조)** — `/diagnose` 라우트 등록 방식·현 라우터 구성. `/compare`를 어디에 어떻게 추가할지 제안(권장: 별도 라우터 파일 `app/routers/compare.py` 또는 main에 직접 추가, 프로젝트 관례에 따름).
2. **GPT-4o-mini 호출 코드** — 케어 가이드 생성에 쓰는 OpenAI 클라이언트 위치·환경변수(`OPENAI_API_KEY` 등)·호출 패턴. 재사용 가능한 함수 추출 가능 여부 보고.
3. **`app/schemas.py` (또는 동등 파일)** — Pydantic 모델 추가 위치 제안 (`CompareRequest`·`DiagnosisSnapshot`·`CompareResponse`).
4. **`lib/api.ts`** — `diagnosePlant` 호출 패턴. `comparePlantDiagnoses` 추가 위치·시그니처 제안.
5. **`components/TimelineView.tsx`** — 진단 카드 JSX 구조. 비교 버튼 삽입 위치 + 이벤트 버블링 차단 방법(예: `e.stopPropagation()` 추가) 제안.
6. **`components/SaveDiagnosisModal.tsx`** — 모달 스타일·오버레이 패턴 참조용. `CompareModal`을 동일 톤으로 작성하기 위한 공통 패턴 추출 가능 여부(첫 컷은 공통 추출 없이 개별 작성 권장).
7. **`types/diagnosis.ts` / `lib/db.ts`** — `DiagnosisRecord` 필드 확인 + 백엔드 페이로드 매핑 일치성.

보고 후 진행.

---

## 2. 범위 (이번 라운드만)

### 백엔드 (FastAPI)
- `/compare` POST 엔드포인트 신설. 입력 = 두 진단 snapshot, 출력 = `comparison: str`.
- 비교 전용 GPT-4o-mini 호출 함수 + 프롬프트 빌더 신설.
- 케어 가이드 LLM 호출 코드 무변경(재사용만).

### 프론트엔드
- `lib/api.ts`에 `comparePlantDiagnoses(prev, curr)` 추가.
- `components/CompareModal.tsx` 신규 — 로딩/결과/에러 상태 + 닫기.
- `components/TimelineView.tsx` 확장 — 진단 카드에 비교 버튼 + 클릭 핸들러 + 모달 상태 관리.

### 불변
- `/diagnose`·진단 파이프라인·Gemini 비전 분석 무변경.
- 시계열 기존 코드(`lib/db.ts`·`lib/historyAdapter.ts`·`MyPlantsView`·`ResultView`·`pages/index.tsx` 등) 무변경. 단 `TimelineView`는 본 라운드에서 변경.
- `eval/baseline.json`·측정 인프라 무변경.
- 새 Screen 추가 없음.

---

## 3. 작업

### 3.1 백엔드 — `/compare` 엔드포인트

#### 3.1.1 Pydantic 스키마

`app/schemas.py` (또는 동등 위치):

```python
class DiagnosisSnapshot(BaseModel):
    date: str               # ISO 날짜 문자열 (프론트 전달)
    status: str
    summary: str
    current_state: str
    cause: str
    action_plan: list[str]
    observed_symptoms: list[str]

class CompareRequest(BaseModel):
    previous: DiagnosisSnapshot
    current: DiagnosisSnapshot

class CompareResponse(BaseModel):
    comparison: str
```

#### 3.1.2 LLM 호출 함수

기존 GPT-4o-mini 클라이언트 재사용. 비교 전용 함수 신설 (위치는 §0-2 보고 따라):

```python
def generate_comparison(prev: DiagnosisSnapshot, curr: DiagnosisSnapshot) -> str:
    """두 진단 snapshot을 받아 정성 비교 서술을 생성."""
    prompt = build_compare_prompt(prev, curr)
    # 기존 OpenAI 클라이언트로 GPT-4o-mini 호출
    # system + user 메시지 패턴, temperature 0.3~0.5 권장(과장 억제)
    # 응답 텍스트 그대로 반환
```

#### 3.1.3 비교 프롬프트 (build_compare_prompt)

골격(CC가 최종 다듬기):

```
[system]
당신은 식물 진단 비교 분석가입니다. 동일한 식물의 두 시점 진단 결과를 받아
정성적 변화만 객관적으로 서술합니다.

[user]
다음은 같은 식물의 직전 진단과 이번 진단입니다.

【직전 진단 — {prev.date}】
- 상태: {prev.status}
- 요약: {prev.summary}
- 현재 상태 서술: {prev.current_state}
- 원인: {prev.cause}
- 관찰된 증상: {prev.observed_symptoms (쉼표 구분, 없으면 "특이사항 없음")}

【이번 진단 — {curr.date}】
- 상태: {curr.status}
- 요약: {curr.summary}
- 현재 상태 서술: {curr.current_state}
- 원인: {curr.cause}
- 관찰된 증상: {curr.observed_symptoms}

다음 규칙을 엄격히 지켜 비교 서술을 작성하세요.

규칙:
1. 두 진단에 명시되지 않은 정량 수치(예: "잎 면적 12% 증가", "성장 30%")를 절대 만들어내지 마세요. 가짜 수치 생성 금지.
2. status·요약·증상·원인의 질적 변화만 서술하세요.
3. 변화가 미미하면 솔직히 "큰 변화 없음"이라고 쓰세요. 억지로 변화를 만들지 마세요.
4. "완치", "악화 확정", "치명적" 같은 의학적 단정·과장 표현 금지.
5. 한국어 2~4문장으로 자연스럽게.
6. 끝에 짧은 케어 조언 1문장 추가 가능(선택).
```

#### 3.1.4 라우트

```python
@router.post("/compare", response_model=CompareResponse)
def compare_diagnoses(req: CompareRequest) -> CompareResponse:
    comparison = generate_comparison(req.previous, req.current)
    return CompareResponse(comparison=comparison)
```

CORS 설정·앱 등록은 기존 `/diagnose`와 동일 정책(중복 설정 회피).

#### 3.1.5 에러 처리
- OpenAI API 실패 → `HTTPException(status_code=502, detail="LLM 호출 실패")`.
- 입력 검증 실패 → Pydantic 422 자동.

---

### 3.2 프론트 — API 클라이언트

`lib/api.ts`에 추가:

```typescript
export type DiagnosisSnapshot = {
  date: string;
  status: string;
  summary: string;
  current_state: string;
  cause: string;
  action_plan: string[];
  observed_symptoms: string[];
};

export type CompareResponse = {
  comparison: string;
};

export async function comparePlantDiagnoses(
  previous: DiagnosisSnapshot,
  current: DiagnosisSnapshot,
): Promise<CompareResponse>;
```

`diagnosePlant`와 동일한 base URL·에러 패턴 사용. 단순 fetch POST.

---

### 3.3 프론트 — `components/CompareModal.tsx` 신규

#### Props
```ts
type Props = {
  previous: DiagnosisRecord;  // 직전 진단
  current: DiagnosisRecord;   // 이번 진단
  onClose: () => void;
};
```

#### 동작
- `useEffect`로 마운트 시 `comparePlantDiagnoses` 호출.
- 상태: `loading` | `success(text)` | `error(message)`.
- 페이로드 변환: `DiagnosisRecord` → `DiagnosisSnapshot`.
  - `date` ← `createdAt?.toISOString() ?? ""`.
  - 나머지 필드는 동일명/camelCase→snake_case 매핑.

#### UI
- 오버레이 + 시트(SaveDiagnosisModal 패턴 재사용 — 디자인 시트 토큰).
- 헤더: "진단 비교" + X 닫기.
- 상단 메타: 두 진단의 날짜·status 배지 한 줄씩 작게.
- 본문:
  - loading → "비교 분석 중…" 스피너/문구.
  - success → `comparison` 텍스트(줄바꿈 보존, `white-space: pre-wrap`).
  - error → 에러 카드 + "다시 시도" 버튼(다시 호출).
- 하단: "닫기" 버튼 1개.

#### 스타일
- `styled-jsx scoped`. `globals.css` `var(--*)` 토큰.

---

### 3.4 프론트 — `components/TimelineView.tsx` 확장

#### 추가 요소
1. 진단 카드 우측 하단(또는 카드 내부 보조 영역)에 작은 텍스트 버튼 "이전 진단과 비교".
2. **가장 오래된 카드(`records[records.length - 1]`)에서는 버튼 숨김** — 비교 대상 없음.
3. 버튼 클릭 시 `e.stopPropagation()` 호출(카드 본체 클릭=ResultView 진입과 격리).
4. 모달 상태 관리:
   ```ts
   const [compareTarget, setCompareTarget] = useState<{
     previous: DiagnosisRecord;
     current: DiagnosisRecord;
   } | null>(null);
   ```
5. 비교 버튼 클릭 → `setCompareTarget({ previous: records[i+1], current: records[i] })`.
6. `compareTarget !== null` → `<CompareModal>` 렌더.

#### 인덱싱 주의
- `records`는 `orderBy("createdAt","desc")` → **최신순**.
- 인덱스 `i`(current) vs `i+1`(previous, 한 칸 더 오래된 것).
- `i === records.length - 1`이면 버튼 숨김.

#### 스타일
- 비교 버튼: 작은 텍스트 링크 톤(예: 14px green-medium, underline 또는 dashed). 디자인 시트 토큰 활용. 카드 본체 호버와 시각적으로 격리되게.

---

## 4. 제약 (불변)

- `/diagnose`·`app/main.py`의 기존 라우트·진단 파이프라인·Gemini 호출 무변경.
- `eval/`·`data/`·`scripts/`·`eval/baseline.json` 무변경.
- 가짜 정량/수치 신설 금지(LLM 프롬프트에 명시 + 코드상 후처리 검증은 미도입, 첫 컷은 프롬프트 신뢰).
- 새 Screen 추가 없음. `pages/index.tsx`·상태머신·`ResultView`·`MyPlantsView`·`CareGuideView`·`SaveDiagnosisModal` 코드 무변경.
- `lib/db.ts`·`lib/historyAdapter.ts` 무변경.
- Firebase Admin SDK·토큰 인증 도입 금지(별건).
- 캐싱·구조화 비교 필드(delta_status 등) 도입 금지(v2).
- 명명 정합 변경(`main_rag` 등) 금지(B-2 보류 중).

---

## 5. 검증

### 5.1 정적
- **백엔드**: `python -m pytest`(있으면) 또는 `python -c "from app.main import app"` 임포트 체크. uvicorn 실행 가능 여부.
- **프론트**: `npx tsc --noEmit` 통과 + `npm run build` 성공.

### 5.2 수동 E2E (사용자 PowerShell — LLM 과금 발생)

전제: Firestore에 같은 식물의 진단 ≥2건 보유.

1. **백엔드 띄우기** — `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
2. **프론트** — `npm run build && npm run start`.
3. **케이스 A — 정상 비교**:
   - 로그인 → 내 식물 → 식물 선택 → 타임라인 진입.
   - 타임라인 상단(최신) 진단 카드 우측 하단 "이전 진단과 비교" 버튼 클릭(가장 오래된 카드 제외 모든 카드에서 표시되어야).
   - 모달 오픈 → 로딩 → 비교 서술 표시(2~4문장 한국어, 가짜 수치 없음 시각 확인).
   - 닫기 → 타임라인 복귀.
4. **케이스 B — 가장 오래된 카드**:
   - 가장 오래된(타임라인 최하단) 진단 카드에 비교 버튼이 **표시되지 않아야 함**.
5. **케이스 C — 카드 본체 클릭 격리**:
   - 비교 버튼이 아닌 카드 본체 클릭 → ResultView(history) 진입 정상.
   - 비교 버튼 클릭 → 모달만 열림, ResultView로 이동하지 않아야.
6. **케이스 D — 에러 처리**:
   - 백엔드 끄기 → 비교 버튼 클릭 → 모달에 에러 메시지 + "다시 시도" 버튼 표시.
   - 백엔드 켜고 "다시 시도" → 정상 결과.
7. **케이스 E — 회귀**:
   - 기존 흐름(저장·history result·care·fresh 진단) 콘솔 에러 0, 동작 무변경.

각 케이스 결과(스크린샷 권장: A·B·D) + 콘솔 에러 0 확인.

### 5.3 LLM 출력 품질 점검 (사용자)
케이스 A에서 받은 비교 서술을 시각 확인:
- 가짜 수치(N%·N센티미터·N개월 등) 없음.
- 변화 명백할 땐 변화 짚고, 미미하면 "큰 변화 없음" 솔직히.
- 의학적 단정/과장 없음.
- 자연스러운 한국어.

문제 시 프롬프트 후속 튜닝 라운드 가능.

---

## 6. 커밋 (분리·푸시 보류)

- `docs:` — 본 프롬프트(`docs/work_history/cc_timeline_step3_compare.md`).
- `feat:` — 코드 변경:
  - 백엔드: `app/schemas.py`(+ `app/routers/compare.py` 또는 `app/main.py`), 프롬프트/호출 함수.
  - 프론트: `lib/api.ts`, `components/CompareModal.tsx`, `components/TimelineView.tsx`.

커밋 메시지 안(사용자 확정 후):
```
feat: [시계열 3단계] 진단 비교 — /compare 엔드포인트 + 타임라인 비교 UI

- 백엔드: FastAPI /compare 신설. 두 진단 snapshot(status·summary·
  current_state·cause·action_plan·observed_symptoms·date) 입력 → GPT-4o-mini로
  정성 비교 서술 생성. 프롬프트에 가짜 수치 금지·변화 미미 시 솔직 서술·
  의학적 단정 금지 룰 명시. /diagnose·진단 파이프라인 무변경.
- 프론트: lib/api.ts에 comparePlantDiagnoses 추가. CompareModal 신규
  (로딩/결과/에러 + 다시 시도). TimelineView 진단 카드에 "이전 진단과 비교"
  작은 버튼 추가, 가장 오래된 카드는 숨김, 카드 본체 클릭과 이벤트 격리.
- 인증·캐싱·구조화 비교 필드는 별건 백로그.

범위: 비교 기능 첫 컷. 시계열 Slice 2 완료.
```

---

## 보고

- 0번 게이트 결과(7개 항목별 현황·시그니처·매핑 제안).
- 변경 파일 목록, 정적 검증 결과.
- 사용자 수동 E2E 진행 가이드 명시(LLM 과금 영역, CC 자동화 불가).
- LLM 응답 품질 첫 인상 — 합성 입력으로 한 번 호출해본 결과가 있으면 공유(선택).

`eval/`·`data/`·`scripts/`·`/diagnose` 관련 코드·시계열 기존 컴포넌트 add 금지. mock 데이터 커밋 금지.

---

## 7. 주의

- **LLM 호출 비용**: 비교 1회 = GPT-4o-mini 호출 1회. 캐싱 없음 → 같은 비교 누를 때마다 재호출. 사용자 검증 시 과도한 클릭 자제.
- **프롬프트 신뢰 첫 컷**: 가짜 수치 검출 후처리(예: 정규식으로 N% 패턴 차단) 미도입. LLM이 규칙 어기면 프롬프트 튜닝 후속 라운드.
- **이벤트 버블링**: 비교 버튼 `e.stopPropagation()` 필수. 카드 본체 onClick과 격리되지 않으면 비교 + ResultView 동시 트리거 버그.
- **인덱싱**: records[0]이 가장 최신. previous = records[i+1], current = records[i]. 헷갈리면 변수명 명확히.
- **모달 z-index**: SaveDiagnosisModal과 동시 열릴 일 없지만(다른 화면) 안전한 z 값 사용.
- **eval/baseline.json 절대 손대지 말 것**.
- **명명 정합 변경(`main_rag`) 금지**: B-2 보류 중.
- **다음 작업**: 시계열 Slice 2 완료로 시계열 기능 종료. 이후는 정확도 트랙(라벨 구축·FP/FN 측정·가드 튜닝) 또는 인증 통합(별건).
