type LoadingViewProps = {
  progress: number;
};

const STEPS = ["이미지 분석", "잎 상태 진단", "처방 생성"];

export default function LoadingView({ progress }: LoadingViewProps) {
  const currentStep = Math.min(STEPS.length - 1, Math.floor(progress / 34));

  return (
    <section className="loading-wrap">
      <div className="plant-glow" aria-hidden="true">
        🌿
      </div>
      <h2>진단 중입니다</h2>
      <p>식물의 상태를 차근차근 분석하고 있어요.</p>

      <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <ul>
        {STEPS.map((step, idx) => (
          <li key={step} className={idx <= currentStep ? "active" : ""}>
            {step}
          </li>
        ))}
      </ul>

      <style jsx>{`
        .loading-wrap {
          background: #ffffff;
          border-radius: 24px;
          padding: 28px 20px;
          text-align: center;
          box-shadow: 0 12px 30px rgba(46, 125, 50, 0.14);
          animation: fadeIn 0.25s ease;
        }
        .plant-glow {
          width: 86px;
          height: 86px;
          margin: 0 auto 16px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 2rem;
          background: radial-gradient(circle, #d6f3d8 0%, #a5d6a7 48%, #81c784 100%);
          animation: pulse 1.3s infinite ease-in-out;
        }
        h2 {
          margin: 0;
          color: #1f6f2a;
        }
        p {
          margin: 8px 0 18px;
          color: #4e7f50;
        }
        .progress-track {
          width: 100%;
          background: #e8f5e9;
          height: 10px;
          border-radius: 999px;
          overflow: hidden;
        }
        .progress-fill {
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #43a047, #2e7d32);
          transition: width 0.22s ease;
        }
        ul {
          list-style: none;
          padding: 0;
          margin: 16px 0 0;
          text-align: left;
        }
        li {
          padding: 8px 0;
          color: #8ba38d;
          font-size: 0.95rem;
        }
        li.active {
          color: #2e7d32;
          font-weight: 700;
        }
        @keyframes pulse {
          0% {
            transform: scale(0.98);
            box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.45);
          }
          70% {
            transform: scale(1);
            box-shadow: 0 0 0 18px rgba(46, 125, 50, 0);
          }
          100% {
            transform: scale(0.98);
            box-shadow: 0 0 0 0 rgba(46, 125, 50, 0);
          }
        }
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(4px);
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
