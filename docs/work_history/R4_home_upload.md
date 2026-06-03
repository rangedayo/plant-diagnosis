# R4 — 홈 화면 + 업로드 카드 + 탭바 (디자인 리디자인 마지막 조각)

`docs/design/plantia_home.html` → 홈 화면 전면 교체. 인사말 + 업로드 카드(촬영 가이드 + 카메라/앨범)
+ 최근 진단 기록(데이터 없음=empty state) + 탭바. **업로드 카드의 실제 동작(파일 선택→진단)을
기존 로직에 빠짐없이 연결하는 게 핵심.** R1~R3 산출 기반. 백엔드·측정 무관.

---

## 0. 선결 게이트 (없으면 중단·보고)

- `git status` clean (R3 푸시 후).
- `docs/design/plantia_home.html`·`plantia_screen_data_mapping.md`·`plantia_design_system_sheet.md` 존재.
- R1~R3 산출 확인: `globals.css` 토큰, `ResultView`/`CareGuideView`, `index.tsx` 상태머신(home/loading/result/care).

## 1. 현 구조·시안 정독 (view) — ★업로드 로직 보존이 최우선

- `components/UploadCard.tsx`(또는 현 업로드 컴포넌트) **전체** — 파일 선택 input, onChange, `diagnosePlant` 호출, 에러 처리, loading 전환 트리거. **이 동작 로직을 새 디자인에 그대로 옮겨야 진단이 작동**.
- `pages/index.tsx` — home screen 렌더, `file`/`previewUrl` state, `URL.createObjectURL`/`revokeObjectURL`, loading→result 전환, 에러 표시.
- `lib/api.ts` — `diagnosePlant(file)` 시그니처.
- `docs/design/plantia_home.html` — **전체 정독**. 헤더(Plantia 로고·알림 벨), 인사말, 진단 카드(타이틀·촬영 가이드 3포인트·카메라 버튼·앨범 버튼), 최근 진단 기록 2칸, 탭바 4개. 인라인 SVG·더미데이터 위치.
- `docs/design/plantia_screen_data_mapping.md` §1·§4 — 바인딩 정본.

## 2. 업로드 카드 — 디자인 교체 + 동작 연결 (★핵심)

시안 진단 카드 UI로 교체하되, **기존 진단 동작을 모두 보존**:

- **카메라 버튼**: `<input type="file" accept="image/*" capture="environment">` 트리거 (모바일=카메라, 데스크탑=파일 선택).
- **앨범에서 선택**: `<input type="file" accept="image/*">` 트리거 (갤러리/파일 선택).
- 파일 선택 시 → 기존 흐름 그대로: `file` state 세팅 → `previewUrl` 생성 → `diagnosePlant(file)` 호출 → loading screen → 성공 시 result, 실패 시 에러 표시.
- 촬영 가이드 3포인트(잎 전체·초점·화분 배경)는 정적 텍스트(매핑 md §1).
- ⚠ 기존 `diagnosePlant` 호출·에러 처리·objectURL cleanup 로직을 **누락 없이** 연결. UI만 새 디자인, 동작은 동일. (input 2개로 분리되니 onChange 핸들러 공유.)

## 3. 홈 레이아웃 — `index.tsx` home screen 또는 `components/HomeView.tsx`

시안 `plantia_home.html` 구조로 home screen 구성:
1. **헤더**: Plantia 로고(인라인 SVG) + 알림 벨. 알림 기능 없음 → 벨은 **비활성/무반응**(또는 dot 더미 제거). 클릭 동작 연결 금지.
2. **인사말**: "안녕하세요! 🌱" + "오늘 식물 상태는 어떤가요?" (정적).
3. **진단 카드**: §2 업로드 카드.
4. **최근 진단 기록**: §4 참조.
5. **탭바**: §5 참조.

> 홈을 별도 `HomeView.tsx`로 빼도 되고 index 내 home 분기에 직접 둬도 됨(view 후 판단). 스타일은 styled-jsx scoped + `globals.css` 토큰. 시안 `@import` 줄 제거.
> loading/result/care 화면엔 탭바 없음(시안 기준 홈 전용). 기존 그대로.

## 4. 최근 진단 기록 — empty state (데이터 소스 없음)

매핑 md §4: 진단 저장·조회 기능 미구현 → **더미(산세베리아·몬스테라) 제거**.
- 빈 상태로: "아직 진단 기록이 없어요" 안내 + (선택)진단 유도 문구. 섹션을 통째 숨기기보다 empty state가 홈이 휑하지 않아 권장.
- ⚠ 더미 카드 노출 금지. localStorage/DB 저장 **구현하지 말 것**(시계열 라운드 별건).
- "전체 보기" 링크도 데이터 없으니 비활성 또는 숨김.

