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
