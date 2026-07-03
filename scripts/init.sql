-- Run this in Supabase SQL Editor to enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables (auto-created by SQLAlchemy, provided here for reference)
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Add AI recommendation columns to tickets (if they don't exist yet)
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS recommendation VARCHAR(50),
ADD COLUMN IF NOT EXISTS recommendation_reasoning TEXT,
ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS conflicts_with_existing_kb BOOLEAN;

-- Create system_settings table for feature flags
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL
);
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
