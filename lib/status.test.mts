// [UI status 표시 분기] statusLabel / statusToTier 단위 테스트.
// 실행: node --test lib/status.test.mts  (Node 24+ 타입 스트립, 추가 의존성 0, 모델 호출 0)
// .mts 확장자 → tsconfig "**/*.ts" glob 미포함 → next build/lint 무간섭.
import test from "node:test";
import assert from "node:assert/strict";
import { statusLabel, statusToTier } from "./status.ts";

// status 7종(+경미) → 기대 (거친/세부) 라벨. 경계는 run_eval _status_to_tier와 일치.
const CASES: Array<{ status: string; coarse: string; detail: string; tier: string }> = [
  { status: "건강", coarse: "건강", detail: "건강", tier: "건강" },
  { status: "경미", coarse: "양호 (가벼운 주의)", detail: "경미", tier: "경미" },
  { status: "과습", coarse: "주의 관찰", detail: "비건강 · 과습", tier: "비건강" },
  { status: "건조", coarse: "주의 관찰", detail: "비건강 · 건조", tier: "비건강" },
  { status: "병해 의심", coarse: "주의 관찰", detail: "비건강 · 병해 의심", tier: "비건강" },
  { status: "영양 부족", coarse: "주의 관찰", detail: "비건강 · 영양 부족", tier: "비건강" },
  { status: "비건강-원인미상", coarse: "주의 관찰", detail: "비건강 · 원인미상", tier: "비건강" },
];

for (const c of CASES) {
  test(`statusLabel(${c.status}) → coarse/detail`, () => {
    const { coarse, detail } = statusLabel(c.status);
    assert.equal(coarse, c.coarse);
    assert.equal(detail, c.detail);
  });
  test(`statusToTier(${c.status}) = ${c.tier}`, () => {
    assert.equal(statusToTier(c.status), c.tier);
  });
}

test("빈값/null → 라벨 빈 문자열 + tier null (호출부 fallback)", () => {
  for (const empty of ["", "   ", null, undefined]) {
    const { coarse, detail } = statusLabel(empty);
    assert.equal(coarse, "");
    assert.equal(detail, "");
    assert.equal(statusToTier(empty), null);
  }
});

test("미지원 status → 안전 측 비건강 (run_eval과 동일)", () => {
  const { coarse, detail } = statusLabel("미지원값");
  assert.equal(statusToTier("미지원값"), "비건강");
  assert.equal(coarse, "주의 관찰");
  assert.equal(detail, "비건강 · 미지원값");
});

test("앞뒤 공백 trim", () => {
  assert.equal(statusToTier("  건강  "), "건강");
  assert.equal(statusLabel("  경미  ").coarse, "양호 (가벼운 주의)");
});
