"""Production Security, RBAC, Recovery Tokens, and Invitations

Revision ID: a8910bc12345
Revises: e1289bc12340
Create Date: 2026-08-31 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8910bc12345'
down_revision: Union[str, None] = 'e1289bc12340'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organization_invitations
    op.create_table(
        'organization_invitations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_prefix', sa.String(length=12), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invited_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_invitations_email'), 'organization_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_organization_invitations_id'), 'organization_invitations', ['id'], unique=False)
    op.create_index(op.f('ix_organization_invitations_organization_id'), 'organization_invitations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_invitations_token_hash'), 'organization_invitations', ['token_hash'], unique=True)

    # 2. revoked_tokens
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_revoked_tokens_id'), 'revoked_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_revoked_tokens_token_hash'), 'revoked_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_revoked_tokens_user_id'), 'revoked_tokens', ['user_id'], unique=False)

    # 3. recovery_tokens
    op.create_table(
        'recovery_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('recovery_case_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_prefix', sa.String(length=12), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recovery_case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_tokens_id'), 'recovery_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_recovery_tokens_organization_id'), 'recovery_tokens', ['organization_id'], unique=False)
    op.create_index(op.f('ix_recovery_tokens_recovery_case_id'), 'recovery_tokens', ['recovery_case_id'], unique=False)
    op.create_index(op.f('ix_recovery_tokens_token_hash'), 'recovery_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_table('recovery_tokens')
    op.drop_table('revoked_tokens')
    op.drop_table('organization_invitations')
