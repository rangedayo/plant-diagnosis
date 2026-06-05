import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import CareGuideView from "../components/CareGuideView";
import HomeView from "../components/HomeView";
import LoadingView from "../components/LoadingView";
import MyPlantsView from "../components/MyPlantsView";
import ResultView from "../components/ResultView";
import SaveDiagnosisModal from "../components/SaveDiagnosisModal";
import TimelineView from "../components/TimelineView";
import { type TabKey } from "../components/BottomTabBar";
import { diagnosePlant } from "../lib/api";
import { useAuth } from "../lib/auth";
import { diagnosisRecordToResponse } from "../lib/historyAdapter";
import { type DiagnosisRecord, type PlantSummary } from "../lib/db";
import { DiagnosisResponse } from "../types/diagnosis";

type Screen = "home" | "loading" | "result" | "care" | "myPlants" | "timeline";

export default function HomePage() {
  const { user, signInWithGoogle } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const [showSave, setShowSave] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  // 2-B 읽기 UI — fresh 진단(result/file)과 격리. history 진입 시 result state는 건드리지 않음.
  const [selectedPlant, setSelectedPlant] = useState<PlantSummary | null>(null);
  const [historyDiagnosis, setHistoryDiagnosis] = useState<DiagnosisRecord | null>(null);

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // 파일 선택 시 즉시 진단(시안엔 별도 "분석 시작" 버튼 없음). file 인자로 setState 비동기 회피.
  const runDiagnosis = async (selectedFile: File) => {
    setFile(selectedFile); // previewUrl(result 화면 사진) 생성용
    setError("");
    setProgress(4);
    setScreen("loading");

    const progressTimer = window.setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 7 : prev));
    }, 260);

    try {
      const data = await diagnosePlant(selectedFile);
      setResult(data);
      setProgress(100);
      window.setTimeout(() => {
        setScreen("result");
      }, 260);
    } catch (err) {
      const message = err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.";
      setError(message);
      setScreen("home");
    } finally {
      window.clearInterval(progressTimer);
    }
  };

  const handleReset = () => {
    setScreen("home");
    setResult(null);
    setFile(null);
    setProgress(0);
    setError("");
    setShowSave(false);
    setHistoryDiagnosis(null); // fresh 복귀 시 history 격리 상태도 정리
  };

  // 하단 탭바 전환 (diagnose/settings는 disabled — 호출 안 옴).
  const handleTabChange = (tab: TabKey) => {
    if (tab === "home") setScreen("home");
    else if (tab === "myPlants") setScreen("myPlants");
  };

  // myPlants 식물 카드 클릭 → timeline.
  const handlePickPlant = (plant: PlantSummary) => {
    setSelectedPlant(plant);
    setScreen("timeline");
  };

  // timeline 진단 카드 클릭 → result(history 모드).
  const handlePickDiagnosis = (record: DiagnosisRecord) => {
    setHistoryDiagnosis(record);
    setScreen("result");
  };

  // 저장 버튼: 미로그인 시 로그인 게이트 → 성공하면 모달 오픈. 로그인돼 있으면 곧장 모달.
  const handleSaveClick = async () => {
    setSavedMsg("");
    if (!user) {
      try {
        await signInWithGoogle();
      } catch {
        return; // 팝업 취소/실패 시 모달 미오픈
      }
    }
    setShowSave(true);
  };

  const handleSaved = () => {
    setShowSave(false);
    setSavedMsg("기록에 저장했어요.");
    window.setTimeout(() => setSavedMsg(""), 3000);
  };

  return (
    <>
      <Head>
        <title>Plantia</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {screen === "home" ? (
        <main>
          <HomeView onFileSelect={runDiagnosis} error={error} onTabChange={handleTabChange} />
        </main>
      ) : screen === "myPlants" ? (
        <main>
          <MyPlantsView
            onPickPlant={handlePickPlant}
            onGoDiagnose={() => setScreen("home")}
            onTabChange={handleTabChange}
          />
        </main>
      ) : (
        <main className="container">
          {/* 브랜드 워드마크는 시안에 없음 → 전역 헤더 제거. 로딩(전용 시안 없음)에만 Plantia 표시. */}
          {screen === "loading" ? (
            <>
              <h1>Plantia</h1>
              <LoadingView progress={progress} />
            </>
          ) : null}

          {/* result: history(과거 진단) vs fresh(신규 진단) 분기 — historyDiagnosis로 격리 */}
          {screen === "result" ? (
            historyDiagnosis ? (
              <ResultView
                result={diagnosisRecordToResponse(historyDiagnosis, { name: selectedPlant?.name ?? "" })}
                imageUrl={historyDiagnosis.imageUrl}
                mode="history"
                onReset={() => {
                  setHistoryDiagnosis(null);
                  setScreen("timeline");
                }}
                onViewCare={historyDiagnosis.careGuide ? () => setScreen("care") : undefined}
              />
            ) : result ? (
              <ResultView
                result={result}
                imageUrl={previewUrl}
                mode="fresh"
                onReset={handleReset}
                onViewCare={result.care_guide ? () => setScreen("care") : undefined}
                onSave={() => void handleSaveClick()}
              />
            ) : null
          ) : null}

          {/* care: history면 historyDiagnosis.careGuide, fresh면 result.care_guide */}
          {screen === "care"
            ? (() => {
                const cg = historyDiagnosis ? historyDiagnosis.careGuide : result?.care_guide;
                if (!cg) return null;
                return <CareGuideView careGuide={cg} onBack={() => setScreen("result")} />;
              })()
            : null}

          {screen === "timeline" && user && selectedPlant ? (
            <TimelineView
              uid={user.uid}
              plant={selectedPlant}
              onBack={() => setScreen("myPlants")}
              onPickDiagnosis={handlePickDiagnosis}
            />
          ) : null}
        </main>
      )}

      {/* 저장 모달 — 로그인·결과·파일이 모두 갖춰졌을 때만 (file은 result 화면 동안 유지됨) */}
      {showSave && user && result && file ? (
        <SaveDiagnosisModal
          result={result}
          imageFile={file}
          onClose={() => setShowSave(false)}
          onSaved={handleSaved}
        />
      ) : null}

      {/* 저장 성공 토스트 */}
      {savedMsg ? (
        <div className="toast" role="status">
          <i className="ti ti-circle-check" aria-hidden="true" />
          {savedMsg}
        </div>
      ) : null}

      <style jsx>{`
        .toast {
          position: fixed;
          left: 50%;
          bottom: 28px;
          transform: translateX(-50%);
          z-index: 60;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: #1f6f2a;
          color: #fff;
          font-size: 14px;
          font-weight: 700;
          padding: 12px 20px;
          border-radius: 999px;
          box-shadow: 0 6px 20px rgba(31, 111, 42, 0.35);
          animation: toastIn 0.24s ease;
        }
        .toast i {
          font-size: 18px;
        }
        @keyframes toastIn {
          from {
            opacity: 0;
            transform: translateX(-50%) translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
          }
        }
        .container {
          max-width: 460px;
          margin: 0 auto;
          min-height: 100vh;
          padding: 20px 16px 40px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        h1 {
          font-size: 1.9rem;
          color: #1f6f2a;
          margin: 4px 4px 6px;
          text-align: left;
        }
      `}</style>
    </>
  );
}
