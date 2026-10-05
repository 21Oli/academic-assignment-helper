"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import {
  FileText,
  Trash2,
  BarChart2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
  AlertCircle,
  ShieldCheck,
  Clock,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import UploadZone from "@/components/UploadZone";
import {
  getMe,
  listAssignments,
  uploadAssignment,
  deleteAssignment,
  startAnalysis,
  getAssignment,
  AssignmentSummary,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

// Turnitin-style color coding: blue (0%), green (1-24%), yellow (25-49%), orange (50-74%), red (75-100%)
function getScoreColor(score: number) {
  if (score === 0)    return { badge: "bg-blue-50 text-blue-700",    bar: "bg-blue-500",    label: "No matches" };
  if (score < 0.25)   return { badge: "bg-emerald-50 text-emerald-700", bar: "bg-emerald-500", label: "Low" };
  if (score < 0.50)   return { badge: "bg-amber-50 text-amber-700",  bar: "bg-amber-500",   label: "Moderate" };
  if (score < 0.75)   return { badge: "bg-orange-50 text-orange-700", bar: "bg-orange-500",  label: "High" };
  return                     { badge: "bg-red-50 text-red-700",       bar: "bg-red-500",     label: "Very High" };
}

export default function DashboardPage() {
  const router = useRouter();

  const [email, setEmail] = useState<string>("");
  const [assignments, setAssignments] = useState<AssignmentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [analysisMap, setAnalysisMap] = useState<Record<number, { has: boolean; score?: number }>>({});

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  const fetchAssignments = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await listAssignments(p, 10);
      setAssignments(data.items);
      setTotal(data.total);
      setPages(data.pages);
      const details: Record<number, { has: boolean; score?: number }> = {};
      for (const a of data.items) {
        try {
          const d = await getAssignment(a.id);
          details[a.id] = { has: d.has_analysis, score: d.latest_analysis?.plagiarism_score ?? undefined };
        } catch { /* ignore */ }
      }
      setAnalysisMap(details);
    } catch {
      toast.error("Failed to load assignments.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getMe()
      .then((me) => setEmail(me.email))
      .catch(() => router.replace("/login"));
    fetchAssignments(page);
  }, [page, fetchAssignments, router]);

  async function handleUpload(file: File) {
    setUploading(true);
    try {
      await uploadAssignment(file);
      toast.success(`Uploaded: ${file.name}`);
      await fetchAssignments(1);
      setPage(1);
    } catch {
      toast.error("Upload failed. Check file type and size.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this assignment and all its analysis results?")) return;
    setDeletingId(id);
    try {
      await deleteAssignment(id);
      toast.success("Assignment deleted.");
      fetchAssignments(page);
    } catch {
      toast.error("Failed to delete.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleAnalyse(id: number) {
    setAnalyzingId(id);
    try {
      await startAnalysis(id);
      toast.success("Analysis complete!");
      const detail = await getAssignment(id);
      setAnalysisMap((prev) => ({
        ...prev,
        [id]: { has: detail.has_analysis, score: detail.latest_analysis?.plagiarism_score ?? undefined },
      }));
    } catch {
      toast.error("Analysis failed. Please try again.");
    } finally {
      setAnalyzingId(null);
    }
  }

  return (
    <>
      <Navbar email={email} />
      <main className="mx-auto max-w-5xl px-4 py-8">
        {/* Hero header */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-brand-50 p-2">
              <ShieldCheck size={24} className="text-brand-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
              <p className="text-sm text-slate-500">
                Upload assignments, detect plagiarism, and get AI-powered research insights.
              </p>
            </div>
          </div>
        </div>

        {/* Upload zone */}
        <div className="mb-8">
          <UploadZone onFile={handleUpload} loading={uploading} />
        </div>

        {/* Assignments list */}
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">
              Your Documents{" "}
              {total > 0 && (
                <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">
                  {total}
                </span>
              )}
            </h2>
            <button
              onClick={() => fetchAssignments(page)}
              className="btn-secondary text-xs"
              aria-label="Refresh list"
            >
              <RefreshCw size={13} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
            </div>
          ) : assignments.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <div className="rounded-full bg-slate-100 p-4">
                <FileText size={32} className="text-slate-300" />
              </div>
              <p className="font-medium text-slate-600">No documents yet</p>
              <p className="text-sm text-slate-400 max-w-sm">
                Upload a PDF, DOCX, or text file above to start running plagiarism analysis.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {assignments.map((a) => {
                const info = analysisMap[a.id];
                const isAnalyzing = analyzingId === a.id;
                const hasAnalysis = info?.has ?? false;
                const score = info?.score;
                const colors = score != null ? getScoreColor(score) : null;

                return (
                  <li key={a.id} className="flex items-center gap-3 py-4 hover:bg-slate-50/50 -mx-2 px-2 rounded-lg transition">
                    {/* File type icon */}
                    <div className="rounded-lg bg-brand-50 p-2.5 shrink-0">
                      <FileText size={20} className="text-brand-600" />
                    </div>

                    {/* Filename + meta */}
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/assignments/${a.id}`}
                        className="block truncate font-medium text-slate-800 hover:text-brand-600 transition"
                      >
                        {a.filename ?? "Unnamed file"}
                      </Link>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                        {/* Status badge */}
                        {isAnalyzing ? (
                          <span className="badge bg-blue-50 text-blue-600">
                            <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500" />
                            Analyzing…
                          </span>
                        ) : hasAnalysis && score != null && colors ? (
                          <span className={`badge ${colors.badge}`}>
                            <ShieldCheck size={11} className="mr-1" />
                            {Math.round(score * 100)}% similarity · {colors.label}
                          </span>
                        ) : (
                          <span className="badge bg-slate-100 text-slate-500">
                            <AlertCircle size={11} className="mr-1" />
                            Not analyzed
                          </span>
                        )}
                        {/* Word count */}
                        {a.word_count != null && (
                          <span className="text-slate-400">{a.word_count.toLocaleString()} words</span>
                        )}
                        {/* Date */}
                        {a.uploaded_at && (
                          <span className="inline-flex items-center gap-0.5 text-slate-400">
                            <Clock size={11} />
                            {new Date(a.uploaded_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex shrink-0 gap-2">
                      {hasAnalysis && !isAnalyzing && (
                        <Link
                          href={`/assignments/${a.id}`}
                          className="btn-primary text-xs"
                        >
                          <Eye size={13} />
                          View Report
                        </Link>
                      )}
                      <button
                        onClick={() => handleAnalyse(a.id)}
                        disabled={isAnalyzing}
                        className="btn-secondary text-xs"
                        aria-label={`Analyze assignment ${a.id}`}
                      >
                        {isAnalyzing ? (
                          <>
                            <div className="h-3 w-3 animate-spin rounded-full border border-brand-600 border-t-transparent" />
                            Analyzing
                          </>
                        ) : (
                          <>
                            <BarChart2 size={13} />
                            {hasAnalysis ? "Re-scan" : "Analyze"}
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => handleDelete(a.id)}
                        disabled={deletingId === a.id || isAnalyzing}
                        className="btn-danger text-xs"
                        aria-label={`Delete assignment ${a.id}`}
                      >
                        {deletingId === a.id ? (
                          <div className="h-3 w-3 animate-spin rounded-full border border-white border-t-transparent" />
                        ) : (
                          <Trash2 size={13} />
                        )}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {/* Pagination */}
          {pages > 1 && (
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary text-xs"
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <span className="text-xs text-slate-500">
                Page {page} of {pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page === pages}
                className="btn-secondary text-xs"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
