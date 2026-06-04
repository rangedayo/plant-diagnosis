# 시계열(진단 이력) 기능 설계 — Firebase 기반 (DRAFT)

> 목적: 1차 정확도 작업을 데이터 트랙이 받쳐줄 때까지 보류하는 동안, **과거 진단을 저장·비교하는 시계열 기능**을 구축한다. 부수 효과로 실사용 진단(이미지+결과)이 서버에 쌓여 향후 데이터 트랙(라벨 확보)의 씨앗이 된다.

---

## 0. 하드 제약 (기존 데이터 범위 원칙 유지)

- 시계열 = **과거 진단들의 정성 비교**다. 예: "3주 전엔 병해 의심·잎끝 갈변 → 이번엔 건강·증상 호전."
- **토양습도%·일조량·성장% 등 측정/센서/정량 시계열 그래프는 영원히 금지.** 가짜 숫자 금지.
- 비교 출력은 status·증상·요약 텍스트의 **질적 변화 서술만**. 변화가 미미하면 "뚜렷한 변화 없음"이라고 말한다(없는 변화를 지어내지 않음).
- 미래/빈 데이터 UI는 조건부 렌더(이력 없으면 숨김). 더미 금지.

---

## 1. 아키텍처 — 백엔드 둘로 분담

```
[Next.js 프론트]
   │  진단 요청(이미지)            ┌───────────────────────────┐
   ├───────────────────────────▶ │ FastAPI (app/)            │
   │  ◀── structured_result ──────│  - /diagnose  (불변)       │
   │                              │  - /compare   (신규, 정성) │
   │                              └───────────────────────────┘
   │  로그인 / 이력 쓰기·읽기 / 이미지 업로드
   ▼
┌───────────────────────────────────────────┐
│ Firebase                                  │
│  - Auth      (Google 로그인)               │
│  - Firestore (진단 이력·식물 엔티티)        │
│  - Storage   (진단 이미지)                 │
└───────────────────────────────────────────┘
```

- **진단 자체는 변경 없음**: 프론트 → FastAPI `/diagnose` → `structured_result`+`care_guide` 반환(기존 그대로).
- **이력 쓰기·읽기는 프론트에서 Firebase SDK로 직접** 수행(Firestore + Storage). FastAPI는 저장에 관여하지 않음 → 진단 경로 무변경.
- **비교만 신규 FastAPI 엔드포인트** `/compare` (LLM 재사용). Firebase는 LLM을 안 거침.
- FastAPI가 사용자 신원을 알 필요는 MVP에선 없음(`/compare`는 프론트가 넘긴 두 결과를 변환할 뿐). Firebase ID 토큰 검증은 후속 하드닝으로.

---

## 2. 인증 (MVP)

- **Google 로그인** 단독으로 시작(비밀번호 관리 불필요, 1탭에 가까움).
- 미로그인 시 진단은 가능하되 **이력 저장은 로그인 유도**(저장 버튼에서 로그인 게이트).
- 후순위 옵션: 익명 로그인 → 나중에 Google 계정으로 업그레이드(이력 승계). MVP엔 미포함.

---

## 3. 데이터 모델 (Firestore)

소유자 격리: 모든 데이터는 `users/{uid}` 하위. 보안규칙으로 `request.auth.uid == uid`만 read/write.

```
users/{uid}
  plants/{plantId}
    name: string            # 사용자가 붙인 별칭 (예: "거실 행운목")
    speciesKey: string|null # 진단에서 매칭된 종 키(있으면)
    coverImageUrl: string|null
    createdAt: timestamp
    diagnoses/{dxId}
      createdAt: timestamp
      imageUrl: string            # Storage 다운로드 URL (또는 경로)
      status: string              # 5종 원값
      isHealthy: boolean
      summary: string
      currentState: string
      cause: string
      actionPlan: string[]        # ≥2
      careGuide: map|null
      observedSymptoms: string[]  # (가능하면, 비교 품질용)
```

