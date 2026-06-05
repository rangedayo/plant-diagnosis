import {
  addDoc,
  collection,
  doc,
  getDocs,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
} from "firebase/firestore";
import { getDownloadURL, ref, uploadBytes } from "firebase/storage";
import { db, storage } from "./firebase";
import { DiagnosisResponse } from "../types/diagnosis";

// Firestore 데이터 레이어 — 진단 이력 쓰기 경로 (설계 docs/design/design_timeline_firebase.md §3).
// 소유자 격리: 모든 경로는 users/{uid} 하위. 보안규칙(firestore.rules/storage.rules)이 본인만 read/write 강제.

// 식물 픽커용 간단 요약 (전체 문서 필드 중 목록 표시에 필요한 것만).
export type PlantSummary = {
  id: string;
  name: string;
  speciesKey: string | null;
  coverImageUrl: string | null;
};

type CreatePlantInput = {
  name: string;
  speciesKey?: string | null;
  coverImageUrl?: string | null;
};

type SaveDiagnosisInput = {
  imageFile: File;
  result: DiagnosisResponse;
};

type SaveDiagnosisResult = {
  dxId: string;
  imageUrl: string;
};

// 픽커용 식물 목록 (최신 생성 순).
export async function listPlants(uid: string): Promise<PlantSummary[]> {
  const plantsCol = collection(db, "users", uid, "plants");
  const snap = await getDocs(query(plantsCol, orderBy("createdAt", "desc")));
  return snap.docs.map((d) => {
    const data = d.data();
    return {
      id: d.id,
      name: typeof data.name === "string" ? data.name : "(이름 없음)",
      speciesKey: typeof data.speciesKey === "string" ? data.speciesKey : null,
      coverImageUrl: typeof data.coverImageUrl === "string" ? data.coverImageUrl : null,
    };
  });
}

// 새 식물 엔티티 생성 → plantId 반환.
export async function createPlant(uid: string, input: CreatePlantInput): Promise<string> {
  const plantsCol = collection(db, "users", uid, "plants");
  const docRef = await addDoc(plantsCol, {
    name: input.name,
    speciesKey: input.speciesKey ?? null,
    coverImageUrl: input.coverImageUrl ?? null,
    createdAt: serverTimestamp(),
  });
  return docRef.id;
}

// 신규 식물의 대표 이미지를 첫 진단 이미지로 갱신.
export async function updatePlantCover(uid: string, plantId: string, coverImageUrl: string): Promise<void> {
  const plantRef = doc(db, "users", uid, "plants", plantId);
  await updateDoc(plantRef, { coverImageUrl });
}

// 진단 1건 저장: (1) dxId 선발급 → (2) 이미지 Storage 업로드 → (3) diagnoses 문서 기록.
// 매핑(설계 §3): current_state→currentState, action_plan→actionPlan, isHealthy는 status==="건강" 파생.
export async function saveDiagnosis(
  uid: string,
  plantId: string,
  { imageFile, result }: SaveDiagnosisInput,
): Promise<SaveDiagnosisResult> {
  // Firestore auto-id를 미리 발급(아직 쓰지 않음) → Storage 경로에 동일 dxId 사용.
  const diagnosesCol = collection(db, "users", uid, "plants", plantId, "diagnoses");
  const dxRef = doc(diagnosesCol);
  const dxId = dxRef.id;

  // 이미지 업로드 → 다운로드 URL. 경로 규약: users/{uid}/plants/{plantId}/{dxId}.jpg.
  const storageRef = ref(storage, `users/${uid}/plants/${plantId}/${dxId}.jpg`);
  await uploadBytes(storageRef, imageFile, { contentType: imageFile.type || "image/jpeg" });
  const imageUrl = await getDownloadURL(storageRef);

  const sr = result.structured_result;
  const analysis = result.analysis;

  await setDoc(dxRef, {
    createdAt: serverTimestamp(),
    imageUrl,
    status: sr.status ?? "",
    isHealthy: sr.status === "건강",
    summary: sr.summary ?? "",
    currentState: sr.current_state ?? "",
    cause: sr.cause ?? "",
    actionPlan: Array.isArray(sr.action_plan) ? sr.action_plan : [],
    careGuide: result.care_guide ?? null,
    observedSymptoms: Array.isArray(analysis?.observed_symptoms) ? analysis?.observed_symptoms : [],
  });

  return { dxId, imageUrl };
}
