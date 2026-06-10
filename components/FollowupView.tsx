import FollowupQuestions from "./FollowupQuestions";
import { type FollowupQuestion } from "../lib/followupQuestions";
import { type FollowupAnswer } from "../types/diagnosis";

// [챗봇 단계3] 질문 전용 화면. CareGuideView의 .pg-header(뒤로가기) 패턴을 재사용하고
// 본문에 기존 FollowupQuestions 폼을 그대로 배치. 보정 성공 시 상위(index)가 result로 복귀시킨다
// (이 화면에서 refined 완료 상태는 노출되지 않으므로 refined=false 고정).
type FollowupViewProps = {
  questions: FollowupQuestion[];
  onSubmit: (answers: FollowupAnswer[]) => void;
  submitting: boolean;
  error?: string;
  onBack: () => void; // 1차 결과 화면으로 복귀
};

export default function FollowupView({ questions, onSubmit, submitting, error, onBack }: FollowupViewProps) {
  return (
    <section className="fv">
      {/* 페이지 헤더 — CareGuideView .pg-header 패턴 재사용(뒤로 → 1차 결과). ✦ 장식 동일 */}
      <div className="pg-header">
        <button className="pg-back" type="button" onClick={onBack} aria-label="진단 결과로 돌아가기">
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>
        <h2 className="pg-title">더 정확한 진단</h2>
        <span className="pg-plus" aria-hidden="true">✦</span>
      </div>

      <p className="fv-intro">아래 질문에 답할수록 진단이 더 정확해져요. 해당하는 항목만 골라주세요.</p>

      <FollowupQuestions
        questions={questions}
        onSubmit={onSubmit}
        submitting={submitting}
        refined={false}
        error={error}
      />

      <style jsx>{`
        .fv {
          display: flex;
          flex-direction: column;
          gap: 14px;
          animation: fadeIn 0.26s ease;
        }
        .pg-header {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .pg-back {
          background: none;
          border: none;
          cursor: pointer;
          line-height: 1;
          padding: 4px 4px 4px 0;
          color: var(--green-dark);
          display: flex;
          align-items: center;
        }
        .pg-back i {
          font-size: 26px;
        }
        .pg-title {
          font-size: 22px;
          font-weight: 800;
          color: var(--green-dark);
          letter-spacing: -0.02em;
          margin: 0;
        }
        .pg-plus {
          margin-left: auto;
          font-size: 18px;
          color: var(--text-disabled);
        }
        .fv-intro {
          margin: 0;
          font-size: 13.5px;
          color: var(--text-muted);
          font-weight: 500;
          line-height: 1.55;
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
