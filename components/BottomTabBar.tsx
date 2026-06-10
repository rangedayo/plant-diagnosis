// 하단 탭바 공용 컴포넌트 (HomeView에서 추출, 시각 스타일·SVG·아이콘 1:1 유지).
// home·myPlants만 활성(클릭 시 onTabChange), settings는 기존대로 disabled(무반응).
// 진단 탭은 홈 카드와 중복이라 제거(3탭) — flex:1 균등 분할 자동.
export type TabKey = "home" | "myPlants" | "settings";

type Props = {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
};

export default function BottomTabBar({ activeTab, onTabChange }: Props) {
  const isHome = activeTab === "home";
  const isMyPlants = activeTab === "myPlants";

  return (
    <nav className="tab-bar" aria-label="하단 내비게이션">
      <button
        type="button"
        className={`tab-item${isHome ? " active" : ""}`}
        onClick={() => onTabChange("home")}
        aria-current={isHome ? "page" : undefined}
      >
        {/* 채움 제거 → "내 식물"(line 아이콘)처럼 진녹 stroke만. 문도 outline rect로 통일 */}
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 3 L21 11 L19 11 L19 20.5 L5 20.5 L5 11 L3 11 Z"
            fill="none"
            stroke="#587A4E"
            strokeWidth="1.6"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <rect x="9.2" y="14" width="5.6" height="6.5" rx="1.2" fill="none" stroke="#587A4E" strokeWidth="1.4" />
        </svg>
        <span>홈</span>
      </button>

      <button
        type="button"
        className={`tab-item${isMyPlants ? " active" : ""}`}
        onClick={() => onTabChange("myPlants")}
        aria-current={isMyPlants ? "page" : undefined}
      >
        <i className="ti ti-plant-2" aria-hidden="true" />
        <span>내 식물</span>
      </button>

      <div className="tab-item disabled" aria-disabled="true">
        <i className="ti ti-settings" aria-hidden="true" />
        <span>설정</span>
      </div>

      <style jsx>{`
        .tab-bar {
          margin-top: auto;
          background: var(--bg-card);
          border-top: 1px solid var(--border-tab);
          display: flex;
          padding: 10px 0 20px;
        }
        .tab-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 3px;
          background: none;
          border: none;
          cursor: pointer;
        }
        .tab-item i {
          font-size: 24px;
          color: var(--text-disabled);
        }
        .tab-item span {
          font-size: 10.5px;
          color: var(--text-disabled);
          font-weight: 500;
        }
        .tab-item.active i {
          color: var(--green-dark);
        }
        .tab-item.active span {
          color: var(--green-dark);
          font-weight: 700;
        }
        /* 비활성 탭의 home SVG는 dim (글리프 자체는 시안 불변, active/inactive 처리만) */
        .tab-item:not(.active) svg {
          opacity: 0.4;
        }
        .tab-item.disabled {
          cursor: default;
        }
      `}</style>
    </nav>
  );
}
