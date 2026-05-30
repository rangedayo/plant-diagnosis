# [1-3] analyze 프롬프트 초안 v3

> 목적: identify_node + describe_node를 통합할 analyze_node의 시스템 프롬프트 초안 작성.
> [1-4] analyze_node 구현 시 `app/prompts.py`에 박을 형태로 확정 예정.
>
> 작성일: 2026-05-29
> 단계: 리팩토링 1단계의 세 번째 하위 작업 ([1-3])
> 선행: [1-2] GeminiProvider 구현 완료, vision 모델 `gemini-2.5-pro` 업그레이드 + self_haengun_001 통합 테스트 검증 완료.
>
> **v2 변경 (2026-05-29, 검토 포인트 1~4 확정):**
> - (1) Dracaena 4종 인라인 나열 → 톤다운. 일반 원칙 "같은 속 안에서 잎 형태 유사 종 우선" + Dracaena/Aglaonema 속 예시만. 비-Dracaena 앵커링 노이즈 최소화.
> - (2) visual_description 식물학적 용어 예시 4개 → 2개 축소 (KISS, 모델의 용어 억지 끼워넣기 유인 감소).
> - (3) plant_confidence high/med/low 정의 — 변경 없이 유지 (genus/species 기준 명확).
> - (4) system_prompt 위치 — 현행 `types.Part.from_text()` 첫 part 유지. gemini.py 무변경. `system_instruction` 전환은 후속 정리 task로.
>
> **v3 변경 (2026-05-29, v2 통합 검증 8장 결과 반영 — 아래 "통합 검증" 섹션):**
> - (A) observed_symptoms 과잉 보고 억제: "2~4개 권장" → "명확히 보이는 이상만 기록, 개수 채우려 만들지 말 것. 종 특성 무늬·형태, 물리적 흠집·벌레 자국, 물방울·먼지 환경요인은 증상 아님". (정상 식물 3장에서 2~3개 과잉 보고된 패턴 대응)
> - (B) plant_name_korean 통명 강화: "한국 원예·화훼 시장 유통명 우선 사용" 명시 (예: 스파티필름, 몬스테라). spathiphyllum→"피스 릴리", monstera→음역만 출력된 편차 대응.

---

## ANALYZE_SYSTEM (시스템 프롬프트)

```
당신은 식물 이미지를 분석해 구조화된 JSON으로 답하는 조력자입니다.
출력은 유효한 JSON 객체 하나뿐이어야 합니다. 마크다운, 코드 블록, 설명 문장은 절대 금지입니다.

반드시 다음 6개 키를 모두 사용하세요 (이름·순서 변경 금지):

- "plant_name": 문자열. 식물 학명(영문). 가장 가능성 높은 1위만.
- "plant_name_korean": 문자열. 식물의 한국어 명칭. 한국 원예·화훼 시장에서 통용되는 유통명이 있으면 그 이름을 우선 사용하세요 (예: "스파티필름", "몬스테라", "산세베리아"). 학명 음역만 알려진 경우 음역을 쓰되, 통용명이 있으면 음역 옆 괄호로 함께 표기할 수 있습니다 (예: "드라세나 프라그란스 (행운목)").
- "plant_confidence": 문자열. 정확히 다음 중 하나만: "low", "med", "high".
  - "high": 잎·줄기·전체 형태가 명확해 단일 종으로 확신할 때.
  - "med": 같은 속(genus) 안에서 1~2개 후보로 좁혔으나 종(species) 확신은 약할 때.
  - "low": 속 단위에서도 후보가 분산되거나 이미지 품질이 불충분할 때.
- "alt_candidates": 문자열 배열. 대안 학명 후보(영문 학명만). 최대 3개.
  같은 속(genus) 안에서 잎 형태가 유사해 헷갈리는 종이 있으면 우선 포함하세요 (예: Dracaena 속이나 Aglaonema 속).
- "visual_description": 문자열. 이미지에 보이는 식물의 시각적 묘사를 한국어로 작성.
  잎의 모양·색·무늬·잎맥, 줄기 형태, 화분 환경 등을 사실 그대로 기술하세요.
  가능하면 식물학적 용어를 활용하면 좋습니다 (예: "평행한 잎맥", "긴 피침형 잎").
- "observed_symptoms": 문자열 배열. 이미지에서 명확히 보이는 이상 징후만 간결한 명사구로 기록(한국어).
  예: "잎끝 갈변", "잎 표면 노란 반점", "잎 처짐".
  개수를 채우려 없는 증상을 만들지 마세요. 종 고유의 무늬·형태, 물리적 흠집·벌레 먹은 자국, 물방울·먼지 같은 환경 요인은 증상이 아닙니다.
  이상이 보이지 않으면 빈 배열 [].

규칙:
- 값은 모두 한국어로 작성하되, plant_name과 alt_candidates의 학명만은 영문 그대로.
- 당신의 역할은 **관찰**입니다. 진단(병명 단정)·처방(조치 권고)·건강 여부 판단은 다른 단계의 책임이므로 이 출력에는 포함하지 마세요.
  "~로 보입니다", "~가 관찰됩니다" 같은 관찰형 표현을 쓰고, "이 식물은 ~병에 걸렸습니다", "이 식물은 건강합니다" 같은 단정 표현은 피하세요.
- 식별 신뢰도는 자기보고(self-report)입니다. 분명히 모르겠으면 "low"를 솔직히 선택하세요. 거짓 확신은 금지입니다.
- JSON 키는 반드시 큰따옴표로 감싼 표준 JSON 형식.
- 출력 외 어떤 텍스트도 추가하지 마세요.
```

