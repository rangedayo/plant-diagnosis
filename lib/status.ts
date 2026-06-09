// status 원값 → 배지 메인 색 (CSS 변수명 반환)
// R0 §B-1 확정 매핑. 실제 ALLOWED_STRUCT_STATUS 5종을 3색 + fallback(정보색)에 대응.
export const STATUS_COLOR: Record<string, string> = {
  "건강": "var(--status-healthy)",
  "과습": "var(--status-caution)",
  "건조": "var(--status-caution)",
  "영양 부족": "var(--status-caution)",
  "병해 의심": "var(--status-disease)",
};

export function statusColor(status: string | null | undefined): string {
  if (!status) return "var(--status-info)";
  return STATUS_COLOR[status] ?? "var(--status-info)"; // 미스 키 → fallback
}

// status 원값 → 배지 배경/텍스트 색 페어 (시트 §상태 색 ※제안값, R2 시각 확정 대상)
export const STATUS_BADGE: Record<string, { bg: string; fg: string }> = {
  "건강": { bg: "#D8F0CC", fg: "#2A5428" },
  "과습": { bg: "#FBF1D2", fg: "#7A5B12" },
  "건조": { bg: "#FBF1D2", fg: "#7A5B12" },
  "영양 부족": { bg: "#FBF1D2", fg: "#7A5B12" },
  "병해 의심": { bg: "#FBE2DD", fg: "#9A3D32" },
};

export function statusBadge(status: string | null | undefined): { bg: string; fg: string } {
  if (!status) return { bg: "#E3EEF5", fg: "#3A5B70" }; // fallback(정보색)
  return STATUS_BADGE[status] ?? { bg: "#E3EEF5", fg: "#3A5B70" };
}

// ── [UI status 표시 분기] 3단 tier 거친 라벨 / 디버그 세부 라벨 ──
// 경계 진실원 = scripts/run_eval.py `_status_to_tier` (R16). 프론트는 Python을
// import할 수 없으므로 동일 경계를 TS로 미러링(중복 정의 아님, 측정용과 표시용 분리).
//   건강 → 건강 · 경미 → 경미 · 그 외 비건강 status → 비건강.
// 빈값/None은 표시 fallback을 위해 null (run_eval은 None만 None, 측정엔 빈값 안 옴).
export type StatusTier = "건강" | "경미" | "비건강";

export function statusToTier(status: string | null | undefined): StatusTier | null {
  const s = (status ?? "").trim();
  if (!s) return null;
  if (s === "건강") return "건강";
  if (s === "경미") return "경미";
  return "비건강"; // 5종 비건강 + 비건강-원인미상 + 미지원값(안전 측=비건강), run_eval과 동일
}

// tier → 사용자 거친 라벨 (사용자(랑) 확정 문구). 종/케이스 하드코딩 없이 tier로만 분기.
const COARSE_BY_TIER: Record<StatusTier, string> = {
  "건강": "건강",
  "경미": "양호 (가벼운 주의)",
  "비건강": "주의 관찰",
};

// status → { coarse: 사용자 거친 라벨, detail: 디버그 세부 라벨 }
// detail은 비건강일 때 "비건강 · {원본 status}"로 원본을 그대로 포함(원인미상은 접두 제거).
// 빈값 → 둘 다 "" (호출부에서 "진단 완료" 등으로 fallback).
export function statusLabel(status: string | null | undefined): { coarse: string; detail: string } {
  const tier = statusToTier(status);
  if (tier === null) return { coarse: "", detail: "" };
  const coarse = COARSE_BY_TIER[tier];
  if (tier !== "비건강") {
    const s = (status ?? "").trim(); // 건강 / 경미 → detail = 원본
    return { coarse, detail: s };
  }
  const s = (status ?? "").trim();
  const cause = s === "비건강-원인미상" ? "원인미상" : s;
  return { coarse, detail: `비건강 · ${cause}` };
}
