# [시계열 1단계 후속] Google 로그인 콘솔 위생 fix

## 참조
- 본 작업 = **1단계(인증) 후속 fix 미니 라운드**. 2-B 검증 중 노출된 잠재 이슈 처리.
- 범위: 두 가지 콘솔 에러만 정리. 인증 동작·UX 변경 없음.

## 발견된 콘솔 에러 (2-B 수동 E2E 중 노출)

### 에러 1 — `FirebaseError: Firebase: Error (auth/cancelled-popup-request)`
- 발생 조건: 로그인 팝업이 떠 있는 동안 또 로그인 트리거(중복 클릭, 헤더 + 카드 버튼 둘 다 클릭 등) → 이전 팝업의 promise가 cancel되며 reject.
- 영향: 실제 로그인은 정상 완료. 잡히지 않은 promise rejection이 콘솔에 빨간 에러로 남음.
- 비고: AuthControl + MyPlantsView 로그인 카드처럼 화면에 로그인 진입점이 둘 이상일 때 트리거 쉬움.

### 에러 2 — `Cross-Origin-Opener-Policy policy would block the window.closed / window.close call`
- 발생 조건: Chrome의 COOP 정책이 기본 strict에서 Firebase Auth `signInWithPopup`이 팝업 창 상태 체크할 때 발생.
- 영향: Firebase SDK가 자체적으로 우회 처리 — 실제 로그인 동작에 영향 없음. 콘솔에 경고만 남음.
- 알려진 fix: 응답 헤더 `Cross-Origin-Opener-Policy: same-origin-allow-popups` 추가.

---

## 0. Read-only 선결 게이트 (먼저 보고, 불일치 시 중단)

변경 전 다음을 view로 확인하고 보고:

1. **`lib/auth.tsx`** — `signInWithGoogle`·`signOut` 현 구조. try-catch 추가 위치 제안 + 에러 분기 방식(권장: `FirebaseError` import 후 `error.code === "auth/cancelled-popup-request"`만 silent, 그 외 throw).
2. **`next.config.js`(또는 `.ts`/`.mjs`)** 존재 여부 + 현 `headers()` 함수 유무. 없으면 신설 제안.
3. **`signInWithGoogle` 호출처 전수 확인** — `AuthControl.tsx`·`MyPlantsView.tsx`·기타. 호출 측에서 `await`·`.catch()` 사용 패턴 점검. silent 처리로 인해 호출 측 의도가 깨지는 곳 있는지(예: 호출 측이 promise 결과로 후속 동작 결정하는 경우 — 현재 코드상 그런 패턴 없을 것으로 추정).
4. **다른 Firebase Auth 에러 코드 처리 정책 확인** — `auth/popup-blocked`(팝업 차단)·`auth/popup-closed-by-user`(사용자가 팝업 닫음) 등도 silent 후보일 수 있음. 다만 본 라운드는 `cancelled-popup-request` 단일 처리만 (다른 에러는 사용자가 봐야 할 정보일 수 있어 보수적).

보고 후 진행.

---

## 1. 범위 (이번 라운드만)

- `lib/auth.tsx` `signInWithGoogle`에 try-catch — `auth/cancelled-popup-request`만 silent, 그 외 에러는 그대로 throw.
- `next.config.js`에 `Cross-Origin-Opener-Policy: same-origin-allow-popups` 헤더 추가.
- **불변**: 인증 UX·로그인 버튼 위치·AuthControl/MyPlantsView 디자인 무변경. 다른 Firebase Auth 에러 코드 처리 미도입(별건). 시계열·진단·eval 무관.

---

## 2. 작업

### 2.1 `lib/auth.tsx` — `signInWithGoogle` 가드

권장 패턴:

```ts
import { FirebaseError } from "firebase/app";
// ... 기존 import

signInWithGoogle: async () => {
  const provider = new GoogleAuthProvider();
  try {
    await signInWithPopup(auth, provider);
  } catch (err) {
    // 중복 클릭/연속 호출로 이전 팝업이 cancel된 경우 — 정상 동작의 부산물이라 silent.
    // 다른 모든 에러는 호출 측이 처리할 수 있게 그대로 throw.
    if (err instanceof FirebaseError && err.code === "auth/cancelled-popup-request") {
      return;
    }
    throw err;
  }
},
```

- `signOut`은 변경 없음.
- console.log/warn 추가 금지 (조용히 무시).
- `FirebaseError` import 경로는 `firebase/app` (SDK v10+).

### 2.2 `next.config.js` — COOP 헤더

현재 `next.config.js`(또는 `.ts`/`.mjs`)에 `headers()` 함수가 없다면 신설, 있으면 확장. 모든 경로에 적용:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // ... 기존 설정 유지
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

- 기존 `headers()`가 있으면 배열에 본 항목 추가 (덮어쓰기 금지).
- `Cross-Origin-Embedder-Policy`는 추가하지 말 것 — Firebase 외부 리소스(아바타 이미지 등)와 충돌 가능성.
- `same-origin-allow-popups`가 정확한 값. `same-origin`은 너무 strict해서 동일 문제 재발.

---

## 3. 제약 (불변)

