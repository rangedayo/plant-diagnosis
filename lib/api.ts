import { DiagnosisResponse, RefineRequest } from "../types/diagnosis";
import { auth } from "./firebase";

// [인증 통합] 보호 엔드포인트 호출 시 Firebase ID 토큰을 Authorization에 첨부.
// 비로그인(currentUser 없음)이면 헤더 없음 → 백엔드 401(이 경로는 로그인 상태에서만 호출됨).
async function authHeader(): Promise<Record<string, string>> {
  const user = auth.currentUser;
  if (!user) return {};
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

const LOGIN_REQUIRED_MESSAGE = "로그인 후 진단을 이용할 수 있습니다.";

// [배포 비용 가드] 진단(Gemini·OpenAI 과금)은 로그인 필수. 토큰 없이 보내도 백엔드가 401이므로,
// 왕복 없이 같은 안내를 먼저 던져 화면 에러 배너에 그대로 표시한다.
async function requireAuthHeader(): Promise<Record<string, string>> {
  const header = await authHeader();
  if (!header.Authorization) {
    throw new Error(LOGIN_REQUIRED_MESSAGE);
  }
  return header;
}

export async function diagnosePlant(file: File): Promise<DiagnosisResponse> {
  const headers = await requireAuthHeader();

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/diagnose", {
    method: "POST",
    headers,
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

// [챗봇 2차 보정] 1차 analysis·refine_context를 변형 없이 echo-back + 객관식 답변을 실어
// /diagnose/refine 호출 → 2차 DiagnosisResponse. diagnosePlant와 동일 에러 처리 패턴.
export async function refineDiagnosis(req: RefineRequest): Promise<DiagnosisResponse> {
  const response = await fetch("/diagnose/refine", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await requireAuthHeader()) },
    body: JSON.stringify(req),
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
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
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

// [추이 요약] 진단 이력 전체(시간순 오래된→최신)를 백엔드 /trend로 전달 → 전반 흐름 간결 요약.
// 백엔드 TrendRequest(diagnoses)·TrendResponse(trend)와 1:1 대응. comparePlantDiagnoses와 동일 패턴.
export type TrendResponse = {
  trend: string;
};

export async function summarizeDiagnosisTrend(
  diagnoses: DiagnosisSnapshot[],
): Promise<TrendResponse> {
  const response = await fetch("/trend", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: JSON.stringify({ diagnoses }),
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

  return (await response.json()) as TrendResponse;
}
