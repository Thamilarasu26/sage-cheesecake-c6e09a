# ☁️ CloudShare – Secure Cloud File Sharing System

> **CSE Mini Project** | Flask · MySQL · Bootstrap 5 · AWS S3  
> A complete, production-grade secure cloud file sharing platform

---

## 🗂️ Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [ER Diagram](#er-diagram)
- [Architecture Diagram](#architecture-diagram)
- [Quick Start](#quick-start)
- [AWS S3 Setup](#aws-s3-setup)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Demo Steps](#demo-steps)
- [Viva Q&A](#viva-qa)

---

## Project Overview

**CloudShare** is a full-stack web application built with Python Flask that allows registered users to upload, store, and securely share files. Key capabilities:

- Secure registration and session-based authentication
- Multi-file upload with drag-and-drop support
- File manager with search, rename, and delete
- Cryptographically strong sharing links with expiry, revocation, and password protection
- Dual storage backends: local filesystem (development) and AWS S3 (production)
- Comprehensive security: CSRF protection, rate limiting, ownership checks, hashed passwords

---

## Features

| Feature | Details |
|---|---|
| Authentication | Bcrypt hashing, session cookies, remember-me |
| File Upload | Drag & drop, 50 MB limit, 30+ allowed types |
| File Manager | Search, rename, delete with confirmation |
| Sharing Links | Unique tokens, expiry dates, passwords, revocation |
| Storage | Local filesystem OR AWS S3 (via env variable) |
| Security | CSRF, rate limiting, ownership checks, no path traversal |
| Responsive UI | Bootstrap 5, mobile-friendly sidebar, dark nav |
| Tests | pytest suite covering all critical paths |

---

## Tech Stack

- **Backend:** Python 3.11+, Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter
- **Database:** MySQL 8.x (SQLite for tests)
- **Frontend:** HTML5, CSS3 (custom), JavaScript (vanilla), Bootstrap 5.3
- **Storage:** Local filesystem (dev) / AWS S3 (prod)
- **Security:** Werkzeug password hashing, `secrets` module, SHA-256 token hashing

---

## Project Structure

```
cloudshare/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # SQLAlchemy models
│   ├── auth/                # Registration, login, profile
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── files/               # Upload, download, rename, delete
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── sharing/             # Link creation, revocation, public access
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── main/                # Landing page
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── storage/             # Local + S3 backend
│   │   ├── __init__.py
│   │   └── backend.py
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── partials/
│   │   ├── main/
│   │   ├── auth/
│   │   ├── files/
│   │   └── sharing/
│   └── static/
│       ├── css/main.css
│       └── js/main.js
├── tests/
│   ├── conftest.py
│   └── test_cloudshare.py
├── config.py                # Dev / Prod / Test config classes
├── run.py                   # Entry point
├── seed_data.py             # Sample data seeder
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ER Diagram

```mermaid
erDiagram
    users {
        int id PK
        varchar name
        varchar email UK
        varchar password_hash
        datetime created_at
        datetime updated_at
    }

    files {
        int id PK
        int owner_id FK
        varchar original_filename
        varchar storage_key UK
        varchar mime_type
        bigint file_size
        varchar folder
        datetime created_at
        datetime updated_at
    }

    shared_links {
        int id PK
        int file_id FK
        int created_by FK
        varchar token UK
        varchar token_hash UK
        varchar password_hash
        datetime expires_at
        boolean allow_download
        boolean is_revoked
        datetime created_at
    }

    download_logs {
        int id PK
        int file_id FK
        int shared_link_id FK
        varchar ip_address
        datetime accessed_at
        varchar outcome
    }

    users ||--o{ files : "owns"
    users ||--o{ shared_links : "creates"
    files ||--o{ shared_links : "shared via"
    files ||--o{ download_logs : "logs"
    shared_links ||--o{ download_logs : "accessed through"
```

---

## Architecture Diagram

```mermaid
graph TB
    subgraph Client["🌐 Browser / Client"]
        UI["Bootstrap 5 UI\nHTML + CSS + JS"]
    end

    subgraph Flask["🐍 Flask Application"]
        direction TB
        Auth["Auth Blueprint\n/auth/*"]
        Files["Files Blueprint\n/files/*"]
        Sharing["Sharing Blueprint\n/share/*"]
        Main["Main Blueprint\n/"]
        Models["SQLAlchemy Models\nUser · File · SharedLink · Log"]
        Storage["Storage Abstraction\nbackend.py"]
    end

    subgraph DB["🗃️ Database"]
        MySQL[(MySQL\ncloudshare_db)]
    end

    subgraph StorageBackend["📦 File Storage"]
        Local["Local Filesystem\n/uploads/"]
        S3["AWS S3\nPrivate Bucket"]
    end

    UI -->|HTTPS POST/GET| Auth
    UI --> Files
    UI --> Sharing
    UI --> Main

    Auth --> Models
    Files --> Models
    Sharing --> Models
    Files --> Storage
    Sharing --> Storage

    Models --> MySQL
    Storage -->|STORAGE_BACKEND=local| Local
    Storage -->|STORAGE_BACKEND=s3| S3
```

---

## Quick Start

### 1. Prerequisites

```bash
# Python 3.11+
python --version

# MySQL 8.x running
mysql --version

# Git
git --version
```

### 2. Clone & Setup

```bash
# Navigate to project
cd cloudshare

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example env file
copy .env.example .env      # Windows
cp .env.example .env        # macOS/Linux

# Edit .env with your values
```

Key values to set in `.env`:

```env
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost/cloudshare_db
STORAGE_BACKEND=local
```

### 4. Create MySQL Database

```sql
-- In MySQL shell or Workbench:
CREATE DATABASE cloudshare_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Initialize Database & Run

```bash
# Tables are auto-created on first run
python run.py
```

Open **http://localhost:5000** in your browser.

### 6. Seed Sample Data (optional)

```bash
python seed_data.py
```

---

## AWS S3 Setup

1. **Create an S3 bucket** (enable "Block all public access")
2. **Create an IAM user** with `AmazonS3FullAccess` (or a custom policy)
3. **Generate access keys** for the IAM user
4. Update `.env`:

```env
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_PRESIGNED_URL_EXPIRY=300
```

Files will be uploaded to S3 with AES-256 server-side encryption.  
Downloads use short-lived presigned URLs (never expose bucket URLs directly).

---

## Running Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run a specific test class
pytest tests/test_cloudshare.py::TestSharingLinks -v

# With coverage report
pip install pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Deployment (Production)

### Environment Changes

```env
FLASK_ENV=production
SECRET_KEY=<64-char random hex>
DATABASE_URL=mysql+pymysql://user:pass@prod-host/cloudshare_db
STORAGE_BACKEND=s3
```

### Gunicorn + Nginx

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

Configure Nginx to proxy to Gunicorn and handle TLS via Let's Encrypt.

> **Never** run with `debug=True` in production.

---

## Security Notes

| Control | Implementation |
|---|---|
| Password Hashing | Werkzeug `generate_password_hash` (scrypt) |
| Share Tokens | `secrets.token_urlsafe(32)` — 256 bits entropy |
| Token Storage | SHA-256 hash stored in DB (not plaintext) |
| CSRF | Flask-WTF on all POST forms |
| Rate Limiting | Flask-Limiter (10 req/min on login) |
| Ownership | Every file/link route checks `owner_id == current_user.id` |
| Path Traversal | `pathlib.Path(filename).name` strips directory components |
| Allowed Types | Extension whitelist + MIME type check |
| Session | `HttpOnly`, `SameSite=Lax`, `Secure` in production |
| Secrets | All credentials in `.env`, never committed |

**Limitation:** Extension + MIME type checks are best-effort.  
Polyglot files (e.g., JPEG that is also valid JavaScript) can bypass these.  
For production, consider virus scanning (ClamAV) and content inspection.

---

## Demo Steps

1. Open `http://localhost:5000` — Landing page
2. Click **Sign Up Free** — Register with email + password
3. Log in — View empty dashboard
4. Upload a file via **Upload Files** (drag & drop demo)
5. View **File Manager** — search, rename, download, delete
6. Go to **Sharing Links** → Create Link → set expiry + password
7. Copy the link → open in **incognito window**
8. Enter share password → download the file
9. Return to dashboard → Revoke the link → verify it's blocked
10. **Profile** → Change password → Log out

---

## Viva Q&A

**Q1. What is Flask and why was it chosen?**  
Flask is a lightweight WSGI Python web framework. It was chosen for its simplicity, modularity, and ease of learning — ideal for a college mini project while still being production-capable.

**Q2. How are passwords stored securely?**  
Passwords are hashed using Werkzeug's `generate_password_hash()` which uses the scrypt algorithm (memory-hard, resistant to brute-force). The plaintext password is never stored or logged.

**Q3. How does the secure sharing link work?**  
A cryptographically random token (`secrets.token_urlsafe(32)`, 256-bit entropy) is generated. Its SHA-256 hash is stored in the database. The plaintext token appears only in the URL. This prevents timing attacks and hash-reversal.

**Q4. What is CSRF and how is it prevented?**  
Cross-Site Request Forgery tricks a browser into making an authenticated request to a trusted site. Flask-WTF generates a unique token per session; every state-changing POST form must include it. Requests with missing/invalid tokens are rejected.

**Q5. What is the difference between local and S3 storage?**  
Local mode stores files in a server directory outside the web root. S3 mode uploads to a private AWS bucket. In both cases, files are never served directly — users receive authorized downloads through Flask routes or time-limited S3 presigned URLs.

**Q6. How is path traversal prevented?**  
Using `pathlib.Path(filename).name`, which extracts only the filename portion, stripping any `../` or absolute-path components. Storage keys are UUID-based, not derived from user input.

**Q7. What are the tables in the database?**  
`users`, `files`, `shared_links`, `download_logs`. Each file has a UUID-based `storage_key`. Sharing links store a token hash, expiry, password hash, and revocation flag. Download logs capture every access with outcome and IP.

**Q8. How does expiry checking work?**  
The `SharedLink.is_expired` property compares `expires_at` (UTC) with `datetime.now(timezone.utc)`. If expired, the sharing route renders an "expired" page and logs the attempt.

**Q9. What testing approach was used?**  
pytest with Flask's test client. Tests cover registration, login, file upload validation, unauthorized download attempts, sharing link creation/expiry/revocation/password, and ownership enforcement. An in-memory SQLite database is used for test isolation.

**Q10. What are the future enhancements?**  
Real-time upload progress via WebSockets, file preview (PDF viewer, image gallery), email notifications when a link is accessed, folder hierarchies, team workspaces, virus scanning, two-factor authentication, and OAuth (Google/GitHub login).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pymysql'` | `pip install pymysql` |
| `sqlalchemy.exc.OperationalError: Can't connect to MySQL` | Check MySQL is running and credentials in `.env` are correct |
| `CSRF token missing` | Ensure `{{ csrf_token() }}` is in every POST form |
| `FileNotFoundError` on download | `LOCAL_UPLOAD_DIR` path must exist and match upload location |
| `boto3.exceptions.NoCredentialsError` | Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env` |
| `413 Request Entity Too Large` | Increase `MAX_CONTENT_LENGTH` in `config.py` or Nginx client body size |
