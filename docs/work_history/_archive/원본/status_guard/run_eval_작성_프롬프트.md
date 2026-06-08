# baseline 측정 — 2단계: run_eval.py 작성 프롬프트

> 1단계 읽기전용 진단 결과를 반영한 실제 코드 작성 프롬프트.
> 측정 범위 확정: **식물 이름 / 건강 여부 / status 분포** 3개 + 보조 지표(JSON 파싱 성공률, latency).
> symptoms 코드 채점과 diagnosis 텍스트 채점은 **baseline에서 제외** (나중에 정밀 채점기 별도 작업).

---

## 진단으로 확정된 사실 (프롬프트에 반영됨)

- 진단 그래프: `build_diagnosis_graph(client)` (app/graph.py:358) → `graph.ainvoke({...,"image_bytes": bytes,...})` 로 HTTP 없이 직접 구동 가능.
- 기존 `scripts/eval_rag.py`가 이미 이 방식으로 호출 중 → `_initial_state` 구성 방식을 그대로 참고/재사용.
- 출력: `structured_result`는 5키 고정(summary, current_state, cause, action_plan, status). `plant_id.plant_name`은 학명(영어) 1위.
- status enum: `{"건강","과습","건조","병해 의심","영양 부족"}` (app/model_utils.py:533).
- 정답지: `test_data/main_eval/labels.json` (33장). `ground_truth`에 plant_name_korean, is_healthy, symptoms, diagnosis.
- 이름 매핑: `PLANT_NAME_KO_MAP` (labeling_vocab.py:27, 학명→한국어, 10종) — 단 정답지 일부 종("아글라오네마" 등)이 맵에 없음. 매칭 안 되면 "매칭불가"로 별도 집계.

---

## Claude Code에 붙여넣을 프롬프트

