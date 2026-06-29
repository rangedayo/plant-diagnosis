import { useCallback, useEffect, useState } from "react";
import { summarizeDiagnosisTrend, type DiagnosisSnapshot } from "../lib/api";
import { type DiagnosisRecord } from "../lib/db";
import { statusColor, statusLabel } from "../lib/status";

// [추이 한눈에] 진단 이력 화면 맨 위 상단 카드.
// (1) 옵션 A — 오래된→최신 가로 타임라인 스트립(상태 색 점 + 라벨 + 날짜, 최신 강조, 탭→해당 진단)
// (2) 전체 흐름을 간결히 설명하는 LLM 요약(/trend). 비교(2건)보다 짧게 큰 그림만.
// 호출부(TimelineView)는 records 2건 이상일 때만 렌더한다(추이는 점 2개 이상에서 의미).

type Props = {
  records: DiagnosisRecord[]; // 최신순(desc) — TimelineView의 listDiagnoses 결과 그대로
  onPick: (record: DiagnosisRecord) => void; // 점 탭 → 해당 진단 카드로 이동
};

type SummaryState =
  | { kind: "loading" }
  | { kind: "success"; text: string }
  | { kind: "error"; message: string };

// DiagnosisRecord → 백엔드 비교/요약용 정성 스냅샷 (CompareModal.toSnapshot과 동형).
function toSnapshot(r: DiagnosisRecord): DiagnosisSnapshot {
  return {
    date: r.createdAt?.toISOString() ?? "",
    status: r.status,
    summary: r.summary,
    current_state: r.currentState,
    cause: r.cause,
    action_plan: r.actionPlan,
    observed_symptoms: r.observedSymptoms,
  };
}

// 스트립용 짧은 날짜(M.DD).
function shortDate(d: Date | null): string {
  if (!d) return "—";
  return `${d.getMonth() + 1}.${String(d.getDate()).padStart(2, "0")}`;
}

export default function TrendStrip({ records, onPick }: Props) {
  const [state, setState] = useState<SummaryState>({ kind: "loading" });

  // 스트립은 오래된→최신. records는 desc라 역순으로 렌더·전송.
  const ordered = [...records].reverse();

  const run = useCallback(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    const snaps = [...records].reverse().map(toSnapshot); // 시간순(오래된→최신)
    summarizeDiagnosisTrend(snaps)
      .then((res) => {
        if (!cancelled) setState({ kind: "success", text: res.trend });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message:
              err instanceof Error
                ? err.message
                : "추이 요약을 가져오지 못했어요. 잠시 후 다시 시도해주세요.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [records]);

  useEffect(() => run(), [run]);

  return (
    <section className="trend" aria-label="진단 추이">
      <div className="trend-hdr">
        <span className="trend-ttl">진단 추이</span>
        <span className="trend-cnt">총 {records.length}회</span>
      </div>

      {/* 옵션 A — 가로 타임라인 스트립 */}
      <div className="strip-scroll">
        <ul className="strip">
          {ordered.map((r, i) => {
            const isLast = i === ordered.length - 1;
            const label = statusLabel(r.status).coarse || r.status || "진단";
            return (
              <li key={r.id} className="node-wrap">
                <button
                  className={`node${isLast ? " last" : ""}`}
                  type="button"
                  onClick={() => onPick(r)}
                  aria-label={`${shortDate(r.createdAt)} ${label} 진단 보기`}
                >
                  <span className="dot" style={{ background: statusColor(r.status) }} />
                  <span className="st">{r.status || "진단"}</span>
                  <span className="dt">{shortDate(r.createdAt)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="divider" />

      {/* 전체 흐름 간결 요약 */}
      <div className="summary">
        {state.kind === "loading" ? (
          <p className="s-loading">전체 추이를 요약하는 중…</p>
        ) : state.kind === "error" ? (
          <div className="s-err">
            <span className="s-err-msg">{state.message}</span>
            <button className="s-retry" type="button" onClick={run}>
              다시 시도
            </button>
          </div>
        ) : (
          <p className="s-text">{state.text}</p>
        )}
      </div>

      <style jsx>{`
        .trend {
          background: var(--bg-card);
          border-radius: 18px;
          box-shadow: var(--shadow-card);
          padding: 16px 4px 14px;
        }
        .trend-hdr {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          padding: 0 16px 12px;
        }
        .trend-ttl {
          font-size: 14px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.01em;
        }
        .trend-cnt {
          font-size: 11.5px;
          font-weight: 600;
          color: var(--text-muted);
        }
        .strip-scroll {
          overflow-x: auto;
          /* overflow-x:auto가 세로도 잘라내므로(스펙상 overflow-y=auto) 확대된 최신 점의
             링이 잘리지 않도록 상하 여백 확보 */
          padding: 7px 16px 4px;
          -webkit-overflow-scrolling: touch;
        }
        .strip {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          align-items: flex-start;
          min-width: max-content;
          position: relative;
        }
        /* 점들을 잇는 연결선(첫·끝 점 중심 사이) */
        .strip::before {
          content: "";
          position: absolute;
          top: 7px;
          left: 32px;
          right: 32px;
          height: 2px;
          background: #e3eae0;
        }
        .node-wrap {
          position: relative;
          z-index: 1;
        }
        .node {
          width: 64px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0;
          border: none;
          background: none;
          padding: 0;
          cursor: pointer;
        }
        .dot {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          border: 3px solid var(--bg-card);
          box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.05);
          transition: transform 0.15s ease;
        }
        .node.last .dot {
          transform: scale(1.28);
          box-shadow: 0 0 0 3px rgba(123, 203, 143, 0.28);
        }
        .node:hover .dot,
        .node:focus-visible .dot {
          transform: scale(1.28);
        }
        .st {
          margin-top: 9px;
          font-size: 11.5px;
          font-weight: 700;
          color: var(--text-secondary);
          text-align: center;
          line-height: 1.25;
          word-break: keep-all;
        }
        .node.last .st {
          color: var(--text-primary);
        }
        .dt {
          margin-top: 3px;
          font-size: 10.5px;
          color: var(--text-muted);
          font-weight: 600;
        }
        .divider {
          height: 1px;
          background: #edf2ea;
          margin: 12px 16px 0;
        }
        .summary {
          padding: 12px 16px 0;
        }
        .s-loading {
          margin: 0;
          font-size: 13px;
          color: var(--text-secondary);
        }
        .s-text {
          margin: 0;
          font-size: 13.5px;
          line-height: 1.65;
          color: var(--text-primary);
          white-space: pre-wrap;
        }
        .s-err {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }
        .s-err-msg {
          font-size: 12.5px;
          color: #b71c1c;
        }
        .s-retry {
          height: 32px;
          padding: 0 14px;
          border-radius: 999px;
          border: 1px solid var(--green-medium);
          background: transparent;
          color: var(--green-medium);
          font-size: 12.5px;
          font-weight: 700;
          cursor: pointer;
        }
      `}</style>
    </section>
  );
}
