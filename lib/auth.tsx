import { FirebaseError } from "firebase/app";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
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

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signInWithGoogle: async () => {
        const provider = new GoogleAuthProvider();
        try {
          await signInWithPopup(auth, provider);
        } catch (err) {
          // 중복 클릭/연속 호출로 이전 팝업이 cancel된 경우 — 정상 동작의 부산물이라 silent.
          // 다른 모든 에러는 호출 측이 처리할 수 있게 그대로 throw.
          if (err instanceof FirebaseError && err.code === "auth/cancelled-popup-request") {
            return;
          }
          throw err;
        }
      },
      signOut: async () => {
        await firebaseSignOut(auth);
      },
    }),
    [user, loading],
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