```
plant-diagnosis 프로젝트에 baseline 측정 스크립트 scripts/run_eval.py 를 새로 작성한다.
목적: 현재 진단 시스템을 고치기 전에, 33장 평가셋으로 baseline 점수를 박아둔다.

[측정 범위 — 이것만 측정한다]
1. 식물 이름 정확도
2. 건강 여부 정확도 (is_healthy)
3. status 분포 + status별 정확도
4. 보조 지표: JSON 파싱 성공률, 케이스별 처리 시간(latency)

증상(symptoms) 코드 채점과 diagnosis 텍스트 채점은 이번엔 하지 않는다. (TODO 주석만 남겨라)

[진단 호출 방식 — 기존 코드 재사용]
- scripts/eval_rag.py 가 build_diagnosis_graph(app/graph.py)를 import해서
  파일→bytes로 graph.ainvoke({..., "image_bytes": bytes, ...}) 하는 패턴을 그대로 따른다.
- eval_rag.py 의 _initial_state 구성과 app/main.py:183-199 의 초기 state 키 세트를 참고해
  동일하게 state를 만들어라. plant_filter_mode 는 "strict" 기본값 유지.
- HTTP 엔드포인트(/diagnose)는 쓰지 말고 그래프를 직접 구동한다.

[입력]
- 평가셋: test_data/main_eval/labels.json (33장)
- 각 항목의 image_path 로 이미지 파일을 읽어 bytes로 변환 → 그래프에 투입.
- 각 항목의 ground_truth 와 모델 출력을 image_id 기준으로 매칭.

[채점 로직]
1. 식물 이름:
   - 모델 출력 plant_id.plant_name (학명, 영어)을 labeling_vocab.PLANT_NAME_KO_MAP으로 한국어 변환.
   - 변환된 한국어가 ground_truth.plant_name_korean 과 일치하면 correct.
   - PLANT_NAME_KO_MAP에 학명이 없어서 변환 불가능한 경우는 "매칭불가"로 따로 카운트
     (correct로도 wrong으로도 세지 말고 unmappable로 별도 집계).
   - 최종 출력: correct / wrong / unmappable 3개 수치 + 정확도(매칭가능한 것 중 비율).
   - 주의: PLANT_NAME_KO_MAP은 학명→한국어 방향. plant_name이 "Spathiphyllum"처럼
     종소명 없는 경우도 있으니, 정확히 키가 일치할 때만 변환하고 안 되면 unmappable.

2. 건강 여부 (is_healthy):
   - 모델 출력 structured_result.status 를 boolean으로 변환:
     "건강" → True, 나머지("과습","건조","병해 의심","영양 부족") → False.
   - ground_truth.is_healthy 와 비교.
   - 정답지가 28(healthy) : 5(unhealthy)로 불균형하므로 accuracy만 내지 말고
     confusion matrix (TP/TN/FP/FN) + precision + recall 까지 함께 출력.
     (소수 클래스인 "비건강"을 positive로 잡아라.)

3. status 분포:
   - 모델이 출력한 status 5종이 각각 몇 번 나왔는지 분포 집계.
   - ground_truth.is_healthy 와 교차표도 출력 (어떤 status가 healthy/unhealthy에 몰리는지).

[보조 지표]
- JSON 파싱 성공률: structured_result가 5키를 정상적으로 갖춘 비율. 실패 케이스는 image_id 기록.
- latency: 케이스당 처리 시간(초) 측정 → 평균/최소/최대.
  (eval_rag.py 가 graph.astream(stream_mode="updates")로 노드별 시간을 재는 패턴이 있으면 참고하되,
   baseline은 케이스 전체 시간만으로도 충분하다. 과하게 만들지 마라.)

[출력]
- 콘솔에 사람이 읽을 요약표 출력.
- 동시에 결과를 eval/baseline.json 으로 저장 (코드_정리_계획.md의 eval/after_X.json 컨벤션과 맞춤).
  저장 구조 예시:
  {
    "measured_at": "...",
    "total": 33,
    "plant_name": {"correct": ..., "wrong": ..., "unmappable": ..., "accuracy": ...},
    "is_healthy": {"tp":...,"tn":...,"fp":...,"fn":...,"precision":...,"recall":...,"accuracy":...},
    "status_distribution": {...},
    "json_parse_success_rate": ...,
    "latency_sec": {"mean":...,"min":...,"max":...},
    "per_case": [ {image_id, gt_plant, pred_plant_scientific, pred_plant_ko, plant_match,
                   gt_is_healthy, pred_status, pred_is_healthy, healthy_match, latency_sec, json_ok}, ... ]
  }
- per_case 를 꼭 남겨라 — 나중에 케이스별로 뭘 틀렸는지 봐야 한다.

[제약]
- 파일 인코딩은 BOM 없이 UTF-8 (Windows PowerShell Set-Content 쓰지 말고 Python json.dump로 저장).
- 기존 app/ 코드는 수정하지 마라. scripts/run_eval.py 와 eval/ 폴더 생성만 허용.
- 추측으로 채우지 말고, eval_rag.py 의 실제 import/state 구성을 먼저 열어 확인한 뒤 동일 패턴을 써라.
- 다 만들면 33장 전체를 실제로 한 번 돌려서 eval/baseline.json 을 생성하고, 콘솔 요약을 보고해라.
```

---

## 돌린 뒤 함께 볼 것

baseline.json이 나오면 이 세 가지를 같이 확인한다:

1. **unmappable이 몇 장인지** — 정답지 9종 중 PLANT_NAME_KO_MAP에 없는 종이 얼마나 점수를 못 받고 있는지. 많으면 맵 보강이 다음 우선순위.
2. **is_healthy의 recall** — 비건강 5장(전부 self 행운목/드라세나)을 모델이 몇 개나 잡아내는지. 소수 클래스라 여기가 약점일 가능성.
3. **status 분포 쏠림** — 모델이 "건강"으로만 답하는 경향이 있는지 (결과.md에서 본 "멀쩡한데 병들었다고 함" 문제의 반대 방향일 수도).

이 결과가 곧 코드_정리_계획.md의 리팩토링(Gemini 통합 등) 전 baseline이 되고, 고친 뒤 `eval/after_1.json`과 -5%p 게이트로 비교하게 된다.
