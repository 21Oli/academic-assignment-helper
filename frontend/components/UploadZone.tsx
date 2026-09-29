"use client";
import { useRef, useState, DragEvent } from "react";
import { Upload, FileText } from "lucide-react";

interface Props {
  onFile: (file: File) => void;
  loading: boolean;
}

const ACCEPTED = [".pdf", ".docx", ".txt"];

export default function UploadZone({ onFile, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      onClick={() => !loading && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      aria-label="Upload assignment file"
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition
        ${dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white hover:border-brand-400 hover:bg-slate-50"}
        ${loading ? "cursor-not-allowed opacity-50" : ""}
      `}
    >
      <div className="rounded-full bg-brand-100 p-3">
        {loading ? (
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        ) : (
          <Upload size={24} className="text-brand-600" />
        )}
      </div>
      <div>
        <p className="font-semibold text-slate-700">
          {loading ? "Uploading…" : "Drop your file here or click to browse"}
        </p>
        <p className="mt-1 text-xs text-slate-500">Supported: PDF, DOCX, TXT · Max 20 MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
        className="sr-only"
        onChange={handleChange}
        disabled={loading}
        aria-hidden="true"
      />
    </div>
  );
}
