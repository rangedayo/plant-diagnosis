# generate 입력 컨텍스트 덤프 - self_dracaena_001

> 단계 B' 측정 당시 구조를 재현한 **재실행** 덤프 (analyze=Gemini 비결정이라 바이트 동일이 아닌 동일 파이프라인 1회 실행). 종 정상화 카드 섹션은 결정적.

## 메타
- ground_truth: plant=`드라세나 송 오브 인디아`, is_healthy=**True**, gt_diagnosis="잎 끝과 아래쪽 잎에 갈색 마름이 있으나 드라세나 종 특성상 정상 범위. 새 잎은 건강하게 자라는 중."
- analyze 식별: plant_name=`Dracaena sanderiana` / 통명=`드라세나 산데리아나 (개운죽)` / conf=`med`
- observed_symptoms: `['잎끝 갈변', '잎 가장자리 갈색 반점', '잎집(엽초) 갈변']`
- rag_query: `Dracaena sanderiana 잎끝 갈변 잎 가장자리 갈색 반점 잎집(엽초) 갈변`
- 종 정상화 카드 매칭: species=`드라세나` (카드 1건)
- RAG 청크: 총 10개 중 **[disease] 3개**
- 분포(top_3 problem_type 가중): `{'majority': 'disease', 'distribution': {'abiotic': 0.3361, 'disease': 0.6639}, 'top_problem_type': 'abiotic'}`
- **AI 최종 진단 status: `병해 의심`**  (gt_healthy=True -> FP 오진)

## (1) generate가 받은 context_summary (묘사+관찰+분포+종 카드)
```
묘사:
식물의 줄기와 잎자루 부분을 근접 촬영한 이미지. 잎은 중앙이 녹색이고 가장자리가 넓은 흰색인 무늬를 가진 긴 피침형이다. 여러 개의 잎이 줄기에서 뻗어 나온다. 줄기에는 마디가 뚜렷하며, 잎이 붙어있는 잎집(엽초)은 어두운 녹색과 흰색 줄무늬가 있다. 일부 잎의 끝과 가장자리가 갈색으로 변한 것이 관찰된다.

[관찰 정보]
- 식물명(학명 1위): Dracaena sanderiana
- 식물명(통명): 드라세나 산데리아나 (개운죽)
- 식별 신뢰도: med
- 대안 후보: Dracaena reflexa, Dracaena deremensis
- 관찰된 증상: 잎끝 갈변, 잎 가장자리 갈색 반점, 잎집(엽초) 갈변

[검색된 자료의 타입 분포 (top_3 sim 가중)]
- 우세 타입: disease
- 1위 카드 타입: abiotic
- 분포: disease 0.66, abiotic 0.34

[이 종의 정상 생육 특성 (참고)]
- [드라세나] 이 종(드라세나속)의 정상 생육 특성: 내음성이 강해 실내 밝은 곳에서 잘 자란다. 오래되거나 아래쪽 잎의 잎끝 색이 바뀌거나 말라 들어가는 경우가 흔하며, 이는 생리적 현상으로 2년에 한 번 분갈이로 관리한다. 겨울철 차가운 물을 주면 잎이 황변할 수 있고, 수돗물의 불소 성분 때문에 잎끝이 갈변되기도 한다. 물이 부족하면 잎무늬에 기미가 낄 수 있다.

```

