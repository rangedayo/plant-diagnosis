# generate 입력 컨텍스트 덤프 - inat_sansevieria_trifasciata_002

> 단계 B' 측정 당시 구조를 재현한 **재실행** 덤프 (analyze=Gemini 비결정이라 바이트 동일이 아닌 동일 파이프라인 1회 실행). 종 정상화 카드 섹션은 결정적.

## 메타
- ground_truth: plant=`산세베리아`, is_healthy=**True**, gt_diagnosis="실내 화분에서 자라는 성숙한 산세베리아. 잎이 곧고 색·가로 줄무늬 모두 정상이며, 다수의 꽃대가 올라온 것은 식물이 충분히 성숙·건강한 상태라는 신호."
- analyze 식별: plant_name=`Dracaena trifasciata` / 통명=`산세베리아` / conf=`high`
- observed_symptoms: `['잎 일부 갈변']`
- rag_query: `Dracaena trifasciata 잎 일부 갈변`
- 종 정상화 카드 매칭: species=`산세베리아` (카드 1건)
- RAG 청크: 총 10개 중 **[disease] 2개**
- 분포(top_3 problem_type 가중): `{'majority': 'tie', 'distribution': {'abiotic': 0.3347, 'disease': 0.3336, 'frame': 0.3317}, 'top_problem_type': 'abiotic'}`
- **AI 최종 진단 status: `병해 의심`**  (gt_healthy=True -> FP 오진)

## (1) generate가 받은 context_summary (묘사+관찰+분포+종 카드)
```
묘사:
길고 뾰족한 칼 모양의 잎들이 빽빽하게 위로 뻗어 자라는 다육질 식물. 잎 표면은 짙은 녹색 바탕에 밝은 회녹색의 불규칙한 가로 줄무늬가 있어 뱀가죽 같은 무늬를 형성함. 잎들 사이에서 여러 개의 긴 꽃대가 올라와 있으며, 연한 녹백색의 작은 꽃들이 뭉쳐서 피어 있음.

[관찰 정보]
- 식물명(학명 1위): Dracaena trifasciata
- 식물명(통명): 산세베리아
- 식별 신뢰도: high
- 대안 후보: Dracaena zeylanica, Dracaena hyacinthoides
- 관찰된 증상: 잎 일부 갈변

[검색된 자료의 타입 분포 (top_3 sim 가중)]
- 우세 타입: tie
- 1위 카드 타입: abiotic
- 분포: abiotic 0.33, disease 0.33, frame 0.33

[이 종의 정상 생육 특성 (참고)]
- [산세베리아] 산세베리아(스네이크플랜트)의 정상 생육 특성: 대표적인 CAM 공기정화식물이다. 잎 가장자리에 노란 테두리가 있는 품종이 가장 보편적이며, 금색·노란색·흰색·크림색 무늬는 품종 고유의 정상적인 잎 색이다.

```

