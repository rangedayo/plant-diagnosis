# 작업: 홈 화면 묶음 — 최근 진단 기록 연결 · 진단 탭 제거 · 홈 아이콘 · 업로드 흐름

> 프론트 전용. 백엔드·진단 파이프라인·챗봇 무관(동결).
> 워크플로우: CLAUDE.md §5·§10. recon-first, 변수 격리(atomic 커밋 분리), 푸시 보류→검토. git·커밋 PowerShell(§3.1).

---

## 0. 선행 — 커밋 상태 동기화
- `git status`로 미커밋/보류 확인. **CLAUDE.md 챗봇 마무리 `docs:` 커밋이 미푸시면 먼저 푸시**(별도 작업, 독립). 그 후 깨끗한 상태에서 이번 묶음 시작.

## 1. 이번 변수 (4개 — 변수 격리 위해 atomic 커밋 분리)
홈 화면 UX 4건. 각각 독립 커밋. 진단 파이프라인·`runDiagnosis` 로직 자체·백엔드·챗봇 무변경.

## 2. 선결 게이트 (READ-ONLY, 보고 후 진행 — §5.1)
1. 현재 브랜치/tip — 0번 동기화 상태.
2. `components/BottomTabBar.tsx` — `TabKey` 타입·4탭 구조·홈 SVG(`fill="#D4EBC8"` path + 문 rect)·active/inactive 스타일.
3. `components/HomeView.tsx` — 식물 일러스트(PlantHero)·촬영 가이드 3포인트·카메라/앨범 버튼·"최근 진단 기록" empty state.
4. `pages/index.tsx` — `runDiagnosis` 즉시 호출 지점·`file`/`previewUrl` state·`handlePickDiagnosis`(history 진입 패턴).
5. **Firestore 조회 패턴:** `lib/db.ts`(`DiagnosisRecord`·`PlantSummary`·기존 쿼리), `lib/auth`(`useAuth` 로그인 상태), `TimelineView`(식물별 진단 조회 방식). **cross-plant 최근 진단 N개 조회 함수가 있는지** 확인 — 없으면 신설 범위 판단.

> ⚠ 항목 D(최근 진단 기록)가 cross-plant 쿼리 신설 등으로 무거우면 **D만 분리 라운드로 보고**하고 A·B·C 먼저 진행해도 됨(사용자 결정).

## 3. 구현 항목

### A. "진단" 탭 제거 (`BottomTabBar`)
- `TabKey`에서 `"diagnose"` 제거 + 진단 탭 `div` 삭제 → 3탭(홈·내 식물·설정). 진단은 홈 카드에 있어 중복.
- 3탭 균등 분할(기존 `flex:1` 유지면 자동). 설정 탭은 기존대로 disabled.

### B. 홈 탭 아이콘 채움 제거 (`BottomTabBar`)
- 홈 SVG의 연두 채움(`fill="#D4EBC8"`) 제거 → "내 식물"처럼 **진녹 테두리(stroke)만** 보이게. 문 rect도 라인 무게에 맞춰 조정(채움 과하면 stroke화). active=진녹/inactive=dim 처리는 유지.

### C. 업로드 → 미리보기 + "진단 시작" (`HomeView` + `pages/index.tsx`)
- 현재: 파일 선택 즉시 `runDiagnosis` 호출. **변경: 선택 시 진단하지 말고** 일러스트 자리에 **선택 사진 미리보기**(`previewUrl`) + **"진단 시작" 버튼 활성화** + **"다른 사진 선택"**(교체). "진단 시작" 클릭 시에만 `runDiagnosis(file)` 호출.
- 촬영 가이드 3포인트는 사진 선택 후 숨김(목업 기준). 미선택 상태는 기존 일러스트+가이드+카메라/앨범 유지.
- `runDiagnosis` 내부 로직은 무변경 — **호출 시점만 버튼으로 이연**.
- 디자인: 기존 카드·버튼 스타일 재사용. "진단 시작"=primary(진녹 채움), "다른 사진 선택"=outline. (버튼 문구 "진단 시작" 기준, 더 적절한 표현 있으면 제안.)

### D. 최근 진단 기록(홈) Firestore 연결 (`HomeView` + `lib/db`)
- 로그인 사용자의 **최근 진단 N개(cross-plant, 최신순)**를 Firestore에서 조회 → 홈 "최근 진단 기록" 카드로 표시(썸네일·식물명·status·날짜 수준).
- **미로그인**: 기존 empty state 유지(또는 "로그인하면 기록을 볼 수 있어요" 가벼운 안내 — 재량).
- 기록 카드 탭 → 해당 진단 상세(history 모드) 또는 식물 타임라인. 기존 `handlePickDiagnosis`/타임라인 패턴 재사용.
- ⚠ **더미 금지**(기존 원칙) — 데이터 있을 때만 표시, 빈 껍데기·가짜 항목 금지.

## 4. UX·게이트 보존
- 진단 파이프라인·백엔드·챗봇 2차 보정 경로 무접촉. 1차 진단은 C에서 **호출 시점만 이연**, 로직 동일.
- ResultView·챗봇 흐름(refine 진입 카드·배너·토글) 무변경.
- history 격리 유지(fresh state 오염 금지).

## 5. 합성 검증 (§5.2)
- `tsc --noEmit`·`next build` 통과.
- 1차 진단 흐름 회귀 없음("진단 시작" 버튼 경유로 정상 진단·결과 표시).
- D: 로그인/미로그인 분기 동작, 더미 미표시, 기록 카드 탭 네비.
- 챗봇(refine)·history·care·timeline 경로 무회귀.

## 6. 커밋·푸시
- Atomic 분리: 예) `feat(web):` 진단 탭 제거 / `style(web):` 홈 아이콘 채움 제거 / `feat(web):` 업로드 미리보기+진단 시작 / `feat(web):` 최근 진단 기록 Firestore 연결. (A·B 동일 파일이면 묶음 허용, 단 의도 명확히.)
- **푸시 보류 → diff 보고 후 사용자 검토.**

## 7. 금지 사항
- 백엔드·진단 로직·챗봇 경로·ResultView 렌더 변경.
- `runDiagnosis` 내부 로직 변경(호출 시점만).
- 더미/플레이스홀더 데이터 노출(D).
- 새 디자인 시스템 임의 도입(기존 토큰·카드·버튼 재사용).
- 측정(run_eval) CC 임의 실행 금지.
