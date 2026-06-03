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

export type DiagnosisResponse = {
  message: string;
  analysis: AnalysisResult | null;
  structured_result: StructuredResult;
  care_guide: CareGuide | null;
};
