FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Build argument: set to "true" to include sentence-transformers + torch
# for offline local embedding fallback. Adds ~2 GB — disabled by default.
#
# Usage:  docker build --build-arg ENABLE_LOCAL_EMBEDDINGS=true .
# ---------------------------------------------------------------------------
ARG ENABLE_LOCAL_EMBEDDINGS=false

WORKDIR /app

# System deps needed by psycopg2-binary and some Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Conditionally install local embedding stack (~2 GB with torch)
RUN if [ "$ENABLE_LOCAL_EMBEDDINGS" = "true" ]; then \
        pip install --no-cache-dir torch sentence-transformers; \
    fi

# Copy backend source (hot-reload via volume mount in docker-compose)
COPY backend /app/backend

# Copy academic sources data for seeding on startup
COPY data /app/data

# Copy Alembic config so migrations can run inside the container
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the port Uvicorn listens on
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
