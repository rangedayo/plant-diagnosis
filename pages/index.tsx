import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import CareGuideView from "../components/CareGuideView";
import HomeView from "../components/HomeView";
import LoadingView from "../components/LoadingView";
import ResultView from "../components/ResultView";
import { diagnosePlant } from "../lib/api";
import { DiagnosisResponse } from "../types/diagnosis";

type Screen = "home" | "loading" | "result" | "care";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);

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
  };

  return (
    <>
      <Head>
        <title>Plant Butler</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {screen === "home" ? (
        <main>
          <HomeView onFileSelect={runDiagnosis} error={error} />
        </main>
      ) : (
        <main className="container">
          <h1>Plant Butler</h1>

          {screen === "loading" ? <LoadingView progress={progress} /> : null}

          {screen === "result" && result ? (
            <ResultView
              result={result}
              imageUrl={previewUrl}
              onReset={handleReset}
              onViewCare={result.care_guide ? () => setScreen("care") : undefined}
            />
          ) : null}

          {screen === "care" && result?.care_guide ? (
            <CareGuideView careGuide={result.care_guide} onBack={() => setScreen("result")} />
          ) : null}
        </main>
      )}

      <style jsx>{`
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
