# [시계열 1단계] Firebase 배선 + Google 인증 (파운데이션)

## 참조
- 설계 정본: `docs/design/design_timeline_firebase.md` (이 라운드 전에 `docs:`로 커밋됨). 본 작업 = 그 문서의 **Slice 0 + Slice 1의 "인증/배선" 부분만**. 영속화(저장 흐름·이력 UI)와 비교(`/compare`)는 다음 라운드.
- 확정: 인증 = **Google 로그인 단독**. 분담 = Firebase(인증·이력·이미지) / FastAPI(진단 불변 + 추후 `/compare`).

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)
변경 전 확인·보고:
- `pages/index.tsx` 상태머신(`Screen` 타입·전환)과 헤더 모델(R5: 전역 워드마크 없음, 화면별 네비 헤더). **로그인 상태/진입점을 어디에 붙일지 제안**(R5 정합 유지).
- `lib/api.ts`(diagnose 경로) — 이번 라운드 무변경 확인.
- `package.json`에 `firebase` SDK 설치 여부. 없으면 "설치 필요"라고 보고(설치는 사용자 PowerShell `npm i firebase`).
- `.env.local`에 `NEXT_PUBLIC_FIREBASE_*` 존재 여부(사용자가 콘솔 web config로 채워넣을 예정).
보고 후 진행.

## 1. 범위 (이번 라운드만)
Firebase 초기화 + Google 로그인/로그아웃/auth 상태 + 보안규칙 파일. **영속화·이력 UI는 없음.**

## 2. 작업
- `lib/firebase.ts`: `NEXT_PUBLIC_FIREBASE_*` env로 app/auth/firestore/storage 초기화. **중복 init 가드**(`getApps().length`) — Fast Refresh/SSR 안전.
- 인증: `GoogleAuthProvider` + `signInWithPopup` 로그인, `signOut`, `onAuthStateChanged` 구독. React `AuthProvider` context + `useAuth()` 훅으로 노출. `_app.tsx`에 Provider 주입.
- UI: 로그인/로그아웃 진입점(0번 게이트 제안 위치, **R5 헤더 모델 존중 — 전역 워드마크 부활 금지**). 로그인 시 사용자(이름/아바타)+로그아웃, 미로그인 시 "Google로 로그인".
- 보안규칙 파일(배포는 사용자): `firestore.rules`·`storage.rules` — `users/{uid}/**` 본인만 read/write, 그 외 차단. 데이터 모델은 설계 §3 기준.
- `.env.local.example`에 `NEXT_PUBLIC_FIREBASE_*` 키 목록만(값 없이).

## 3. 제약 (불변)
- `/diagnose` 경로·FastAPI·`scripts/`·`eval/baseline.json`·측정 인프라 무변경.
- R5/R6 확정 UI 깨지 않기. `current_state`·미사용 care 필드 타입 유지(백엔드 호환).
- Firebase config 키 하드코딩 금지(전부 env).

## 4. 검증
- `tsc` 통과.
- **prod 빌드로 확인**(`npm run build && npm run start`) — Next16 Turbopack dev 풀리로드 루프 회피. 의심 시 `.next` 삭제 후 재시작.
- 수동: Google 로그인 → 사용자 표시 → 로그아웃. (콘솔 설정·`.env.local`이 채워진 상태 전제. 미충족이면 거기까지만 배선하고 보고.)

## 5. 커밋 (분리·푸시는 검토 후)
- `docs:` — 본 프롬프트(`docs/work_history/...md`). 설계 문서 `docs:` 커밋이 선행돼 있어야 함.
- `feat:` — Firebase 배선 + Google 인증(코드) + 규칙 파일.

## 보고
- 0번 게이트 결과(상태머신·헤더·SDK/env 현황 + 로그인 진입점 제안).
- 변경 파일 목록, `tsc`·빌드 결과, 수동 로그인 검증 결과.