## 5. 탭바 — 시각 표시, 기능 없는 탭 빈 화면 방지

시안 탭 4개(홈·진단·내 식물·설정). 현 상태머신엔 home/loading/result/care만 — 내 식물·설정 화면 없음.
- **홈 탭**: 활성 표시(현 화면).
- **나머지 탭(진단·내 식물·설정)**: 기능 화면 없음 → **비활성 스타일 + 클릭 무반응**. 빈 화면으로 전환 금지.
  (진단 탭은 홈에 업로드 카드가 이미 있어 중복 → 비활성 또는 홈 유지. 빈 화면 진입만 막으면 됨.)
- 라우팅·새 screen 추가하지 말 것(기능 미구현). 탭바는 디자인 골격만.

## 6. 검증

```bash
npx tsc --noEmit          # 0
```

**전체 흐름 시각 확인** (next dev). R4는 진단 입구라 e2e가 중요:

1. **홈 렌더**: 인사말·업로드 카드(촬영 가이드)·최근기록 empty state·탭바 정상.
2. **업로드 동작 (★)**: 카메라/앨범 버튼 → 파일 선택 다이얼로그 → 선택 시 loading 전환 → `diagnosePlant` 호출.
   - 백엔드(127.0.0.1:8000) 띄울 수 있으면 **실제 e2e**: 홈→사진 선택→로딩→결과(R2)→"지속 관리법 보기"→케어(R3)→뒤로→결과. **전체 리디자인 흐름 한 번 관통 확인**.
   - 백엔드 불가 시: 파일 선택→loading 전환 + diagnose 호출 트리거(네트워크)까지 확인, 결과 화면은 mock으로.
3. **에러 경로**: diagnose 실패 시 기존 에러 표시 동작 보존 확인.
4. **탭바**: 홈 활성, 나머지 클릭 무반응(빈 화면 안 뜸).
5. **empty state**: 최근 기록 더미 없이 빈 상태.

> 헤드리스 캡처 시 Tabler 웹폰트 로드 대기(`--virtual-time-budget`) — 즉시 캡처하면 아이콘 빈 원(R3 메모).
> mock·임시 코드는 검증 후 제거(커밋 미포함).

각 항목 스크린샷/상태 보고. 콘솔 에러 0.

## 7. 보고 + 커밋

### 변경 파일 (예상)
```
components/UploadCard.tsx   (또는 HomeView.tsx 신설) — 시안 이식 + 업로드 동작 연결
pages/index.tsx            — home 레이아웃(인사말·최근기록 empty·탭바), 업로드 핸들러 배선
```

### 보고
- 전체 흐름(홈→업로드→로딩→결과→케어→뒤로) 동작 결과 + 스크린샷
- 업로드 동작(카메라/앨범 input·diagnose 호출·에러) 보존 확인
- empty state·탭바 비활성 처리 방식
- e2e 실제 진단 여부(백엔드 띄웠는지)

### 커밋 메시지 (사용자 확정 후)
```
feat: [리디자인 R4] 홈 화면 + 업로드 카드 + 탭바

- 홈: plantia_home.html 시안 이식 (인사말·진단 카드·최근기록·탭바)
- 업로드 카드: 촬영 가이드 3포인트 + 카메라/앨범 input, 기존 diagnosePlant 동작 연결
  (UI만 교체, 파일선택→loading→result 흐름·에러·objectURL cleanup 보존)
- 최근 진단 기록: 데이터 소스 없음 → empty state (더미 제거, 저장 미구현)
- 탭바: 홈 활성, 기능 없는 탭(진단·내 식물·설정) 비활성/무반응 (빈 화면 방지)
- styled-jsx scoped, @import 제거(_document 의존)

범위: 홈·업로드 화면. 리디자인 R1~R4 완료. 백엔드·측정·시계열 무관.
```

`eval/`·`data/`·백엔드 add 금지. mock·localStorage 저장 커밋 금지.

## 8. 주의
- **업로드 동작 보존이 최우선** — 새 UI에 기존 diagnose 흐름을 누락 없이 연결. 이게 깨지면 진단 자체가 안 됨.
- 최근 기록 저장·탭 화면·알림은 **구현하지 말 것** (기능 미정의/별건 라운드). 빈 화면·더미만 방지.
- styled-jsx scoped 유지, 전역 오염 금지.
- `eval/baseline.json` 절대 손대지 말 것.
- R4 완료 = 디자인 리디자인(R1~R4) 종료. 다음은 기능 라운드(객관식 2차 진단 → 시계열) + 남은 정리(NCPMS vector_db 재구축).
