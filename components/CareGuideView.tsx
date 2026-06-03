import { CareGuide } from "../types/diagnosis";

type Props = {
  careGuide: CareGuide; // null 아님 보장(care 진입 = care_guide 존재). 진입 가드는 index.tsx.
  onBack: () => void; // 결과 화면으로 복귀
};

// ── 시안 인라인 SVG 헬퍼 (plantia_care_guide.html 1:1 이식) ───────────
function SoilIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <path d="M4 19 Q13 10 22 19" stroke="#2A5428" strokeWidth="1.7" strokeLinecap="round" fill="none" />
      <line x1="4" y1="21" x2="22" y2="21" stroke="#2A5428" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M13 18 L13 10 M10 14 Q13 10 16 14" stroke="#2A5428" strokeWidth="1.5" strokeLinecap="round" fill="none" />
    </svg>
  );
}

function PlacementIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <path d="M8 14 L7 22 L19 22 L18 14 Z" stroke="#2A5428" strokeWidth="1.6" strokeLinejoin="round" fill="none" />
      <line x1="6" y1="14" x2="20" y2="14" stroke="#2A5428" strokeWidth="1.6" strokeLinecap="round" />
      <line x1="13" y1="14" x2="13" y2="7" stroke="#2A5428" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M13 10 Q9 7 9 4 Q12 4 13 8" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" fill="none" />
      <path d="M13 9 Q17 6 17 3 Q14 3 13 7" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" fill="none" />
    </svg>
  );
}

function SeasonHeaderDrop() {
  return (
    <svg width="20" height="20" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path
        d="M11 2 C16 8 19 13 19 16.5 C19 20 15.4 22 11 22 C6.6 22 3 20 3 16.5 C3 13 6 8 11 2Z"
        stroke="#2A5428"
        strokeWidth="1.7"
        fill="none"
      />
      <path d="M8 17 Q11 13 14 17" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" fill="none" />
    </svg>
  );
}

// 계절 물방울 공통 외곽
function DropOuter() {
  return (
    <path
      d="M26 3 C38 17 49 33 49 46 C49 57 38.5 63 26 63 C13.5 63 3 57 3 46 C3 33 14 17 26 3 Z"
      fill="#EBF6E5"
      stroke="#2A5428"
      strokeWidth="1.8"
    />
  );
}

function SpringDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 52 64" fill="none" aria-hidden="true">
      <DropOuter />
      <line x1="26" y1="54" x2="26" y2="36" stroke="#2A5428" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M26 44 Q20 40 18 33 Q23 32 26 38" fill="none" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M26 44 Q32 40 34 33 Q29 32 26 38" fill="none" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function SummerDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 52 64" fill="none" aria-hidden="true">
      <DropOuter />
      <circle cx="26" cy="42" r="8" stroke="#2A5428" strokeWidth="1.6" fill="none" />
      <line x1="26" y1="26" x2="26" y2="30" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="26" y1="54" x2="26" y2="58" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="10" y1="42" x2="14" y2="42" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="38" y1="42" x2="42" y2="42" stroke="#2A5428" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="14.9" y1="31" x2="17.8" y2="33.8" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="37.1" y1="31" x2="34.2" y2="33.8" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="17.8" y1="50.2" x2="14.9" y2="53" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="34.2" y1="50.2" x2="37.1" y2="53" stroke="#2A5428" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function AutumnDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 52 64" fill="none" aria-hidden="true">
      <DropOuter />
      <path d="M20 30 C17 27 15 22 18 19 C22 19 24 24 20 30Z" stroke="#2A5428" strokeWidth="1.3" fill="none" strokeLinejoin="round" />
      <line x1="20" y1="30" x2="16" y2="36" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M34 40 C31 37 29 32 32 29 C36 29 38 34 34 40Z" stroke="#2A5428" strokeWidth="1.3" fill="none" strokeLinejoin="round" />
      <line x1="34" y1="40" x2="30" y2="46" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M22 50 C19 47 17 42 20 39 C24 39 26 44 22 50Z" stroke="#2A5428" strokeWidth="1.3" fill="none" strokeLinejoin="round" />
      <line x1="22" y1="50" x2="18" y2="56" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

function WinterDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 52 64" fill="none" aria-hidden="true">
      <DropOuter />
      <line x1="26" y1="24" x2="26" y2="58" stroke="#2A5428" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="11.6" y1="32" x2="40.4" y2="50" stroke="#2A5428" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="40.4" y1="32" x2="11.6" y2="50" stroke="#2A5428" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="26" y1="32" x2="22" y2="28" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <line x1="26" y1="32" x2="30" y2="28" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <line x1="26" y1="50" x2="22" y2="54" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <line x1="26" y1="50" x2="30" y2="54" stroke="#2A5428" strokeWidth="1.1" strokeLinecap="round" />
      <circle cx="26" cy="41" r="2.5" fill="#2A5428" />
    </svg>
  );
}

function TempIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="2" width="6" height="14" rx="3" stroke="#3A6E37" strokeWidth="1.7" fill="none" />
      <circle cx="12" cy="17" r="4" stroke="#3A6E37" strokeWidth="1.7" fill="none" />
      <circle cx="12" cy="17" r="2" fill="#3A6E37" />
      <line x1="11" y1="7" x2="13" y2="7" stroke="#3A6E37" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="11" y1="10" x2="13" y2="10" stroke="#3A6E37" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function HumidityIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2 C17 8 20 13 20 16.5 C20 20 16.4 22 12 22 C7.6 22 4 20 4 16.5 C4 13 7 8 12 2Z"
        stroke="#3A6E37"
        strokeWidth="1.7"
        fill="none"
      />
      <path d="M9 16 Q12 12.5 15 16" stroke="#3A6E37" strokeWidth="1.3" strokeLinecap="round" fill="none" />
    </svg>
  );
}

function FertilizerIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="5" y="8" width="14" height="13" rx="3" stroke="#3A6E37" strokeWidth="1.7" fill="none" />
      <path
        d="M8 8 L8 5 Q8 3 10 3 L14 3 Q16 3 16 5 L16 8"
        stroke="#3A6E37"
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line x1="9" y1="13" x2="15" y2="13" stroke="#3A6E37" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="9" y1="16" x2="13" y2="16" stroke="#3A6E37" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

// 빈값 판정(공백 문자열도 미표시)
const filled = (v: string | null | undefined): v is string => typeof v === "string" && v.trim() !== "";

