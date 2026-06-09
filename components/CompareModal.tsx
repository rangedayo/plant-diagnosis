import { useCallback, useEffect, useState } from "react";
import {
  comparePlantDiagnoses,
  type DiagnosisSnapshot,
} from "../lib/api";
import { type DiagnosisRecord } from "../lib/db";
import { statusBadge, statusLabel } from "../lib/status";

type Props = {
  previous: DiagnosisRecord; // 직전(더 오래된) 진단
  current: DiagnosisRecord; // 이번(최신) 진단
  onClose: () => void;
};

type State =
  | { kind: "loading" }
  | { kind: "success"; text: string }
  | { kind: "error"; message: string };

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

function formatDate(d: Date | null): string {
  if (!d) return "날짜 미상";
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

// [시계열 3단계] 직전 vs 이번 진단의 정성 비교를 모달로 표시.
// 마운트 시 /compare 호출 → 로딩/결과/에러. SaveDiagnosisModal 오버레이 톤 재사용.
export default function CompareModal({ previous, current, onClose }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    comparePlantDiagnoses(toSnapshot(previous), toSnapshot(current))
      .then((res) => {
        if (!cancelled) setState({ kind: "success", text: res.comparison });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message:
              err instanceof Error
                ? err.message
                : "비교 결과를 가져오지 못했어요. 잠시 후 다시 시도해주세요.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [previous, current]);

  useEffect(() => run(), [run]);

  const prevBadge = statusBadge(previous.status);
  const currBadge = statusBadge(current.status);

  return (
    <div className="ov" role="dialog" aria-modal="true" aria-label="진단 비교">
      <button className="ov-bg" type="button" aria-label="닫기" onClick={onClose} />
      <div className="sheet">
        <div className="sheet-hdr">
          <h2 className="sheet-ttl">진단 비교</h2>
          <button className="sheet-x" type="button" onClick={onClose} aria-label="닫기">
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>

        {/* 두 진단 메타 — 날짜 + status 배지 */}
        <div className="meta">
          <div className="meta-row">
            <span className="meta-lbl">이전</span>
            <span className="meta-date">{formatDate(previous.createdAt)}</span>
            {previous.status ? (
              <span className="badge" style={{ background: prevBadge.bg, color: prevBadge.fg }}>
                {statusLabel(previous.status).coarse || previous.status}
              </span>
            ) : null}
          </div>
          <i className="ti ti-arrow-down meta-arrow" aria-hidden="true" />
          <div className="meta-row">
            <span className="meta-lbl">이번</span>
            <span className="meta-date">{formatDate(current.createdAt)}</span>
            {current.status ? (
              <span className="badge" style={{ background: currBadge.bg, color: currBadge.fg }}>
                {statusLabel(current.status).coarse || current.status}
              </span>
            ) : null}
          </div>
        </div>

        {/* 본문 */}
        <div className="body">
          {state.kind === "loading" ? (
            <p className="loading">비교 분석 중…</p>
          ) : state.kind === "error" ? (
            <div className="err-wrap">
              <p className="err">{state.message}</p>
              <button className="retry" type="button" onClick={run}>
                다시 시도
              </button>
            </div>
          ) : (
            <p className="result">{state.text}</p>
          )}
        </div>

        <div className="sheet-actions">
          <button className="btn-fill" type="button" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>

      <style jsx>{`
        .ov {
          position: fixed;
          inset: 0;
          z-index: 60;
          display: flex;
          align-items: flex-end;
          justify-content: center;
        }
        .ov-bg {
          position: absolute;
          inset: 0;
          border: none;
          padding: 0;
          background: rgba(20, 35, 22, 0.45);
          cursor: pointer;
          animation: ovFade 0.2s ease;
        }
        .sheet {
          position: relative;
          width: 100%;
          max-width: 460px;
          background: var(--bg-card);
          border-radius: 24px 24px 0 0;
          padding: 20px 18px calc(20px + env(safe-area-inset-bottom));
          box-shadow: 0 -8px 30px rgba(20, 35, 22, 0.2);
          animation: sheetUp 0.26s ease;
        }
        .sheet-hdr {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .sheet-ttl {
          font-size: 18px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.01em;
          margin: 0;
        }
        .sheet-x {
          width: 34px;
          height: 34px;
          border: none;
          background: none;
          cursor: pointer;
          color: var(--text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .sheet-x i {
          font-size: 22px;
        }
        .meta {
          display: flex;
          flex-direction: column;
          gap: 4px;
          background: var(--bg-info-row);
          border-radius: 14px;
          padding: 12px 14px;
          margin-bottom: 14px;
        }
        .meta-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .meta-lbl {
          font-size: 12px;
          font-weight: 700;
          color: var(--text-muted);
          width: 30px;
          flex-shrink: 0;
        }
        .meta-date {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
          flex: 1;
        }
        .meta-arrow {
          font-size: 16px;
          color: var(--text-muted);
          margin-left: 8px;
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
        .body {
          min-height: 96px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .loading {
          font-size: 14px;
          color: var(--text-secondary);
          padding: 24px 2px;
        }
        .result {
          font-size: 14.5px;
          line-height: 1.7;
          color: var(--text-primary);
          white-space: pre-wrap;
          margin: 0;
          align-self: stretch;
        }
        .err-wrap {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          align-self: stretch;
        }
        .err {
          margin: 0;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 12px 14px;
          font-size: 13px;
          text-align: center;
          width: 100%;
        }
        .retry {
          height: 42px;
          padding: 0 22px;
          border-radius: var(--radius-button);
          border: 1.5px solid var(--green-medium);
          background: transparent;
          color: var(--green-medium);
          font-size: 13.5px;
          font-weight: 700;
          cursor: pointer;
        }
        .sheet-actions {
          display: flex;
          margin-top: 16px;
        }
        .btn-fill {
          flex: 1;
          height: 52px;
          border-radius: var(--radius-button);
          border: none;
          background: var(--green-dark);
          color: #fff;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
        }
        @keyframes ovFade {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        @keyframes sheetUp {
          from {
            transform: translateY(18px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
