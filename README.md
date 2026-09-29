# 🎓 Academic Assignment Helper & Plagiarism Detector

An AI-powered academic assistance and plagiarism detection platform using **Retrieval-Augmented Generation (RAG)** and **n8n automation** to analyse student assignments, detect similarity against academic sources, and suggest improvements.

---

## 🚀 Overview

Students upload assignments (PDF, DOCX, or plain text). The backend:

1. Extracts text from the file
2. Generates OpenAI embeddings and searches a pgvector database of academic sources
3. Detects potential plagiarism via cosine similarity
4. Calls GPT to produce research suggestions, citation recommendations, and an academic level assessment
5. Triggers an n8n workflow to automate the full pipeline

---

## 🧱 Tech Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI (async) + Python 3.11 |
| ORM / Driver | SQLAlchemy 2.x (async) + asyncpg |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| LLM | OpenAI GPT (`gpt-4o-mini` by default) |
| Auth | JWT via `python-jose` + bcrypt via `passlib` |
| Automation | n8n workflow engine |
| Containerisation | Docker + Docker Compose |

---

## 🗂️ Project Structure

```
academic-assignment-helper/
├── backend/
│   ├── main.py                  # FastAPI app entry point + lifespan startup
│   ├── database.py              # Async SQLAlchemy engine + session factory
│   ├── models.py                # ORM models (Student, Assignment, AnalysisResult, AcademicSource)
│   ├── auth.py                  # JWT creation + bcrypt password helpers
│   ├── deps.py                  # Shared FastAPI dependencies (get_current_student)
│   ├── rag_service.py           # RAG pipeline: embed → search → plagiarism → GPT → persist
│   ├── requirements.txt
│   ├── routes/
│   │   ├── auth_routes.py       # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── upload_routes.py     # POST /upload/
│   │   ├── assignment_routes.py # GET /assignments/, GET /assignments/{id}, DELETE /assignments/{id}
│   │   └── analysis_routes.py   # POST /analysis/start, GET /analysis/{id}
│   └── utils/
│       └── load_sources.py      # DB seeder — loads data/sample_academic_sources.json on startup
├── data/
│   └── sample_academic_sources.json   # 10 pre-built academic sources for seeding
├── workflows/
│   └── assignment_analysis_workflow.json  # n8n workflow (import into n8n UI)
├── docker-compose.yml
├── Dockerfile
├── init.sql                     # Enables pgvector extension in the app database
└── .env.example
```

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/academic-assignment-helper.git
cd academic-assignment-helper
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# PostgreSQL
POSTGRES_DB=academic_helper
POSTGRES_USER=student
POSTGRES_PASSWORD=change_me_strong_password

# OpenAI
OPENAI_API_KEY=sk-xxxxxx
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_COMPLETION_MODEL=gpt-4o-mini

# Auth
JWT_SECRET_KEY=replace_with_a_long_random_secret

# n8n webhook (internal Docker network address)
N8N_WEBHOOK_URL=http://n8n:5678/webhook/assignment

# RAG tuning
RAG_CHUNK_SIZE=2000
RAG_MAX_CHUNKS=5
PLAGIARISM_THRESHOLD=0.85
```

### 3. Build and run

```bash
docker-compose up --build
```

This starts three services:

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| FastAPI docs (Swagger) | http://localhost:8000/docs |
| n8n automation | http://localhost:5678 |
| PostgreSQL | localhost:5432 |

On first startup the backend will:
- Create all database tables
- Enable the `pgvector` extension
- Seed 10 academic sources from `data/sample_academic_sources.json` (with OpenAI embeddings)

---

## 📘 API Reference

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register a new student account |
| POST | `/auth/login` | — | Log in, receive JWT access token |
| GET | `/auth/me` | ✅ | Get current student profile |

```http
POST /auth/register?email=student@uni.edu&password=secret&full_name=Jane
POST /auth/login?email=student@uni.edu&password=secret
```

### Assignments

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/upload/` | ✅ | Upload a PDF/DOCX assignment |
| GET | `/assignments/` | ✅ | List all your assignments (paginated) |
| GET | `/assignments/{id}` | ✅ | Get assignment detail + latest analysis summary |
| DELETE | `/assignments/{id}` | ✅ | Delete assignment + file + analysis results |

```http
# Upload (multipart/form-data)
POST /upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data
[file field: your_assignment.pdf]

# List with pagination
GET /assignments/?page=1&page_size=20
Authorization: Bearer <token>
```

### Analysis

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/analysis/start` | ✅ | Trigger analysis (single or batch) |
| GET | `/analysis/{assignment_id}` | ✅ | Get the latest analysis result |

```http
# Single assignment
POST /analysis/start
Authorization: Bearer <token>
Content-Type: application/json
{ "assignment_id": 1 }

# Batch
POST /analysis/start
Authorization: Bearer <token>
Content-Type: application/json
{ "assignment_ids": [1, 2, 3] }

# Get result
GET /analysis/1
Authorization: Bearer <token>
```

**Analysis result fields:**

| Field | Description |
|---|---|
| `plagiarism_score` | Max cosine similarity (0–1) across all chunks vs. academic sources |
| `flagged_sections` | Chunks exceeding `PLAGIARISM_THRESHOLD` with matched source details |
| `suggested_sources` | Top-K semantically similar academic sources |
| `research_suggestions` | GPT-generated research improvement recommendations |
| `citation_recommendations` | GPT-generated citation recommendations |
| `confidence_score` | GPT-assessed confidence in the analysis (0–1) |

---

## 🧠 n8n Workflow Setup

1. Open http://localhost:5678
2. Go to **Workflows → Import from file**
3. Import `workflows/assignment_analysis_workflow.json`
4. Set the `BACKEND_SERVICE_TOKEN` environment variable in n8n with a valid student JWT (obtained from `/auth/login`)
5. Activate the workflow

The workflow listens at `POST http://localhost:5678/webhook/assignment` and is automatically triggered by the backend whenever a file is uploaded. It:
- Receives `{ assignment_id, student_email }` from the upload route
- POSTs to `/analysis/start` with a Bearer token
- Branches on success/failure and responds accordingly

---

## 🔒 Security Notes

- JWT tokens are passed via `Authorization: Bearer` header — never as query parameters
- All assignment and analysis endpoints enforce student ownership (you can only access your own data)
- Uploaded files are namespaced by student ID to prevent collisions
- Uploaded files persist across container restarts via a named Docker volume (`uploads_data`)

---

## ⚠️ Common Issues

| Problem | Cause | Fix |
|---|---|---|
| `429 Too Many Requests` | OpenAI rate limit | Reduce `RAG_MAX_CHUNKS` or use a paid-tier key |
| `500` on `/analysis/start` | No text extracted from file | Check the file is not a scanned image PDF |
| `401 Unauthorized` | Missing or expired token | Re-login at `/auth/login` and use the new token |
| No sources seeded | OpenAI key missing on startup | Set `OPENAI_API_KEY` and restart the backend |
| n8n can't reach backend | Wrong URL in workflow | Use `http://backend:8000` (Docker network), not `localhost` |

---

## 📚 Future Improvements

- 🔄 Frontend dashboard (Next.js / React)
- 🔒 Instructor / admin role with RBAC
- 📊 Analytics dashboard for plagiarism reports
- 🗂️ HNSW index on `academic_sources.embedding` for sub-millisecond vector search at scale
- 🔁 Webhook retry queue for failed n8n triggers

---

## 👨‍💻 Author

Oli Bakala — Software Engineer