- `/diagnose`·FastAPI·`scripts/`·`eval/baseline.json` 무변경.
- 2-A·2-B 코드(`lib/db.ts`·`historyAdapter`·`MyPlantsView`·`TimelineView`·`SaveDiagnosisModal` 등) 무변경.
- AuthControl/MyPlantsView 로그인 카드의 위치·디자인·UX 무변경 (로그인 진입점 2개 유지).
- 인증 흐름 변경 없음 — 단지 콘솔 위생만.
- 명명 정합 변경(`main_rag` 등) 금지(B-2 보류 중).
- 다른 Firebase Auth 에러 코드(`auth/popup-blocked` 등) 처리 도입 금지 — 별건.

---

## 4. 검증

### 4.1 정적
- `npx tsc --noEmit` 통과.
- `npm run build` 성공.

### 4.2 수동 (prod 빌드로 — `npm run start`)

1. **에러 1 fix 검증** — 로그아웃 상태에서 "내 식물" 탭 진입 → 로그인 유도 카드 노출 → **헤더 "로그인" 버튼 + 카드 "Google로 로그인" 버튼을 빠르게 연속 클릭** (또는 한 버튼을 빠르게 2~3번 클릭) → 콘솔에 `cancelled-popup-request` 에러가 **표시되지 않아야 함**. 정상 로그인은 한 팝업만 떠서 완료되어야.
2. **에러 2 fix 검증** — 정상적으로 한 번만 로그인 클릭 → 팝업 → 로그인 → 콘솔에 COOP `would block the window.close` 경고가 **표시되지 않아야 함**.
3. **다른 에러는 그대로 노출되는지 확인** (보수성 체크) — (선택, 어려움) 의도적으로 팝업을 사용자가 닫아본 후 콘솔에 `auth/popup-closed-by-user` 같은 다른 에러가 그대로 표시되는지 확인. silent 범위가 `cancelled-popup-request` 단일에 한정됐는지.
4. **2-B 흐름 무영향** (regression) — 로그인 → 내 식물 → 식물 선택 → 타임라인 → 진단 상세 → 케어 → 뒤로. 한 흐름 관통 + 콘솔 에러 0.
5. **fresh 흐름 무영향** — 진단 → 저장 → 토스트. 콘솔 에러 0.

각 케이스 결과 + 콘솔 스크린샷(있으면) 보고.

---

## 5. 커밋 (분리·푸시 보류)

- `docs:` — 본 프롬프트(`docs/work_history/cc_timeline_step1_followup_auth_hygiene.md`).
- `fix:` — 코드 변경:
  - `lib/auth.tsx`
  - `next.config.js` (또는 `.ts`/`.mjs`)

커밋 메시지 안(사용자 확정 후):
```
fix: [시계열 1단계 후속] Google 로그인 콘솔 위생

- lib/auth.tsx: signInWithGoogle에 try-catch. auth/cancelled-popup-request
  (중복 클릭/연속 호출로 이전 팝업이 cancel되는 케이스)만 silent로 처리,
  그 외 FirebaseError는 그대로 throw. 정상 동작에 영향 없는 잡히지 않은
  promise rejection 제거.
- next.config.js: Cross-Origin-Opener-Policy: same-origin-allow-popups 헤더
  추가. Firebase Auth signInWithPopup의 window.close/closed 호출이 COOP
  strict 정책에 의해 차단되며 발생하던 콘솔 경고 제거 (실 동작 영향 없던 알려진 이슈).

범위: 콘솔 위생만. 인증 UX·로그인 진입점·흐름 무변경. 시계열·진단 무관.
2-B 검증 중 발견된 잠재 이슈, 1단계 인증 영역의 정리 작업.
```

---

## 보고

- 0번 게이트 결과(파일 현황 + 호출처 점검 결과 + 추가 silent 후보 에러 의견).
- 변경 파일 목록, `tsc`·`npm run build` 결과.
- 5개 검증 케이스 결과 + 콘솔 에러 0 확인.
- 의외 발견(예: 다른 Firebase 경고 동시 발견, COOP 헤더가 외부 리소스 로딩에 영향 등) 즉시 보고.

`eval/`·`data/`·백엔드·`lib/db.ts`·`lib/historyAdapter.ts`·시계열 신규 컴포넌트 코드 add 금지.

---

## 7. 주의

- **silent 범위 최소화**: `cancelled-popup-request` 단일만. 다른 인증 에러(`popup-blocked`·`popup-closed-by-user`·`network-request-failed` 등)는 사용자가 알아야 할 정보일 수 있으니 본 라운드 silent 대상 아님. 별건으로 검토.
- **COOP 헤더 정확한 값**: `same-origin-allow-popups`. `same-origin`만 쓰면 동일 문제 재발.
- **Cross-Origin-Embedder-Policy 추가 금지**: Firebase 콘솔 아바타(googleusercontent.com) 등 외부 리소스 로딩 깨질 위험.
- **2-B 검증 케이스 회귀 확인 필수**: 본 fix가 인증 흐름을 깨지 않는지 한 번 더.
- **명명 정합 변경(`main_rag`) 금지**: B-2 보류 중. 본 라운드와 무관.
- **eval/baseline.json 절대 손대지 말 것**.
- **다음 라운드(3단계)**: FastAPI `/compare` + 타임라인 비교 UI. 본 fix 완료 후 진입.
