import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import CareGuideView from "../components/CareGuideView";
import FollowupView from "../components/FollowupView";
import HomeView from "../components/HomeView";
import LoadingView from "../components/LoadingView";
import MyPlantsView from "../components/MyPlantsView";
import RefineBanner from "../components/RefineBanner";
import RefineEntryCard from "../components/RefineEntryCard";
import ResultView from "../components/ResultView";
import SaveDiagnosisModal from "../components/SaveDiagnosisModal";
import TimelineView from "../components/TimelineView";
import { type TabKey } from "../components/BottomTabBar";
import { diagnosePlant, refineDiagnosis } from "../lib/api";
import { useAuth } from "../lib/auth";
import { diagnosisRecordToResponse } from "../lib/historyAdapter";
import { type DiagnosisRecord, type PlantSummary } from "../lib/db";
import { FOLLOWUP_QUESTIONS } from "../lib/followupQuestions";
import { DiagnosisResponse, type FollowupAnswer } from "../types/diagnosis";

type Screen = "home" | "loading" | "result" | "followup" | "care" | "myPlants" | "timeline";

export default function HomePage() {
  const { user, signInWithGoogle } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  // [챗봇 2차 보정] 1차 result는 echo 원본(불변 보존), 2차 결과는 별도 state로 격리.
  const [refinedResult, setRefinedResult] = useState<DiagnosisResponse | null>(null);
  const [refining, setRefining] = useState(false);
  const [refineError, setRefineError] = useState<string>("");
  // [단계3] 2차 결과 화면에서 1차 진단을 다시 보는 토글. true=1차 표시, false=2차 표시.
  const [showPrimary, setShowPrimary] = useState(false);
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
    setRefinedResult(null); // 새 진단 시작 → 이전 2차 보정 결과·에러 초기화
    setRefineError("");
    setShowPrimary(false); // 토글 상태도 기본(2차)로 리셋
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
    setRefinedResult(null); // 2차 보정 결과·진행 상태도 초기화
    setRefining(false);
    setRefineError("");
    setShowPrimary(false);
    setFile(null);
    setProgress(0);
    setError("");
    setShowSave(false);
    setHistoryDiagnosis(null); // fresh 복귀 시 history 격리 상태도 정리
  };

  // [챗봇 2차 보정] 1차 result(echo 원본)의 analysis·refine_context를 변형 없이 그대로
  // RefineRequest로 실어 /diagnose/refine 호출 → refinedResult 갱신. 실패 시 1차 결과 유지.
  const handleRefine = async (answers: FollowupAnswer[]) => {
    const src = result; // pristine 1차(echo-back 무결성 — 프론트가 증상·RAG 미가공)
    if (!src?.analysis || !src.refine_context) return;
    setRefining(true);
    setRefineError("");
    try {
      const data = await refineDiagnosis({
        analysis: src.analysis,
        refine_context: src.refine_context,
        answers,
      });
      setRefinedResult(data);
      setShowPrimary(false); // 보정 직후엔 2차 결과를 보여줌
      setScreen("result"); // [단계3] 질문 화면 → 2차 결과로 복귀
    } catch (err) {
      const message = err instanceof Error ? err.message : "보정에 실패했습니다.";
      setRefineError(message); // 실패 시 질문 화면 유지(FollowupView가 에러 표시)
    } finally {
      setRefining(false);
    }
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

  // [단계3] fresh 화면에 실제 표시할 결과 = 2차(refinedResult) 있고 1차 토글이 꺼져 있으면 2차, 그 외 1차.
  // result가 null이면 null. ResultView/care가 공유.
  const displayResult = refinedResult && !showPrimary ? refinedResult : result;

  return (
    <>
      <Head>
        <title>Plantia</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {screen === "home" ? (
        <main>
          <HomeView onStartDiagnosis={runDiagnosis} error={error} onTabChange={handleTabChange} />
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
              <>
                {/* [단계3] 2차 보정 완료 시 결과 상단에 변화 안내 배너 + 1차/2차 토글 */}
                {refinedResult ? (
                  <RefineBanner
                    primaryStatus={result.structured_result.status || ""}
                    refinedStatus={refinedResult.structured_result.status || ""}
                    showPrimary={showPrimary}
                    onToggle={() => setShowPrimary((v) => !v)}
                  />
                ) : null}
                {/* 표시 결과 = displayResult(2차 ↔ 토글 시 1차). ResultView 렌더 로직 무변경 */}
                <ResultView
                  result={displayResult ?? result}
                  imageUrl={previewUrl}
                  mode="fresh"
                  onReset={handleReset}
                  onViewCare={(displayResult ?? result).care_guide ? () => setScreen("care") : undefined}
                  onSave={() => void handleSaveClick()}
                />
                {/* [단계3] 진입 카드 — fresh + 1차 echo 재료 존재 + 아직 보정 전(2차 없음)일 때만.
                    탭 → 질문 전용 화면. history는 별도 분기라 미노출. */}
                {!refinedResult && result.analysis && result.refine_context ? (
                  <RefineEntryCard
                    onClick={() => {
                      setRefineError("");
                      setScreen("followup");
                    }}
                  />
                ) : null}
              </>
            ) : null
          ) : null}

          {/* [단계3] 질문 전용 화면 — fresh + 1차 echo 재료 존재 시만(history 미노출). 뒤로 → 1차 결과 */}
          {screen === "followup" && result && result.analysis && result.refine_context ? (
            <FollowupView
              questions={FOLLOWUP_QUESTIONS}
              onSubmit={(answers) => void handleRefine(answers)}
              submitting={refining}
              error={refineError}
              onBack={() => setScreen("result")}
            />
          ) : null}

          {/* care: history면 historyDiagnosis.careGuide, fresh면 displayResult.care_guide(토글 반영) */}
          {screen === "care"
            ? (() => {
                const cg = historyDiagnosis ? historyDiagnosis.careGuide : displayResult?.care_guide;
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
