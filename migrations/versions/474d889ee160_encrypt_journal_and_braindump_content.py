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
    bind = op.get_bind()
    
    # 1. Safely fetch the key
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("CRITICAL: ENCRYPTION_KEY must be set in your .env to run this migration!")
        
    f = Fernet(key.encode())

    # 2. Expand columns to TEXT first (Ciphertext is longer than plain text)
    with op.batch_alter_table('brain_dumps', schema=None) as batch_op:
        batch_op.alter_column('content', type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.alter_column('content', type_=sa.Text(), existing_nullable=False)

    # 3. Encrypt Brain Dumps
    dumps = bind.execute(text("SELECT id, content FROM brain_dumps")).fetchall()
    for dump in dumps:
        dump_id = dump[0]
        dump_content = dump[1]
        if dump_content and not str(dump_content).startswith('gAAAAA'): 
            encrypted = f.encrypt(str(dump_content).encode('utf-8')).decode('utf-8')
            bind.execute(
                text("UPDATE brain_dumps SET content = :enc WHERE id = :id"),
                {"enc": encrypted, "id": dump_id}
            )

    # 4. Encrypt Journal Entries
    entries = bind.execute(text("SELECT id, content FROM journal_entries")).fetchall()
    for entry in entries:
        entry_id = entry[0]
        entry_content = entry[1]
        if entry_content and not str(entry_content).startswith('gAAAAA'):
            encrypted = f.encrypt(str(entry_content).encode('utf-8')).decode('utf-8')
            bind.execute(
                text("UPDATE journal_entries SET content = :enc WHERE id = :id"),
                {"enc": encrypted, "id": entry_id}
            )

def downgrade():
    # Downgrading encryption is complex and risky, we pass for now.
    # If you ever need to decrypt the DB, it should be done via a dedicated script.
    pass
