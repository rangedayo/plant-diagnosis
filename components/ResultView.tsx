import { DiagnosisResponse } from "../types/diagnosis";
import { statusBadge } from "../lib/status";

type ResultViewProps = {
  result: DiagnosisResponse;
  imageUrl: string | null;
  onReset: () => void;
  onViewCare?: () => void; // R3에서 케어 화면 연결 예정 (현재 미연결 placeholder)
};

export default function ResultView({ result, imageUrl, onReset, onViewCare }: ResultViewProps) {
  const { structured_result: sr, analysis, care_guide } = result;

  const plantName = analysis?.plant_name_korean ?? analysis?.plant_name ?? "식물명 미식별";
  const status = sr.status || "";
  const statusText = status || "진단 완료";
  const badge = statusBadge(status);

  const summary = sr.summary?.trim() ?? "";
  const cause = sr.cause?.trim() ?? "";
  const actionPlan = Array.isArray(sr.action_plan) ? sr.action_plan : [];

  return (
    <section className="dr">
      {/* 사진 카드 + 상태 배지 */}
      <div className="card ph-card">
        <div className="ph-img">
          {imageUrl ? <img className="ph-photo" src={imageUrl} alt="진단한 식물 이미지" /> : null}
        </div>
        <div className="ph-badge-wrap">
          <span className="ph-badge" style={{ background: badge.bg, color: badge.fg }}>
            <i className="ti ti-leaf" aria-hidden="true" />
            {statusText}
          </span>
        </div>
      </div>

      {/* 진단 요약 */}
      <div className="card">
        <div className="card-body">
          <div className="sec-hdr">
            <div className="sec-ic">
              <i className="ti ti-clipboard-list" aria-hidden="true" />
            </div>
            <span className="sec-ttl">진단 요약</span>
          </div>
          <div className="info-block">
            <div className="info-row">
              <div className="info-leaf">
                <i className="ti ti-leaf" aria-hidden="true" />
              </div>
              <span className="info-lbl">식물 이름</span>
              <span className="info-val">{plantName}</span>
            </div>
            <div className="row-sep" />
            <div className="info-row">
              <div className="info-leaf">
                <i className="ti ti-leaf" aria-hidden="true" />
              </div>
              <span className="info-lbl">현재 상태</span>
              <span className="info-val" style={{ color: badge.fg }}>
                {statusText}
              </span>
            </div>
          </div>
          {summary ? <p className="dr-summary">{summary}</p> : null}
        </div>
      </div>

      {/* 원인 설명 (빈값 시 카드 숨김) */}
      {cause ? (
        <div className="card">
          <div className="card-body">
            <div className="sec-hdr">
              <div className="sec-ic">
                <i className="ti ti-bulb" aria-hidden="true" />
              </div>
              <span className="sec-ttl">원인 설명</span>
            </div>
            <p className="dr-cause">{cause}</p>
          </div>
        </div>
      ) : null}

      {/* 처방 (빈 list 시 카드 숨김) */}
      {actionPlan.length > 0 ? (
        <div className="card">
          <div className="card-body">
            <div className="sec-hdr">
              <div className="sec-ic">
                <i className="ti ti-clipboard-check" aria-hidden="true" />
              </div>
              <span className="sec-ttl">처방</span>
            </div>
            {actionPlan.map((item, idx) => (
              <div className="rx-item" key={`${idx}-${item}`}>
                <div className="rx-chk">
                  <i className="ti ti-check" aria-hidden="true" />
                </div>
                <p className="rx-txt">{item}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 지속 관리법 보기 (care_guide 있을 때만; onClick은 R3 연결) */}
      {care_guide ? (
        <button className="care-nav-card" type="button" onClick={() => onViewCare?.()}>
          <div className="care-nav-ic">
            <i className="ti ti-leaf" aria-hidden="true" />
          </div>
          <div className="care-nav-text">
            <div className="care-nav-title">지속 관리법 보기</div>
            <div className="care-nav-sub">이 식물의 케어 가이드를 확인해보세요</div>
          </div>
          <div className="care-nav-arrow">
            <i className="ti ti-chevron-right" aria-hidden="true" />
          </div>
        </button>
      ) : null}

      {/* 하단 액션 */}
      <div className="dr-actions">
        <button className="dr-btn-out" type="button" onClick={() => window.print()} aria-label="리포트 저장">
          <i className="ti ti-download" aria-hidden="true" />
          리포트 저장
        </button>
        <button className="dr-btn-fill" type="button" onClick={onReset} aria-label="홈으로 돌아가기">
          <i className="ti ti-smart-home" aria-hidden="true" />
          홈으로 돌아가기
        </button>
      </div>

      <style jsx>{`
        .dr {
          display: flex;
          flex-direction: column;
          gap: 14px;
          animation: fadeIn 0.26s ease;
        }
        .card {
          background: var(--bg-card);
          border-radius: var(--radius-card);
          box-shadow: var(--shadow-card);
          overflow: hidden;
        }
        .card-body {
          padding: 20px;
        }

        /* 사진 카드 */
        .ph-card {
          overflow: visible;
          padding: 12px 12px 0;
        }
        .ph-img {
          width: 100%;
          height: 270px;
          background: var(--bg-photo-placeholder);
          border-radius: var(--radius-photo-inner);
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .ph-photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .ph-badge-wrap {
          display: flex;
          justify-content: center;
          padding: 16px 0 18px;
        }
        .ph-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          font-weight: 700;
          letter-spacing: -0.01em;
          padding: 9px 22px;
          border-radius: var(--radius-badge);
        }
        .ph-badge i {
          font-size: 16px;
        }

        /* 섹션 헤더 */
        .sec-hdr {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 16px;
        }
        .sec-ic {
          width: 38px;
          height: 38px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .sec-ic i {
          font-size: 20px;
          color: var(--green-dark);
        }
        .sec-ttl {
          font-size: 16px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }

        /* 진단 요약 */
        .info-block {
          background: var(--bg-info-row);
          border-radius: var(--radius-info-block);
        }
        .info-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 13px 14px;
        }
        .row-sep {
          margin: 0 14px;
          border-top: 1.4px dashed var(--border-dashed);
        }
        .info-leaf {
          width: 30px;
          height: 30px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle-accent);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .info-leaf i {
          font-size: 14px;
          color: var(--green-dark);
        }
        .info-lbl {
          flex: 1;
          font-size: 14px;
          color: var(--text-secondary);
          font-weight: 500;
        }
        .info-val {
          font-size: 14px;
          color: var(--text-primary);
          font-weight: 600;
        }
        .dr-summary {
          margin-top: 8px;
          font-size: 14px;
          color: #3a4a3c;
          line-height: 1.65;
          font-weight: 500;
        }

        /* 원인 */
        .dr-cause {
          font-size: 14px;
          color: var(--text-secondary);
          line-height: 1.7;
          font-weight: 500;
        }

        /* 처방 */
        .rx-item {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 0;
          border-bottom: 1px solid #f0f7ec;
        }
        .rx-item:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }
        .rx-chk {
          width: 22px;
          height: 22px;
          border-radius: var(--radius-circle);
          background: var(--green-dark);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-top: 1px;
        }
        .rx-chk i {
          font-size: 12px;
          color: #fff;
          line-height: 1;
        }
        .rx-txt {
          font-size: 14px;
          color: #3a4a3c;
          line-height: 1.55;
          font-weight: 500;
        }

        /* 케어 가이드 이동 카드 */
        .care-nav-card {
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
        }
        .care-nav-card:active {
          background: #f5faf3;
        }
        .care-nav-ic {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-circle);
          background: var(--bg-section-header-icon);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .care-nav-ic i {
          font-size: 22px;
          color: var(--green-dark);
        }
        .care-nav-text {
          flex: 1;
          text-align: left;
        }
        .care-nav-title {
          font-size: 15px;
          font-weight: 700;
          color: #1b2b1c;
          letter-spacing: -0.01em;
        }
        .care-nav-sub {
          font-size: 12.5px;
          color: var(--text-muted);
          margin-top: 3px;
          font-weight: 500;
        }
        .care-nav-arrow {
          color: #b0c4b2;
        }
        .care-nav-arrow i {
          font-size: 20px;
        }

        /* 하단 액션 */
        .dr-actions {
          margin-top: 4px;
          padding: 4px 0 8px;
          display: flex;
          gap: 10px;
        }
        .dr-btn-out {
          flex: 2;
          height: 52px;
          border-radius: var(--radius-button);
          border: 1.5px solid var(--green-medium);
          background: transparent;
          color: var(--green-medium);
          font-size: 14px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          cursor: pointer;
          letter-spacing: -0.01em;
        }
        .dr-btn-fill {
          flex: 3;
          height: 52px;
          border-radius: var(--radius-button);
          border: none;
          background: var(--green-dark);
          color: #fff;
          font-size: 14px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          cursor: pointer;
          letter-spacing: -0.01em;
        }
        .dr-btn-out i,
        .dr-btn-fill i {
          font-size: 17px;
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
