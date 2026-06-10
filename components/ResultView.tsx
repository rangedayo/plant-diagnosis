import { useRouter } from "next/router";
import { DiagnosisResponse } from "../types/diagnosis";
import { statusBadge, statusLabel } from "../lib/status";

type ResultViewProps = {
  result: DiagnosisResponse;
  imageUrl: string | null;
  onReset: () => void;
  onViewCare?: () => void; // R3에서 케어 화면 연결 예정 (현재 미연결 placeholder)
  onSave?: () => void; // 진단 기록 저장(로그인 게이트·모달은 상위에서). 미제공 시 버튼 숨김.
  mode?: "fresh" | "history"; // 미제공 = "fresh"(기존 동작). history는 하단 우측 버튼만 분기.
};

export default function ResultView({ result, imageUrl, onReset, onViewCare, onSave, mode }: ResultViewProps) {
  const isHistory = mode === "history";
  const { structured_result: sr, analysis, care_guide } = result;

  const router = useRouter();
  const debug = router.query.debug === "1"; // ?debug=1 → 디버그 세부 라벨

  const plantName = analysis?.plant_name_korean ?? analysis?.plant_name ?? "식물명 미식별";
  const status = sr.status || "";
  // 기본 = 사용자 거친 라벨(3단), ?debug=1 = 세부 라벨 + 원본 status. 빈값 → "진단 완료".
  const { coarse, detail } = statusLabel(status);
  const statusText = (debug ? detail : coarse) || "진단 완료";
  const badge = statusBadge(status); // 색은 원본 status 기준 유지(라벨만 분기, §40)

  const cause = sr.cause?.trim() ?? "";
  const actionPlan = Array.isArray(sr.action_plan) ? sr.action_plan : [];

  return (
    <section className="dr">
      {/* 진단 결과 네비 헤더 (정본 plantia_combined.html .dr-hdr). 뒤로=onReset(result→home), ✦=무액션 장식 */}
      <div className="dr-hdr">
        <button className="dr-back" type="button" onClick={onReset} aria-label="홈으로 돌아가기">
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>
        <h1 className="dr-htitle">진단 결과</h1>
        <span className="dr-plus" aria-hidden="true">✦</span>
      </div>

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
              <span className="sec-ttl">이렇게 판단했어요</span>
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

      {/* 진단 기록 저장 (onSave 제공 시만; 로그인 게이트·모달은 상위에서 처리) */}
      {onSave ? (
        <button className="dr-save" type="button" onClick={onSave} aria-label="이 식물 기록에 저장">
          <i className="ti ti-bookmark" aria-hidden="true" />
          이 식물 기록에 저장
        </button>
      ) : null}

      {/* 하단 액션 */}
      <div className="dr-actions">
        <button className="dr-btn-out" type="button" onClick={() => window.print()} aria-label="리포트 저장">
          <i className="ti ti-download" aria-hidden="true" />
          리포트 저장
        </button>
        <button
          className="dr-btn-fill"
          type="button"
          onClick={onReset}
          aria-label={isHistory ? "타임라인으로 돌아가기" : "홈으로 돌아가기"}
        >
          <i className={`ti ${isHistory ? "ti-chevron-left" : "ti-smart-home"}`} aria-hidden="true" />
          {isHistory ? "타임라인으로 돌아가기" : "홈으로 돌아가기"}
        </button>
      </div>

      <style jsx>{`
        .dr {
          display: flex;
          flex-direction: column;
          gap: 14px;
          animation: fadeIn 0.26s ease;
        }

        /* 진단 결과 네비 헤더 (정본 .dr-hdr) */
        .dr-hdr {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 0 6px;
        }
        .dr-back {
          width: 36px;
          height: 36px;
          border-radius: var(--radius-circle);
          background: none;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-left: -7px; /* 36px 버튼 내 22px 셰브론을 컨테이너 좌측 패딩에 시각 정렬 */
        }
        .dr-back i {
          font-size: 22px;
          color: var(--text-primary);
        }
        .dr-htitle {
          font-size: 18px;
          font-weight: 700;
          color: var(--green-dark);
          letter-spacing: -0.01em;
          margin: 0;
        }
        .dr-plus {
          font-size: 18px;
          color: var(--text-disabled);
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
          margin: 0; /* globals.css가 p 마진 미리셋 → UA 기본 margin-block 제거(체크 아이콘 정렬) */
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

        /* 진단 기록 저장 버튼 (시안 톤: 연한 그린 배경 + 다크 그린 텍스트) */
        .dr-save {
          width: 100%;
          height: 52px;
          border-radius: var(--radius-button);
          border: 1.5px solid var(--green-medium);
          background: var(--bg-icon-circle);
          color: var(--green-dark);
          font-size: 14px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          cursor: pointer;
          letter-spacing: -0.01em;
        }
        .dr-save i {
          font-size: 18px;
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