## ANALYZE_USER_TEMPLATE

```
첨부된 이미지의 식물을 분석해 위 스키마의 JSON 한 개만 출력하세요.
```

이미지는 `types.Part.from_bytes(...)`로 별도 첨부 — `GeminiProvider.analyze()`의 현재 패턴 그대로.

---

## 설계 결정 매핑

| 인사이트 출처 | 반영된 부분 |
|---|---|
| phase2_decisions #1 (관찰/진단 분리) | "당신의 역할은 **관찰**입니다 … 건강 여부 판단은 다른 단계 책임" |
| [1-2] A. Pro 자발적 한국어 통명 | "한국에서 통용되는 이름이 있으면 학명 음역 옆에 괄호로" (권장 톤, 강제 X) |
| [1-2] B. visual_description 결 차이 | "식물학적 용어 활용 권장" + 4개 예시 |
| [1-2] C. observed_symptoms 압축 | "2~4개 권장, 간결한 명사구" |
| [1-2] D. alt_candidates 동일 속 우선 | "같은 속 안에서 헷갈리는 종이 있으면 우선" + Dracaena/Aglaonema 예시 |
| v8 남은 오답 5장 Dracaena 혼동 | Dracaena 4종(fragrans/reflexa/trifasciata/deremensis) 명시 — alt에 들어가도록 유도 |
| 3중 금지 풀기 (decisions 강제 3개 원칙) | "단정 표현 피하세요" 권장 톤 (강제 X). 강제는 JSON·confidence enum·한국어 3개만 |
| Confidence enum 자기보고 정의 | high/med/low 각각의 판단 기준 명시 — Pro 결정 일관성 ↑ |

## 강제 vs 권장

`docs/phase2_decisions.md`의 "강제 3개" 원칙을 analyze 단계에 적용:

| 강제 (어기면 시스템 실패) | 권장 (어겨도 동작) |
|---|---|
| JSON 6필드 형식 | 한국어 통명 병기 |
| plant_confidence enum (low/med/high) | 식물학적 용어 활용 |
| 한국어 출력 (학명 외) | observed_symptoms 2~4개 |
| 출력 외 텍스트 금지 | 관찰형 표현 (단정 회피) |
| | alt_candidates 동일 속 우선 |

---

## 검증 계획

설계 OK면 통합 테스트로 실제 출력 확인. **5~10장**이 적절:

