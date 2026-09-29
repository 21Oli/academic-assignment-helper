-- This script runs inside the database specified by POSTGRES_DB (e.g. academic_helper).
-- The pgvector extension must be created in the app database, not in a separate one.
CREATE EXTENSION IF NOT EXISTS vector;
