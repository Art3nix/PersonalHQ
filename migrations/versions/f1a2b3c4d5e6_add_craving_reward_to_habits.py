"""Add craving and reward fields to habits

Revision ID: f1a2b3c4d5e6
Revises: e3bed0f30f6b
Create Date: 2026-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e3bed0f30f6b'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('habits', sa.Column('craving', sa.String(), nullable=True))
    op.add_column('habits', sa.Column('reward', sa.String(), nullable=True))

def downgrade():
    op.drop_column('habits', 'reward')
    op.drop_column('habits', 'craving')
