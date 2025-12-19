"""Add AI tasks table.

Revision ID: g1234567895
Revises: f1234567894
Create Date: 2024-12-18

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g1234567895'
down_revision = 'f1234567894'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("DO $$ BEGIN CREATE TYPE ai_task_type AS ENUM ('DOCUMENT_ANALYSIS', 'PYSIS_EXTRACTION', 'BATCH_ANALYSIS'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE ai_task_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create AI tasks table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_type ai_task_type NOT NULL,
            status ai_task_status NOT NULL DEFAULT 'PENDING',
            name VARCHAR(255) NOT NULL,
            description TEXT,
            process_id UUID REFERENCES pysis_processes(id) ON DELETE CASCADE,
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            progress_current INTEGER NOT NULL DEFAULT 0,
            progress_total INTEGER NOT NULL DEFAULT 0,
            current_item VARCHAR(255),
            fields_extracted INTEGER NOT NULL DEFAULT 0,
            avg_confidence FLOAT,
            error_message TEXT,
            error_details JSONB NOT NULL DEFAULT '{}',
            celery_task_id VARCHAR(255)
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_tasks_task_type ON ai_tasks(task_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_tasks_status ON ai_tasks(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_tasks_process_id ON ai_tasks(process_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_tasks_document_id ON ai_tasks(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_tasks_celery_task_id ON ai_tasks(celery_task_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_tasks")
    op.execute("DROP TYPE IF EXISTS ai_task_status")
    op.execute("DROP TYPE IF EXISTS ai_task_type")
