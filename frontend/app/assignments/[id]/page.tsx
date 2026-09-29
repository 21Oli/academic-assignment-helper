"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  ArrowLeft,
  BookOpen,
  AlertTriangle,
  Lightbulb,
  Quote,
  BarChart2,
  RefreshCw,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import PlagiarismGauge from "@/components/PlagiarismGauge";
import {
  getMe,
  getAssignment,
  getAnalysisResult,
  startAnalysis,
  AssignmentDetail,
  AnalysisResult,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

export default function AssignmentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);

  const [email, setEmail]               = useState("");
  const [assignment, setAssignment]     = useState<AssignmentDetail | null>(null);
  const [analysis, setAnalysis]         = useState<AnalysisResult | null>(null);
  const [analysing, setAnalysing]       = useState(false);
  const [loadingPage, setLoadingPage]   = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    getMe().then((me) => setEmail(me.email)).catch(() => router.replace("/login"));
  }, [router]);

  async function load() {
    setLoadingPage(true);
    try {
      const a = await getAssignment(id);
      setAssignment(a);
      if (a.has_analysis) {
        const r = await getAnalysisResult(id);
        setAnalysis(r);
      }
    } catch {
      toast.error("Assignment not found.");
      router.replace("/dashboard");
    } finally {
      setLoadingPage(false);
    }
  }

  useEffect(() => { if (id) load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAnalyse() {
    setAnalysing(true);
    try {
      await startAnalysis(id);
      toast.success("Analysis complete!");
      await load();
    } catch {
      toast.error("Analysis failed.");
    } finally {
      setAnalysing(false);
    }
  }

  if (loadingPage) {
    return (
      <>
        <Navbar email={email} />
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        </div>
      </>
    );
  }

  if (!assignment) return null;

  const flaggedSections = (analysis?.flagged_sections ?? []) as Array<{
    chunk_preview?: string;
    score?: number;
    best_match?: { title?: string; authors?: string };
  }>;

  const suggestedSources = (analysis?.suggested_sources ?? []) as Array<{
    title?: string;
    authors?: string;
    publication_year?: number;
    source_type?: string;
    score?: number;
  }>;

  return (
    <>
      <Navbar email={email} />
      <main className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        {/* Back */}
        <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
          <ArrowLeft size={14} /> Back to dashboard
        </Link>

        {/* Assignment header */}
        <div className="card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-900">{assignment.filename ?? "Assignment"}</h1>
              <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-500">
                {assignment.word_count != null && (
                  <span>{assignment.word_count.toLocaleString()} words</span>
                )}
                {assignment.academic_level && (
                  <span className="badge bg-brand-100 text-brand-700 capitalize">
                    {assignment.academic_level}
                  </span>
                )}
                {assignment.uploaded_at && (
                  <span>Uploaded {new Date(assignment.uploaded_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
            <button
              onClick={handleAnalyse}
              disabled={analysing}
              className="btn-primary shrink-0 text-sm"
            >
              {analysing ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <RefreshCw size={15} />
              )}
              {assignment.has_analysis ? "Re-analyse" : "Analyse"}
            </button>
          </div>
        </div>

        {/* No analysis yet */}
        {!analysis && (
          <div className="card flex flex-col items-center gap-3 py-12 text-center text-slate-500">
            <BarChart2 size={36} className="text-slate-300" />
            <p className="font-medium">No analysis yet</p>
            <p className="text-sm">Click &ldquo;Analyse&rdquo; above to run AI-powered plagiarism detection.</p>
          </div>
        )}

        {analysis && (
          <>
            {/* Plagiarism score */}
            <div className="card space-y-4">
              <h2 className="font-semibold text-slate-900">Plagiarism Score</h2>
              <PlagiarismGauge score={analysis.plagiarism_score ?? 0} />
              <div className="flex gap-4 text-sm text-slate-600">
                <span>
                  Confidence:{" "}
                  <strong>{Math.round((analysis.confidence_score ?? 0) * 100)}%</strong>
                </span>
                <span>
                  Flagged sections: <strong>{flaggedSections.length}</strong>
                </span>
              </div>
            </div>

            {/* Flagged sections */}
            {flaggedSections.length > 0 && (
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-red-700">
                  <AlertTriangle size={16} /> Flagged Sections
                </h2>
                {flaggedSections.map((f, i) => (
                  <div key={i} className="rounded-lg border border-red-100 bg-red-50 p-3 text-sm">
                    <p className="font-mono text-slate-700 line-clamp-3">
                      &ldquo;{f.chunk_preview}&rdquo;
                    </p>
                    {f.best_match && (
                      <p className="mt-1 text-xs text-red-600">
                        Matched: <em>{f.best_match.title}</em>
                        {f.best_match.authors ? ` — ${f.best_match.authors}` : ""}
                        {f.score != null ? ` (${Math.round(f.score * 100)}% similarity)` : ""}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Research suggestions */}
            {analysis.research_suggestions && (
              <div className="card space-y-2">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <Lightbulb size={16} className="text-amber-500" /> Research Suggestions
                </h2>
                <p className="whitespace-pre-wrap text-sm text-slate-700">
                  {analysis.research_suggestions}
                </p>
              </div>
            )}

            {/* Citation recommendations */}
            {analysis.citation_recommendations && (
              <div className="card space-y-2">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <Quote size={16} className="text-brand-500" /> Citation Recommendations
                </h2>
                <p className="whitespace-pre-wrap text-sm text-slate-700">
                  {analysis.citation_recommendations}
                </p>
              </div>
            )}

            {/* Suggested sources */}
            {suggestedSources.length > 0 && (
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <BookOpen size={16} className="text-brand-500" /> Suggested Sources
                </h2>
                <ul className="space-y-2">
                  {suggestedSources.map((s, i) => (
                    <li key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
                      <p className="font-medium text-slate-800">{s.title ?? "Untitled"}</p>
                      <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-slate-500">
                        {s.authors && <span>{s.authors}</span>}
                        {s.publication_year && <span>{s.publication_year}</span>}
                        {s.source_type && (
                          <span className="badge bg-slate-200 text-slate-600">{s.source_type}</span>
                        )}
                        {s.score != null && (
                          <span className="ml-auto font-medium text-brand-600">
                            {Math.round(s.score * 100)}% match
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
