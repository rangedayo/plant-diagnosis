import { DiagnosisResponse } from "../types/diagnosis";

export async function diagnosePlant(file: File): Promise<DiagnosisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/diagnose", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `요청 실패 (${response.status})`;
    try {
      const errorBody = (await response.json()) as { detail?: string };
      if (errorBody?.detail) {
        errorMessage = errorBody.detail;
      }
    } catch {
      // ignore json parse failures and keep fallback message
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as DiagnosisResponse;
}

// [시계열 3단계] 진단 비교 — 두 진단의 정성 스냅샷을 백엔드 /compare로 전달.
// 백엔드 CompareRequest(previous/current)·CompareResponse(comparison)와 1:1 대응.
export type DiagnosisSnapshot = {
  date: string;
  status: string;
  summary: string;
  current_state: string;
  cause: string;
  action_plan: string[];
  observed_symptoms: string[];
};

export type CompareResponse = {
  comparison: string;
};

export async function comparePlantDiagnoses(
  previous: DiagnosisSnapshot,
  current: DiagnosisSnapshot,
): Promise<CompareResponse> {
  const response = await fetch("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ previous, current }),
  });

  if (!response.ok) {
    let errorMessage = `요청 실패 (${response.status})`;
    try {
      const errorBody = (await response.json()) as { detail?: string };
      if (errorBody?.detail) {
        errorMessage = errorBody.detail;
      }
    } catch {
      // ignore json parse failures and keep fallback message
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as CompareResponse;
}
