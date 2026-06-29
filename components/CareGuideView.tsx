import { CareGuide } from "../types/diagnosis";

type Props = {
  careGuide: CareGuide; // null 아님 보장(care 진입 = care_guide 존재). 진입 가드는 index.tsx.
  onBack: () => void; // 결과 화면으로 복귀
};

// ── 시안 인라인 SVG 헬퍼 (plantia_care_guide.html 1:1 이식) ───────────
function SoilIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#2A5428"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 20h18l-6.921 -14.612a2.3 2.3 0 0 0 -4.158 0l-6.921 14.612" />
      <path d="M7.5 11l2 2.5l2.5 -2.5l2 3l2.5 -2" />
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
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#2A5428"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4.072 20.3a2.999 2.999 0 0 0 3.856 0a3.002 3.002 0 0 0 .67 -3.798l-2.095 -3.227a.6 .6 0 0 0 -1.005 0l-2.098 3.227a3.003 3.003 0 0 0 .671 3.798" />
      <path d="M16.072 20.3a2.999 2.999 0 0 0 3.856 0a3.002 3.002 0 0 0 .67 -3.798l-2.095 -3.227a.6 .6 0 0 0 -1.005 0l-2.098 3.227a3.003 3.003 0 0 0 .671 3.798" />
      <path d="M10.072 10.3a2.999 2.999 0 0 0 3.856 0a3.002 3.002 0 0 0 .67 -3.798l-2.095 -3.227a.6 .6 0 0 0 -1.005 0l-2.098 3.227a3.003 3.003 0 0 0 .671 3.798l.001 0" />
    </svg>
  );
}

// 계절별 물주기 아이콘 (제공 SVG 1:1 이식 — viewBox 64×64, green-medium #3A6E37)
function SpringDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path d="M32 5 C 23 19 12 29 12 42 C 12 53 21 60 32 60 C 43 60 52 53 52 42 C 52 29 41 19 32 5 Z" fill="#f4f8ef" stroke="#3A6E37" strokeWidth="3.4" strokeLinejoin="round" />
      <path d="M32 51 C 32 47 32 43 32 38" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <path d="M32 44 C 27 45 23.5 42 24 37.5 C 29 37.5 32 40.5 32 44 Z" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinejoin="round" />
      <path d="M32 40 C 37 41 40.5 38 40 33.5 C 35 33.5 32 36.5 32 40 Z" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinejoin="round" />
    </svg>
  );
}

function SummerDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path d="M32 5 C 23 19 12 29 12 42 C 12 53 21 60 32 60 C 43 60 52 53 52 42 C 52 29 41 19 32 5 Z" fill="#f4f8ef" stroke="#3A6E37" strokeWidth="3.4" strokeLinejoin="round" />
      <circle cx="32" cy="39" r="4.3" fill="none" stroke="#3A6E37" strokeWidth="2.7" />
      <line x1="38.90" y1="39.00" x2="41.50" y2="39.00" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="36.88" y1="43.88" x2="38.72" y2="45.72" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="32.00" y1="45.90" x2="32.00" y2="48.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="27.12" y1="43.88" x2="25.28" y2="45.72" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="25.10" y1="39.00" x2="22.50" y2="39.00" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="27.12" y1="34.12" x2="25.28" y2="32.28" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="32.00" y1="32.10" x2="32.00" y2="29.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="36.88" y1="34.12" x2="38.72" y2="32.28" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
    </svg>
  );
}

function AutumnDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path d="M32 5 C 23 19 12 29 12 42 C 12 53 21 60 32 60 C 43 60 52 53 52 42 C 52 29 41 19 32 5 Z" fill="#f4f8ef" stroke="#3A6E37" strokeWidth="3.4" strokeLinejoin="round" />
      <g transform="translate(27,34) rotate(-28)">
        <path d="M0 -4.6 C 2.4 -1.4 2.4 1.4 0 4.6 C -2.4 1.4 -2.4 -1.4 0 -4.6 Z" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinejoin="round" />
      </g>
      <g transform="translate(36.5,40) rotate(22)">
        <path d="M0 -4.6 C 2.4 -1.4 2.4 1.4 0 4.6 C -2.4 1.4 -2.4 -1.4 0 -4.6 Z" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinejoin="round" />
      </g>
      <g transform="translate(29,47) rotate(-12)">
        <path d="M0 -4.6 C 2.4 -1.4 2.4 1.4 0 4.6 C -2.4 1.4 -2.4 -1.4 0 -4.6 Z" fill="none" stroke="#3A6E37" strokeWidth="2.7" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

function WinterDrop() {
  return (
    <svg className="drop-svg" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path d="M32 5 C 23 19 12 29 12 42 C 12 53 21 60 32 60 C 43 60 52 53 52 42 C 52 29 41 19 32 5 Z" fill="#f4f8ef" stroke="#3A6E37" strokeWidth="3.4" strokeLinejoin="round" />
      <line x1="32.00" y1="40.00" x2="32.00" y2="29.00" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="32.00" y1="33.50" x2="34.06" y2="31.05" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="33.50" x2="29.94" y2="31.05" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="40.00" x2="41.53" y2="34.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="37.63" y1="36.75" x2="40.78" y2="37.31" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="37.63" y1="36.75" x2="38.72" y2="33.74" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="40.00" x2="41.53" y2="45.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="37.63" y1="43.25" x2="38.72" y2="46.26" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="37.63" y1="43.25" x2="40.78" y2="42.69" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="40.00" x2="32.00" y2="51.00" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="32.00" y1="46.50" x2="29.94" y2="48.95" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="46.50" x2="34.06" y2="48.95" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="40.00" x2="22.47" y2="45.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="26.37" y1="43.25" x2="23.22" y2="42.69" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="26.37" y1="43.25" x2="25.28" y2="46.26" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="32.00" y1="40.00" x2="22.47" y2="34.50" stroke="#3A6E37" strokeWidth="2.7" strokeLinecap="round" />
      <line x1="26.37" y1="36.75" x2="25.28" y2="33.74" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
      <line x1="26.37" y1="36.75" x2="23.22" y2="37.31" stroke="#3A6E37" strokeWidth="2.43" strokeLinecap="round" />
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
      icon: <i className="ti ti-gauge" style={{ color: "var(--green-dark)" }} aria-hidden="true" />,
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
          width: 46px;
          height: 46px;
          flex-shrink: 0;
        }
      `}</style>
    </section>
  );
}
