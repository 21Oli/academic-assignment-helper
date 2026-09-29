-- Runs inside POSTGRES_DB (e.g. academic_helper) at first container start.
-- Enables pgvector and creates the HNSW index for fast cosine similarity search.

CREATE EXTENSION IF NOT EXISTS vector;
