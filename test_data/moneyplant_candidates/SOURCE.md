# Money Plant Disease Dataset (보관)

- 종: Epipremnum aureum (스킨답서스 / 골든포토스)
- 출처: https://data.mendeley.com/datasets/rzjww3vdxt/3
- 라이선스: CC BY 4.0 (출처 표기 의무)
- 논문: Money plant disease atlas, Data in Brief 2024, DOI 10.1016/j.dib.2024.111216
- 클래스(original): healthy 700 / bacterial_wilt 576 / manganese_toxicity 596
- 사용 방침:
  - **original 폴더만 사용** (augmented 제외 — 평가셋 부적합).
  - 평가셋 편입 후보는 우선 **bacterial_wilt → true_status="병해 의심"**.
  - healthy·manganese_toxicity는 **현재 보관만**. 편입 안 함.
    - manganese_toxicity는 영양 "과잉"(독성)이라 현 5-status에 매핑 칸 없음 → 보류.
      (향후 "영양 과잉" status 신설 시 활용 — 백로그.)
  - 잎 위주 크롭·224 리사이즈본이라 메인(실사용 폰 원본) 분포와 차이 → 편입 시 사람 검수 필요.
- 편입(labels 매핑·run_eval 연결)은 별도 후속 라운드에서 진행.
