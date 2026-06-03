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
