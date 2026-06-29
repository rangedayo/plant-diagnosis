import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDocs,
  limit,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  Timestamp,
  updateDoc,
} from "firebase/firestore";
import { deleteObject, getDownloadURL, ref, uploadBytes } from "firebase/storage";
import { db, storage } from "./firebase";
import { CareGuide, DiagnosisResponse } from "../types/diagnosis";

// Firestore 데이터 레이어 — 진단 이력 쓰기(2-A) + 읽기(2-B) 경로 (설계 docs/design/design_timeline_firebase.md §3).
// 소유자 격리: 모든 경로는 users/{uid} 하위. 보안규칙(firestore.rules/storage.rules)이 본인만 read/write 강제.

// Firestore Timestamp → JS Date. serverTimestamp pending write 등으로 누락 시 null.
function toDate(value: unknown): Date | null {
  return value instanceof Timestamp ? value.toDate() : null;
}

// diagnoses 문서 1건 → DiagnosisRecord (방어적 기본값). listDiagnoses·listRecentDiagnoses 공용.
function toDiagnosisRecord(id: string, data: Record<string, unknown>): DiagnosisRecord {
  return {
    id,
    createdAt: toDate(data.createdAt),
    imageUrl: typeof data.imageUrl === "string" ? data.imageUrl : "",
    status: typeof data.status === "string" ? data.status : "",
    isHealthy: data.isHealthy === true,
    summary: typeof data.summary === "string" ? data.summary : "",
    currentState: typeof data.currentState === "string" ? data.currentState : "",
    cause: typeof data.cause === "string" ? data.cause : "",
    actionPlan: Array.isArray(data.actionPlan) ? (data.actionPlan as string[]) : [],
    careGuide: (data.careGuide ?? null) as CareGuide | null,
    observedSymptoms: Array.isArray(data.observedSymptoms) ? (data.observedSymptoms as string[]) : [],
  };
}

// 식물 목록 카드용 — 마지막 진단 메타.
export type LastDiagnosisMeta = {
  status: string;
  summary: string;
  createdAt: Date | null;
};

// 식물 픽커/목록용 요약 (전체 문서 필드 중 표시에 필요한 것만).
export type PlantSummary = {
  id: string;
  name: string;
  speciesKey: string | null;
  coverImageUrl: string | null;
  lastDiagnosis: LastDiagnosisMeta | null; // 진단 0건이면 null(현 흐름상 거의 없지만 방어)
};

