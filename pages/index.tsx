import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import LoadingView from "../components/LoadingView";
import ResultView from "../components/ResultView";
import UploadCard from "../components/UploadCard";
import { diagnosePlant } from "../lib/api";
import { DiagnosisResponse } from "../types/diagnosis";

type Screen = "home" | "loading" | "result";

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

  const handleAnalyze = async () => {
    if (!file) {
      setError("이미지를 먼저 선택해 주세요.");
      return;
    }

    setError("");
    setProgress(4);
    setScreen("loading");

    const progressTimer = window.setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 7 : prev));
    }, 260);

    try {
      const data = await diagnosePlant(file);
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

      <main className="container">
        <h1>Plant Butler</h1>

        {screen === "home" ? (
          <>
            <UploadCard file={file} previewUrl={previewUrl} onFileSelect={setFile} />
            <button className="analyze-button" onClick={handleAnalyze} type="button">
              분석 시작
            </button>
          </>
        ) : null}

        {screen === "loading" ? <LoadingView progress={progress} /> : null}

        {screen === "result" && result ? (
          <ResultView result={result} imageUrl={previewUrl} onReset={handleReset} />
        ) : null}

        {error ? <div className="error-message">{error}</div> : null}
      </main>

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
        .analyze-button {
          margin-top: 6px;
          border: 0;
          height: 52px;
          border-radius: 16px;
          color: #fff;
          background: #2e7d32;
          font-size: 1rem;
          font-weight: 700;
          cursor: pointer;
          box-shadow: 0 10px 18px rgba(46, 125, 50, 0.28);
          transition: transform 0.16s ease, filter 0.16s ease;
        }
        .analyze-button:hover {
          transform: translateY(-1px);
          filter: brightness(1.02);
        }
        .error-message {
          margin-top: 4px;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 10px 12px;
          font-size: 0.92rem;
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
}
