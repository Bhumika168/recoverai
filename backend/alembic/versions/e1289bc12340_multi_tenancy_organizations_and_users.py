"""Multi-tenancy Organizations, Users, and Memberships

Revision ID: e1289bc12340
Revises: f432cf614865
Create Date: 2026-08-30 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1289bc12340'
down_revision: Union[str, None] = 'f432cf614865'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('environment', sa.String(length=32), server_default='Production', nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('high_value_threshold', sa.Float(), server_default='25000.0', nullable=False),
        sa.Column('require_human_approval', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('hard_decline_behavior', sa.String(length=32), server_default='SUPPRESS', nullable=False),
        sa.Column('auto_escalate_rules', sa.String(length=64), server_default='AFTER_MAX_RETRIES', nullable=False),
        sa.Column('auto_retry_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_created_at'), 'organizations', ['created_at'], unique=False)
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 3. organization_memberships
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='OWNER', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'organization_id', name='uq_user_organization')
    )
    op.create_index(op.f('ix_organization_memberships_id'), 'organization_memberships', ['id'], unique=False)
    op.create_index(op.f('ix_organization_memberships_organization_id'), 'organization_memberships', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_memberships_user_id'), 'organization_memberships', ['user_id'], unique=False)

    # 4. password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_id'), 'password_reset_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)

    # 5. payment_provider_connections
    op.create_table(
        'payment_provider_connections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='NOT_CONNECTED', nullable=False),
        sa.Column('environment', sa.String(length=20), server_default='TEST', nullable=False),
        sa.Column('api_key_masked', sa.String(length=100), nullable=True),
        sa.Column('webhook_secret_masked', sa.String(length=100), nullable=True),
        sa.Column('raw_credentials_encrypted', sa.JSON(), nullable=True),
        sa.Column('webhook_url', sa.String(length=255), nullable=True),
        sa.Column('events_received_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('events_processed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('events_failed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_webhook_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'provider', name='uq_org_provider')
    )
    op.create_index(op.f('ix_payment_provider_connections_id'), 'payment_provider_connections', ['id'], unique=False)
    op.create_index(op.f('ix_payment_provider_connections_organization_id'), 'payment_provider_connections', ['organization_id'], unique=False)
    op.create_index(op.f('ix_payment_provider_connections_provider'), 'payment_provider_connections', ['provider'], unique=False)

    # 6. webhook_events
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_event_id', sa.String(length=100), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('processing_status', sa.String(length=50), server_default='PROCESSED', nullable=False),
        sa.Column('processing_time_ms', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('normalized_event', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_events_id'), 'webhook_events', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_events_organization_id'), 'webhook_events', ['organization_id'], unique=False)
    op.create_index(op.f('ix_webhook_events_payload_hash'), 'webhook_events', ['payload_hash'], unique=False)
    op.create_index(op.f('ix_webhook_events_provider'), 'webhook_events', ['provider'], unique=False)
    op.create_index(op.f('ix_webhook_events_provider_event_id'), 'webhook_events', ['provider_event_id'], unique=False)

    # 7. message_templates
    op.create_table(
        'message_templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=32), server_default='EMAIL', nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=16), server_default='EN', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_templates_id'), 'message_templates', ['id'], unique=False)
    op.create_index(op.f('ix_message_templates_organization_id'), 'message_templates', ['organization_id'], unique=False)

    # 8. communication_logs
    op.create_table(
        'communication_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('recovery_case_id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=True),
        sa.Column('channel', sa.String(length=32), nullable=False),
        sa.Column('recipient_reference', sa.String(length=255), nullable=False),
        sa.Column('provider_message_id', sa.String(length=100), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('rendered_body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='QUEUED', nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recovery_case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['message_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_communication_logs_id'), 'communication_logs', ['id'], unique=False)
    op.create_index(op.f('ix_communication_logs_organization_id'), 'communication_logs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_communication_logs_recovery_case_id'), 'communication_logs', ['recovery_case_id'], unique=False)

    # 9. customer_opt_outs
    op.create_table(
        'customer_opt_outs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('customer_email', sa.String(length=255), nullable=True),
        sa.Column('customer_phone', sa.String(length=64), nullable=True),
        sa.Column('reason', sa.String(length=255), server_default='USER_UNSUBSCRIBED', nullable=False),
        sa.Column('opted_out_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'customer_email', name='uq_org_cust_email_optout')
    )
    op.create_index(op.f('ix_customer_opt_outs_customer_email'), 'customer_opt_outs', ['customer_email'], unique=False)
    op.create_index(op.f('ix_customer_opt_outs_customer_phone'), 'customer_opt_outs', ['customer_phone'], unique=False)
    op.create_index(op.f('ix_customer_opt_outs_id'), 'customer_opt_outs', ['id'], unique=False)
    op.create_index(op.f('ix_customer_opt_outs_organization_id'), 'customer_opt_outs', ['organization_id'], unique=False)

    # 10. merchant_notifications
    op.create_table(
        'merchant_notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=32), server_default='INFO', nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('related_case_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_case_id'], ['recovery_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_merchant_notifications_created_at'), 'merchant_notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_merchant_notifications_id'), 'merchant_notifications', ['id'], unique=False)
    op.create_index(op.f('ix_merchant_notifications_is_read'), 'merchant_notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_merchant_notifications_organization_id'), 'merchant_notifications', ['organization_id'], unique=False)

    # 11. Add organization_id and missing columns to existing tables
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key('fk_audit_logs_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('ix_audit_logs_organization_id'), ['organization_id'], unique=False)

    with op.batch_alter_table('campaigns') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key('fk_campaigns_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('ix_campaigns_organization_id'), ['organization_id'], unique=False)

    with op.batch_alter_table('customers') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key('fk_customers_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('ix_customers_organization_id'), ['organization_id'], unique=False)

    with op.batch_alter_table('transactions') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('transaction_id', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('customer_email', sa.String(length=255), nullable=True))
        batch_op.create_foreign_key('fk_transactions_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('ix_transactions_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_transactions_transaction_id'), ['transaction_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_transactions_customer_email'), ['customer_email'], unique=False)

    with op.batch_alter_table('recovery_cases') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('campaign_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key('fk_recovery_cases_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_recovery_cases_campaign_id', 'campaigns', ['campaign_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index(batch_op.f('ix_recovery_cases_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovery_cases_campaign_id'), ['campaign_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('recovery_cases') as batch_op:
        batch_op.drop_index(batch_op.f('ix_recovery_cases_campaign_id'))
        batch_op.drop_index(batch_op.f('ix_recovery_cases_organization_id'))
        batch_op.drop_constraint('fk_recovery_cases_campaign_id', type_='foreignkey')
        batch_op.drop_constraint('fk_recovery_cases_organization_id', type_='foreignkey')
        batch_op.drop_column('campaign_id')
        batch_op.drop_column('organization_id')

    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_index(batch_op.f('ix_transactions_customer_email'))
        batch_op.drop_index(batch_op.f('ix_transactions_transaction_id'))
        batch_op.drop_index(batch_op.f('ix_transactions_organization_id'))
        batch_op.drop_constraint('fk_transactions_organization_id', type_='foreignkey')
        batch_op.drop_column('customer_email')
        batch_op.drop_column('transaction_id')
        batch_op.drop_column('organization_id')

    with op.batch_alter_table('customers') as batch_op:
        batch_op.drop_index(batch_op.f('ix_customers_organization_id'))
        batch_op.drop_constraint('fk_customers_organization_id', type_='foreignkey')
        batch_op.drop_column('organization_id')

    with op.batch_alter_table('campaigns') as batch_op:
        batch_op.drop_index(batch_op.f('ix_campaigns_organization_id'))
        batch_op.drop_constraint('fk_campaigns_organization_id', type_='foreignkey')
        batch_op.drop_column('organization_id')

    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_organization_id'))
        batch_op.drop_constraint('fk_audit_logs_organization_id', type_='foreignkey')
        batch_op.drop_column('organization_id')

    op.drop_table('merchant_notifications')
    op.drop_table('customer_opt_outs')
    op.drop_table('communication_logs')
    op.drop_table('message_templates')
    op.drop_table('webhook_events')
    op.drop_table('payment_provider_connections')
    op.drop_table('password_reset_tokens')
    op.drop_table('organization_memberships')
    op.drop_table('users')
    op.drop_table('organizations')
