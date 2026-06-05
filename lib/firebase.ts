import { getApp, getApps, initializeApp, type FirebaseApp, type FirebaseOptions } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";
import { getStorage, type FirebaseStorage } from "firebase/storage";

// 모든 값은 NEXT_PUBLIC_FIREBASE_* env에서만 주입 (하드코딩 금지). 콘솔 web config로 채움.
const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// 중복 init 가드 — Fast Refresh/SSR에서 initializeApp 재호출 방지.
const app: FirebaseApp = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);

export const firebaseApp = app;
export const auth: Auth = getAuth(app);
// Firestore는 명명 DB(plant-diagnosis)로 생성됨 — getFirestore(app)은 '(default)'를 가리켜 못 찾음.
// env로 DB id 주입, 미설정 시 확인된 id로 fallback.
const firestoreDbId = process.env.NEXT_PUBLIC_FIREBASE_FIRESTORE_DATABASE_ID || "plant-diagnosis";
export const db: Firestore = getFirestore(app, firestoreDbId);
export const storage: FirebaseStorage = getStorage(app);
