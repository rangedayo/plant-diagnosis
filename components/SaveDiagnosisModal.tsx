import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { createPlant, listPlants, saveDiagnosis, updatePlantCover, type PlantSummary } from "../lib/db";
import { DiagnosisResponse } from "../types/diagnosis";

type Props = {
  result: DiagnosisResponse;
  imageFile: File;
  onClose: () => void;
  onSaved: () => void;
};

type Mode = "pick" | "new";

// 진단 결과를 "내 식물" 기록에 저장하는 오버레이 모달.
// 기존 식물 선택 또는 새 식물 생성(별칭) → 이미지 Storage 업로드 + diagnoses 문서 기록.
export default function SaveDiagnosisModal({ result, imageFile, onClose, onSaved }: Props) {
  const { user } = useAuth();
  const uid = user?.uid ?? null;

  const [plants, setPlants] = useState<PlantSummary[]>([]);
  const [loadingPlants, setLoadingPlants] = useState(true);
  const [mode, setMode] = useState<Mode>("pick");
  const [selectedPlantId, setSelectedPlantId] = useState<string>("");
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!uid) return;
    let cancelled = false;
    setLoadingPlants(true);
    listPlants(uid)
      .then((items) => {
        if (cancelled) return;
        setPlants(items);
        // 식물이 하나도 없으면 곧장 "새 식물 만들기"로.
        if (items.length === 0) {
          setMode("new");
        } else {
          setSelectedPlantId(items[0].id);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "식물 목록을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoadingPlants(false);
      });
    return () => {
      cancelled = true;
    };
  }, [uid]);

  const handleConfirm = async () => {
    if (!uid) {
      setError("로그인이 필요합니다.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      let plantId = selectedPlantId;
      const isNew = mode === "new";

      if (isNew) {
        const name = newName.trim();
        if (!name) {
          setError("식물 별칭을 입력해주세요.");
          setSaving(false);
          return;
        }
        plantId = await createPlant(uid, {
          name,
          speciesKey: result.care_guide?.species_key ?? null,
          coverImageUrl: null,
        });
      }

      if (!plantId) {
        setError("식물을 선택하거나 새로 만들어주세요.");
        setSaving(false);
        return;
      }

      const { imageUrl } = await saveDiagnosis(uid, plantId, { imageFile, result });

      // 신규 식물은 대표 이미지를 이 진단 이미지로 설정.
      if (isNew) {
        await updatePlantCover(uid, plantId, imageUrl);
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
      setSaving(false);
    }
  };

  return (
    <div className="ov" role="dialog" aria-modal="true" aria-label="진단 기록 저장">
      <button className="ov-bg" type="button" aria-label="닫기" onClick={onClose} disabled={saving} />
      <div className="sheet">
        <div className="sheet-hdr">
          <h2 className="sheet-ttl">이 식물 기록에 저장</h2>
          <button className="sheet-x" type="button" onClick={onClose} aria-label="닫기" disabled={saving}>
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>

        <p className="sheet-note">이미지와 진단 결과가 내 계정에 저장됩니다.</p>

        {loadingPlants ? (
          <p className="sheet-loading">식물 목록을 불러오는 중…</p>
        ) : (
          <>
            {/* 모드 토글 (기존 식물이 있을 때만 노출) */}
            {plants.length > 0 ? (
              <div className="seg">
                <button
                  type="button"
                  className={`seg-btn${mode === "pick" ? " on" : ""}`}
                  onClick={() => setMode("pick")}
                  disabled={saving}
                >
                  기존 식물
                </button>
                <button
                  type="button"
                  className={`seg-btn${mode === "new" ? " on" : ""}`}
                  onClick={() => setMode("new")}
                  disabled={saving}
                >
                  새 식물
                </button>
              </div>
            ) : null}

            {mode === "pick" && plants.length > 0 ? (
              <ul className="plant-list">
                {plants.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      className={`plant-item${selectedPlantId === p.id ? " sel" : ""}`}
                      onClick={() => setSelectedPlantId(p.id)}
                      disabled={saving}
                    >
                      <span className="plant-thumb">
                        {p.coverImageUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={p.coverImageUrl} alt="" />
                        ) : (
                          <i className="ti ti-plant-2" aria-hidden="true" />
                        )}
                      </span>
                      <span className="plant-name">{p.name}</span>
                      {selectedPlantId === p.id ? (
                        <i className="ti ti-check plant-chk" aria-hidden="true" />
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}

            {mode === "new" ? (
              <div className="new-wrap">
                <label className="new-lbl" htmlFor="plant-name">
                  식물 별칭
                </label>
                <input
                  id="plant-name"
                  className="new-input"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="예: 거실 행운목"
                  maxLength={40}
                  disabled={saving}
                />
              </div>
            ) : null}
          </>
        )}

        {error ? <p className="sheet-err">{error}</p> : null}

        <div className="sheet-actions">
          <button className="btn-out" type="button" onClick={onClose} disabled={saving}>
            취소
          </button>
          <button className="btn-fill" type="button" onClick={() => void handleConfirm()} disabled={saving || loadingPlants}>
            {saving ? "저장 중…" : "저장"}
          </button>
        </div>
      </div>

      <style jsx>{`
        .ov {
          position: fixed;
          inset: 0;
          z-index: 50;
          display: flex;
          align-items: flex-end;
          justify-content: center;
        }
        .ov-bg {
          position: absolute;
          inset: 0;
          border: none;
          padding: 0;
          background: rgba(20, 35, 22, 0.45);
          cursor: pointer;
          animation: ovFade 0.2s ease;
        }
        .sheet {
          position: relative;
          width: 100%;
          max-width: 460px;
          background: var(--bg-card);
          border-radius: 24px 24px 0 0;
          padding: 20px 18px calc(20px + env(safe-area-inset-bottom));
          box-shadow: 0 -8px 30px rgba(20, 35, 22, 0.2);
          animation: sheetUp 0.26s ease;
        }
        .sheet-hdr {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 6px;
        }
        .sheet-ttl {
          font-size: 18px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.01em;
          margin: 0;
        }
        .sheet-x {
          width: 34px;
          height: 34px;
          border: none;
          background: none;
          cursor: pointer;
          color: var(--text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .sheet-x i {
          font-size: 22px;
        }
        .sheet-note {
          font-size: 12.5px;
          color: var(--text-muted);
          font-weight: 500;
          margin: 0 0 14px;
        }
        .sheet-loading {
          font-size: 14px;
          color: var(--text-secondary);
          padding: 18px 2px;
        }
        .seg {
          display: flex;
          gap: 6px;
          background: var(--bg-info-row);
          border-radius: 14px;
          padding: 4px;
          margin-bottom: 14px;
        }
        .seg-btn {
          flex: 1;
          height: 38px;
          border: none;
          border-radius: 11px;
          background: transparent;
          color: var(--text-secondary);
          font-size: 13.5px;
          font-weight: 700;
          cursor: pointer;
        }
        .seg-btn.on {
          background: var(--bg-card);
          color: var(--green-dark);
          box-shadow: 0 1px 4px rgba(42, 84, 40, 0.12);
        }
        .plant-list {
          list-style: none;
          margin: 0 0 4px;
          padding: 0;
          max-height: 260px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .plant-item {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: 14px;
          border: 1.5px solid var(--border-tab);
          background: var(--bg-card);
          cursor: pointer;
          text-align: left;
        }
        .plant-item.sel {
          border-color: var(--green-medium);
          background: #f5faf3;
        }
        .plant-thumb {
          width: 42px;
          height: 42px;
          border-radius: 12px;
          background: var(--bg-icon-circle);
          flex-shrink: 0;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .plant-thumb img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .plant-thumb i {
          font-size: 20px;
          color: var(--green-medium);
        }
        .plant-name {
          flex: 1;
          font-size: 14.5px;
          font-weight: 600;
          color: var(--text-primary);
        }
        .plant-chk {
          font-size: 18px;
          color: var(--green-dark);
        }
        .new-wrap {
          margin-bottom: 4px;
        }
        .new-lbl {
          display: block;
          font-size: 13px;
          font-weight: 700;
          color: var(--text-secondary);
          margin-bottom: 7px;
        }
        .new-input {
          width: 100%;
          height: 50px;
          border-radius: 14px;
          border: 1.5px solid var(--border-tab);
          background: var(--bg-card);
          padding: 0 14px;
          font-size: 15px;
          color: var(--text-primary);
          outline: none;
        }
        .new-input:focus {
          border-color: var(--green-medium);
        }
        .sheet-err {
          margin: 12px 0 0;
          background: #ffebee;
          border: 1px solid #ffcdd2;
          color: #b71c1c;
          border-radius: 12px;
          padding: 10px 12px;
          font-size: 13px;
        }
        .sheet-actions {
          display: flex;
          gap: 10px;
          margin-top: 18px;
        }
        .btn-out {
          flex: 1;
          height: 52px;
          border-radius: var(--radius-button);
          border: 1.5px solid var(--green-medium);
          background: transparent;
          color: var(--green-medium);
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
        }
        .btn-fill {
          flex: 2;
          height: 52px;
          border-radius: var(--radius-button);
          border: none;
          background: var(--green-dark);
          color: #fff;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
        }
        .btn-fill:disabled,
        .btn-out:disabled {
          opacity: 0.55;
          cursor: default;
        }
        @keyframes ovFade {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        @keyframes sheetUp {
          from {
            transform: translateY(18px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
