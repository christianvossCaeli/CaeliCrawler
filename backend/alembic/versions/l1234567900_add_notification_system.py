"""Add notification system tables.

This migration introduces the notification system:
- user_email_addresses: Additional email addresses per user for notifications
- notification_rules: User-defined rules for triggering notifications
- notifications: Notification queue and history
- Updates users table with notification preference columns

Revision ID: l1234567900
Revises: k1234567899
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "l1234567900"
down_revision: Union[str, None] = "k1234567899"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Create ENUM types
    # =========================================================================

    notification_channel_enum = postgresql.ENUM(
        'EMAIL', 'WEBHOOK', 'IN_APP', 'MS_TEAMS',
        name='notification_channel',
        create_type=False,
    )
    notification_channel_enum.create(op.get_bind(), checkfirst=True)

    notification_event_type_enum = postgresql.ENUM(
        'NEW_DOCUMENT', 'DOCUMENT_CHANGED', 'DOCUMENT_REMOVED',
        'CRAWL_STARTED', 'CRAWL_COMPLETED', 'CRAWL_FAILED',
        'AI_ANALYSIS_COMPLETED', 'HIGH_CONFIDENCE_RESULT',
        'SOURCE_STATUS_CHANGED', 'SOURCE_ERROR',
        name='notification_event_type',
        create_type=False,
    )
    notification_event_type_enum.create(op.get_bind(), checkfirst=True)

    notification_status_enum = postgresql.ENUM(
        'PENDING', 'QUEUED', 'SENT', 'FAILED', 'READ',
        name='notification_status',
        create_type=False,
    )
    notification_status_enum.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Step 2: Add notification columns to users table
    # =========================================================================

    op.add_column(
        'users',
        sa.Column(
            'notifications_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='true',
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'notification_digest_time',
            sa.String(5),
            nullable=True,
        ),
    )

    # =========================================================================
    # Step 3: Create user_email_addresses table
    # =========================================================================

    op.create_table(
        'user_email_addresses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('label', sa.String(100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # =========================================================================
    # Step 4: Create notification_rules table
    # =========================================================================

    op.create_table(
        'notification_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'event_type',
            sa.Enum(
                'NEW_DOCUMENT', 'DOCUMENT_CHANGED', 'DOCUMENT_REMOVED',
                'CRAWL_STARTED', 'CRAWL_COMPLETED', 'CRAWL_FAILED',
                'AI_ANALYSIS_COMPLETED', 'HIGH_CONFIDENCE_RESULT',
                'SOURCE_STATUS_CHANGED', 'SOURCE_ERROR',
                name='notification_event_type',
                create_type=False,
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'channel',
            sa.Enum(
                'EMAIL', 'WEBHOOK', 'IN_APP', 'MS_TEAMS',
                name='notification_channel',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            'conditions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column(
            'channel_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column('digest_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('digest_frequency', sa.String(20), nullable=True),
        sa.Column('last_digest_sent', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # =========================================================================
    # Step 5: Create notifications table
    # =========================================================================

    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'rule_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('notification_rules.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'event_type',
            sa.Enum(
                'NEW_DOCUMENT', 'DOCUMENT_CHANGED', 'DOCUMENT_REMOVED',
                'CRAWL_STARTED', 'CRAWL_COMPLETED', 'CRAWL_FAILED',
                'AI_ANALYSIS_COMPLETED', 'HIGH_CONFIDENCE_RESULT',
                'SOURCE_STATUS_CHANGED', 'SOURCE_ERROR',
                name='notification_event_type',
                create_type=False,
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'channel',
            sa.Enum(
                'EMAIL', 'WEBHOOK', 'IN_APP', 'MS_TEAMS',
                name='notification_channel',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('related_entity_type', sa.String(50), nullable=True),
        sa.Column('related_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'payload',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING', 'QUEUED', 'SENT', 'FAILED', 'READ',
                name='notification_status',
                create_type=False,
            ),
            nullable=False,
            server_default='PENDING',
            index=True,
        ),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('email_recipient', sa.String(255), nullable=True),
        sa.Column('email_message_id', sa.String(255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )

    # Create additional indexes for common queries
    op.create_index(
        'ix_notifications_user_status',
        'notifications',
        ['user_id', 'status'],
    )
    op.create_index(
        'ix_notifications_user_read',
        'notifications',
        ['user_id', 'read_at'],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_notifications_user_status', table_name='notifications')

    # Drop tables
    op.drop_table('notifications')
    op.drop_table('notification_rules')
    op.drop_table('user_email_addresses')

    # Remove columns from users
    op.drop_column('users', 'notification_digest_time')
    op.drop_column('users', 'notifications_enabled')

    # Drop ENUM types
    notification_status_enum = postgresql.ENUM(
        'PENDING', 'QUEUED', 'SENT', 'FAILED', 'READ',
        name='notification_status',
    )
    notification_status_enum.drop(op.get_bind(), checkfirst=True)

    notification_event_type_enum = postgresql.ENUM(
        'NEW_DOCUMENT', 'DOCUMENT_CHANGED', 'DOCUMENT_REMOVED',
        'CRAWL_STARTED', 'CRAWL_COMPLETED', 'CRAWL_FAILED',
        'AI_ANALYSIS_COMPLETED', 'HIGH_CONFIDENCE_RESULT',
        'SOURCE_STATUS_CHANGED', 'SOURCE_ERROR',
        name='notification_event_type',
    )
    notification_event_type_enum.drop(op.get_bind(), checkfirst=True)

    notification_channel_enum = postgresql.ENUM(
        'EMAIL', 'WEBHOOK', 'IN_APP', 'MS_TEAMS',
        name='notification_channel',
    )
    notification_channel_enum.drop(op.get_bind(), checkfirst=True)
