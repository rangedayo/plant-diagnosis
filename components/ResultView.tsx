import { DiagnosisResponse } from "../types/diagnosis";

type ResultViewProps = {
  result: DiagnosisResponse;
  imageUrl: string | null;
  onReset: () => void;
};

export default function ResultView({ result, imageUrl, onReset }: ResultViewProps) {
  const plantName =
    result.analysis?.plant_name_korean ?? result.analysis?.plant_name ?? "식물 이름 미확인";
  const state = result.structured_result.current_state || "상태 정보 없음";
  const summary = result.structured_result.summary || "요약 정보 없음";
  const cause = result.structured_result.cause || "원인 정보 없음";
  const actionPlan =
    result.structured_result.action_plan?.length > 0
      ? result.structured_result.action_plan
      : ["추가 진단이 필요합니다. 다른 각도의 사진으로 다시 시도해 주세요."];
  const statusBadge = result.structured_result.status || "진단 완료";

  return (
    <section className="result-wrap">
      {imageUrl ? <img className="top-image" src={imageUrl} alt="진단한 식물 이미지" /> : null}
      <div className="badge">{statusBadge}</div>

      <article className="card">
        <h3>진단 요약</h3>
        <p>
          <strong>식물 이름</strong> {plantName}
        </p>
        <p>
          <strong>현재 상태</strong> {state}
        </p>
        <p>{summary}</p>
      </article>

      <article className="card">
        <h3>원인 설명</h3>
        <p>{cause}</p>
      </article>

      <article className="card">
        <h3>처방 (Action Plan)</h3>
        <ul>
          {actionPlan.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>

      <div className="button-row">
        <button
          className="secondary"
          onClick={() => window.print()}
          type="button"
          aria-label="리포트 저장"
        >
          리포트 저장
        </button>
        <button className="primary" onClick={onReset} type="button" aria-label="홈으로 돌아가기">
          홈으로 돌아가기
        </button>
      </div>

      <style jsx>{`
        .result-wrap {
          display: flex;
          flex-direction: column;
          gap: 14px;
          animation: slideUp 0.26s ease;
        }
        .top-image {
          width: 100%;
          border-radius: 22px;
          max-height: 260px;
          object-fit: cover;
          box-shadow: 0 12px 24px rgba(46, 125, 50, 0.2);
        }
        .badge {
          align-self: flex-start;
          background: #e8f5e9;
          color: #1f6f2a;
          padding: 8px 12px;
          border-radius: 999px;
          font-size: 0.85rem;
          font-weight: 700;
        }
        .card {
          border-radius: 18px;
          background: #ffffff;
          box-shadow: 0 10px 26px rgba(46, 125, 50, 0.14);
          padding: 16px;
        }
        h3 {
          margin-top: 0;
          color: #1f6f2a;
        }
        p {
          margin: 8px 0;
          color: #2d4630;
          line-height: 1.5;
        }
        ul {
          margin: 0;
          padding-left: 20px;
          color: #2d4630;
          line-height: 1.7;
        }
        .meta {
          margin-top: 12px;
          display: flex;
          justify-content: space-between;
          font-size: 0.86rem;
          color: #4e7f50;
          gap: 8px;
          flex-wrap: wrap;
        }
        .button-row {
          display: grid;
          grid-template-columns: 1fr;
          gap: 10px;
          margin-top: 6px;
        }
        button {
          border: 0;
          border-radius: 14px;
          height: 48px;
          font-size: 0.97rem;
          font-weight: 700;
          cursor: pointer;
        }
        .primary {
          background: #2e7d32;
          color: #fff;
        }
        .secondary {
          background: #eef7ee;
          color: #1f6f2a;
        }
        @keyframes slideUp {
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
