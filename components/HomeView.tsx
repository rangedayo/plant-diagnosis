import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../lib/auth";
import { listRecentDiagnoses, type RecentDiagnosis } from "../lib/db";
import { statusBadge, statusLabel } from "../lib/status";
import AuthControl from "./AuthControl";
import BottomTabBar, { type TabKey } from "./BottomTabBar";

type Props = {
  onStartDiagnosis: (file: File) => void; // "진단 시작" 클릭 시에만 상위에서 진단 흐름 트리거
  error?: string;
  onTabChange: (tab: TabKey) => void; // 하단 탭바 전환 (상위 상태머신에서 처리)
  onPickRecent: (item: RecentDiagnosis) => void; // [홈 D] 최근 기록 탭 → 해당 진단 상세(history 모드)
};

// 진단 시점 표기: 최근은 상대시간, 오래되면 날짜.
function formatWhen(d: Date | null): string {
  if (!d) return "";
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "오늘";
  if (days === 1) return "어제";
  if (days < 7) return `${days}일 전`;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

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

export default function HomeView({ onStartDiagnosis, error, onTabChange, onPickRecent }: Props) {
  const cameraRef = useRef<HTMLInputElement | null>(null);
  const albumRef = useRef<HTMLInputElement | null>(null);
  // [홈 C] 선택했지만 아직 진단하지 않은 사진. null=미선택(일러스트+가이드), 존재=미리보기+진단 시작.
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const previewUrl = useMemo(() => (pendingFile ? URL.createObjectURL(pendingFile) : null), [pendingFile]);
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // [홈 D] 로그인 사용자의 cross-plant 최근 진단(최신순 2개). 미로그인=빈 목록(empty state 유지).
  // 홈 보조 위젯이라 실패 시 조용히 빈 목록(에러 배너 없음 — 더미는 절대 금지, 데이터 있을 때만 표시).
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  const [recent, setRecent] = useState<RecentDiagnosis[]>([]);
  const [recentLoading, setRecentLoading] = useState(false);
  useEffect(() => {
    if (!uid) {
      setRecent([]);
      return;
    }
    let cancelled = false;
    setRecentLoading(true);
    listRecentDiagnoses(uid, 2)
      .then((items) => {
        if (!cancelled) setRecent(items);
      })
      .catch(() => {
        if (!cancelled) setRecent([]);
      })
      .finally(() => {
        if (!cancelled) setRecentLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [uid]);

  // 카메라/앨범 input 공유 onChange — 이미지면 pending으로 보관(즉시 진단 X, "진단 시작"에서 호출).
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected?.type.startsWith("image/")) {
      setPendingFile(selected);
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
        {/* 우측: 인증 진입점(Google 로그인/아바타) + 무반응 알림 벨(기존 장식 유지) */}
        <div className="ms-hdr-right">
          <AuthControl />
          {/* 알림 기능 미구현 → 비활성·무반응(클릭 핸들러 없음) */}
          <span className="ms-bell" aria-hidden="true">
            <i className="ti ti-bell" />
          </span>
        </div>
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

        {pendingFile ? (
          <>
            {/* [홈 C] 선택 사진 미리보기 — 일러스트+가이드 자리 대체(가이드 3포인트 숨김) */}
            <div className="preview-wrap">
              <img className="preview-img" src={previewUrl ?? ""} alt="선택한 식물 사진 미리보기" />
            </div>
            <div className="action-wrap">
              <button className="start-btn" type="button" onClick={() => onStartDiagnosis(pendingFile)}>
                <i className="ti ti-stethoscope" aria-hidden="true" />
                진단 시작
              </button>
              <button className="repick-btn" type="button" onClick={() => albumRef.current?.click()}>
                <i className="ti ti-photo" aria-hidden="true" />
                다른 사진 선택
              </button>
            </div>
          </>
        ) : (
          <>
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
          </>
        )}

        {error ? <p className="diag-error">{error}</p> : null}
      </div>

      {/* 최근 진단 기록 — [홈 D] 로그인+데이터 있을 때만 리스트, 그 외 empty state(더미 금지) */}
      <div className="sec-row">
        <div className="sec-left">
          <i className="ti ti-clock" aria-hidden="true" />
          최근 진단 기록
        </div>
        {recent.length > 0 ? (
          <button className="sec-more" type="button" onClick={() => onTabChange("myPlants")}>
            전체 보기
            <i className="ti ti-chevron-right" aria-hidden="true" />
          </button>
        ) : null}
      </div>
      {uid && recentLoading ? (
        <p className="rec-loading">최근 기록을 불러오는 중…</p>
      ) : recent.length > 0 ? (
        <ul className="rec-list">
          {recent.map((item) => {
            const r = item.diagnosis;
            const badge = statusBadge(r.status);
            return (
              <li key={`${item.plant.id}/${r.id}`}>
                <button className="rec-card" type="button" onClick={() => onPickRecent(item)}>
                  {/* 왼쪽: 카드 높이만큼 세로로 꽉 찬 큰 사진 */}
                  <span className="rec-photo">
                    {r.imageUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={r.imageUrl} alt="" />
                    ) : (
                      <i className="ti ti-photo" aria-hidden="true" />
                    )}
                  </span>
                  {/* 오른쪽: 식물명 → status 배지 → 날짜 → 요약 1줄, 우하단 화살표 */}
                  <span className="rec-body">
                    <span className="rec-name">{item.plant.name}</span>
                    {r.status ? (
                      <span className="rec-badge" style={{ background: badge.bg, color: badge.fg }}>
                        {statusLabel(r.status).coarse || r.status}
                      </span>
                    ) : null}
                    <span className="rec-when">{formatWhen(r.createdAt)}</span>
                    {r.summary ? <span className="rec-summary">{r.summary}</span> : null}
                  </span>
                  <i className="ti ti-chevron-right rec-arrow" aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="rec-empty">
          <div className="rec-empty-ic">
            <i className="ti ti-history" aria-hidden="true" />
          </div>
          <p className="rec-empty-title">아직 진단 기록이 없어요</p>
          <p className="rec-empty-sub">첫 진단을 시작해 식물 상태를 기록해보세요.</p>
        </div>
      )}

      {/* 탭바 — 공용 컴포넌트(home 활성). diagnose/settings disabled, myPlants는 상위에서 전환 */}
      <BottomTabBar activeTab="home" onTabChange={onTabChange} />

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
          padding: 20px 16px 10px;
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
        .ms-hdr-right {
          display: flex;
          align-items: center;
          gap: 8px;
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
          padding: 10px 16px 16px;
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

        /* [홈 C] 선택 사진 미리보기 + 액션 버튼 */
        .preview-wrap {
          margin: 14px 0 18px;
          border-radius: 22px;
          overflow: hidden;
          background: var(--bg-photo-placeholder);
          aspect-ratio: 4 / 3;
        }
        .preview-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }
        .action-wrap {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .start-btn {
          width: 100%;
          height: 54px;
          border-radius: 16px;
          border: none;
          background: var(--green-dark);
          color: #fff;
          font-size: 15px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 9px;
          cursor: pointer;
          letter-spacing: -0.01em;
        }
        .start-btn i {
          font-size: 20px;
        }
        .repick-btn {
          width: 100%;
          height: 52px;
          border-radius: 16px;
          border: 1.5px solid var(--green-medium);
          background: var(--bg-card);
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
        .repick-btn i {
          font-size: 18px;
          color: var(--green-camera);
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
          padding: 0 16px;
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

        /* 섹션 헤더 "전체 보기" 링크 */
        .sec-more {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          color: var(--green-medium);
          letter-spacing: -0.01em;
        }
        .sec-more i {
          font-size: 16px;
        }

        /* [홈 D 후속] 최근 진단 기록 — 큰 사진 카드(풀폭, 세로 2 스택) */
        .rec-loading {
          margin: 0 16px;
          padding: 22px 4px;
          font-size: 13.5px;
          color: var(--text-secondary);
          text-align: center;
        }
        .rec-list {
          list-style: none;
          margin: 0 16px;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .rec-card {
          position: relative;
          width: 100%;
          display: flex;
          gap: 14px;
          padding: 12px;
          border-radius: var(--radius-card);
          border: none;
          background: var(--bg-card);
          box-shadow: var(--shadow-card);
          cursor: pointer;
          text-align: left;
          min-height: 116px;
        }
        .rec-photo {
          width: 100px;
          align-self: stretch; /* 카드 높이만큼 세로로 꽉 */
          border-radius: 16px;
          background: var(--bg-icon-circle);
          flex-shrink: 0;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .rec-photo img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .rec-photo i {
          font-size: 30px;
          color: var(--green-medium);
        }
        .rec-body {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 5px;
          padding: 2px 24px 2px 0; /* 우하단 화살표 자리 확보 */
        }
        .rec-name {
          font-size: 16px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.01em;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .rec-badge {
          align-self: flex-start;
          display: inline-flex;
          align-items: center;
          font-size: 11.5px;
          font-weight: 700;
          padding: 4px 12px;
          border-radius: var(--radius-badge);
        }
        .rec-when {
          font-size: 12px;
          color: var(--text-muted);
          font-weight: 500;
        }
        .rec-summary {
          font-size: 12.5px;
          color: var(--text-secondary);
          line-height: 1.45;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .rec-arrow {
          position: absolute;
          right: 14px;
          bottom: 12px;
          font-size: 20px;
          color: #b0c4b2;
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
