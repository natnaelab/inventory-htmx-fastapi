"""Combined audit_logs and users tables

Revision ID: combined_audit_and_users_tables
Revises: 83941195d793
Create Date: 2025-08-19 06:05:10.713044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'combined_audit_and_users_tables'
down_revision: Union[str, None] = '83941195d793'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('method', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('path', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
    sa.Column('query_params', sa.Text(), nullable=True),
    sa.Column('user_agent', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('remote_addr', sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('response_time_ms', sa.Float(), nullable=True),
    sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('username', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('request_body_size', sa.Integer(), nullable=True),
    sa.Column('response_body_size', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('ad_object_guid', sa.String(length=100), nullable=True),
    sa.Column('ad_last_sync', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.Column('current_session_token', sa.String(length=500), nullable=True),
    sa.Column('session_expires', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('login_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
    sa.Column('last_ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_ad_object_guid'), 'users', ['ad_object_guid'], unique=True)
    
    # Add additional indexes for performance
    op.create_index('idx_users_role', 'users', ['role'], unique=False)
    op.create_index('idx_users_active', 'users', ['is_active'], unique=False)
    op.create_index('idx_users_session_token', 'users', ['current_session_token'], unique=False)


def downgrade() -> None:
    # Drop users table and indexes
    op.drop_index('idx_users_session_token', table_name='users')
    op.drop_index('idx_users_active', table_name='users')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index(op.f('ix_users_ad_object_guid'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop audit_logs table and indexes
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
