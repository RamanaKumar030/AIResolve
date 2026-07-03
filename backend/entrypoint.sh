#!/bin/bash
set -e

echo "Running database migrations..."
# In production, use Alembic. For now, run raw SQL to create tables.
python -c "
import asyncio
from sqlalchemy import text as sqltext
from app.db.session import engine
from app.db.base import Base
import app.db.models  # noqa: F401

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(sqltext(\"\"\"
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS recommendation VARCHAR(50),
            ADD COLUMN IF NOT EXISTS recommendation_reasoning TEXT,
            ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS conflicts_with_existing_kb BOOLEAN;
        \"\"\"))
        await conn.execute(sqltext(\"\"\"
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL
            );
        \"\"\"))

asyncio.run(init())
print('Tables created successfully')
"

echo "Starting server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
