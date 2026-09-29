"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { FileText, Trash2, BarChart2, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import UploadZone from "@/components/UploadZone";
import {
  getMe,
  listAssignments,
  uploadAssignment,
  deleteAssignment,
  startAnalysis,
  AssignmentSummary,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();

  const [email, setEmail]             = useState<string>("");
  const [assignments, setAssignments] = useState<AssignmentSummary[]>([]);
  const [total, setTotal]             = useState(0);
  const [pages, setPages]             = useState(1);
  const [page, setPage]               = useState(1);
  const [uploading, setUploading]     = useState(false);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [deletingId, setDeletingId]   = useState<number | null>(null);
  const [loading, setLoading]         = useState(true);

  // Guard: redirect to login if no token
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
      const res = await uploadAssignment(file);
      toast.success(`Uploaded: ${file.name}`);
      fetchAssignments(1);
      setPage(1);
      // Auto-trigger analysis
      setAnalyzingId(res.assignment_id);
      await startAnalysis(res.assignment_id);
      toast.success("Analysis complete!");
      fetchAssignments(1);
    } catch {
      toast.error("Upload or analysis failed. Check file type and size.");
    } finally {
      setUploading(false);
      setAnalyzingId(null);
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
      fetchAssignments(page);
    } catch {
      toast.error("Analysis failed.");
    } finally {
      setAnalyzingId(null);
    }
  }

  return (
    <>
      <Navbar email={email} />
      <main className="mx-auto max-w-5xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            Upload assignments and run AI-powered plagiarism analysis.
          </p>
        </div>

        {/* Upload zone */}
        <div className="mb-8">
          <UploadZone onFile={handleUpload} loading={uploading} />
        </div>

        {/* Assignments list */}
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">
              Your Assignments{" "}
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
            <div className="flex flex-col items-center gap-2 py-12 text-center text-slate-500">
              <FileText size={36} className="text-slate-300" />
              <p className="font-medium">No assignments yet</p>
              <p className="text-sm">Upload a file above to get started.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {assignments.map((a) => (
                <li key={a.id} className="flex items-center gap-3 py-3">
                  <div className="rounded-lg bg-brand-50 p-2">
                    <FileText size={18} className="text-brand-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/assignments/${a.id}`}
                      className="block truncate font-medium text-slate-800 hover:text-brand-600"
                    >
                      {a.filename ?? "Unnamed file"}
                    </Link>
                    <p className="text-xs text-slate-400">
                      {a.word_count != null ? `${a.word_count} words` : ""}
                      {a.academic_level ? ` · ${a.academic_level}` : ""}
                      {a.uploaded_at
                        ? ` · ${new Date(a.uploaded_at).toLocaleDateString()}`
                        : ""}
                    </p>
                  </div>

                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => handleAnalyse(a.id)}
                      disabled={analyzingId === a.id}
                      className="btn-secondary text-xs"
                      aria-label={`Analyse assignment ${a.id}`}
                    >
                      {analyzingId === a.id ? (
                        <div className="h-3 w-3 animate-spin rounded-full border border-brand-600 border-t-transparent" />
                      ) : (
                        <BarChart2 size={13} />
                      )}
                      Analyse
                    </button>
                    <button
                      onClick={() => handleDelete(a.id)}
                      disabled={deletingId === a.id}
                      className="btn-danger text-xs"
                      aria-label={`Delete assignment ${a.id}`}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </li>
              ))}
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
