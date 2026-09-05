"""Add missing CaseStatus enum values

Revision ID: d1045ef67890
Revises: c9032de34567
Create Date: 2026-09-05 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1045ef67890'
down_revision: Union[str, None] = 'c9032de34567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        all_statuses = [
            'DETECTED', 'DIAGNOSED', 'POLICY_REVIEW', 'APPROVED',
            'ACTION_SCHEDULED', 'CUSTOMER_CONTACTED', 'RETRY_PENDING',
            'PAYMENT_ATTEMPTED', 'VERIFICATION', 'OPEN', 'IN_PROGRESS',
            'PENDING_APPROVAL', 'RECOVERED', 'ESCALATED', 'EXHAUSTED',
            'BLOCKED', 'CANCELLED', 'EXPIRED', 'UNRECOVERABLE', 'STOPPED', 'FAILED'
        ]
        # In PostgreSQL, ALTER TYPE ... ADD VALUE must run outside of transaction block in earlier versions
        # or can run with autocommit block
        with op.get_context().autocommit_block():
            for val in all_statuses:
                op.execute(sa.text(f"ALTER TYPE casestatus ADD VALUE IF NOT EXISTS '{val}'"))


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums without recreating the type
    pass
