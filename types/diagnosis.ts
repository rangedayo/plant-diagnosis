export type Candidate = {
  name: string;
  probability: number;
};

export type PlantIdResult = {
  plant_name: string | null;
  disease_name: string | null;
  confidence: number | null;
  is_healthy_prob: number | null;
  top_candidates: Candidate[];
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
  plant_id: PlantIdResult;
  structured_result: StructuredResult;
};
