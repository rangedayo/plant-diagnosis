import { ChangeEvent, useRef } from "react";

type Props = {
  onFileSelect: (file: File) => void; // 파일 선택 시 상위에서 진단 흐름 트리거
  error?: string;
};

// 진단 카드 중앙 식물 일러스트 (plantia_home.html 1:1 이식, 장식용)
function PlantHero() {
  return (
    <svg
      viewBox="0 0 324 288"
      width={259}
      height={211}
      // styled-jsx 스코프는 자식 컴포넌트(PlantHero)에 미적용 → 치수/위치를 인라인으로 고정(정본 HTML과 동일)
      style={{ position: "absolute", left: "50%", top: 0, transform: "translateX(-50%)" }}
      aria-hidden="true"
    >
      <g transform="translate(162 215)">
        <g transform="rotate(-78) scale(0.85)">
          <path d="M0 0 C-12 -25 -16 -70 0 -110 C16 -70 12 -25 0 0 Z" fill="#2E6A35" />
        </g>
        <g transform="rotate(78) scale(0.82)">
          <path d="M0 0 C-12 -25 -16 -70 0 -110 C16 -70 12 -25 0 0 Z" fill="#2E6A35" />
        </g>
      </g>
      <g transform="translate(162 215)">
        <g transform="rotate(-55) scale(0.95)">
          <path d="M0 0 C-12 -25 -16 -70 0 -110 C16 -70 12 -25 0 0 Z" fill="#3D8744" />
          <path d="M0 -4 C-1 -55 1 -100 0 -107" stroke="#9FD3A2" strokeWidth="0.8" fill="none" opacity="0.6" />
        </g>
        <g transform="rotate(-30) scale(1.04)">
          <path d="M0 0 C-12 -25 -16 -70 0 -115 C16 -70 12 -25 0 0 Z" fill="#4A9550" />
          <path d="M0 -4 C-1 -55 1 -105 0 -112" stroke="#9FD3A2" strokeWidth="0.8" fill="none" opacity="0.65" />
        </g>
        <g transform="rotate(-5) scale(1.12)">
          <path d="M0 0 C-13 -28 -17 -75 0 -120 C17 -75 13 -28 0 0 Z" fill="#52A056" />
          <path d="M0 -4 C-1 -60 1 -110 0 -117" stroke="#A8DDA8" strokeWidth="0.9" fill="none" opacity="0.7" />
        </g>
        <g transform="rotate(22) scale(1.06)">
          <path d="M0 0 C-12 -25 -16 -70 0 -115 C16 -70 12 -25 0 0 Z" fill="#4A9550" />
          <path d="M0 -4 C-1 -55 1 -105 0 -112" stroke="#9FD3A2" strokeWidth="0.8" fill="none" opacity="0.65" />
        </g>
        <g transform="rotate(48) scale(0.97)">
          <path d="M0 0 C-12 -25 -16 -70 0 -110 C16 -70 12 -25 0 0 Z" fill="#3D8744" />
          <path d="M0 -4 C-1 -55 1 -100 0 -107" stroke="#9FD3A2" strokeWidth="0.8" fill="none" opacity="0.6" />
        </g>
      </g>
      <ellipse cx="162" cy="215" rx="50" ry="6" fill="#3D2E1F" />
      <rect x="108" y="210" width="108" height="12" rx="2.5" fill="#EBE2CC" />
      <path d="M111 222 L213 222 L206 268 L118 268 Z" fill="#DDD3BD" />
      <path d="M111 222 L113 229 L211 229 L213 222 Z" fill="#C9BFA5" opacity="0.4" />
      <ellipse cx="164" cy="115" rx="2.5" ry="3.5" fill="#fff" opacity="0.9" />
      <ellipse cx="139" cy="142" rx="2" ry="3" fill="#fff" opacity="0.8" />
      <ellipse cx="184" cy="145" rx="2.2" ry="3.2" fill="#fff" opacity="0.85" />
    </svg>
  );
}

