import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import CareGuideView from "../components/CareGuideView";
import HomeView from "../components/HomeView";
import LoadingView from "../components/LoadingView";
import ResultView from "../components/ResultView";
import SaveDiagnosisModal from "../components/SaveDiagnosisModal";
import { diagnosePlant } from "../lib/api";
import { useAuth } from "../lib/auth";
import { DiagnosisResponse } from "../types/diagnosis";

type Screen = "home" | "loading" | "result" | "care";

export default function HomePage() {
  const { user, signInWithGoogle } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const [showSave, setShowSave] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

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
          <HomeView onFileSelect={runDiagnosis} error={error} />
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

          {screen === "result" && result ? (
            <ResultView
              result={result}
              imageUrl={previewUrl}
              onReset={handleReset}
              onViewCare={result.care_guide ? () => setScreen("care") : undefined}
              onSave={() => void handleSaveClick()}
            />
          ) : null}

          {screen === "care" && result?.care_guide ? (
            <CareGuideView careGuide={result.care_guide} onBack={() => setScreen("result")} />
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
