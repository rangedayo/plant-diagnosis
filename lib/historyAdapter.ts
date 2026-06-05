import { DiagnosisRecord, PlantSummary } from "./db";
import { DiagnosisResponse } from "../types/diagnosis";

// Firestore DiagnosisRecord → ResultView가 기대하는 DiagnosisResponse 변환 (history 표시 전용).
//
// ⚠ analysis는 부분 mock: 저장 시 plant_name을 보존하지 않았고, 사용자 별칭(plant.name)이
//   매번 달라질 수 있는 AI 식별 결과보다 안정적·의미 있음 → plant_name_korean에 별칭 주입.
//   이 mock은 ResultView 입력 전용 — 외부로 노출 금지(다른 곳에서 analysis 사용 시 mock이 샘).
//   추후 saveDiagnosis가 plant_name을 직접 저장하면 이 변환에서 제거.
export function diagnosisRecordToResponse(
  record: DiagnosisRecord,
  plant: Pick<PlantSummary, "name">,
): DiagnosisResponse {
  return {
    message: "",
    analysis: {
      plant_name: null,
      plant_name_korean: plant.name,
      plant_confidence: null,
      alt_candidates: [],
      visual_description: "",
      observed_symptoms: record.observedSymptoms,
    },
    structured_result: {
      summary: record.summary,
      current_state: record.currentState,
      cause: record.cause,
      action_plan: record.actionPlan,
      status: record.status,
    },
    care_guide: record.careGuide,
  };
}
