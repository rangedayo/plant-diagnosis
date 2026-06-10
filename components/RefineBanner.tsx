import { statusLabel } from "../lib/status";

// [챗봇 단계3] 2차 결과 상단 변화 안내 배너 + 1차/2차 토글.
// status 변화는 한글 조사(으로/로) 오류를 피하려고 화살표 칩(1차 라벨 → 2차 라벨)으로 시각 표현.
// 사용자 라벨은 statusLabel(...).coarse(건강/양호 (가벼운 주의)/주의 관찰)을 재사용.
type RefineBannerProps = {
  primaryStatus: string; // 1차 structured_result.status (원값)
  refinedStatus: string; // 2차 structured_result.status (원값)
  showPrimary: boolean; // true면 현재 1차 표시 중, false면 2차 표시 중
  onToggle: () => void;
};

export default function RefineBanner({ primaryStatus, refinedStatus, showPrimary, onToggle }: RefineBannerProps) {
  const primaryLabel = statusLabel(primaryStatus).coarse || "진단";
  const refinedLabel = statusLabel(refinedStatus).coarse || "진단";
  const changed = primaryLabel !== refinedLabel;

  return (
    <div className="rb">
      <div className="rb-head">
        <div className="rb-ic">
          <i className="ti ti-sparkles" aria-hidden="true" />
        </div>
        <div className="rb-title">입력하신 정보를 반영해 진단을 다듬었어요</div>
      </div>

      {changed ? (
        <div className="rb-change">
          <span className="rb-chip rb-chip-from">{primaryLabel}</span>
          <i className="ti ti-arrow-right rb-arrow" aria-hidden="true" />
          <span className="rb-chip rb-chip-to">{refinedLabel}</span>
          <span className="rb-change-note">상태를 다시 평가했어요</span>
        </div>
      ) : (
        <p className="rb-same">상태는 그대로지만 처방을 보강했어요.</p>
      )}

      <div className="rb-foot">
        <span className="rb-now">
          지금 보는 건 {showPrimary ? "1차" : "2차"} 진단이에요
        </span>
        <button className="rb-toggle" type="button" onClick={onToggle}>
          <i className="ti ti-switch-horizontal" aria-hidden="true" />
          {showPrimary ? "2차 진단 보기" : "1차 진단 보기"}
        </button>
      </div>

      <style jsx>{`
        .rb {
          background: var(--bg-card);
          border-radius: var(--radius-card);
          box-shadow: var(--shadow-card);
          border: 1.5px solid var(--green-medium);
          padding: 16px 18px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          animation: fadeIn 0.26s ease;
        }
        .rb-head {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .rb-ic {
          width: 36px;
          height: 36px;
          border-radius: var(--radius-circle);
          background: var(--bg-section-header-icon);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .rb-ic i {
          font-size: 19px;
          color: var(--green-dark);
        }
        .rb-title {
          font-size: 14.5px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
          line-height: 1.4;
        }
        .rb-change {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
        }
        .rb-chip {
          font-size: 13px;
          font-weight: 700;
          padding: 5px 14px;
          border-radius: var(--radius-badge);
          letter-spacing: -0.01em;
        }
        .rb-chip-from {
          background: var(--bg-info-row);
          color: var(--text-secondary);
        }
        .rb-chip-to {
          background: var(--bg-icon-circle);
          color: var(--green-dark);
        }
        .rb-arrow {
          font-size: 16px;
          color: var(--text-muted);
        }
        .rb-change-note {
          font-size: 12.5px;
          color: var(--text-muted);
          font-weight: 500;
          margin-left: 2px;
        }
        .rb-same {
          margin: 0;
          font-size: 13.5px;
          color: var(--text-secondary);
          font-weight: 500;
          line-height: 1.5;
        }
        .rb-foot {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          border-top: 1px solid var(--border-card-subtle);
          padding-top: 12px;
        }
        .rb-now {
          font-size: 12.5px;
          color: var(--text-muted);
          font-weight: 600;
        }
        .rb-toggle {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: none;
          border: 1.5px solid var(--green-medium);
          color: var(--green-dark);
          font-size: 13px;
          font-weight: 700;
          padding: 7px 14px;
          border-radius: var(--radius-badge);
          cursor: pointer;
          letter-spacing: -0.01em;
          flex-shrink: 0;
        }
        .rb-toggle i {
          font-size: 16px;
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
    </div>
  );
}
