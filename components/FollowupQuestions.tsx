import { useState } from "react";
import { type FollowupQuestion } from "../lib/followupQuestions";
import { type FollowupAnswer } from "../types/diagnosis";

type FollowupQuestionsProps = {
  questions: FollowupQuestion[];
  onSubmit: (answers: FollowupAnswer[]) => void;
  submitting: boolean;
  refined: boolean; // 2차 보정 완료 여부 — true면 폼 대신 완료 표시
  error?: string;
};

// [챗봇 2차 보정] fresh 결과 하단 객관식 질문 카드. 디자인은 ResultView 카드 시스템
// (전역 토큰 + .card/.sec-hdr 패턴)을 그대로 재현 — 새 디자인 도입 없음.
export default function FollowupQuestions({
  questions,
  onSubmit,
  submitting,
  refined,
  error,
}: FollowupQuestionsProps) {
  // 질문 id → 선택된 옵션. 미선택 문항은 제출 시 무시(전부 선택 강제 X).
  const [selected, setSelected] = useState<Record<string, string>>({});

  const pick = (id: string, option: string) => {
    setSelected((prev) => (prev[id] === option ? omit(prev, id) : { ...prev, [id]: option }));
  };

  const answeredCount = Object.keys(selected).length;

  const handleSubmit = () => {
    const answers: FollowupAnswer[] = questions
      .filter((q) => selected[q.id])
      .map((q) => ({ question: q.question, answer: selected[q.id] }));
    if (answers.length === 0) return;
    onSubmit(answers);
  };

  if (refined) {
    return (
      <div className="fq-done card">
        <div className="fq-done-ic">
          <i className="ti ti-circle-check" aria-hidden="true" />
        </div>
        <div className="fq-done-text">
          <div className="fq-done-title">추가 정보로 진단을 보정했어요</div>
          <div className="fq-done-sub">위 결과가 보정된 진단입니다.</div>
        </div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="sec-hdr">
          <div className="sec-ic">
            <i className="ti ti-message-2" aria-hidden="true" />
          </div>
          <span className="sec-ttl">더 정확한 진단을 위해</span>
        </div>
        <p className="fq-guide">해당하는 항목만 골라주세요. 모르면 비워둬도 괜찮아요.</p>

        {questions.map((q) => (
          <div className="fq-q" key={q.id}>
            <div className="fq-q-label">{q.question}</div>
            <div className="fq-opts">
              {q.options.map((opt) => {
                const active = selected[q.id] === opt;
                return (
                  <button
                    type="button"
                    key={opt}
                    className={`fq-chip${active ? " is-active" : ""}`}
                    aria-pressed={active}
                    onClick={() => pick(q.id, opt)}
                    disabled={submitting}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {error ? (
          <p className="fq-error" role="alert">
            {error}
          </p>
        ) : null}

        <button
          type="button"
          className="fq-submit"
          onClick={handleSubmit}
          disabled={submitting || answeredCount === 0}
        >
          {submitting ? (
            <>
              <i className="ti ti-loader-2 fq-spin" aria-hidden="true" />
              보정 중…
            </>
          ) : (
            <>
              <i className="ti ti-sparkles" aria-hidden="true" />
              더 정확한 진단 받기
            </>
          )}
        </button>
      </div>
      <style jsx>{styles}</style>
    </div>
  );
}

function omit(obj: Record<string, string>, key: string): Record<string, string> {
  const next = { ...obj };
  delete next[key];
  return next;
}

// ResultView와 동일 카드/섹션 헤더 토큰 재사용(styled-jsx 스코프 분리라 클래스는 자체 정의).
const styles = `
  .card {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-card);
    overflow: hidden;
    animation: fadeIn 0.26s ease;
  }
  .card-body {
    padding: 20px;
  }
  .sec-hdr {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
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
  .fq-guide {
    margin: 0 0 16px;
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 500;
    line-height: 1.5;
  }
  .fq-q {
    padding: 12px 0;
    border-bottom: 1px solid var(--border-card-subtle);
  }
  .fq-q:last-of-type {
    border-bottom: none;
  }
  .fq-q-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 10px;
  }
  .fq-opts {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .fq-chip {
    border: 1.5px solid var(--border-tab);
    background: var(--bg-info-row);
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 600;
    padding: 8px 14px;
    border-radius: var(--radius-badge);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    letter-spacing: -0.01em;
  }
  .fq-chip:disabled {
    cursor: default;
    opacity: 0.6;
  }
  .fq-chip.is-active {
    border-color: var(--green-medium);
    background: var(--bg-icon-circle);
    color: var(--green-dark);
  }
  .fq-error {
    margin: 14px 0 0;
    font-size: 13px;
    color: #c0392b;
    font-weight: 600;
  }
  .fq-submit {
    margin-top: 18px;
    width: 100%;
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
    gap: 8px;
    cursor: pointer;
    letter-spacing: -0.01em;
  }
  .fq-submit:disabled {
    background: var(--text-disabled);
    cursor: default;
  }
  .fq-submit i {
    font-size: 18px;
  }
  .fq-spin {
    animation: fqSpin 0.9s linear infinite;
  }

  /* 보정 완료 표시 */
  .fq-done {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
  }
  .fq-done-ic {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-circle);
    background: var(--bg-section-header-icon);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .fq-done-ic i {
    font-size: 24px;
    color: var(--green-check);
  }
  .fq-done-title {
    font-size: 15px;
    font-weight: 700;
    color: #1b2b1c;
    letter-spacing: -0.01em;
  }
  .fq-done-sub {
    font-size: 12.5px;
    color: var(--text-muted);
    margin-top: 3px;
    font-weight: 500;
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
  @keyframes fqSpin {
    to {
      transform: rotate(360deg);
    }
  }
`;