| 카테고리 | 선택 케이스 | 검증 포인트 |
|---|---|---|
| Self Dracaena 혼동 그룹 | `self_dracaena_001`, `self_haengun_001`, `self_haengun_004` | Dracaena 4종 구별 / alt에 fragrans·reflexa 들어가는지 |
| 흔한 한국 관엽 | `inat_monstera_deliciosa_001`, `inat_sansevieria_trifasciata_001`, `inat_spathiphyllum_001` | 한국어 통명("몬스테라", "산세베리아", "스파티필름") 적용 |
| 건강 케이스 | `inat_chlorophytum_comosum_002` (정상) | observed_symptoms 빈 배열 [] 정상 나오는지 |
| 증상 명확 | `self_haengun_002` (unhealthy) | observed_symptoms 간결 명사구 |

**예상 비용**: 10장 × 2.5 Pro 호출 ≈ **$0.05** (체감 무시 수준).

### v2 통합 검증 결과 (2026-05-29, 8장 실측)

`_validate_analyze_prompt_v2.py`로 8장 1회씩 호출 (latency 17~24s, 합산 ≈$0.05).

**강제 항목 위반 0건**: JSON 6필드·confidence enum·한국어·관찰형 표현 모두 정상. is_healthy/health_notes 누출 없음 (결정 #1 충족).

| 이미지 | GT 통명 | 모델 한국어명 | conf | symptoms | 메모 |
|---|---|---|---|---|---|
| self_dracaena_001 | 송오브인디아(reflexa) | 드라세나 프라그란스 '와네키' | med | 3 | 속 정답·종 혼동, alt에 reflexa ✓ |
| self_haengun_001 | 행운목 | 드라세나 프라그란스 (행운목) | high | 2 | 통명 병기 정확 ✓ |
| self_haengun_004 | 행운목 | 드라세나 프라그란스 (행운목) | high | 2 | alt에 Dracaena 속 ✓ |
| monstera_001 | 몬스테라 | 몬스테라 델리시오사 | high | 3(GT0) | 증상 과잉, 음역만 |
| sansevieria_001 | 산세베리아 | 드라세나 트리파스키아타 (산세베리아) | high | 3(GT0) | 학명 최신·통명 ✓, 증상 과잉 |
| spathiphyllum_001 | 스파티필름 | 스파티필룸 왈리시이 (피스 릴리) | high | 2(GT0) | 통명 빗나감, 증상 과잉 |
| chlorophytum_002 | 접란 | 클로로피텀 코모섬 (접란) | high | 0 | 빈 배열 정상 ✓✓ |
| self_haengun_002 | 행운목(unhealthy) | 드라세나 프라그란스 (행운목) | high | 4 | 증상 케이스 양호 ✓ |

**발견 2건 → v3 반영**: (A) 정상 식물 3장에서 증상 2~3개 과잉 보고 → observed_symptoms 톤조정. (B) spathiphyllum/monstera 통명 편차 → plant_name_korean 유통명 우선 강화.

**핫스팟 확인**: Dracaena 톤다운 alt 유도 작동 — dracaena_001 med+reflexa, haengun_004 alt에 Dracaena 속.

---

## 검토 포인트 (해결됨 — v2에서 확정)

1. ~~"Dracaena 4종 명시"가 과한가?~~ → **톤다운 유지**. 일반 원칙 + Dracaena/Aglaonema 속 예시만, 4종 나열 제거.
2. ~~"식물학적 용어" 예시 4개~~ → **2개로 축소**.
3. ~~plant_confidence 정의 명확성~~ → **그대로 유지** (genus/species 기준 명확).
4. ~~system_prompt 위치~~ → **현행 첫 Part 유지**, gemini.py 무변경. system_instruction 전환은 후속 정리 task.

---

## 다음 단계

1. 위 4개 검토 포인트에 답 → 필요 시 v2 수정
2. 5~10장 통합 테스트 의뢰 프롬프트 작성 → Claude Code 의뢰
3. 결과 검토 후 v3 확정 (필요 시 수정 반복)
4. 확정되면 `app/prompts.py`에 `ANALYZE_SYSTEM` / `ANALYZE_USER_TEMPLATE` 상수로 박는 형태로 Claude Code 의뢰
5. [1-4] analyze_node 작성 진입
