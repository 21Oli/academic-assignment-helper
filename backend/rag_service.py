import os
import asyncio
import json
import hashlib
import random
import re
from typing import List, Dict, Any

import numpy as np
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AcademicSource, AnalysisResult, Assignment

# Try to import local embedding model
try:
    from sentence_transformers import SentenceTransformer
    LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    USE_LOCAL_FALLBACK = True
    print("🧠 Local embedding model loaded successfully.")
except Exception:
    LOCAL_MODEL = None
    USE_LOCAL_FALLBACK = False
    print("⚠️ Local embedding model not available. Using OpenAI only.")

# ---------- Environment Config ----------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COMPLETION_MODEL = os.getenv("OPENAI_COMPLETION_MODEL", "gpt-4o-mini")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "2000"))
PLAGIARISM_THRESHOLD = float(os.getenv("PLAGIARISM_THRESHOLD", "0.85"))
MAX_RETRIES = 6
CACHE_PATH = "data/embeddings_cache.json"

# ---------- Cache Manager ----------
if not os.path.exists("data"):
    os.makedirs("data")

if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            EMBEDDING_CACHE = json.load(f)
    except Exception:
        EMBEDDING_CACHE = {}
else:
    EMBEDDING_CACHE = {}

def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def save_cache():
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(EMBEDDING_CACHE, f)

