# [시계열 2-A] 영속화 — 쓰기 경로 (진단 저장)

## 참조
- 설계 정본: `docs/design/design_timeline_firebase.md` (§3 데이터 모델, §4 저장 흐름). 본 작업 = 그 문서 Slice 1의 **쓰기 경로만**(데이터 레이어 + 저장 흐름). **읽기 UI(내 식물·타임라인)는 2-B, 비교(`/compare`)는 3단계.**
- 전제: 1단계(인증) 완료 — `lib/firebase.ts`(auth·db·storage export), `useAuth()` 사용 가능. Firestore·Storage 생성 및 owner-only 규칙 배포 완료.

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)
변경 전 확인·보고:
1. 결과 화면 컴포넌트(진단 `structured_result`를 렌더하는 곳) — "저장" 버튼 붙일 위치 제안.
2. **원본 이미지 File/blob이 결과 단계에서 접근 가능한지** ← 핵심. Storage 업로드에 필요. 진단 전송 후 File을 버린다면, 저장용으로 보관할 방법 제안(예: 결과 상태에 File 또는 dataURL 유지).
3. `lib/firebase.ts`의 `db`·`storage` export 존재 + `useAuth()`로 로그인/uid 접근 가능 확인.
4. 현재 `structured_result`의 실제 필드명/형태 → Firestore diagnoses 문서 필드(설계 §3)로의 **매핑표** 보고(예: `current_state`→`currentState`, `action_plan`→`actionPlan`). 불일치 시 제안.
보고 후 진행.

## 1. 범위 (이번 라운드만)
Firestore·Storage 데이터 레이어 + 결과 화면 "저장" 흐름(식물 선택/생성 → 이미지 업로드 + 진단 문서 기록). **새 화면(내 식물·타임라인) 추가 없음 — 2-B. 저장은 모달/오버레이로.**

## 2. 작업
- `lib/db.ts`(또는 적절한 이름): 타입드 데이터 레이어
  - `listPlants(uid)` → 픽커용 간단 목록.
  - `createPlant(uid, {name, speciesKey|null, coverImageUrl|null})` → plantId.
  - `saveDiagnosis(uid, plantId, {imageFile, result})`:
    1. dxId 생성(Firestore auto-id 권장).
    2. 이미지 File을 Storage `users/{uid}/plants/{plantId}/{dxId}.jpg` 업로드 → downloadURL.
    3. diagnoses 문서 기록 — 설계 §3 필드: `createdAt`(serverTimestamp)·`imageUrl`·`status`·`isHealthy`·`summary`·`currentState`·`cause`·`actionPlan[]`·`careGuide`·`observedSymptoms[]`.
    4. 신규 식물이면 plant `coverImageUrl`를 이 이미지로 갱신.
- 저장 UI: 결과 화면에 **"이 식물 기록에 저장"** 버튼(0-1 제안 위치).
  - **미로그인이면 로그인 먼저**(`useAuth`, `signInWithPopup` 또는 로그인 유도).
  - 클릭 → 모달: 기존 식물 목록(`listPlants`) 선택 **또는** "새 식물 만들기"(별칭 입력 → `createPlant`).
  - 확정 → `saveDiagnosis` → 성공 피드백(토스트/메시지). 저장 후 화면 이동은 2-B 화면 생긴 뒤 — 지금은 "저장됨" 표시까지.

## 3. 제약 (불변)
- `/diagnose`·`lib/api.ts`·FastAPI·`scripts/`·`eval/baseline.json` 무변경.
- R5/R6 UI·상태머신 구조 보존(이번 라운드 새 Screen 추가 없음, 모달만).
- `current_state`·care 필드 타입 유지(백엔드 호환). Firestore 필드는 camelCase 매핑(0-4 매핑표대로).
- 가짜 정량/숫자 신설 금지(진단 원본 값 그대로 저장).

## 4. 검증
- `tsc` 통과 + `npm run build` 성공(필요 시 `.next` 정리).
- 수동 E2E: 로그인 → 진단 1건 → "저장" → 새 식물 생성 → 저장 성공.
- **Firebase 콘솔 확인**(읽기 UI 없으니 이게 검증 수단):
  - Firestore에 `users/{uid}/plants/{plantId}/diagnoses/{dxId}` 문서가 올바른 필드로 생성.
  - Storage에 해당 경로로 이미지 업로드됨.

## 5. 커밋 (분리·푸시 보류)
- `docs:` — 본 프롬프트(`docs/work_history/...md`).
- `feat:` — 데이터 레이어 + 저장 흐름(코드).

## 보고
- 0번 게이트 결과(저장 버튼 위치·이미지 File 보관 방식·필드 매핑표).
- 변경 파일, `tsc`·빌드 결과, 콘솔에서 확인한 저장 문서/이미지 경로(또는 스크린샷).
