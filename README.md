# 🎓 Academic Assignment Helper & Plagiarism Detector

An AI-powered academic assistance and plagiarism detection platform that uses **Retrieval-Augmented Generation (RAG)** and **n8n automation** to analyze student assignments, detect similarity, and suggest academic improvements.

---

## 🚀 Overview

This project helps automate academic assignment analysis by integrating:

- **FastAPI** backend (RAG-powered)
- **PostgreSQL + pgvector** for semantic similarity search
- **OpenAI API** for embeddings and intelligent analysis
- **n8n** workflow automation to trigger and monitor analysis
- **Docker Compose** for simple setup and orchestration

---

## 🧩 Features

✅ Upload and store student assignments  
✅ Extract text from `.pdf`, `.docx`, or plain text  
✅ Generate OpenAI embeddings and similarity search via pgvector  
✅ Detect potential plagiarism using cosine similarity  
✅ Suggest research improvements, citations, and academic level  
✅ Trigger analysis automatically through **n8n workflows**  
✅ REST API endpoints for assignment management and results  

---

## 🧱 Tech Stack

| Component | Description |
|------------|-------------|
| **Backend** | FastAPI + SQLAlchemy (async) |
| **Database** | PostgreSQL with pgvector |
| **AI** | OpenAI Embeddings + GPT Models |
| **Automation** | n8n Workflow Engine |
| **Containerization** | Docker & Docker Compose |

---

## 🗂️ Folder Structure

```
academic-assignment-helper/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── rag_service.py
│   └── routes/
│       ├── auth_routes.py
│       ├── upload_routes.py
│       └── analysis_routes.py
│
├── n8n_workflows/
│   └── assignment_analysis_workflow.json
│
├── data/
│   ├── academic_sources.json     # Preloaded sample data
│   └── samples/
│       └── sample_assignment.pdf # Example input file
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/academic-assignment-helper.git
cd academic-assignment-helper
```

### 2. Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Example:
```
OPENAI_API_KEY=sk-xxxxxx
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_COMPLETION_MODEL=gpt-4o-mini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/academicdb
N8N_WEBHOOK_URL=http://n8n:5678/webhook/assignment
RAG_CHUNK_SIZE=2000
RAG_MAX_CHUNKS=5
PLAGIARISM_THRESHOLD=0.85
```

---

### 3. Build and Run with Docker

```bash
docker-compose up --build
```

This starts:
- `backend` → FastAPI on port `8000`
- `db` → PostgreSQL with pgvector
- `n8n` → Automation editor on port `5678`

---

## 🧠 n8n Workflow Setup

1. Open [http://localhost:5678](http://localhost:5678)
2. Import the provided JSON workflow file:
   ```
   n8n_workflows/assignment_analysis_workflow.json
   ```
3. The workflow listens at:
   ```
   POST http://localhost:5678/webhook/assignment
   ```
4. It triggers the backend endpoint:
   ```
   POST http://backend:8000/analysis/start
   ```
   and sends `assignment_id` in the JSON body.

✅ Optionally, add a “Respond to Webhook” node to confirm success logs.

---

## 📘 API Reference

### 1. Register and Login
```http
POST /auth/register?email=oli@gmail.com&password=123&full_name=Oli
POST /auth/login?email=oli@gmail.com&password=123
```

### 2. Upload Assignment
```http
POST /upload/?token=<JWT_TOKEN>
```
Uploads `.pdf` or `.docx` assignment and returns its ID.

### 3. Trigger Analysis
```http
POST /analysis/start
{
  "assignment_id": 1
}
```

### 4. Get Analysis Result
```http
GET /analysis/1
```

---

## 📄 Sample Academic Data

Preload sources from `data/academic_sources.json`:
```json
[
  {
    "title": "Deep Learning in Education",
    "authors": "Goodfellow, Bengio & Courville",
    "publication_year": 2016,
    "abstract": "Explores applications of deep learning in adaptive education systems.",
    "source_type": "journal"
  },
  {
    "title": "AI Ethics and Society",
    "authors": "Bender & Gebru",
    "publication_year": 2021,
    "abstract": "Discusses ethical frameworks for AI use in academia.",
    "source_type": "conference"
  }
]
```

---

## 🧪 Testing the System

1. Open **FastAPI docs** at [http://localhost:8000/docs](http://localhost:8000/docs)
2. Register & Login → copy token  
3. Upload a sample file → get assignment ID  
4. Trigger `/analysis/start` → wait for response  
5. Check `/analysis/{id}` for plagiarism score, flagged sections, and research suggestions.

---

## ⚠️ Common Issues

| Problem | Cause | Fix |
|----------|--------|-----|
| **429 Too Many Requests** | OpenAI rate limit | Use paid API key or reduce `RAG_MAX_CHUNKS` |
| **500 Internal Server Error** | API timeout or invalid response | Retry after a few seconds |
| **No analysis result found** | Assignment not analyzed yet | Trigger manually via n8n |

---

## 📚 Future Improvements

- ✅ Caching embeddings to reduce cost  
- ✅ Batch analysis for multiple assignments  
- 🔄 Frontend dashboard (Next.js / Flutter)  
- 🔒 Role-based access for instructors and students  
- 📊 Analytics dashboard for plagiarism reports  

---

## 👨‍💻 Author

Oli Bakala  
Software Engineer
