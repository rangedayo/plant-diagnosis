import { FirebaseError } from "firebase/app";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { auth } from "./firebase";

type AuthContextValue = {
  user: User | null;
  loading: boolean; // 초기 auth 상태 확인 중 (onAuthStateChanged 첫 콜백 전)
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // 진행 중인 로그인 시도(팝업) 1개를 추적 — 중복 팝업 방지용.
  const signInPromiseRef = useRef<Promise<void> | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const signInWithGoogle = useCallback(async () => {
    // 이미 로그인 시도가 진행 중이면 새 팝업을 띄우지 않고 기존 작업을 재사용한다.
    // 버튼 빠른 더블클릭 시 두 번째 팝업이 첫 팝업을 취소시켜 cancelled-popup-request가
    // 나던 문제를 근본 차단(두 번째 호출은 첫 Promise를 그대로 await).
    if (signInPromiseRef.current) {
      return signInPromiseRef.current;
    }
    const provider = new GoogleAuthProvider();
    const attempt = (async () => {
      try {
        await signInWithPopup(auth, provider);
      } catch (err) {
        // 번들 환경에서 instanceof가 어긋날 수 있어 code를 안전하게 추출.
        const code =
          err instanceof FirebaseError ? err.code : (err as { code?: string } | null)?.code;
        // 연속 호출로 이전 팝업이 취소됐거나 사용자가 팝업을 닫은 경우 — 정상 부산물이라 silent.
        // 그 외 에러는 호출 측이 처리할 수 있게 그대로 throw.
        if (
          code === "auth/cancelled-popup-request" ||
          code === "auth/popup-closed-by-user"
        ) {
          return;
        }
        throw err;
      } finally {
        signInPromiseRef.current = null;
      }
    })();
    signInPromiseRef.current = attempt;
    return attempt;
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, signInWithGoogle, signOut }),
    [user, loading, signInWithGoogle, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
