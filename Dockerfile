FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install base dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🧠 Install local embedding dependencies for fallback mode
# (includes torch + sentence-transformers + numpy)
RUN pip install --no-cache-dir torch sentence-transformers numpy

# Copy backend code (for hot reload, we mount it later in docker-compose)
COPY backend /app/backend

# Make Python see 'backend' as top-level package
ENV PYTHONPATH=/app

# Unbuffered output
ENV PYTHONUNBUFFERED=1

# Optional: preload model weights during build (to avoid runtime downloads)
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Run Uvicorn with reload (reload watches /app/backend)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/backend"]
