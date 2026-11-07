# MaanCamera — Dependency Allowlist

**Document ID:** MC-GOV-002  
**Status:** Approved Allowlist  

Every runtime dependency used in the MaanCamera codebase has been vetted for compliance with our Free & Open-Source Software (FOSS) policy.

## 1. Backend Stack (Python 3.11+)

| Package | Version Range | License | Primary Purpose |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | MIT | High-performance modular async web framework |
| `uvicorn[standard]` | `>=0.29.0` | BSD-3-Clause | ASGI web server runtime |
| `pydantic` | `>=2.6.0` | MIT | Data validation and schema enforcement |
| `pydantic-settings` | `>=2.2.0` | MIT | Environment configuration management |
| `sqlalchemy` | `>=2.0.28` | MIT | SQL toolkit & Object Relational Mapper |
| `asyncpg` | `>=0.29.0` | Apache-2.0 | Async PostgreSQL client driver |
| `psycopg2-binary` | `>=2.9.9` | LGPL / BSD | Synchronous PostgreSQL driver (migrations) |
| `alembic` | `>=1.13.1` | MIT | Database schema migration management |
| `pgvector` | `>=0.2.5` | PostgreSQL | Vector embedding extension interface |
| `valkey` / `redis` | `>=5.0.3` | BSD-3-Clause | In-memory caching and message broker client |
| `celery` | `>=5.3.6` | BSD-3-Clause | Distributed task queue for asynchronous jobs |
| `aioboto3` | `>=12.3.0` | Apache-2.0 | Async AWS S3 SDK for SeaweedFS integration |
| `pillow` | `>=10.2.0` | HPND | Image processing, thumbnailing, and EXIF sanitization |
| `passlib[argon2]` | `>=1.7.4` | BSD-3-Clause | Argon2id secure password hashing |
| `python-jose[cryptography]`| `>=3.3.0` | MIT | Secure token encoding and verification |
| `httpx` | `>=0.27.0` | BSD-3-Clause | Async HTTP client for Ollama & external APIs |
| `pytest` | `>=8.1.1` | MIT | Unit and integration testing |
| `ruff` | `>=0.3.4` | MIT | Ultra-fast Python linter and formatter |

## 2. Frontend Stack (Node.js 20+ / TypeScript)

| Package | Version Range | License | Primary Purpose |
| :--- | :--- | :--- | :--- |
| `next` | `>=14.2.0` | MIT | React server & client application framework |
| `react` / `react-dom` | `>=18.2.0` | MIT | UI component library |
| `typescript` | `>=5.4.0` | Apache-2.0 | Static type safety |
| `tailwindcss` | `>=3.4.0` | MIT | Utility-first CSS engine |
| `lucide-react` | `>=0.360.0` | ISC | Accessible open icon set |
| `clsx` / `tailwind-merge` | `>=2.0.0` | MIT | Conditional class utility merging |
| `vitest` | `>=1.4.0` | MIT | Next-generation frontend unit test runner |

## 3. Infrastructure & Services

| Technology | License | Open Source Repository / Foundation |
| :--- | :--- | :--- |
| **PostgreSQL 16** | PostgreSQL License | The PostgreSQL Global Development Group |
| **pgvector** | PostgreSQL License | pgvector GitHub community |
| **Valkey 7.2** | BSD-3-Clause | Linux Foundation Valkey Project |
| **SeaweedFS** | Apache-2.0 | SeaweedFS distributed object storage |
| **Ollama** | MIT | Ollama Go / C++ local AI model runtime |
