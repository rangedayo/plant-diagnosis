import { ChangeEvent, DragEvent, useRef } from "react";

type UploadCardProps = {
  file: File | null;
  previewUrl: string | null;
  onFileSelect: (file: File) => void;
  disabled?: boolean;
};

export default function UploadCard({
  file,
  previewUrl,
  onFileSelect,
  disabled = false,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (disabled) {
      return;
    }

    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile?.type.startsWith("image/")) {
      onFileSelect(droppedFile);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected?.type.startsWith("image/")) {
      onFileSelect(selected);
    }
  };

  return (
    <div
      className={`upload-card ${disabled ? "disabled" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={(event) => event.preventDefault()}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        hidden
        disabled={disabled}
      />
      {file && previewUrl ? (
        <img className="preview-image" src={previewUrl} alt="선택한 식물 이미지 미리보기" />
      ) : (
        <div className="placeholder">
          <p className="placeholder-title">이미지를 업로드하세요</p>
          <p className="placeholder-desc">드래그 앤 드롭 또는 탭해서 선택</p>
        </div>
      )}

      <style jsx>{`
        .upload-card {
          width: 100%;
          min-height: 260px;
          border-radius: 24px;
          border: 2px dashed #9ccc9c;
          background: #f6fff6;
          box-shadow: 0 10px 30px rgba(46, 125, 50, 0.12);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          padding: 12px;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .upload-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 30px rgba(46, 125, 50, 0.18);
        }
        .upload-card.disabled {
          cursor: not-allowed;
          opacity: 0.7;
        }
        .preview-image {
          width: 100%;
          border-radius: 16px;
          object-fit: cover;
          max-height: 360px;
        }
        .placeholder {
          text-align: center;
          color: #2e7d32;
        }
        .placeholder-title {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 700;
        }
        .placeholder-desc {
          margin-top: 8px;
          color: #4e7f50;
          font-size: 0.92rem;
        }
      `}</style>
    </div>
  );
}
