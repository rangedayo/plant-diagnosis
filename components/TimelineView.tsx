import { useEffect, useState } from "react";
import { listDiagnoses, type DiagnosisRecord, type PlantSummary } from "../lib/db";
import { statusBadge } from "../lib/status";
import AuthControl from "./AuthControl";
import CompareModal from "./CompareModal";

// 비교 대상: previous(더 오래된) vs current(선택 카드).
type CompareTarget = {
  previous: DiagnosisRecord;
  current: DiagnosisRecord;
};

type Props = {
  uid: string;
  plant: PlantSummary; // 헤더 이름 표시 + 진단 카드 변환 컨텍스트
  onBack: () => void; // → myPlants
  onPickDiagnosis: (record: DiagnosisRecord) => void;
};

function formatDate(d: Date | null): string {
  if (!d) return "";
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

export default function TimelineView({ uid, plant, onBack, onPickDiagnosis }: Props) {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [compareTarget, setCompareTarget] = useState<CompareTarget | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    listDiagnoses(uid, plant.id)
      .then((items) => {
        if (!cancelled) setRecords(items);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "진단 이력을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [uid, plant.id]);

  return (
    <section className="tl">
      {/* 헤더 — 뒤로가기 + 식물 별칭 + AuthControl */}
      <div className="tl-hdr">
        <button className="tl-back" type="button" onClick={onBack} aria-label="내 식물로 돌아가기">
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>
        <h1 className="tl-title">{plant.name}</h1>
        <div className="tl-hdr-right">
          <AuthControl />
        </div>
      </div>

      {loading ? (
        <p className="tl-msg">진단 이력을 불러오는 중…</p>
      ) : error ? (
        <p className="tl-err">{error}</p>
      ) : records.length === 0 ? (
        <p className="tl-msg">진단 이력이 없습니다.</p>
      ) : (
        <ul className="dx-list">
          {records.map((r, i) => {
            const badge = statusBadge(r.status);
            // records는 최신순(desc). previous = 한 칸 더 오래된 records[i+1].
            // 가장 오래된 카드(최하단)는 비교 대상이 없어 버튼 숨김.
            const previous = i < records.length - 1 ? records[i + 1] : null;
            return (
              <li key={r.id} className="dx-item">
                <button className="dx-card" type="button" onClick={() => onPickDiagnosis(r)}>
                  <span className="thumb">
                    {r.imageUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={r.imageUrl} alt="" />
                    ) : (
                      <i className="ti ti-leaf" aria-hidden="true" />
                    )}
                  </span>
                  <span className="info">
                    <span className="top">
                      {r.status ? (
                        <span className="badge" style={{ background: badge.bg, color: badge.fg }}>
                          {r.status}
                        </span>
                      ) : null}
                      <span className="date">{formatDate(r.createdAt)}</span>
                    </span>
                    {r.summary ? <span className="summary">{r.summary}</span> : null}
                  </span>
                  <i className="ti ti-chevron-right arrow" aria-hidden="true" />
                </button>
                {previous ? (
                  <button
                    className="cmp-btn"
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setCompareTarget({ previous, current: r });
                    }}
                  >
                    <i className="ti ti-arrows-up-down" aria-hidden="true" />
                    이전 진단과 비교
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {compareTarget ? (
        <CompareModal
          previous={compareTarget.previous}
          current={compareTarget.current}
          onClose={() => setCompareTarget(null)}
        />
      ) : null}

      <style jsx>{`
        .tl {
          display: flex;
          flex-direction: column;
          gap: 12px;
          animation: fadeIn 0.26s ease;
        }
        .tl-hdr {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0 0 6px;
        }
        .tl-back {
          width: 36px;
          height: 36px;
          border: none;
          background: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-left: -7px;
        }
        .tl-back i {
          font-size: 24px;
          color: var(--text-primary);
        }
        .tl-title {
          flex: 1;
          font-size: 19px;
          font-weight: 800;
          color: var(--green-dark);
          letter-spacing: -0.01em;
          margin: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .tl-hdr-right {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }
        .tl-msg {
          padding: 32px 4px;
          font-size: 14px;
          color: var(--text-secondary);
          text-align: center;
        }
        .tl-err {
          margin: 8px 0;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 12px 14px;
          font-size: 13px;
        }

        .dx-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .dx-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .dx-card {
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
        .cmp-btn {
          align-self: center;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          height: 36px;
          padding: 0 16px;
          border: 0.5px solid #b3b3b3;
          background: var(--bg-card);
          color: #0f6e56;
          font-size: 13px;
          font-weight: 700;
          letter-spacing: -0.01em;
          cursor: pointer;
          border-radius: 999px;
        }
        .cmp-btn i {
          font-size: 15px;
        }
        .cmp-btn:hover {
          background: var(--bg-icon-circle);
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
          font-size: 26px;
          color: var(--green-medium);
        }
        .info {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .top {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          font-size: 11.5px;
          font-weight: 700;
          padding: 4px 12px;
          border-radius: var(--radius-badge);
          flex-shrink: 0;
        }
        .date {
          font-size: 12.5px;
          color: var(--text-muted);
          font-weight: 600;
        }
        .summary {
          font-size: 13px;
          color: var(--text-secondary);
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
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
    </section>
  );
}