## (2) generate가 받은 rag_chunks (b_dataset/main RAG, problem_type prefix)
```
[abiotic] Brown leaf tips • Chemical: Brown leaf tips • Chemical burn from overapplication of pesticides or fertilizer • Soft water • Soil remains dry for extended periods of time • Temperature is too low

[disease] Leaf spot fungus: Leaf spot fungus — oval, brown/black spots, not limited by leaf veins, often with a yellow halo or purple band. Airborne spores spread to healthy leaves. Commonly affected plants include palms, yucca, orchids, prayer plant and dumbcane.

[disease] Leaf spots Fungi: Leaf spots Fungi and bacteria Fungal: • Remove infected leaves • Leaf spots appear brown • Increase air circulation with a yellow halo • Avoid getting water on leaves • Tiny black dots (fungal bodies) can be seen with a magnifying lens on the brown tissue • Portions of or the entire leaf may die Bacterial: • Leaf spots appear water soaked • May also have a yellow halo

[frame] Occasionally, leaves of seemingly healthy houseplants begin…: Occasionally, leaves of seemingly healthy houseplants begin to develop brown tips and margins, dead spots and yellowing. A common assumption is that a disease caused by a pathogen such as a fungus or bacterium might have infested the symptomatic plant. More often, however, these symptoms are the result of an unfavorable environment. Low relative humidity, insufficient light, over or under watering, or too much or too little fertilizer can lead to leaf damage that mimics disease symptoms. To make the problem even more difficult to diagnose, leaf problems often are due to a combination of these environmental factors.

[general] The pattern of leaf damage also can…: The pattern of leaf damage also can provide clues relative to the cause. In the case of damage caused by a disease, the progression of symptoms often transitions from healthy (green) tissue, to chlorotic (yellow) and, finally, to necrotic (brown) tissue. Additionally, when true diseases attack leaves, the dead or dying spots often are scattered on the leaf and occur closer to the growing medium or in the center of the plant where relative humidity is higher or where water got on leaves when the plant was watered.

[disease] Anthracnose Collectrotrichum: Anthracnose Collectrotrichum • Leaf tips turn yellow, then • Remove infected leaves and Gloeosporium fungi brown • Avoid misting leaves • Entire leaf may die

[Marginal or Tip Leaf Burn]
symptoms: Burning of leaf margins or tips, Production of smaller leaves, Discolored or damaged leaf edges
cause: Over-fertilization, Under-watering, High fluoride levels in water or potting soil, Salt buildup in soil from poor quality water
solution: Repot the plant with fresh potting soil, Use scissors to reshape and trim burned tips, Improve water quality if using high-salt or hard water, Adjust watering and fertilization frequency

[general] Additionally, temperatures too low for the houseplant…: Additionally, temperatures too low for the houseplant species in question as well as excessively dry soil for extended periods of time also can cause leaf edge and tip necrosis.

[Brown or scorched leaf tips:]
symptoms: Brown or scorched leaf tips:
cause: Poor health from overwatering, excessive soil dryness (especially between waterings), excessive fertilizer or other soluble salts in the soil or water, Specific nutrient toxicities (e.g., fluoride, copper, or boron), Low humidity, Pesticide or mechanical injury.
solution: The best approach to long term or greenhouse, if available, to reju- and leaf undersides thoroughly. If management is to emphasize preven- venate them. In such cases, inspect possible, spray the plant outdoors so tion through pest exclusion, proper plants closely for pests after returning that the spray residue will be dispersed sanitation, and cultural practices that them indoors and continue to monitor outside, and you will not have to worry create optimal growing conditions and them for a few weeks to assure they are about damaging furniture surfac- plant health. pest-free. es or exposing others to pesticides. Consider using a soap or horticultur- Practice pest exclusion by thoroughly Whenever you detect insect, mite, or al oil, if labeled for your plant pest, examining plants prior to purchasing disease problems on an established before using other types of insecticides and introducing them indoors. Do not plant in your home or office, isolate or miticides. Alternatively, consider purchase or bring home plants with the plant immediately to prevent using a systemic pesticide that can be possible insect, mite or disease infes- the problem from spreading to other applied to the soil, thus avoiding foliar tations. Carefully examine all parts plants. As an additional precaution, sprays. Soil drenches or applications of the plant, including leaf surfaces, wash your hands after touching infest- of insecticide granules may control leaf bases, flower and fruit stalks, and ed plants. soilborne insects; the potting medi- roots, looking for evidence of possi- ble insect pests or disease problems. Make sure you identify the pest or um should be well watered before Houseplants can often be removed disease correctly in order to choose applying a drench or after applying from their containers so that roots can effective management and control granules. Be certain to follow safety be examined. Reject plants that show options. In many instances, control guidelines on the product’s label. evidence of insect or mite infestations of a houseplant pest is impractical as well as possible disease symptoms, or nearly impossible once the pest is such as discolored stems and roots established. The best course of action or leaf spots; these blemishes are not in these situations is to discard the likely to disappear. plant and consider starting fresh with a new one. Select plants with growing require- ments (especially light and tempera-

[Leaf spots, blotches, blemishes, blisters, or scabby spots:]
symptoms: Leaf spots, blotches, blemishes, blisters, or scabby spots:
cause: Excess light (sunburn) associated with a recent move of the plant, Chilling injury (below 50°F), Chemical spray injury, Overwatering, Fungal or bacterial infections (rare unless plants have recently come from outdoors or greenhouses).
solution: The best approach to long term or greenhouse, if available, to reju- and leaf undersides thoroughly. If management is to emphasize preven- venate them. In such cases, inspect possible, spray the plant outdoors so tion through pest exclusion, proper plants closely for pests after returning that the spray residue will be dispersed sanitation, and cultural practices that them indoors and continue to monitor outside, and you will not have to worry create optimal growing conditions and them for a few weeks to assure they are about damaging furniture surfac- plant health. pest-free. es or exposing others to pesticides. Consider using a soap or horticultur- Practice pest exclusion by thoroughly Whenever you detect insect, mite, or al oil, if labeled for your plant pest, examining plants prior to purchasing disease problems on an established before using other types of insecticides and introducing them indoors. Do not plant in your home or office, isolate or miticides. Alternatively, consider purchase or bring home plants with the plant immediately to prevent using a systemic pesticide that can be possible insect, mite or disease infes- the problem from spreading to other applied to the soil, thus avoiding foliar tations. Carefully examine all parts plants. As an additional precaution, sprays. Soil drenches or applications of the plant, including leaf surfaces, wash your hands after touching infest- of insecticide granules may control leaf bases, flower and fruit stalks, and ed plants. soilborne insects; the potting medi- roots, looking for evidence of possi- ble insect pests or disease problems. Make sure you identify the pest or um should be well watered before Houseplants can often be removed disease correctly in order to choose applying a drench or after applying from their containers so that roots can effective management and control granules. Be certain to follow safety be examined. Reject plants that show options. In many instances, control guidelines on the product’s label. evidence of insect or mite infestations of a houseplant pest is impractical as well as possible disease symptoms, or nearly impossible once the pest is such as discolored stems and roots established. The best course of action or leaf spots; these blemishes are not in these situations is to discard the likely to disappear. plant and consider starting fresh with a new one. Select plants with growing require- ments (especially light and tempera-
```

## (3) generate 동반 플래그
`{'rag_failed': False, 'rag_no_docs': False, 'rag_weak_evidence': False}`

## (4) AI 최종 출력 structured_result
```json
{
  "summary": "드라세나 산데리아나의 잎끝과 가장자리에 갈변이 관찰됩니다.",
  "current_state": "여러 잎의 끝과 가장자리가 갈색으로 변한 상태입니다.",
  "cause": "과습 또는 영양 부족일 수 있습니다.",
  "action_plan": [
    "물 주는 빈도를 조절하고 흙의 배수를 개선합니다.",
    "영양제를 적절히 사용하여 식물의 건강을 회복합니다."
  ],
  "status": "병해 의심"
}
```