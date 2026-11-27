# MaanCamera Backend Service

Modular monolith backend powering MaanCamera — India's trusted AI-powered marketplace and business SaaS for photography and videography professionals.

## Architecture

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 16 with pgvector extension
- **ORM & Migrations**: SQLAlchemy 2.0 Async + Alembic
- **Cache & Broker**: Valkey 7.2 (Redis-compatible, BSD-3-Clause)
- **Object Storage**: SeaweedFS (S3-compatible, Apache-2.0)
- **AI Runtime**: Ollama (Self-hosted open models: Llama 3 / Mistral, MIT)
- **Background Tasks**: Celery with Redis broker and Pillow EXIF processing

## Modules

- `app.modules.identity`: User authentication (Argon2id, HTTP-only secure cookies, CSRF protection, RBAC).
- `app.modules.professionals`: Professional profiles, equipment, verified badges, pricing tiers.
- `app.modules.portfolios`: Portfolio projects, responsive WebP variants, EXIF privacy stripping.
- `app.modules.search`: Structured faceted search, multi-category joins, budget filtering, Bayesian ranking.
- `app.modules.enquiries`: Customer RFQ broadcasts, multi-recipient tracking, city/duration handling.
- `app.modules.quotations`: Versioned quotation lifecycle, deposit calculation, auto booking creation.
- `app.modules.bookings`: State-machine transitions, customer acceptance verification, completion metrics.
- `app.modules.payments`: Server-calculated amounts, Razorpay & Mock payment gateway, HMAC webhook verification.
- `app.modules.reviews`: Verified booking reviews, rating constraints, moderation pipeline.
- `app.modules.ai`: 7-factor weighted candidate ranking, query requirement extraction, review summarization.

## Getting Started

```bash
# Install locked dependencies (including dev/test tools)
uv sync --frozen --extra dev

# Apply PostgreSQL + pgvector + RLS migrations and load deterministic dev seed
uv run alembic upgrade head
uv run python -m app.db.seed

# Run checks and tests
uv run ruff check .
uv run mypy app
uv run pytest -q

# Start development server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