// 진단 이력 1건 (Firestore diagnoses 문서 read 형태, Timestamp→Date 변환).
export type DiagnosisRecord = {
  id: string;
  createdAt: Date | null;
  imageUrl: string;
  status: string;
  isHealthy: boolean;
  summary: string;
  currentState: string;
  cause: string;
  actionPlan: string[];
  careGuide: CareGuide | null;
  observedSymptoms: string[];
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

// 픽커/목록용 식물 목록 (최신 생성 순) + 각 식물의 마지막 진단 메타(N+1, Promise.all).
// 주의: N+1이지만 식물 수가 적은 현 단계에선 OK. 향후 denormalized(plant.lastStatus 등) 최적화 여지.
export async function listPlants(uid: string): Promise<PlantSummary[]> {
  const plantsCol = collection(db, "users", uid, "plants");
  const snap = await getDocs(query(plantsCol, orderBy("createdAt", "desc")));

  const plants = snap.docs.map((d) => {
    const data = d.data();
    return {
      id: d.id,
      name: typeof data.name === "string" ? data.name : "(이름 없음)",
      speciesKey: typeof data.speciesKey === "string" ? data.speciesKey : null,
      coverImageUrl: typeof data.coverImageUrl === "string" ? data.coverImageUrl : null,
    };
  });

  const metas = await Promise.all(
    plants.map(async (p): Promise<LastDiagnosisMeta | null> => {
      const dxCol = collection(db, "users", uid, "plants", p.id, "diagnoses");
      const dxSnap = await getDocs(query(dxCol, orderBy("createdAt", "desc"), limit(1)));
      if (dxSnap.empty) return null;
      const dd = dxSnap.docs[0].data();
      return {
        status: typeof dd.status === "string" ? dd.status : "",
        summary: typeof dd.summary === "string" ? dd.summary : "",
        createdAt: toDate(dd.createdAt),
      };
    }),
  );

  return plants.map((p, i) => ({ ...p, lastDiagnosis: metas[i] }));
}

// 특정 식물의 진단 이력 (최신순). 저장 시 누락 가능 필드는 방어적 기본값.
export async function listDiagnoses(uid: string, plantId: string): Promise<DiagnosisRecord[]> {
  const dxCol = collection(db, "users", uid, "plants", plantId, "diagnoses");
  const snap = await getDocs(query(dxCol, orderBy("createdAt", "desc")));
  return snap.docs.map((d) => toDiagnosisRecord(d.id, d.data()));
}

// 홈 "최근 진단 기록"용 — cross-plant 최신순 N개. 중첩 구조(diagnoses가 plant 하위)라
// collectionGroup 대신 fan-out: 식물별 최신 N건씩 모아 병합·정렬·상위 N개(스키마/보안규칙 무변경).
// 식물 수가 적은 현 단계에 적합(N+1은 listPlants와 동일 트레이드오프).
export type RecentDiagnosis = {
  plant: PlantSummary; // 소유 식물 요약(네비에서 selectedPlant로 사용)
  diagnosis: DiagnosisRecord; // 진단 1건(history 모드 표시·진입용)
};

export async function listRecentDiagnoses(uid: string, max = 5): Promise<RecentDiagnosis[]> {
  const plantsCol = collection(db, "users", uid, "plants");
  const plantsSnap = await getDocs(query(plantsCol, orderBy("createdAt", "desc")));

  const plants: PlantSummary[] = plantsSnap.docs.map((d) => {
    const data = d.data();
    return {
      id: d.id,
      name: typeof data.name === "string" ? data.name : "(이름 없음)",
      speciesKey: typeof data.speciesKey === "string" ? data.speciesKey : null,
      coverImageUrl: typeof data.coverImageUrl === "string" ? data.coverImageUrl : null,
      lastDiagnosis: null, // 최근 카드엔 불필요(개별 진단을 직접 들고 다님)
    };
  });

  const perPlant = await Promise.all(
    plants.map(async (p): Promise<RecentDiagnosis[]> => {
      const dxCol = collection(db, "users", uid, "plants", p.id, "diagnoses");
      const dxSnap = await getDocs(query(dxCol, orderBy("createdAt", "desc"), limit(max)));
      return dxSnap.docs.map((d) => ({ plant: p, diagnosis: toDiagnosisRecord(d.id, d.data()) }));
    }),
  );

  return perPlant
    .flat()
    .sort((a, b) => (b.diagnosis.createdAt?.getTime() ?? 0) - (a.diagnosis.createdAt?.getTime() ?? 0))
    .slice(0, max);
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

// 식물 삭제: 하위 diagnoses 문서 + 각 진단 이미지(Storage) + plant 문서를 모두 제거.
// 소유자만 가능(보안규칙 users/{uid} write). 이미지 삭제는 best-effort(객체 부재/이미 삭제 시 무시).
// 이미지 경로 규약은 saveDiagnosis와 동일: users/{uid}/plants/{plantId}/{dxId}.jpg.
export async function deletePlant(uid: string, plantId: string): Promise<void> {
  const dxCol = collection(db, "users", uid, "plants", plantId, "diagnoses");
  const dxSnap = await getDocs(dxCol);

  await Promise.all(
    dxSnap.docs.map(async (d) => {
      const imgRef = ref(storage, `users/${uid}/plants/${plantId}/${d.id}.jpg`);
      try {
        await deleteObject(imgRef);
      } catch {
        // 이미지가 없거나 이미 삭제된 경우 무시 — 문서 삭제는 계속 진행.
      }
      await deleteDoc(d.ref);
    }),
  );

  await deleteDoc(doc(db, "users", uid, "plants", plantId));
}

// 진단 1건 삭제: diagnoses 문서 + 해당 이미지(Storage). 소유자만 가능(보안규칙).
// 이미지 삭제는 best-effort. 주의: 삭제 대상이 plant 대표 이미지(coverImageUrl)의 원본이면
// 목록 썸네일이 깨질 수 있음(현 단계 허용 — 재진단/저장 시 갱신).
export async function deleteDiagnosis(uid: string, plantId: string, dxId: string): Promise<void> {
  const imgRef = ref(storage, `users/${uid}/plants/${plantId}/${dxId}.jpg`);
  try {
    await deleteObject(imgRef);
  } catch {
    // 이미지가 없거나 이미 삭제된 경우 무시 — 문서 삭제는 계속 진행.
  }
  await deleteDoc(doc(db, "users", uid, "plants", plantId, "diagnoses", dxId));
}
