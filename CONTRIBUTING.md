# Contributing to MaanCamera

Thank you for your interest in contributing to MaanCamera — India's open-source, AI-powered marketplace for creative professionals.

---

## 1. Engineering Principles

Before contributing, please review our core policies:
- **Free Software First**: Every dependency must be permissible under MIT, Apache-2.0, BSD-2/3, ISC, or PostgreSQL licenses. See [LICENSE_POLICY.md](file:///./LICENSE_POLICY.md).
- **No Paid APIs Required**: Core functionality must operate locally using self-hosted runtimes (PostgreSQL + pgvector, Valkey, SeaweedFS, Ollama).
- **Separation of Concerns**: Keep business rules inside `service.py`, never directly inside FastAPI route handlers.

---

## 2. Development Workflow

1. Fork and clone the repository.
2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
3. Start the local Docker Compose stack:
   ```bash
   docker compose up -d
   ```
4. Run backend tests:
   ```bash
   cd backend
   pytest
   ```
5. Run code linting:
   ```bash
   ruff check .
   ```

---

## 3. Pull Request Guidelines

- Branch names should follow: `feature/short-description` or `fix/issue-description`.
- Every schema change must include an Alembic migration in `backend/migrations/`.
- Ensure new endpoints are documented in `api/openapi.yaml`.
- Never commit actual `.env` files, production credentials, or real client personal data.
