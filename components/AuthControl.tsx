import { useAuth } from "../lib/auth";

// 홈 헤더 우측 슬롯의 인증 진입점. 미로그인 → "Google로 로그인", 로그인 → 아바타(클릭 시 로그아웃).
export default function AuthControl() {
  const { user, loading, signInWithGoogle, signOut } = useAuth();

  // 초기 auth 확인 중에는 깜빡임 방지를 위해 아무것도 렌더하지 않음.
  if (loading) {
    return null;
  }

  if (!user) {
    return (
      <>
        <button className="auth-login" type="button" onClick={() => void signInWithGoogle()}>
          <i className="ti ti-brand-google" aria-hidden="true" />
          로그인
        </button>
        <style jsx>{`
          .auth-login {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            height: 40px;
            padding: 0 14px;
            border-radius: var(--radius-circle);
            border: 1.5px solid #d0e4cc;
            background: var(--bg-card);
            color: var(--green-dark);
            font-size: 13.5px;
            font-weight: 700;
            cursor: pointer;
          }
          .auth-login i {
            font-size: 16px;
          }
        `}</style>
      </>
    );
  }

  const label = user.displayName ?? user.email ?? "사용자";
  const initial = label.trim().charAt(0).toUpperCase() || "?";

  return (
    <>
      <button
        className="auth-user"
        type="button"
        onClick={() => void signOut()}
        title={`${label} · 로그아웃`}
        aria-label={`${label} · 로그아웃`}
      >
        {user.photoURL ? (
          // 외부(Google) 아바타 — referrerPolicy 미설정 시 403 되는 경우가 있어 no-referrer.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={user.photoURL} alt="" referrerPolicy="no-referrer" />
        ) : (
          <span className="auth-initial">{initial}</span>
        )}
      </button>
      <style jsx>{`
        .auth-user {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-circle);
          border: 1.5px solid #d0e4cc;
          background: var(--bg-card);
          padding: 0;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
        }
        .auth-user img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }
        .auth-initial {
          font-size: 15px;
          font-weight: 800;
          color: var(--green-dark);
        }
      `}</style>
    </>
  );
}
