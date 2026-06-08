# Phase 1 파이프라인 회고 (1-1 ~ 1-10b)

- **기간/라운드**: 2026-05-30 ~ 06-01, 15 라운드.
- **목적**: Vision(analyze)→keyword→retrieve(RAG)→generate 파이프라인 구축 및 슬림화. 핵심 산출은 **코드에 반영 완료**(diagnosis/프롬프트는 이력).
- **주요 결과**: vision provider protocol·Gemini provider·Vertex ADC 전환(1-1~1-2.5) → analyze 프롬프트/노드(1-3~1-4) → graph 와이어링·keyword 축소·generate 재설계·retrieve 정비(1-5~1-8) → state/schema 슬림화(1-9, 51594d2)·RAG_FAILED 폐기·Plant.id sweep(1-10a, ad4d1e1)·temperature 튜닝(1-10b). Plant.id 완전 제거, 5→3단계 거의 도달.
- **교훈**: dead read(rag_failed·disease_name) 제거는 측정 무영향 확인 후 진행. 상세는 MEMORY.md `phase1-*` 참조.

## 원본 파일 (→ `_archive/원본/Phase1/`)
1-1_vision_provider_protocol_프롬프트.md · 1-2_gemini_provider_프롬프트.md · 1-2.5_vertex_ai_adc_전환_진단.md · 1-2.5_vertex_ai_adc_전환_프롬프트.md · 1-3_analyze_프롬프트_초안_v1.md · 1-3_v4_analyze_프롬프트_보강_진단.md · 1-4_analyze_node_프롬프트.md · 1-5_graph_와이어링_진단.md · 1-6_keyword_축소_진단.md · 1-7_generate_재설계_진단.md · 1-7.5_generate_status_경로_정비_프롬프트.md · 1-8_retrieve_정비_작업프롬프트.md · 1-9_state_schema_슬림화_작업프롬프트.md · 1-10a_RAG_FAILED_폐기_Plant_id_sweep_작업프롬프트.md · 1-10b_temperature_튜닝_최종측정_문서갱신_작업프롬프트.md
