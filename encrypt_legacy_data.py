from personalhq import create_app
from personalhq.extensions import db
from sqlalchemy import text
from cryptography.fernet import Fernet
import os

def run_encryption():
    app = create_app()
    
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        print("CRITICAL: ENCRYPTION_KEY is missing!")
        return
        
    f = Fernet(key.encode())

    with app.app_context():
        # 1. Encrypt Brain Dumps
        dumps = db.session.execute(text("SELECT id, content FROM brain_dumps")).fetchall()
        dump_count = 0
        for d in dumps:
            if d[1] and not str(d[1]).startswith('gAAAAA'):
                enc = f.encrypt(str(d[1]).encode('utf-8')).decode('utf-8')
                db.session.execute(text("UPDATE brain_dumps SET content = :enc WHERE id = :id"), {"enc": enc, "id": d[0]})
                dump_count += 1

        # 2. Encrypt Journals
        entries = db.session.execute(text("SELECT id, content FROM journal_entries")).fetchall()
        entry_count = 0
        for e in entries:
            if e[1] and not str(e[1]).startswith('gAAAAA'):
                enc = f.encrypt(str(e[1]).encode('utf-8')).decode('utf-8')
                db.session.execute(text("UPDATE journal_entries SET content = :enc WHERE id = :id"), {"enc": enc, "id": e[0]})
                entry_count += 1

        db.session.commit()
        print(f"Success! Encrypted {dump_count} brain dumps and {entry_count} journal entries.")

if __name__ == "__main__":
    run_encryption()