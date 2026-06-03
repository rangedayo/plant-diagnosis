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
