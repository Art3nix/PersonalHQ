"""encrypt journal and braindump content

Revision ID: 474d889ee160
Revises: e1e35f22c007
Create Date: 2026-06-13 12:45:21.801967

"""
from alembic import op
import sqlalchemy as sa
import os
from cryptography.fernet import Fernet
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '474d889ee160'
down_revision = 'e1e35f22c007'
branch_labels = None
depends_on = None


def upgrade():
    pass

def downgrade():
    pass
