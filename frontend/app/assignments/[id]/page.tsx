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
  FileText,
  Calendar,
  Hash,
  GraduationCap,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import {
  getMe,
  getAssignment,
  getAnalysisResult,
  startAnalysis,
  AssignmentDetail,
  AnalysisResult,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

// Turnitin-style color scale
function getScoreStyle(score: number) {
  if (score === 0)    return { text: "text-blue-600",    bg: "bg-blue-50",    ring: "ring-blue-200",    label: "No matches found",     bar: "bg-blue-500",    badge: "bg-blue-50 text-blue-700" };
  if (score < 0.25)   return { text: "text-emerald-600", bg: "bg-emerald-50", ring: "ring-emerald-200", label: "Low similarity",        bar: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-700" };
  if (score < 0.50)   return { text: "text-amber-600",   bg: "bg-amber-50",   ring: "ring-amber-200",   label: "Moderate similarity",  bar: "bg-amber-500",   badge: "bg-amber-50 text-amber-700" };
  if (score < 0.75)   return { text: "text-orange-600",  bg: "bg-orange-50",  ring: "ring-orange-200",  label: "High similarity",      bar: "bg-orange-500",  badge: "bg-orange-50 text-orange-700" };
  return                      { text: "text-red-600",    bg: "bg-red-50",     ring: "ring-red-200",     label: "Very high similarity", bar: "bg-red-500",     badge: "bg-red-50 text-red-700" };
}

export default function AssignmentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);

  const [email, setEmail] = useState("");
  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [loadingPage, setLoadingPage] = useState(true);

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
      } else {
        setAnalysis(null);
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
      toast.error("Analysis failed. Please try again.");
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

  // Sort sources by score descending (like Turnitin's match overview)
  const sortedSources = [...suggestedSources].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  const researchPoints = (analysis?.research_suggestions ?? "")
    .split("\n").map((s) => s.trim()).filter((s) => s.length > 0);

  const citationPoints = (analysis?.citation_recommendations ?? "")
    .split("\n").map((s) => s.trim()).filter((s) => s.length > 0);

  const score = analysis?.plagiarism_score ?? 0;
  const style = getScoreStyle(score);
  const scorePct = Math.round(score * 100);

  return (
    <>
      <Navbar email={email} />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        {/* Back link */}
        <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
          <ArrowLeft size={14} /> Back to dashboard
        </Link>

        {/* Document header */}
        <div className="card">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="rounded-xl bg-brand-50 p-3 shrink-0">
                <FileText size={24} className="text-brand-600" />
              </div>
              <div className="min-w-0">
                <h1 className="text-xl font-bold text-slate-900 break-words">
                  {assignment.filename ?? "Document"}
                </h1>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-500">
                  {assignment.word_count != null && (
                    <span className="inline-flex items-center gap-1">
                      <Hash size={14} />
                      {assignment.word_count.toLocaleString()} words
                    </span>
                  )}
                  {assignment.academic_level && (
                    <span className="inline-flex items-center gap-1">
                      <GraduationCap size={14} />
                      <span className="badge bg-brand-100 text-brand-700 capitalize">{assignment.academic_level}</span>
                    </span>
                  )}
                  {assignment.uploaded_at && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar size={14} />
                      {new Date(assignment.uploaded_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={handleAnalyse}
              disabled={analysing}
              className="btn-primary shrink-0 text-sm"
            >
              {analysing ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Analyzing…
                </>
              ) : (
                <>
                  {assignment.has_analysis ? <RefreshCw size={15} /> : <BarChart2 size={15} />}
                  {assignment.has_analysis ? "Re-run Scan" : "Run Scan"}
                </>
              )}
            </button>
          </div>

          {analysing && (
            <div className="mt-4 space-y-2 rounded-lg bg-blue-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                Running AI-powered analysis…
              </div>
              <div className="flex gap-1.5 text-xs text-blue-600/70">
                <span>Generating embeddings</span>
                <span>→</span>
                <span>Searching sources</span>
                <span>→</span>
                <span>Detecting similarity</span>
                <span>→</span>
                <span>Generating insights</span>
              </div>
            </div>
          )}
        </div>

        {/* No analysis yet */}
        {!analysis && !analysing && (
          <div className="card flex flex-col items-center gap-4 py-16 text-center">
            <div className="rounded-full bg-slate-100 p-5">
              <BarChart2 size={40} className="text-slate-300" />
            </div>
            <div>
              <p className="font-medium text-slate-600 text-lg">No analysis yet</p>
              <p className="text-sm text-slate-400 mt-1 max-w-md">
                Click &ldquo;Run Scan&rdquo; above to compare this document against 50 academic sources,
                detect plagiarism, and get AI-powered research suggestions.
              </p>
            </div>
            <button onClick={handleAnalyse} className="btn-primary text-sm mt-2">
              <BarChart2 size={15} />
              Run Plagiarism Scan
            </button>
          </div>
        )}

        {analysis && (
          <>
            {/* Similarity Score Hero — Turnitin style */}
            <div className={`card ring-2 ${style.ring} ${style.bg}`}>
              <div className="flex items-center gap-6">
                {/* Big score circle */}
                <div className="shrink-0">
                  <div className={`relative flex h-28 w-28 items-center justify-center rounded-full ${style.bg} ${style.text}`}>
                    <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" strokeWidth="6" className="opacity-15" />
                      <circle
                        cx="50" cy="50" r="42" fill="none" stroke="currentColor" strokeWidth="6"
                        strokeLinecap="round"
                        strokeDasharray={`${scorePct * 2.64} 264`}
                        className="transition-all duration-1000 ease-out"
                      />
                    </svg>
                    <div className="text-center">
                      <span className="text-3xl font-bold">{scorePct}%</span>
                    </div>
                  </div>
                </div>

                {/* Score label + summary */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={18} className={style.text} />
                    <h2 className={`font-bold text-lg ${style.text}`}>{style.label}</h2>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {flaggedSections.length > 0
                      ? `${flaggedSections.length} section${flaggedSections.length > 1 ? "s" : ""} flagged above the similarity threshold.`
                      : "No sections exceeded the similarity threshold."}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                      <TrendingUp size={14} className="text-slate-400" />
                      <span className="text-slate-500">Confidence</span>
                      <span className="font-bold text-slate-800">{Math.round((analysis.confidence_score ?? 0) * 100)}%</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <BookOpen size={14} className="text-slate-400" />
                      <span className="text-slate-500">Sources matched</span>
                      <span className="font-bold text-slate-800">{sortedSources.length}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <AlertTriangle size={14} className="text-slate-400" />
                      <span className="text-slate-500">Flagged</span>
                      <span className="font-bold text-slate-800">{flaggedSections.length}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Two column layout: flagged sections (left) + source list (right) */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Flagged sections */}
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <AlertTriangle size={18} className="text-red-500" />
                  Flagged Sections
                  {flaggedSections.length > 0 && (
                    <span className="badge bg-red-100 text-red-700">{flaggedSections.length}</span>
                  )}
                </h2>
                {flaggedSections.length === 0 ? (
                  <div className="py-6 text-center text-sm text-slate-400">
                    <ShieldCheck size={28} className="mx-auto mb-2 text-emerald-400" />
                    No sections exceeded the similarity threshold.
                    <br />
                    This document appears to be largely original.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {flaggedSections.map((f, i) => {
                      const matchScore = f.score ?? 0;
                      const matchStyle = getScoreStyle(matchScore);
                      return (
                        <div key={i} className={`rounded-lg border p-3 text-sm ${matchStyle.bg} border-current/10`}>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <span className={`badge ${matchStyle.badge ?? ""} ${matchStyle.text}`}>
                              #{i + 1} · {Math.round(matchScore * 100)}% match
                            </span>
                          </div>
                          <p className="font-mono text-slate-700 leading-relaxed line-clamp-3 mb-2">
                            &ldquo;{f.chunk_preview}&rdquo;
                          </p>
                          {f.best_match && (
                            <div className="flex items-center gap-1.5 text-xs text-slate-500 border-t border-slate-200/50 pt-2">
                              <BookOpen size={12} />
                              <span className="truncate">
                                Closest: <em className="font-medium">{f.best_match.title}</em>
                                {f.best_match.authors ? ` — ${f.best_match.authors}` : ""}
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Matched sources — sorted by similarity like Turnitin */}
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <BookOpen size={18} className="text-brand-500" />
                  Matched Sources
                  <span className="text-xs font-normal text-slate-400">(sorted by similarity)</span>
                </h2>
                {sortedSources.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-400">No matching sources found.</p>
                ) : (
                  <div className="space-y-2">
                    {sortedSources.map((s, i) => {
                      const sScore = s.score ?? 0;
                      const sStyle = getScoreStyle(sScore);
                      return (
                        <div key={i} className="rounded-lg border border-slate-100 p-3 hover:bg-slate-50 transition">
                          <div className="flex items-start justify-between gap-2 mb-1.5">
                            <p className="font-medium text-slate-800 text-sm leading-tight">{s.title ?? "Untitled"}</p>
                            <span className={`badge ${sStyle.bg} ${sStyle.text} shrink-0`}>
                              {Math.round(sScore * 100)}%
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mb-2">
                            {s.authors && <span>{s.authors}</span>}
                            {s.publication_year && <span>· {s.publication_year}</span>}
                            {s.source_type && (
                              <span className="badge bg-slate-100 text-slate-500">{s.source_type}</span>
                            )}
                          </div>
                          {/* Similarity bar */}
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                            <div
                              className={`h-full rounded-full transition-all duration-700 ${sStyle.bar}`}
                              style={{ width: `${Math.round(sScore * 100)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Research suggestions */}
            {researchPoints.length > 0 && (
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <Lightbulb size={18} className="text-amber-500" />
                  AI Research Suggestions
                </h2>
                <ul className="space-y-2.5">
                  {researchPoints.map((point, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-700 rounded-lg bg-amber-50/50 p-2.5">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-600">
                        {i + 1}
                      </span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Citation recommendations */}
            {citationPoints.length > 0 && (
              <div className="card space-y-3">
                <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                  <Quote size={18} className="text-brand-500" />
                  Citation Recommendations
                </h2>
                <ul className="space-y-2.5">
                  {citationPoints.map((point, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-700 rounded-lg bg-brand-50/50 p-2.5">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-600">
                        {i + 1}
                      </span>
                      <span className="font-mono text-xs leading-relaxed">{point}</span>
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
