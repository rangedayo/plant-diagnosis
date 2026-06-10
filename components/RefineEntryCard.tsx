// [챗봇 단계3] 1차 결과 하단 진입 카드. 탭 → 질문 전용 화면(followup).
// 디자인은 ResultView의 .care-nav-card(지속 관리법 보기 카드)를 그대로 차용 — 새 디자인 도입 없음.
type RefineEntryCardProps = {
  onClick: () => void;
};

export default function RefineEntryCard({ onClick }: RefineEntryCardProps) {
  return (
    <button className="rf-entry" type="button" onClick={onClick}>
      <div className="rf-entry-ic">
        <i className="ti ti-message-2" aria-hidden="true" />
      </div>
      <div className="rf-entry-text">
        <div className="rf-entry-title">더 정확한 진단 받기</div>
        <div className="rf-entry-sub">몇 가지 질문에 답하면 진단을 더 정확하게 다듬어요</div>
      </div>
      <div className="rf-entry-arrow">
        <i className="ti ti-chevron-right" aria-hidden="true" />
      </div>

      <style jsx>{`
        .rf-entry {
          background: var(--bg-card);
          border-radius: var(--radius-card);
          box-shadow: var(--shadow-card);
          padding: 16px 18px;
          display: flex;
          align-items: center;
          gap: 14px;
          cursor: pointer;
          border: none;
          width: 100%;
          transition: background 0.15s;
          animation: fadeIn 0.26s ease;
        }
        .rf-entry:active {
          background: #f5faf3;
        }
        .rf-entry-ic {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-circle);
          background: var(--bg-section-header-icon);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .rf-entry-ic i {
          font-size: 22px;
          color: var(--green-dark);
        }
        .rf-entry-text {
          flex: 1;
          text-align: left;
        }
        .rf-entry-title {
          font-size: 15px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }
        .rf-entry-sub {
          font-size: 12.5px;
          color: var(--text-muted);
          margin-top: 3px;
          font-weight: 500;
        }
        .rf-entry-arrow {
          color: #b0c4b2;
        }
        .rf-entry-arrow i {
          font-size: 20px;
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
    </button>
  );
}
