import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { listPlants, type PlantSummary } from "../lib/db";
import { statusBadge } from "../lib/status";
import AuthControl from "./AuthControl";
import BottomTabBar, { type TabKey } from "./BottomTabBar";

type Props = {
  onPickPlant: (plant: PlantSummary) => void;
  onGoDiagnose: () => void; // empty state에서 진단 시작 (home으로 이동)
  onTabChange: (tab: TabKey) => void;
};

// 마지막 진단 시점 표기: 최근은 상대시간, 오래되면 날짜.
function formatWhen(d: Date | null): string {
  if (!d) return "";
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "오늘";
  if (days === 1) return "어제";
  if (days < 7) return `${days}일 전`;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

export default function MyPlantsView({ onPickPlant, onGoDiagnose, onTabChange }: Props) {
  const { user, loading: authLoading, signInWithGoogle } = useAuth();
  const uid = user?.uid ?? null;

  const [plants, setPlants] = useState<PlantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!uid) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    listPlants(uid)
      .then((items) => {
        if (!cancelled) setPlants(items);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "식물 목록을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [uid]);

  return (
    <div className="mp">
      {/* 헤더 — 타이틀 + AuthControl(홈과 동일 슬롯) */}
      <div className="mp-hdr">
        <h1 className="mp-title">내 식물</h1>
        <div className="mp-hdr-right">
          <AuthControl />
        </div>
      </div>

      <div className="mp-body">
        {authLoading ? (
          <p className="mp-msg">불러오는 중…</p>
        ) : !user ? (
          // 미로그인 — 로그인 유도 카드 (SaveDiagnosisModal 게이트와 동일 톤)
          <div className="gate-card">
            <div className="gate-ic">
              <i className="ti ti-plant-2" aria-hidden="true" />
            </div>
            <p className="gate-title">로그인하고 내 식물 기록을 확인하세요</p>
            <p className="gate-sub">진단 결과를 식물별로 저장하고 변화를 따라가 보세요.</p>
            <button className="gate-btn" type="button" onClick={() => void signInWithGoogle()}>
              <i className="ti ti-brand-google" aria-hidden="true" />
              Google로 로그인
            </button>
          </div>
        ) : loading ? (
          <p className="mp-msg">식물 목록을 불러오는 중…</p>
        ) : error ? (
          <p className="mp-err">{error}</p>
        ) : plants.length === 0 ? (
          // empty state
          <div className="empty">
            <div className="empty-ic">
              <i className="ti ti-plant-2" aria-hidden="true" />
            </div>
            <p className="empty-title">아직 등록된 식물이 없어요</p>
            <p className="empty-sub">첫 진단을 저장해 식물을 등록해보세요.</p>
            <button className="empty-btn" type="button" onClick={onGoDiagnose}>
              <i className="ti ti-scan" aria-hidden="true" />
              진단 시작
            </button>
          </div>
        ) : (
          <ul className="plant-list">
            {plants.map((p) => {
              const badge = p.lastDiagnosis ? statusBadge(p.lastDiagnosis.status) : null;
              return (
                <li key={p.id}>
                  <button className="plant-card" type="button" onClick={() => onPickPlant(p)}>
                    <span className="thumb">
                      {p.coverImageUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={p.coverImageUrl} alt="" />
                      ) : (
                        <i className="ti ti-plant-2" aria-hidden="true" />
                      )}
                    </span>
                    <span className="info">
                      <span className="name-row">
                        <span className="name">{p.name}</span>
                        {p.lastDiagnosis ? <span className="when">{formatWhen(p.lastDiagnosis.createdAt)}</span> : null}
                      </span>
                      {p.lastDiagnosis ? (
                        <span className="meta-row">
                          {p.lastDiagnosis.status ? (
                            <span className="badge" style={{ background: badge!.bg, color: badge!.fg }}>
                              {p.lastDiagnosis.status}
                            </span>
                          ) : null}
                        </span>
                      ) : null}
                      {p.lastDiagnosis?.summary ? <span className="summary">{p.lastDiagnosis.summary}</span> : null}
                    </span>
                    <i className="ti ti-chevron-right arrow" aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <BottomTabBar activeTab="myPlants" onTabChange={onTabChange} />

      <style jsx>{`
        .mp {
          width: 100%;
          max-width: 460px;
          margin: 0 auto;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          animation: fadeIn 0.26s ease;
        }
        .mp-hdr {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 20px 10px;
        }
        .mp-title {
          font-size: 22px;
          font-weight: 800;
          color: var(--green-dark);
          letter-spacing: -0.02em;
          margin: 0;
        }
        .mp-hdr-right {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .mp-body {
          flex: 1;
          padding: 10px 16px 20px;
        }
        .mp-msg {
          padding: 28px 4px;
          font-size: 14px;
          color: var(--text-secondary);
          text-align: center;
        }
        .mp-err {
          margin: 16px 0;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 12px 14px;
          font-size: 13px;
        }

        /* 미로그인 게이트 카드 / empty state */
        .gate-card,
        .empty {
          margin-top: 32px;
          background: var(--bg-card);
          border-radius: 20px;
          box-shadow: var(--shadow-card);
          padding: 34px 22px 30px;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        .gate-ic,
        .empty-ic {
          width: 60px;
          height: 60px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 16px;
        }
        .gate-ic i,
        .empty-ic i {
          font-size: 30px;
          color: var(--green-medium);
        }
        .gate-title,
        .empty-title {
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0 0 6px;
        }
        .gate-sub,
        .empty-sub {
          font-size: 13px;
          color: var(--text-muted);
          font-weight: 500;
          line-height: 1.55;
          margin: 0 0 20px;
        }
        .gate-btn,
        .empty-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          height: 50px;
          padding: 0 24px;
          border-radius: var(--radius-button);
          border: none;
          background: var(--green-dark);
          color: #fff;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          letter-spacing: -0.01em;
        }
        .gate-btn i,
        .empty-btn i {
          font-size: 18px;
        }

        /* 식물 카드 리스트 */
        .plant-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .plant-card {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px;
          border-radius: 18px;
          border: none;
          background: var(--bg-card);
          box-shadow: var(--shadow-card);
          cursor: pointer;
          text-align: left;
        }
        .thumb {
          width: 64px;
          height: 64px;
          border-radius: 14px;
          background: var(--bg-icon-circle);
          flex-shrink: 0;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .thumb img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .thumb i {
          font-size: 28px;
          color: var(--green-medium);
        }
        .info {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 5px;
        }
        .name-row {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 8px;
        }
        .name {
          font-size: 15.5px;
          font-weight: 700;
          color: var(--text-primary);
          letter-spacing: -0.01em;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .when {
          font-size: 12px;
          color: var(--text-muted);
          font-weight: 500;
          flex-shrink: 0;
        }
        .meta-row {
          display: flex;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          font-size: 11.5px;
          font-weight: 700;
          padding: 4px 12px;
          border-radius: var(--radius-badge);
        }
        .summary {
          font-size: 12.5px;
          color: var(--text-secondary);
          line-height: 1.45;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .arrow {
          font-size: 20px;
          color: #b0c4b2;
          flex-shrink: 0;
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
