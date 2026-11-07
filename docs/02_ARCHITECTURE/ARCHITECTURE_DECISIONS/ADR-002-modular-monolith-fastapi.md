# ADR-002: Modular Monolith Architecture with Python FastAPI

**Status:** Accepted  
**Date:** 2026-11-07  

---

## Context
Marketplace platforms often face premature microservice decomposition, causing high network latency, distributed transaction failures, complex local development, and increased operational overhead.

## Decision
Build MaanCamera as a **Modular Monolith** using **Python 3.11** and **FastAPI**.
Each functional domain (identity, professionals, portfolios, search, enquiries, bookings, payments, reviews, AI) is encapsulated in an isolated module with its own router, schemas, models, and service boundary.

## Consequences
- Fast local development cycle using Docker Compose or single-command startup.
- Clean domain boundaries allow decomposing specific heavy modules (such as video transcoding or vector ranking) into standalone microservices in the future without refactoring client contracts.
- High performance async I/O via Uvicorn and asyncpg.
