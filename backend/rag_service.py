import os
import asyncio
import json
import hashlib
import random
import re
from typing import List, Dict, Any, Optional

import numpy as np
import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AcademicSource, AnalysisResult, Assignment

# ---------- Local embedding fallback (384-dim — NOT stored in DB) ----------
# The DB column is Vector(1536) for OpenAI embeddings. The local model produces
# 384-dim vectors which are ONLY used for in-process similarity when OpenAI is
# unavailable; they are never persisted to academic_sources.embedding.
try:
    from sentence_transformers import SentenceTransformer
    LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    USE_LOCAL_FALLBACK = True
    print("🧠 Local embedding model loaded (384-dim, in-process only).")
except Exception:
    LOCAL_MODEL = None
    USE_LOCAL_FALLBACK = False
    print("⚠️  Local embedding model not available.")

# ---------- Environment Config ----------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
# Unified default — matches .env.example and main.py log message
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COMPLETION_MODEL = os.getenv("OPENAI_COMPLETION_MODEL", "gpt-4o-mini")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "2000"))
PLAGIARISM_THRESHOLD = float(os.getenv("PLAGIARISM_THRESHOLD", "0.85"))
MAX_RETRIES = 6

# OpenAI text-embedding-3-small and text-embedding-ada-002 both produce 1536-dim vectors.
OPENAI_EMBEDDING_DIM = 1536

# ---------- Disk-based embedding cache ----------
CACHE_PATH = "data/embeddings_cache.json"
os.makedirs("data", exist_ok=True)

try:
    with open(CACHE_PATH, "r", encoding="utf-8") as _f:
        EMBEDDING_CACHE: Dict[str, List[float]] = json.load(_f)
except Exception:
    EMBEDDING_CACHE = {}


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _save_cache() -> None:
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(EMBEDDING_CACHE, f)
    except Exception as e:
        print(f"⚠️  Could not save embedding cache: {e}")


# ---------- OpenAI HTTP helper ----------
async def _openai_post(endpoint: str, payload: dict, timeout: int = 40) -> dict:
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
    url = f"https://api.openai.com/v1{endpoint}"

    for attempt in range(1, MAX_RETRIES + 1):
        await asyncio.sleep(random.uniform(1, 3))
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = min(4 ** attempt + random.random(), 60)
                print(f"⚠️  [429] Retry {attempt}/{MAX_RETRIES} in {wait:.1f}s…")
                await asyncio.sleep(wait)
            elif e.response.status_code in (401, 402):
                raise RuntimeError("❌ OpenAI quota exceeded or invalid API key.")
            else:
                raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RequestError) as e:
            wait = 2 ** attempt
            print(f"🌐 [Network] {e}. Retry in {wait}s…")
            await asyncio.sleep(wait)

    raise RuntimeError("❌ OpenAI request failed after all retries.")


# ---------- Embedding ----------
async def get_embedding(text_input: str) -> List[float]:
    """
    Returns a 1536-dim OpenAI embedding, with an in-process local fallback
    (384-dim) when OpenAI is unavailable.

    IMPORTANT: local fallback embeddings are returned for runtime similarity
    comparisons but are NEVER written to the DB (dimension mismatch with
    the Vector(1536) column would cause a pgvector error).
    """
    if not text_input.strip():
        return []

    key = _hash_text(text_input)
    if key in EMBEDDING_CACHE:
        print(f"💾 Cache hit {key[:8]}")
        return EMBEDDING_CACHE[key]

    # --- Try OpenAI first ---
    try:
        data = await _openai_post("/embeddings", {"model": EMBEDDING_MODEL, "input": text_input})
        embedding = data["data"][0]["embedding"]
        EMBEDDING_CACHE[key] = embedding
        _save_cache()
        print(f"✅ OpenAI embedding {key[:8]}")
        return embedding
    except Exception as e:
        print(f"⚠️  OpenAI embedding failed: {e}")

    # --- Local fallback (384-dim, NOT for DB storage) ---
    if USE_LOCAL_FALLBACK and LOCAL_MODEL:
        print("🔄 Using local fallback embedding (384-dim, in-process only).")
        return LOCAL_MODEL.encode(text_input).tolist()

    raise RuntimeError("Embedding failed: OpenAI unavailable and no local fallback.")


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    embeddings = []
    for idx, t in enumerate(texts):
        print(f"🧠 Embedding chunk {idx + 1}/{len(texts)}…")
        embeddings.append(await get_embedding(t))
    return embeddings


