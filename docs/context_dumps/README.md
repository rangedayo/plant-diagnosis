# generate 입력 컨텍스트 덤프 (단계 B')

generate(진단 LLM, GPT)가 진단 시점에 **실제로 읽은 입력 전체**를 케이스별로 떠둔 영구 기록.
`app/model_utils.generate_structured_diagnosis_with_gpt` 호출 인자(`context_summary` + `rag_chunks`)를
가로채 저장했다. 단계 B'(종 메타 정상화 카드)가 왜 순효과 0이었는지 — 즉 **(ii) generate 무시**의
실물 증거.

> 주의: analyze(Gemini)는 매 실행 비결정이라, 이 덤프는 단계 B' 측정 당시 run의 바이트 복제가 아니라
> **동일 파이프라인 1회 재실행** 결과다. 종 정상화 카드 섹션(`[이 종의 정상 생육 특성 (참고)]`)은
> species->텍스트가 결정적이라 측정 당시와 동일하다.

## 입력 컨텍스트 구성 (4부분)
1. **묘사 + 관찰 정보** — analyze가 이미지 1장에 Gemini를 호출해 뽑은 6필드(`visual_description`,
   `observed_symptoms`, plant 식별 등). 이 단계의 산물.
2. **검색된 자료의 타입 분포** — RAG로 뽑힌 top_3 카드의 `problem_type` 메타를 cosine 가중 합산한 분포.
   별도 모델 호출이 아니라 검색 결과 카드에서 계산. (b_dataset_rag 카드만 problem_type 있음, main_rag는 제외)
3. **이 종의 정상 생육 특성 (참고)** — 단계 B'가 주입한 종 정상화 카드. 식별 종을 keyword 매핑
   (`_normalize_species`)해 `species_normal_rag`에서 **결정적 메타 where-get**으로 가져옴.
   증상 검색어와 무관하게 매칭 종 카드만 들어감.
4. **rag_chunks** — 증상 기반 RAG 검색 결과(b_dataset 7 + main 3 = 상위 10). 검색어는
   `plant_name + observed_symptoms`(영문 번역). 묘사(visual_description)는 검색어로 쓰지 않음.
   **특정 problem_type을 "더 뽑아라"는 강제는 없음** — disease 우세는 증상 검색어의 의미적 근접성에서
   창발할 뿐. (소스 가중: b_dataset top_k=7 > main top_k=3, UC_IPM 0.85·generic 0.9 페널티,
   식물명 일치 +0.1 부스트, cosine >= 0.65 필터)

## 케이스
### `generate_input_self_dracaena_001.md` — disease 신호가 있을 때
- 건강한 드라세나(잎끝 갈변). analyze가 "잎 가장자리 갈색 **반점**"을 보고 -> disease RAG와 매칭.
- 종 정상화 카드 + frame 카드(정상화) 2개를 받고도 -> **병해 의심**.

### `generate_input_inat_sansevieria_trifasciata_002.md` — disease 신호가 적을 때
- 건강한 산세베리아(잎 일부 갈변). RAG 10개 중 **[disease] 단 2개**, 나머지는 abiotic/frame/nutrient/env.
- 종 정상화 카드 + frame 카드 존재.
- AI가 **스스로 cause를 "과습 또는 영양 부족"(비-병해)으로 적고도 status=병해 의심** — cause와 status가
  모순될 정도로 "병해 의심"이 기본 escalate임을 보여줌.

## 시사점
두 케이스 모두 정상화 신호(종 카드·frame 카드)와 비-disease 다수 RAG에도 불구하고 병해로 갔다.
-> generate는 입력 신호(룰·분포·종 사실)를 **더 줘서는** 병해 escalate 성향을 못 넘김.
-> 권고: status guard(generate 출력 후 코드 후처리)로 FP 직접 교정.
관련: `eval/after_phase_b_prime.json`, 메모리 `phase-b-prime-species-meta-null-effect`.