- 식물 단위로 진단이 시간축에 쌓이는 구조 → 타임라인/비교에 자연스러움.
- Storage 경로 규약: `users/{uid}/plants/{plantId}/{dxId}.jpg`.

---

## 4. 진단 저장 흐름

1. 기존대로 진단 → 결과 화면.
2. 결과 화면 하단에 **"이 식물 기록에 저장"** (로그인 안 됐으면 로그인 먼저).
3. 모달: 기존 "내 식물" 선택 **또는** 새 식물 생성(별칭 입력).
4. 프론트가 (a) 원본 이미지 File을 **Storage 업로드**, (b) `structured_result`+메타를 **Firestore diagnoses에 기록**.
5. "내 식물" 목록 → 식물 선택 → **진단 타임라인**(최신순, 각 항목 썸네일·status·날짜).

---

## 5. 비교 기능 (`/compare`)

- FastAPI 신규 엔드포인트. 입력 = 같은 식물의 진단 2건(주로 직전 vs 이번)의 status·증상·요약 등. 출력 = **정성 비교 서술**.
- 프롬프트 제약(필수): status/증상/요약의 **질적 변화만** 서술. **정량·수치 신설 금지.** 변화가 약하면 솔직히 "큰 변화 없음". 의학적 단정·과장 금지.
- 프론트: 타임라인에서 "이전 진단과 비교" → 두 진단 doc을 Firestore에서 읽어 `/compare`에 전달 → 결과 표시.

---

## 6. 보안 규칙 (개요 — CC가 파일로 작성)

- Firestore: `users/{uid}/**` 는 본인(uid)만 read/write.
- Storage: `users/{uid}/**` 동일.
- 미인증 접근 전면 차단.

---

## 7. 구현 슬라이스

- **Slice 0 — 셋업**: (사용자) Firebase 프로젝트·Auth(Google)·Firestore·Storage 생성 + web config 발급. (CC) Next.js에 Firebase SDK 초기화·env 배선·보안규칙 파일 작성.
- **Slice 1 — 인증 + 영속화 + 이력 읽기**: 로그인/로그아웃·auth 상태, 결과 저장(식물 선택/생성 → Storage 업로드 + Firestore 기록), "내 식물" 목록 + 타임라인.
- **Slice 2 — 비교**: FastAPI `/compare` + 타임라인의 "이전 진단과 비교" UI.

→ **첫 CC 프롬프트 = Slice 0+1(파운데이션).** Slice 2는 그 다음.

---

## 8. 사용자 선행작업 (Firebase 콘솔 — CC가 못 하는 부분)

1. Firebase 프로젝트 생성.
2. **Authentication** → Google 공급자 활성화.
3. **Firestore Database** 생성(프로덕션 모드, 규칙은 CC가 작성한 걸 배포).
4. **Storage** 활성화.
5. 웹 앱 등록 → **web config(apiKey 등)** 발급 → 프론트 env로 전달(키는 CC에 직접 붙이지 말고 `.env.local`).
6. (선택) Firebase용 Claude 플러그인/MCP 연결 — CC가 Firestore/Auth/Storage를 직접 조작·검증하고 싶을 때.

---

## 9. 확정 필요 / 주의

- **확정 필요**: (a) 인증 = Google 단독으로 OK? (b) 식물 동일성 = 수동 연결로 OK?
- **주의 — stateless 깨짐**: 지금 앱은 단일 페이지 상태머신·계정 없음. 로그인·라우팅(또는 화면 추가)이 들어오므로 상태머신/네비 구조 영향 검토 필요(R5 헤더 모델과의 정합).
- **주의 — 사용자 데이터/동의**: 이미지를 서버에 저장하므로 개인정보 취급·동의 문구 필요(가벼운 안내라도).
- **불변 유지**: FastAPI 진단 파이프라인, `current_state`·미사용 care 필드 타입(백엔드 호환), `eval/baseline.json`·측정 인프라.
