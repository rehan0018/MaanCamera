# ADR-003: Valkey 7.2 and SeaweedFS for Open-Source Cache & S3 Storage

**Status:** Accepted  
**Date:** 2026-11-07  

---

## Context
Redis switched to dual source-available licenses (RSALv2/SSPLv1), conflicting with MaanCamera's strict Free & Open Source engineering mandate. Similarly, relying strictly on AWS S3 creates proprietary lock-in.

## Decision
- Adopt **Valkey 7.2** (BSD-3-Clause open-source fork supported by the Linux Foundation) for caching, rate limiting, and Celery task brokerage.
- Adopt **SeaweedFS** (Apache-2.0 open-source distributed storage) with an S3-compatible gateway for local development and self-hosted object storage.

## Consequences
- 100% compliance with open-source licensing policy.
- Local S3 bucket compatibility allows developers to upload, generate presigned URLs, and test media pipelines without paid cloud storage subscriptions.
