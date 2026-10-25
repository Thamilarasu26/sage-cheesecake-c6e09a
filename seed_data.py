"""
seed_data.py – Populate the database with sample users, files, and sharing links.
Run from the cloudshare/ directory:
    python seed_data.py

WARNING: This inserts demo data. Never run against a production database.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from app import create_app, db
from app.models import User, File, SharedLink


def seed():
    app = create_app()
    with app.app_context():
        # ------------------------------------------------------------------
        # Sample Users
        # ------------------------------------------------------------------
        if User.query.count() > 0:
            print("Database already seeded. Skipping.")
            return

        alice = User(name="Alice Johnson", email="alice@example.com")
        alice.set_password("Alice1234")

        bob = User(name="Bob Smith", email="bob@example.com")
        bob.set_password("Bob12345")

        db.session.add_all([alice, bob])
        db.session.flush()

        # ------------------------------------------------------------------
        # Sample Files (metadata only – no real uploads in seed)
        # ------------------------------------------------------------------
        files_data = [
            ("Project_Report_Final.pdf", "pdf", "application/pdf", 2_400_000),
            ("Design_Mockups.png",       "png", "image/png",        1_100_000),
            ("Database_Schema.sql",      "sql", "text/plain",          45_000),
            ("Presentation_Slides.pptx","pptx","application/vnd.openxmlformats-officedocument.presentationml.presentation", 8_700_000),
            ("Source_Code.zip",          "zip", "application/zip",  14_300_000),
            ("README.md",                "md",  "text/markdown",         8_200),
        ]

        alice_files = []
        for orig, ext, mime, size in files_data[:4]:
            key = secrets.token_hex(16) + "." + ext
            f = File(
                owner_id=alice.id,
                original_filename=orig,
                storage_key=key,
                mime_type=mime,
                file_size=size,
                folder="/",
            )
            db.session.add(f)
            alice_files.append(f)

        bob_files = []
        for orig, ext, mime, size in files_data[4:]:
            key = secrets.token_hex(16) + "." + ext
            f = File(
                owner_id=bob.id,
                original_filename=orig,
                storage_key=key,
                mime_type=mime,
                file_size=size,
                folder="/",
            )
            db.session.add(f)
            bob_files.append(f)

        db.session.flush()

        # Write dummy content files to disk so downloads succeed out of the box
        upload_dir = app.config.get("LOCAL_UPLOAD_DIR", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        for f in alice_files + bob_files:
            file_path = os.path.join(upload_dir, f.storage_key)
            if not os.path.exists(file_path):
                with open(file_path, "wb") as fh:
                    fh.write(f"CloudShare demo file content for: {f.original_filename}\n".encode())

        # ------------------------------------------------------------------
        # Sample Sharing Links
        # ------------------------------------------------------------------
        def make_link(file_obj, user, days_from_now=None, password=None, allow_dl=True):
            token = secrets.token_urlsafe(32)
            th = hashlib.sha256(token.encode()).hexdigest()
            expires = None
            if days_from_now is not None:
                expires = datetime.now(timezone.utc) + timedelta(days=days_from_now)
            link = SharedLink(
                file_id=file_obj.id,
                created_by=user.id,
                token=token,
                token_hash=th,
                expires_at=expires,
                allow_download=allow_dl,
            )
            if password:
                link.set_password(password)
            db.session.add(link)
            return token

        t1 = make_link(alice_files[0], alice, days_from_now=7)
        t2 = make_link(alice_files[1], alice, password="demo123")
        t3 = make_link(alice_files[2], alice, allow_dl=False)

        db.session.commit()

        print("[OK] Seed data inserted successfully!")
        print(f"\n  Alice: alice@example.com / Alice1234")
        print(f"  Bob:   bob@example.com   / Bob12345\n")
        print(f"  Sample sharing tokens:")
        print(f"    {t1}  (7-day expiry)")
        print(f"    {t2}  (password: demo123)")
        print(f"    {t3}  (view-only)")


if __name__ == "__main__":
    seed()
