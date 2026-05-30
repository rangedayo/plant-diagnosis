export type AnalysisResult = {
  plant_name: string | null;
  plant_name_korean: string | null;
  plant_confidence: "low" | "med" | "high" | null;
  alt_candidates: string[];
  visual_description: string;
  observed_symptoms: string[];
};

export type StructuredResult = {
  summary: string;
  current_state: string;
  cause: string;
  action_plan: string[];
  status: string;
};

export type DiagnosisResponse = {
  message: string;
  analysis: AnalysisResult | null;
  structured_result: StructuredResult;
};
