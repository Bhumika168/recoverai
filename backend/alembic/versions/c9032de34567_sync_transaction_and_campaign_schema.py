"""Sync transaction, campaign, recovery case, and token schema

Revision ID: c9032de34567
Revises: a8910bc12345
Create Date: 2026-09-04 06:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9032de34567'
down_revision: Union[str, None] = 'a8910bc12345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. transactions
    txn_cols = {c['name'] for c in inspector.get_columns('transactions')}
    txn_idxs = {idx['name'] for idx in inspector.get_indexes('transactions')}
    with op.batch_alter_table('transactions') as batch_op:
        if 'invoice_id' not in txn_cols:
            batch_op.add_column(sa.Column('invoice_id', sa.String(length=128), nullable=True))
        if 'subscription_id' not in txn_cols:
            batch_op.add_column(sa.Column('subscription_id', sa.String(length=128), nullable=True))
        if 'transaction_time' not in txn_cols:
            batch_op.add_column(sa.Column('transaction_time', sa.DateTime(timezone=True), nullable=True))
        if 'ix_transactions_invoice_id' not in txn_idxs:
            batch_op.create_index('ix_transactions_invoice_id', ['invoice_id'], unique=False)
        if 'ix_transactions_subscription_id' not in txn_idxs:
            batch_op.create_index('ix_transactions_subscription_id', ['subscription_id'], unique=False)
        if 'ix_transactions_transaction_time' not in txn_idxs:
            batch_op.create_index('ix_transactions_transaction_time', ['transaction_time'], unique=False)
        if 'ix_org_transaction_external_id' not in txn_idxs:
            batch_op.create_index('ix_org_transaction_external_id', ['organization_id', 'transaction_id'], unique=False)

    # 2. recovery_cases
    rc_cols = {c['name'] for c in inspector.get_columns('recovery_cases')}
    with op.batch_alter_table('recovery_cases') as batch_op:
        if 'messages_sent_count' not in rc_cols:
            batch_op.add_column(sa.Column('messages_sent_count', sa.Integer(), server_default='0', nullable=False))

    # 3. campaigns
    cmp_cols = {c['name'] for c in inspector.get_columns('campaigns')}
    cmp_idxs = {idx['name'] for idx in inspector.get_indexes('campaigns')}
    with op.batch_alter_table('campaigns') as batch_op:
        if 'recovery_type' not in cmp_cols:
            batch_op.add_column(sa.Column('recovery_type', sa.String(length=64), server_default='FAILED_PAYMENT', nullable=False))
        if 'status' not in cmp_cols:
            batch_op.add_column(sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=False))
        if 'channels_list' not in cmp_cols:
            batch_op.add_column(sa.Column('channels_list', sa.JSON(), nullable=True))
        if 'min_amount' not in cmp_cols:
            batch_op.add_column(sa.Column('min_amount', sa.Float(), server_default='0.0', nullable=False))
        if 'max_amount' not in cmp_cols:
            batch_op.add_column(sa.Column('max_amount', sa.Float(), server_default='1000000.0', nullable=False))
        if 'max_recovery_attempts' not in cmp_cols:
            batch_op.add_column(sa.Column('max_recovery_attempts', sa.Integer(), server_default='3', nullable=False))
        if 'retry_delay_hours' not in cmp_cols:
            batch_op.add_column(sa.Column('retry_delay_hours', sa.Integer(), server_default='24', nullable=False))
        if 'escalation_rules' not in cmp_cols:
            batch_op.add_column(sa.Column('escalation_rules', sa.JSON(), nullable=True))
        if 'enrolled_cases_count' not in cmp_cols:
            batch_op.add_column(sa.Column('enrolled_cases_count', sa.Integer(), server_default='0', nullable=False))
        if 'messages_sent_count' not in cmp_cols:
            batch_op.add_column(sa.Column('messages_sent_count', sa.Integer(), server_default='0', nullable=False))
        if 'actions_executed_count' not in cmp_cols:
            batch_op.add_column(sa.Column('actions_executed_count', sa.Integer(), server_default='0', nullable=False))
        if 'recovered_amount' not in cmp_cols:
            batch_op.add_column(sa.Column('recovered_amount', sa.Float(), server_default='0.0', nullable=False))
        if 'last_activity_at' not in cmp_cols:
            batch_op.add_column(sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True))
        if 'ix_campaigns_status' not in cmp_idxs:
            batch_op.create_index('ix_campaigns_status', ['status'], unique=False)
        if 'ix_campaigns_org_status' not in cmp_idxs:
            batch_op.create_index('ix_campaigns_org_status', ['organization_id', 'status'], unique=False)

    # 4. webhook_events
    wh_cols = {c['name'] for c in inspector.get_columns('webhook_events')}
    with op.batch_alter_table('webhook_events') as batch_op:
        if 'processed_at' not in wh_cols:
            batch_op.add_column(sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))

    # 5. recovery_tokens
    tok_cols = {c['name'] for c in inspector.get_columns('recovery_tokens')}
    tok_idxs = {idx['name'] for idx in inspector.get_indexes('recovery_tokens')}
    with op.batch_alter_table('recovery_tokens') as batch_op:
        if 'action_type' not in tok_cols:
            batch_op.add_column(sa.Column('action_type', sa.String(length=64), server_default='PAYMENT_LINK', nullable=False))
        if 'provider_reference' not in tok_cols:
            batch_op.add_column(sa.Column('provider_reference', sa.String(length=255), nullable=True))
        if 'token_metadata' not in tok_cols:
            batch_op.add_column(sa.Column('token_metadata', sa.JSON(), nullable=True))
        if 'updated_at' not in tok_cols:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        if 'ix_recovery_tokens_status' not in tok_idxs:
            batch_op.create_index('ix_recovery_tokens_status', ['status'], unique=False)
        if 'ix_recovery_tokens_expires_at' not in tok_idxs:
            batch_op.create_index('ix_recovery_tokens_expires_at', ['expires_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 5. recovery_tokens
    tok_cols = {c['name'] for c in inspector.get_columns('recovery_tokens')}
    tok_idxs = {idx['name'] for idx in inspector.get_indexes('recovery_tokens')}
    with op.batch_alter_table('recovery_tokens') as batch_op:
        if 'ix_recovery_tokens_expires_at' in tok_idxs:
            batch_op.drop_index('ix_recovery_tokens_expires_at')
        if 'ix_recovery_tokens_status' in tok_idxs:
            batch_op.drop_index('ix_recovery_tokens_status')
        if 'updated_at' in tok_cols:
            batch_op.drop_column('updated_at')
        if 'token_metadata' in tok_cols:
            batch_op.drop_column('token_metadata')
        if 'provider_reference' in tok_cols:
            batch_op.drop_column('provider_reference')
        if 'action_type' in tok_cols:
            batch_op.drop_column('action_type')

    # 4. webhook_events
    wh_cols = {c['name'] for c in inspector.get_columns('webhook_events')}
    with op.batch_alter_table('webhook_events') as batch_op:
        if 'processed_at' in wh_cols:
            batch_op.drop_column('processed_at')

    # 3. campaigns
    cmp_cols = {c['name'] for c in inspector.get_columns('campaigns')}
    cmp_idxs = {idx['name'] for idx in inspector.get_indexes('campaigns')}
    with op.batch_alter_table('campaigns') as batch_op:
        if 'ix_campaigns_org_status' in cmp_idxs:
            batch_op.drop_index('ix_campaigns_org_status')
        if 'ix_campaigns_status' in cmp_idxs:
            batch_op.drop_index('ix_campaigns_status')
        for col in [
            'last_activity_at', 'recovered_amount', 'actions_executed_count',
            'messages_sent_count', 'enrolled_cases_count', 'escalation_rules',
            'retry_delay_hours', 'max_recovery_attempts', 'max_amount',
            'min_amount', 'channels_list', 'status', 'recovery_type'
        ]:
            if col in cmp_cols:
                batch_op.drop_column(col)

    # 2. recovery_cases
    rc_cols = {c['name'] for c in inspector.get_columns('recovery_cases')}
    with op.batch_alter_table('recovery_cases') as batch_op:
        if 'messages_sent_count' in rc_cols:
            batch_op.drop_column('messages_sent_count')

    # 1. transactions
    txn_cols = {c['name'] for c in inspector.get_columns('transactions')}
    txn_idxs = {idx['name'] for idx in inspector.get_indexes('transactions')}
    with op.batch_alter_table('transactions') as batch_op:
        if 'ix_org_transaction_external_id' in txn_idxs:
            batch_op.drop_index('ix_org_transaction_external_id')
        if 'ix_transactions_transaction_time' in txn_idxs:
            batch_op.drop_index('ix_transactions_transaction_time')
        if 'ix_transactions_subscription_id' in txn_idxs:
            batch_op.drop_index('ix_transactions_subscription_id')
        if 'ix_transactions_invoice_id' in txn_idxs:
            batch_op.drop_index('ix_transactions_invoice_id')
        if 'transaction_time' in txn_cols:
            batch_op.drop_column('transaction_time')
        if 'subscription_id' in txn_cols:
            batch_op.drop_column('subscription_id')
        if 'invoice_id' in txn_cols:
            batch_op.drop_column('invoice_id')
