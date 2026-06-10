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

export type CareWater = {
  spring: string | null;
  summer: string | null;
  autumn: string | null;
  winter: string | null;
};

export type CareGuide = {
  species_key: string;
  display_name: string | null;
  src_cntntsNo: string | null;
  scientific_name: string | null;
  soil: string | null;
  water: CareWater | null;
  light: string | null;
  temperature: string | null;
  humidity: string | null;
  fertilizer: string | null;
  placement: string | null;
  manage_level: string | null;
  winter_min_temp: string | null;
  growth_height_cm: string | null;
  growth_area_cm: string | null;
  note: string | null;
};

// [챗봇 2차 보정] 백엔드 app/schemas.py와 1:1 정합.
// RefineContext = 1차 generate가 쓴 RAG 컨텍스트(2차 generate-only 재실행 재료).
export type RefineContext = {
  rag_docs: string[];
  top_3_problem_type_weighted: Record<string, unknown>;
  rag_failed: boolean;
  rag_no_docs: boolean;
  rag_weak_evidence: boolean;
};

// 객관식 문답 1쌍.
export type FollowupAnswer = {
  question: string;
  answer: string;
};

// /diagnose/refine 요청 — 1차 analysis·refine_context echo-back + 답변.
export type RefineRequest = {
  analysis: AnalysisResult;
  refine_context: RefineContext;
  answers: FollowupAnswer[];
};

export type DiagnosisResponse = {
  message: string;
  analysis: AnalysisResult | null;
  structured_result: StructuredResult;
  care_guide: CareGuide | null;
  // [챗봇 2차 보정] 1차 응답이 실어 보내는 2차 재실행 재료(echo-back용). 1차에만 존재.
  refine_context?: RefineContext | null;
};
