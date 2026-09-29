/**
 * Typed API client for the Academic Assignment Helper backend.
 * All requests attach the stored JWT as an Authorization: Bearer header.
 */
import axios, { AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

// Attach token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ────────────────────────────────────────────────────────────────────

export async function register(email: string, password: string, fullName: string) {
  const res = await api.post("/auth/register", { email, password, full_name: fullName });
  return res.data as { message: string; user_id: number };
}

export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data as { access_token: string; token_type: string };
}

export async function getMe() {
  const res = await api.get("/auth/me");
  return res.data as { id: number; email: string; full_name: string; created_at: string };
}

// ── Assignments ──────────────────────────────────────────────────────────────

export interface AssignmentSummary {
  id: number;
  filename: string | null;
  topic: string | null;
  academic_level: string | null;
  word_count: number | null;
  uploaded_at: string | null;
}

export interface AnalysisSummary {
  analysis_id: number;
  plagiarism_score: number | null;
  confidence_score: number | null;
  flagged_sections_count: number;
  research_suggestions: string | null;
  citation_recommendations: string | null;
  analyzed_at: string | null;
}

export interface AssignmentDetail extends AssignmentSummary {
  has_analysis: boolean;
  latest_analysis: AnalysisSummary | null;
}

export interface AssignmentListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: AssignmentSummary[];
}

export async function listAssignments(page = 1, pageSize = 20): Promise<AssignmentListResponse> {
  const res = await api.get("/assignments/", { params: { page, page_size: pageSize } });
  return res.data;
}

export async function getAssignment(id: number): Promise<AssignmentDetail> {
  const res = await api.get(`/assignments/${id}`);
  return res.data;
}

export async function deleteAssignment(id: number) {
  const res = await api.delete(`/assignments/${id}`);
  return res.data as { success: boolean; message: string };
}

export async function uploadAssignment(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post("/upload/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data as { success: boolean; message: string; assignment_id: number };
}

// ── Analysis ─────────────────────────────────────────────────────────────────

export interface AnalysisResult {
  id: number;
  assignment_id: number;
  suggested_sources: Record<string, unknown>[];
  plagiarism_score: number | null;
  flagged_sections: Record<string, unknown>[];
  research_suggestions: string | null;
  citation_recommendations: string | null;
  confidence_score: number | null;
  analyzed_at: string | null;
}

export async function startAnalysis(assignmentId: number) {
  const res = await api.post("/analysis/start", { assignment_id: assignmentId });
  return res.data as { status: string; result: Record<string, unknown> };
}

export async function getAnalysisResult(assignmentId: number): Promise<AnalysisResult> {
  const res = await api.get(`/analysis/${assignmentId}`);
  return res.data;
}