export default function HomeView({ onFileSelect, error }: Props) {
  const cameraRef = useRef<HTMLInputElement | null>(null);
  const albumRef = useRef<HTMLInputElement | null>(null);

  // 카메라/앨범 input 공유 onChange — 이미지 검증 후 상위로 전달
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected?.type.startsWith("image/")) {
      onFileSelect(selected);
    }
    event.target.value = ""; // 같은 파일 재선택 허용
  };

  return (
    <div className="ms">
      {/* 숨김 file input 2종 (UI만 새 디자인, 동작 동일) */}
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={handleChange} hidden />
      <input ref={albumRef} type="file" accept="image/*" onChange={handleChange} hidden />

      {/* 헤더 — 로고 + 알림 벨(무반응) */}
      <div className="ms-hdr">
        <div className="ms-logo">
          <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
            <path d="M13 3 C8 3 4 7 4 12 C4 17 8 22 13 23 C18 22 22 17 22 12 C22 7 18 3 13 3Z" fill="#2A5428" opacity=".15" />
            <path d="M13 24 L13 10" stroke="#2A5428" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M13 16 Q8 12 8 7 Q13 7 13 13" fill="#2A5428" />
            <path d="M13 13 Q18 9 18 4 Q13 4 13 10" fill="#3D7A3A" />
          </svg>
          Plantia
        </div>
        {/* 알림 기능 미구현 → 비활성·무반응(클릭 핸들러 없음) */}
        <span className="ms-bell" aria-hidden="true">
          <i className="ti ti-bell" />
        </span>
      </div>

      {/* 인사말 */}
      <div className="ms-greet">
        <p className="ms-greet-sub">안녕하세요! 🌱</p>
        <h2 className="ms-greet-main">
          오늘 식물 상태는
          <br />
          어떤가요?
        </h2>
      </div>

      {/* 진단 카드 */}
      <div className="diag-card">
        <h3 className="diag-title">식물 진단 시작하기</h3>
        <p className="diag-desc">
          정확한 진단을 위해
          <br />
          <span className="diag-em">잎이 잘 보이게</span> 촬영해주세요.
        </p>

        <div className="hero-wrap">
          <div className="hero-circle" aria-hidden="true" />
          <PlantHero />

          {/* 가이드 점선 연결선 (정본 plantia_home.html .dl) */}
          <span className="dl dl-focus" aria-hidden="true" />
          <span className="dl dl-leaf" aria-hidden="true" />
          <span className="dl dl-pot" aria-hidden="true" />

          {/* 촬영 가이드 3포인트 (정적) */}
          <div className="guide gd-focus">
            <span className="chk">
              <i className="ti ti-check" aria-hidden="true" />
            </span>
            <span className="col">
              초점이 맞게
              <br />
              선명하게
            </span>
          </div>
          <div className="guide gd-leaf">
            <span className="chk">
              <i className="ti ti-check" aria-hidden="true" />
            </span>
            <span className="col">
              잎 전체가
              <br />
              보이게
            </span>
          </div>
          <div className="guide gd-pot">
            <span className="chk">
              <i className="ti ti-check" aria-hidden="true" />
            </span>
            <span className="col">
              화분과 배경이
              <br />
              잘 보이게
            </span>
          </div>
        </div>

        {/* 카메라(플로팅) + 앨범 버튼 */}
        <div className="cam-wrap">
          <div className="cam-box">
            <p className="cam-title">사진 촬영</p>
            <button className="album-btn" type="button" onClick={() => albumRef.current?.click()}>
              <i className="ti ti-photo" aria-hidden="true" />
              앨범에서 선택
            </button>
          </div>
          <button className="cam-fab" type="button" onClick={() => cameraRef.current?.click()} aria-label="카메라로 촬영">
            <i className="ti ti-camera" aria-hidden="true" />
          </button>
        </div>

        {error ? <p className="diag-error">{error}</p> : null}
      </div>

      {/* 최근 진단 기록 — 데이터 소스 없음 → empty state (더미 제거) */}
      <div className="sec-row">
        <div className="sec-left">
          <i className="ti ti-clock" aria-hidden="true" />
          최근 진단 기록
        </div>
      </div>
      <div className="rec-empty">
        <div className="rec-empty-ic">
          <i className="ti ti-history" aria-hidden="true" />
        </div>
        <p className="rec-empty-title">아직 진단 기록이 없어요</p>
        <p className="rec-empty-sub">첫 진단을 시작해 식물 상태를 기록해보세요.</p>
      </div>

      {/* 탭바 — 홈 활성, 나머지 비활성·무반응 */}
      <nav className="tab-bar" aria-label="하단 내비게이션">
        <div className="tab-item active" aria-current="page">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 3 L21 11 L19 11 L19 20.5 L5 20.5 L5 11 L3 11 Z"
              fill="#D4EBC8"
              stroke="#587A4E"
              strokeWidth="1.6"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            <rect x="9" y="14" width="6" height="6.5" rx="1.2" fill="#587A4E" />
          </svg>
          <span>홈</span>
        </div>
        <div className="tab-item disabled" aria-disabled="true">
          <i className="ti ti-scan" aria-hidden="true" />
          <span>진단</span>
        </div>
        <div className="tab-item disabled" aria-disabled="true">
          <i className="ti ti-plant-2" aria-hidden="true" />
          <span>내 식물</span>
        </div>
        <div className="tab-item disabled" aria-disabled="true">
          <i className="ti ti-settings" aria-hidden="true" />
          <span>설정</span>
        </div>
      </nav>

      <style jsx>{`
        .ms {
          width: 100%;
          max-width: 460px;
          margin: 0 auto;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          animation: fadeIn 0.26s ease;
        }

        /* 헤더 */
        .ms-hdr {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 20px 10px;
        }
        .ms-logo {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 22px;
          font-weight: 800;
          color: #1b3a1c;
          letter-spacing: -0.02em;
        }
        .ms-bell {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-circle);
          border: 1.5px solid #d0e4cc;
          background: var(--bg-card);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: default;
        }
        .ms-bell i {
          font-size: 18px;
          color: #4a6b48;
        }

        /* 인사말 */
        .ms-greet {
          padding: 10px 20px 16px;
        }
        .ms-greet-sub {
          font-size: 14px;
          color: var(--text-muted);
          font-weight: 500;
          margin-bottom: 5px;
        }
        .ms-greet-main {
          font-size: 26px;
          font-weight: 800;
          color: var(--text-primary);
          line-height: 1.25;
          letter-spacing: -0.02em;
          margin: 0;
        }

        /* 진단 카드 */
        .diag-card {
          margin: 0 16px 31px;
          background: var(--bg-card);
          border-radius: 28px;
          padding: 33px 18px 22px;
          box-shadow: var(--shadow-card-elevated);
        }
        .diag-title {
          text-align: center;
          font-size: 24px;
          font-weight: 800;
          color: var(--text-primary);
          margin: 0 0 10px;
          letter-spacing: -0.02em;
        }
        .diag-desc {
          text-align: center;
          font-size: 13.5px;
          color: #6b7b73;
          line-height: 1.65;
          font-weight: 500;
        }
        .diag-em {
          color: var(--green-check);
          font-weight: 700;
        }

        /* 식물 일러스트 + 가이드 */
        .hero-wrap {
          position: relative;
          width: 100%;
          height: 211px;
          margin: 8px auto 4px;
        }
        .hero-circle {
          position: absolute;
          left: 50%;
          top: 24px;
          transform: translateX(-50%);
          width: 120px;
          height: 120px;
          border-radius: var(--radius-circle);
          background: #e7f4e9;
        }
        /* 가이드 점선 연결선 */
        .dl {
          position: absolute;
          border-top: 1.6px dashed var(--border-dashed-upload);
        }
        .dl-focus {
          top: 40px;
          right: 88px;
          width: 24px;
        }
        .dl-leaf {
          top: 96px;
          left: 84px;
          width: 24px;
        }
        .dl-pot {
          top: 168px;
          right: 96px;
          width: 24px;
        }
        .guide {
          position: absolute;
          display: flex;
          align-items: flex-start;
          gap: 5px;
        }
        .gd-focus {
          top: 30px;
          right: 0;
        }
        .gd-leaf {
          top: 86px;
          left: 0;
        }
        .gd-pot {
          top: 158px;
          right: 0;
        }
        .chk {
          width: 21px;
          height: 21px;
          border-radius: var(--radius-circle);
          background: var(--green-check);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          box-shadow: 0 1px 3px rgba(46, 125, 50, 0.25);
        }
        .chk i {
          font-size: 12px;
          color: #fff;
          line-height: 1;
        }
        .col {
          font-size: 12.5px;
          color: var(--text-primary);
          line-height: 1.4;
          font-weight: 500;
          letter-spacing: -0.01em;
        }

        /* 카메라 + 앨범 */
        .cam-wrap {
          position: relative;
          margin-top: 44px;
        }
        .cam-box {
          background: var(--bg-camera-section);
          border-radius: 26px;
          padding: 60px 16px 18px;
        }
        .cam-title {
          text-align: center;
          font-size: 17px;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1.2;
          margin: 0 0 18px; /* p UA 기본 margin-top 제거 → FAB와 간격 정본 일치 */
          letter-spacing: -0.01em;
        }
        .album-btn {
          width: 100%;
          height: 52px;
          border-radius: 16px;
          border: 0;
          background: var(--bg-card);
          color: var(--text-primary);
          font-size: 15px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          cursor: pointer;
          box-shadow: 0 4px 14px rgba(183, 225, 195, 0.4);
        }
        .album-btn i {
          font-size: 20px;
          color: var(--green-camera);
        }
        .cam-fab {
          position: absolute;
          top: -50px;
          left: 50%;
          transform: translateX(-50%);
          width: 100px;
          height: 100px;
          border-radius: var(--radius-circle);
          background: var(--green-camera);
          display: flex;
          align-items: center;
          justify-content: center;
          border: 6px solid #fff;
          box-shadow: var(--shadow-camera-btn);
          z-index: 2;
          cursor: pointer;
        }
        .cam-fab i {
          font-size: 44px;
          color: #fff;
        }
        .diag-error {
          margin-top: 16px;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 10px 12px;
          font-size: 13px;
          text-align: center;
        }

        /* 섹션 헤더 */
        .sec-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 20px;
          margin-bottom: 12px;
        }
        .sec-left {
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary);
        }
        .sec-left i {
          font-size: 18px;
          color: var(--green-medium);
        }

        /* 최근 기록 empty state */
        .rec-empty {
          margin: 0 16px;
          background: var(--bg-card);
          border-radius: 18px;
          box-shadow: 0 2px 12px rgba(42, 84, 40, 0.08);
          padding: 30px 20px 32px;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        .rec-empty-ic {
          width: 52px;
          height: 52px;
          border-radius: var(--radius-circle);
          background: var(--bg-icon-circle);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 12px;
        }
        .rec-empty-ic i {
          font-size: 26px;
          color: var(--text-disabled);
        }
        .rec-empty-title {
          font-size: 14.5px;
          font-weight: 700;
          color: var(--text-secondary);
          margin-bottom: 5px;
        }
        .rec-empty-sub {
          font-size: 12.5px;
          color: var(--text-muted);
          font-weight: 500;
          line-height: 1.5;
        }

        /* 탭바 */
        .tab-bar {
          margin-top: auto;
          background: var(--bg-card);
          border-top: 1px solid var(--border-tab);
          display: flex;
          padding: 10px 0 20px;
        }
        .tab-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 3px;
        }
        .tab-item i {
          font-size: 24px;
          color: var(--text-disabled);
        }
        .tab-item span {
          font-size: 10.5px;
          color: var(--text-disabled);
          font-weight: 500;
        }
        .tab-item.active span {
          color: var(--green-dark);
          font-weight: 700;
        }
        .tab-item.disabled {
          cursor: default;
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