# ---------- Chat Completion ----------
async def call_chat_completion(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": COMPLETION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    try:
        data = await _openai_post("/chat/completions", payload, timeout=90)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return json.dumps({"error": f"LLM call failed: {str(e)}"})


# ---------- Cosine similarity (in-process fallback) ----------
def cosine_sim(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = max(np.linalg.norm(va) * np.linalg.norm(vb), 1e-8)
    return float(np.dot(va, vb) / denom)


# ---------- pgvector similarity search ----------
async def search_similar_sources(
    db: AsyncSession,
    query_embedding: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Use pgvector's native <=> (cosine distance) operator for fast server-side
    nearest-neighbour search, falling back to in-process cosine when the query
    embedding dimension doesn't match the DB column (e.g. local 384-dim fallback).
    """
    dim = len(query_embedding)

    if dim == OPENAI_EMBEDDING_DIM:
        # Fast path: native pgvector <=> (cosine distance = 1 - cosine similarity)
        embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
        sql = text(
            f"""
            SELECT id, title, authors, publication_year, abstract, source_type,
                   1 - (embedding <=> :vec ::vector) AS score
            FROM   academic_sources
            WHERE  embedding IS NOT NULL
            ORDER  BY embedding <=> :vec ::vector
            LIMIT  :k
            """
        )
        rows = (await db.execute(sql, {"vec": embedding_literal, "k": top_k})).fetchall()
        return [
            {
                "id":               r.id,
                "title":            r.title,
                "authors":          r.authors,
                "publication_year": r.publication_year,
                "abstract":         r.abstract,
                "source_type":      r.source_type,
                "score":            float(r.score),
            }
            for r in rows
        ]

    # Slow path: dimension mismatch (local 384-dim fallback) — compute in Python
    print(
        f"⚠️  Query embedding is {dim}-dim (expected {OPENAI_EMBEDDING_DIM}). "
        "Falling back to in-process cosine search."
    )
    res = await db.execute(select(AcademicSource))
    sources = res.scalars().all()
    scored = []
    for s in sources:
        if not s.embedding:
            continue
        scored.append(
            {
                "id":               s.id,
                "title":            s.title,
                "authors":          s.authors,
                "publication_year": s.publication_year,
                "abstract":         s.abstract,
                "source_type":      s.source_type,
                "score":            cosine_sim(query_embedding, s.embedding),
            }
        )
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]


# ---------- Text utilities ----------
def chunk_text(text_input: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    return [text_input[i: i + chunk_size] for i in range(0, len(text_input), chunk_size)]


def extract_text_from_file_path(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        if path.lower().endswith(".pdf"):
            import PyPDF2
            with open(path, "rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif path.lower().endswith(".docx"):
            import docx
            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
    except Exception as e:
        print(f"⚠️  File extraction failed for {path}: {e}")
        return ""


# ---------- Main analysis pipeline ----------
async def analyze_assignment_and_save(
    db: AsyncSession,
    assignment: Assignment,
    top_k_sources: int = 5,
) -> Dict[str, Any]:
    # 1. Get text (from DB record or file)
    text_body = assignment.original_text or ""
    if not text_body and getattr(assignment, "file_path", None):
        loop = asyncio.get_running_loop()
        text_body = await loop.run_in_executor(
            None, extract_text_from_file_path, assignment.file_path
        )

    if not text_body.strip():
        raise ValueError("No text available for analysis.")

    print(f"📘 Analysing Assignment ID: {assignment.id}")

    # 2. Chunk and embed
    max_chunks = int(os.getenv("RAG_MAX_CHUNKS", "3"))
    chunks = chunk_text(text_body)[:max_chunks]
    print(f"🧩 {len(chunks)} chunk(s) (max {max_chunks})")

    embeddings = await get_embeddings(chunks)

    # 3. Plagiarism detection — compare each chunk against academic sources
    flagged: List[Dict] = []
    scores: List[float] = []
    for chunk, emb in zip(chunks, embeddings):
        hits = await search_similar_sources(db, emb, top_k=top_k_sources)
        best = hits[0]["score"] if hits else 0.0
        scores.append(best)
        if best >= PLAGIARISM_THRESHOLD:
            flagged.append(
                {
                    "chunk_preview": chunk[:400],
                    "score": best,
                    "best_match": hits[0] if hits else None,
                    "top_k": hits,
                }
            )

    plagiarism_score = max(scores) if scores else 0.0
    print(f"📊 Plagiarism score: {plagiarism_score:.2f}")

    # 4. Full-document contextual analysis via GPT
    full_emb = await get_embedding(text_body[:15000])
    top_sources = await search_similar_sources(db, full_emb, top_k=top_k_sources)

    sys_prompt = (
        "You are an academic assistant. Given an assignment excerpt and related "
        "academic sources, return a JSON object with these fields: topic, "
        "key_themes (list), research_questions (list), academic_level, "
        "research_suggestions, citation_recommendations, confidence_score (0-1)."
    )
    sources_brief = "\n".join(
        f"- {s['title']} ({s['publication_year']}) by {s['authors']}"
        for s in top_sources
    )
    user_prompt = (
        f"Assignment excerpt:\n{text_body[:2000]}\n\n"
        f"Top {top_k_sources} related sources:\n{sources_brief}\n\n"
        "Return only valid JSON."
    )

    llm_text = await call_chat_completion(sys_prompt, user_prompt)

    try:
        parsed = json.loads(re.search(r"\{.*\}", llm_text, re.S).group(0))
    except Exception:
        parsed = {"raw": llm_text}

    confidence = float(parsed.get("confidence_score", 0.0)) if isinstance(parsed, dict) else 0.0
    if confidence == 0.0:
        confidence = round(max(0.1, 1.0 - plagiarism_score * 0.5), 4)

    # 5. Persist result
    result = AnalysisResult(
        assignment_id=assignment.id,
        suggested_sources=top_sources,
        plagiarism_score=plagiarism_score,
        flagged_sections=flagged,
        research_suggestions=parsed.get("research_suggestions", "") if isinstance(parsed, dict) else "",
        citation_recommendations=parsed.get("citation_recommendations", "") if isinstance(parsed, dict) else "",
        confidence_score=confidence,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    # 6. Back-fill academic_level on the assignment
    if isinstance(parsed, dict) and parsed.get("academic_level"):
        assignment.academic_level = parsed["academic_level"]
        db.add(assignment)
        await db.commit()

    print(f"✅ Analysis complete for Assignment ID: {assignment.id}")
    return {
        "analysis_id":            result.id,
        "plagiarism_score":       plagiarism_score,
        "flagged_sections_count": len(flagged),
        "top_sources":            top_sources,
        "llm_parsed":             parsed,
    }
