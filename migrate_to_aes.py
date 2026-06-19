import os
from personalhq import create_app
from personalhq.extensions import db
from sqlalchemy import text
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

def encrypt_existing_data():
    app = create_app()
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        print("CRITICAL: ENCRYPTION_KEY is missing from the environment!")
        return

    # Initialize the exact encryption wrapper your new model will use
    encryption_type = StringEncryptedType(db.Text, key, AesEngine, 'pkcs5')

    with app.app_context():
        dialect = db.engine.dialect

        # --- MIGRATE BRAIN DUMPS ---
        # Read the plain text directly using raw SQL
        dumps = db.session.execute(text("SELECT id, content FROM brain_dumps WHERE content IS NOT NULL")).fetchall()

        print(f"Found {len(dumps)} Brain Dumps to encrypt...")
        for dump_id, plain_content in dumps:
            # Pass the plain text through the SQLAlchemy-Utils encryption processor
            encrypted_content = encryption_type.process_bind_param(str(plain_content), dialect)

            # Write the AES ciphertext back to the database
            db.session.execute(
                text("UPDATE brain_dumps SET content = :enc WHERE id = :id"),
                {"enc": encrypted_content, "id": dump_id}
            )

        # --- MIGRATE JOURNAL ENTRIES (If applicable) ---
        journals = db.session.execute(text("SELECT id, content FROM journal_entries WHERE content IS NOT NULL")).fetchall()

        print(f"Found {len(journals)} Journal Entries to encrypt...")
        for journal_id, plain_content in journals:
            encrypted_content = encryption_type.process_bind_param(str(plain_content), dialect)

            db.session.execute(
                text("UPDATE journal_entries SET content = :enc WHERE id = :id"),
                {"enc": encrypted_content, "id": journal_id}
            )

        db.session.commit()
        print("\nSUCCESS: All plain text data has been converted to AesEngine encryption.")

if __name__ == "__main__":
    encrypt_existing_data()