## (2) generate가 받은 rag_chunks (b_dataset/main RAG, problem_type prefix)
```
[abiotic] Brown leaf tips • Chemical: Brown leaf tips • Chemical burn from overapplication of pesticides or fertilizer • Soft water • Soil remains dry for extended periods of time • Temperature is too low

[disease] Leaf spot fungus: Leaf spot fungus — oval, brown/black spots, not limited by leaf veins, often with a yellow halo or purple band. Airborne spores spread to healthy leaves. Commonly affected plants include palms, yucca, orchids, prayer plant and dumbcane.

[frame] Occasionally, leaves of seemingly healthy houseplants begin…: Occasionally, leaves of seemingly healthy houseplants begin to develop brown tips and margins, dead spots and yellowing. A common assumption is that a disease caused by a pathogen such as a fungus or bacterium might have infested the symptomatic plant. More often, however, these symptoms are the result of an unfavorable environment. Low relative humidity, insufficient light, over or under watering, or too much or too little fertilizer can lead to leaf damage that mimics disease symptoms. To make the problem even more difficult to diagnose, leaf problems often are due to a combination of these environmental factors.

[Marginal or Tip Leaf Burn]
symptoms: Burning of leaf margins or tips, Production of smaller leaves, Discolored or damaged leaf edges
cause: Over-fertilization, Under-watering, High fluoride levels in water or potting soil, Salt buildup in soil from poor quality water
solution: Repot the plant with fresh potting soil, Use scissors to reshape and trim burned tips, Improve water quality if using high-salt or hard water, Adjust watering and fertilization frequency

[Leaves Small and Off-Color]
symptoms: New leaves appearing smaller than normal, Leaves showing pale or unusual coloration, Visible signs of poor plant vigor
cause: Lack of essential nutrients (poor nutrition), Root death caused by over-watering, Inconsistent feeding schedule
solution: Begin a regular monthly liquid fertilizer program, Reduce fertilization frequency during low-light winter days, Adjust watering habits to prevent root damage

[general] The pattern of leaf damage also can…: The pattern of leaf damage also can provide clues relative to the cause. In the case of damage caused by a disease, the progression of symptoms often transitions from healthy (green) tissue, to chlorotic (yellow) and, finally, to necrotic (brown) tissue. Additionally, when true diseases attack leaves, the dead or dying spots often are scattered on the leaf and occur closer to the growing medium or in the center of the plant where relative humidity is higher or where water got on leaves when the plant was watered.

[nutrient] Nitrogen deficiency: Nitrogen deficiency The oldest leaves turn yellow at the margins and progress inward, which may lead to defoliation and reduced growth. When severe, only the new growth remains green while the rest of the foliage is yellow. An application of a fertilizer with nitrogen can give quick green-up effects.

[env] Sunburn: Sunburn Leaves or tissues turn brown or tan on the side of the plant directly aligned with the sun. This pattern is a good indicator of sunburn. In may cases the plant will still grow but may be stunted for a while. Move the plant out of direct sunshine. Remove the damaged tissues.

[disease] Anthracnose Collectrotrichum: Anthracnose Collectrotrichum • Leaf tips turn yellow, then • Remove infected leaves and Gloeosporium fungi brown • Avoid misting leaves • Entire leaf may die

[Brown or scorched leaf tips:]
symptoms: Brown or scorched leaf tips:
cause: Poor health from overwatering, excessive soil dryness (especially between waterings), excessive fertilizer or other soluble salts in the soil or water, Specific nutrient toxicities (e.g., fluoride, copper, or boron), Low humidity, Pesticide or mechanical injury.
solution: The best approach to long term or greenhouse, if available, to reju- and leaf undersides thoroughly. If management is to emphasize preven- venate them. In such cases, inspect possible, spray the plant outdoors so tion through pest exclusion, proper plants closely for pests after returning that the spray residue will be dispersed sanitation, and cultural practices that them indoors and continue to monitor outside, and you will not have to worry create optimal growing conditions and them for a few weeks to assure they are about damaging furniture surfac- plant health. pest-free. es or exposing others to pesticides. Consider using a soap or horticultur- Practice pest exclusion by thoroughly Whenever you detect insect, mite, or al oil, if labeled for your plant pest, examining plants prior to purchasing disease problems on an established before using other types of insecticides and introducing them indoors. Do not plant in your home or office, isolate or miticides. Alternatively, consider purchase or bring home plants with the plant immediately to prevent using a systemic pesticide that can be possible insect, mite or disease infes- the problem from spreading to other applied to the soil, thus avoiding foliar tations. Carefully examine all parts plants. As an additional precaution, sprays. Soil drenches or applications of the plant, including leaf surfaces, wash your hands after touching infest- of insecticide granules may control leaf bases, flower and fruit stalks, and ed plants. soilborne insects; the potting medi- roots, looking for evidence of possi- ble insect pests or disease problems. Make sure you identify the pest or um should be well watered before Houseplants can often be removed disease correctly in order to choose applying a drench or after applying from their containers so that roots can effective management and control granules. Be certain to follow safety be examined. Reject plants that show options. In many instances, control guidelines on the product’s label. evidence of insect or mite infestations of a houseplant pest is impractical as well as possible disease symptoms, or nearly impossible once the pest is such as discolored stems and roots established. The best course of action or leaf spots; these blemishes are not in these situations is to discard the likely to disappear. plant and consider starting fresh with a new one. Select plants with growing require- ments (especially light and tempera-
```

## (3) generate 동반 플래그
`{'rag_failed': False, 'rag_no_docs': False, 'rag_weak_evidence': False}`

## (4) AI 최종 출력 structured_result
```json
{
  "summary": "산세베리아의 잎 일부가 갈변하고 있습니다.",
  "current_state": "잎 일부가 갈변하여 손상된 상태입니다.",
  "cause": "과습 또는 영양 부족일 수 있습니다.",
  "action_plan": [
    "물빠짐이 좋은 흙으로 옮겨 심기",
    "정기적으로 비료를 주어 영양 상태 개선하기"
  ],
  "status": "병해 의심"
}
```