export default function CareGuideView({ careGuide, onBack }: Props) {
  // ── 지속 관리법 4그리드 (개별 null → 셀 숨김) ──
  const careCells = [
    { key: "soil", label: "토양", value: careGuide.soil, icon: <SoilIcon />, badge: false },
    { key: "light", label: "광량", value: careGuide.light, icon: <i className="ti ti-sun" aria-hidden="true" />, badge: false },
    { key: "placement", label: "배치", value: careGuide.placement, icon: <PlacementIcon />, badge: false },
    {
      key: "manage",
      label: "관리 난이도",
      value: careGuide.manage_level,
      icon: <i className="ti ti-gauge" aria-hidden="true" />,
      badge: true,
    },
  ].filter((c) => filled(c.value));

  // ── 계절별 물주기 (water null → 섹션 전체 숨김 / 개별 null → 카드 숨김) ──
  const water = careGuide.water;
  const seasonDefs = [
    { key: "spring", name: "봄", value: water?.spring, Drop: SpringDrop },
    { key: "summer", name: "여름", value: water?.summer, Drop: SummerDrop },
    { key: "autumn", name: "가을", value: water?.autumn, Drop: AutumnDrop },
    { key: "winter", name: "겨울", value: water?.winter, Drop: WinterDrop },
  ];
  const seasonCards = water ? seasonDefs.filter((s) => filled(s.value)) : [];

  // ── 환경 정보 (개별 null → 행 숨김) ──
  const infoRows = [
    { key: "temperature", label: "생육 적온", value: careGuide.temperature, icon: <TempIcon /> },
    { key: "humidity", label: "습도", value: careGuide.humidity, icon: <HumidityIcon /> },
    { key: "fertilizer", label: "비료", value: careGuide.fertilizer, icon: <FertilizerIcon /> },
  ].filter((r) => filled(r.value));

  const showManageCard = careCells.length > 0 || seasonCards.length > 0;

  return (
    <section className="cg">
      {/* 페이지 헤더 — 뒤로가기 추가, ✦ 제거 */}
      <div className="pg-header">
        <button className="pg-back" type="button" onClick={onBack} aria-label="결과 화면으로 돌아가기">
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>
        <h2 className="pg-title">케어 가이드</h2>
        <span className="pg-plus" aria-hidden="true">✦</span>
      </div>

      {/* Card 1: 지속 관리법 + 계절별 물주기 */}
      {showManageCard ? (
        <div className="card">
          <div className="sec-hdr">
            <div className="sec-icon">
              <i className="ti ti-leaf" aria-hidden="true" />
            </div>
            <div>
              <div className="sec-title">지속 관리법</div>
              <div className="sec-sub">건강한 성장을 위해 꾸준히 관리해 주세요.</div>
            </div>
          </div>

          {careCells.length > 0 ? (
            <div className="care-list">
              {careCells.map((cell) => (
                <div className="care-row" key={cell.key}>
                  <div className="care-ic">{cell.icon}</div>
                  <div className="care-lbl">{cell.label}</div>
                  {cell.badge ? (
                    <span className="diff-badge">{cell.value}</span>
                  ) : (
                    <div className="care-val">{cell.value}</div>
                  )}
                </div>
              ))}
            </div>
          ) : null}

          {seasonCards.length > 0 ? (
            <div className="season-wrap">
              <div className="season-hdr">
                <div className="season-icon">
                  <SeasonHeaderDrop />
                </div>
                <div className="season-hdr-title">계절별 물주기</div>
              </div>
              <div className="season-grid">
                {seasonCards.map((s) => (
                  <div className="season-card" key={s.key}>
                    <s.Drop />
                    <div>
                      <div className="s-name">{s.name}</div>
                      <div className="s-freq">{s.value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Card 2: 환경 정보 리스트 */}
      {infoRows.length > 0 ? (
        <div className="card info-card">
          {infoRows.map((row) => (
            <div className="info-row" key={row.key}>
              <div className="info-ic">{row.icon}</div>
              <div className="info-lbl">{row.label}</div>
              <div className="info-val">{row.value}</div>
            </div>
          ))}
        </div>
      ) : null}

      <style jsx>{`
        .cg {
          display: flex;
          flex-direction: column;
          animation: fadeIn 0.26s ease;
        }

        /* 페이지 헤더 */
        .pg-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 20px;
        }
        .pg-back {
          background: none;
          border: none;
          cursor: pointer;
          line-height: 1;
          padding: 4px 4px 4px 0;
          color: var(--green-dark);
          display: flex;
          align-items: center;
        }
        .pg-back i {
          font-size: 26px;
        }
        .pg-title {
          font-size: 22px;
          font-weight: 800;
          color: var(--green-dark);
          letter-spacing: -0.02em;
          margin: 0;
        }
        .pg-plus {
          margin-left: auto; /* 좌측 뒤로+제목 유지, ✦만 우측 정렬(정본 .cg-hdr ✦ 복원) */
          font-size: 18px;
          color: var(--text-disabled);
        }

        /* 카드 베이스 */
        .card {
          background: var(--bg-card);
          border-radius: var(--radius-card);
          padding: 20px;
          margin-bottom: 14px;
          box-shadow: var(--shadow-card);
        }
        .info-card {
          padding: 4px 20px;
        }

        /* 섹션 헤더 */
        .sec-hdr {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 18px;
        }
        .sec-icon {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-circle);
          background: var(--bg-section-header-icon);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .sec-icon i {
          font-size: 22px;
          color: var(--green-dark);
        }
        .sec-title {
          font-size: 17px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }
        .sec-sub {
          font-size: 12.5px;
          color: var(--text-muted);
          margin-top: 3px;
          font-weight: 500;
        }

        /* 케어 리스트 (세로 1열 스택 — 환경 정보 행과 통일) */
        .care-list {
          display: flex;
          flex-direction: column;
        }
        .care-row {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 13px 2px;
          border-bottom: 1.2px dashed var(--border-dashed-guide);
        }
        .care-row:last-child {
          border-bottom: none;
        }
        .care-ic {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .care-ic i {
          font-size: 22px;
          color: var(--green-dark);
        }
        .care-lbl {
          font-size: 14.5px;
          color: var(--text-secondary);
          font-weight: 500;
          flex: 1;
          white-space: nowrap;
        }
        .care-val {
          font-size: 14px;
          color: #283a2a;
          font-weight: 600;
          line-height: 1.5;
          text-align: right;
        }
        .diff-badge {
          background: var(--bg-section-header-icon);
          color: var(--green-dark);
          font-size: 12px;
          font-weight: 700;
          padding: 5px 16px;
          border-radius: 30px;
          white-space: nowrap;
          flex-shrink: 0;
        }

        /* 계절별 물주기 서브섹션 */
        .season-wrap {
          background: var(--bg-season-wrap);
          border-radius: var(--radius-season-wrap);
          padding: 16px;
          margin-top: 16px;
        }
        .season-hdr {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }
        .season-icon {
          width: 38px;
          height: 38px;
          border-radius: var(--radius-circle);
          background: var(--bg-season-icon);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .season-hdr-title {
          font-size: 16px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }
        .season-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .season-card {
          background: var(--bg-card);
          border-radius: var(--radius-season-card);
          padding: 14px 12px;
          display: flex;
          align-items: center;
          gap: 10px;
          box-shadow: 0 1px 4px rgba(42, 84, 40, 0.06);
        }
        .s-name {
          font-size: 14px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }
        .s-freq {
          font-size: 12.5px;
          color: var(--text-muted);
          margin-top: 2px;
          font-weight: 500;
        }

        /* 환경 정보 리스트 */
        .info-row {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 13px 0;
          border-bottom: 1.2px dashed var(--border-dashed-guide);
        }
        .info-row:last-child {
          border-bottom: none;
        }
        .info-ic {
          width: 42px;
          height: 42px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .info-lbl {
          font-size: 14.5px;
          color: var(--text-primary);
          font-weight: 500;
          flex: 1;
          white-space: nowrap; /* 긴 값(비료)에 라벨이 두 줄로 쪼개지지 않게 */
          flex-shrink: 0;
        }
        .info-val {
          font-size: 14.5px;
          color: var(--green-dark);
          font-weight: 600;
          min-width: 0; /* 긴 값이 값 쪽에서 줄바꿈되도록 */
          text-align: right;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      <style jsx global>{`
        .cg .drop-svg {
          width: 42px;
          height: 50px;
          flex-shrink: 0;
        }
      `}</style>
    </section>
  );
}
