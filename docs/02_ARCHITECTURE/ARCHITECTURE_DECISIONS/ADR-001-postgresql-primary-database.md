# ADR-001: PostgreSQL 16 with pgvector as Master Relational & Vector Store

**Status:** Accepted  
**Date:** 2026-11-07  

---

## Context
MaanCamera requires a robust database capable of enforcing transactional ACID consistency for monetary quotation/booking workflows, complex geospatial queries (service radiuses across Indian cities), full-text trigram indexing (`pg_trgm`), and vector similarity search for semantic AI matching.

## Decision
Adopt **PostgreSQL 16** with extensions `uuid-ossp`, `pgcrypto`, `pg_trgm`, and `pgvector`.

## Alternatives Considered
- *Separate MongoDB + Pinecone*: High operational cost, managed service vendor lock-in, lacks distributed ACID transactions across bookings and payments.
- *MySQL*: Lacks native high-performance vector indexing comparable to pgvector.

## Consequences
- Single unified database engine simplifies backups, local development, and hosting costs.
- Free and open-source under PostgreSQL License.
- Vector search and relational queries execute within the same database transaction boundary.