# ---------- OpenAI Helper ----------
async def _openai_post(endpoint: str, payload: dict, timeout: int = 40) -> dict:
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
    url = f"https://api.openai.com/v1{endpoint}"

    for attempt in range(1, MAX_RETRIES + 1):
        await asyncio.sleep(random.uniform(2, 5))  # cooldown between calls
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = min(4 ** attempt + random.random(), 60)
                print(f"⚠️ [429 Rate Limit] Retry {attempt}/{MAX_RETRIES} in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            elif e.response.status_code in (401, 402):
                raise RuntimeError("❌ OpenAI quota exceeded or invalid API key.")
            else:
                raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RequestError) as e:
            wait_time = 2 ** attempt
            print(f"🌐 [Network Error] {e}. Retrying in {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)

    raise RuntimeError("❌ OpenAI request failed after multiple retries (rate limit likely exceeded).")

# ---------- Embedding Logic ----------
async def get_embedding(text: str) -> List[float]:
    if not text.strip():
        return []

    text_hash = _hash_text(text)
    if text_hash in EMBEDDING_CACHE:
        print(f"💾 Using cached embedding for {text_hash[:8]}")
        return EMBEDDING_CACHE[text_hash]

    # Try OpenAI first
    payload = {"model": EMBEDDING_MODEL, "input": text}
    try:
        data = await _openai_post("/embeddings", payload)
        embedding = data["data"][0]["embedding"]
        EMBEDDING_CACHE[text_hash] = embedding
        save_cache()
        print(f"✅ Cached OpenAI embedding for {text_hash[:8]}")
        return embedding
    except Exception as e:
        print(f"⚠️ OpenAI embedding failed: {e}")
        if USE_LOCAL_FALLBACK and LOCAL_MODEL:
            print("🔄 Falling back to local embedding model...")
            embedding = LOCAL_MODEL.encode(text).tolist()
            EMBEDDING_CACHE[text_hash] = embedding
            save_cache()
            return embedding
        raise

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    embeddings = []
    for idx, t in enumerate(texts):
        print(f"🧠 Embedding chunk {idx+1}/{len(texts)}...")
        emb = await get_embedding(t)
        embeddings.append(emb)
    return embeddings

# ---------- Chat Completion ----------
async def call_chat_completion(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": COMPLETION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    try:
        data = await _openai_post("/chat/completions", payload, timeout=90)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f'{{"error": "LLM call failed: {str(e)}"}}'

# ---------- Similarity ----------
def cosine_sim(a: List[float], b: List[float]) -> float:
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = max(np.linalg.norm(a) * np.linalg.norm(b), 1e-8)
    return float(np.dot(a, b) / denom)

# ---------- Database Search ----------
async def search_similar_sources(db: AsyncSession, query_embedding: List[float], top_k: int = 5):
    res = await db.execute(select(AcademicSource))
    sources = res.scalars().all()
    scored = []
    for s in sources:
        if not s.embedding:
            continue
        score = cosine_sim(query_embedding, s.embedding)
        scored.append({
            "id": s.id,
            "title": s.title,
            "authors": s.authors,
            "publication_year": s.publication_year,
            "abstract": s.abstract,
            "source_type": s.source_type,
            "score": score,
        })
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]

# ---------- File/Text Utilities ----------
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def extract_text_from_file_path(path: str) -> str:
    import os
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
    except Exception:
        return ""

# ---------- Main Analysis Logic ----------
async def analyze_assignment_and_save(db: AsyncSession, assignment: Assignment, top_k_sources: int = 5):
    text = assignment.original_text or ""
    if not text and getattr(assignment, "file_path", None):
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, extract_text_from_file_path, assignment.file_path)

    if not text.strip():
        raise ValueError("No text available for analysis.")

    print(f"📘 Starting analysis for Assignment ID: {assignment.id}")
    chunks = chunk_text(text)
    max_chunks = int(os.getenv("RAG_MAX_CHUNKS", "3"))
    chunks = chunks[:max_chunks]
    print(f"🧩 Split into {len(chunks)} chunks (max {max_chunks})")

    embeddings = await get_embeddings(chunks)

    # --- Plagiarism Detection ---
    flagged, scores = [], []
    for chunk, emb in zip(chunks, embeddings):
        hits = await search_similar_sources(db, emb, top_k=top_k_sources)
        best = hits[0]["score"] if hits else 0.0
        scores.append(best)
        if best >= PLAGIARISM_THRESHOLD:
            flagged.append({
                "chunk_preview": chunk[:400],
                "score": best,
                "best_match": hits[0] if hits else None,
                "top_k": hits,
            })

    plagiarism_score = max(scores) if scores else 0.0
    print(f"📊 Plagiarism Score: {plagiarism_score:.2f}")

    # --- Contextual Analysis ---
    full_emb = await get_embedding(text[:15000])
    top_sources = await search_similar_sources(db, full_emb, top_k=top_k_sources)

    sys_prompt = (
        "You are an academic assistant. Given an assignment and related sources, "
        "return JSON with topic, key_themes, research_questions, academic_level, "
        "research_suggestions, citation_recommendations, confidence_score."
    )
    sources_brief = "\n".join([f"- {s['title']} ({s['publication_year']}) by {s['authors']}" for s in top_sources])
    user_prompt = (
        f"Assignment excerpt:\n{text[:2000]}\n\n"
        f"Top {top_k_sources} related sources:\n{sources_brief}\n\n"
        "Return JSON with all requested fields."
    )

    llm_text = await call_chat_completion(sys_prompt, user_prompt)

    try:
        parsed = json.loads(re.search(r"\{.*\}", llm_text, re.S).group(0))
    except Exception:
        parsed = {"raw": llm_text}

    confidence = float(parsed.get("confidence_score", 0.0)) if isinstance(parsed, dict) else 0.0
    if confidence == 0.0:
        confidence = max(0.1, 1.0 - (plagiarism_score * 0.5))

    result = AnalysisResult(
        assignment_id=assignment.id,
        suggested_sources=top_sources,
        plagiarism_score=plagiarism_score,
        flagged_sections=flagged,
        research_suggestions=parsed.get("research_suggestions", ""),
        citation_recommendations=parsed.get("citation_recommendations", ""),
        confidence_score=confidence,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    if parsed.get("academic_level"):
        assignment.academic_level = parsed["academic_level"]
        db.add(assignment)
        await db.commit()

    print(f"✅ Analysis complete. Chunks: {len(chunks)}")
    return {
        "analysis_id": result.id,
        "plagiarism_score": plagiarism_score,
        "flagged_sections_count": len(flagged),
        "llm_raw": llm_text,
    }
