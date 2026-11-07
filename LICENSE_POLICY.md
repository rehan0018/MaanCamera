# MaanCamera — Free & Open Source Software Policy

**Document ID:** MC-GOV-001  
**Version:** 2.0  
**Status:** Enforced Engineering Principle  

---

## 1. Core Engineering Principle

> **No paid software subscriptions, proprietary paid dependencies, mandatory paid AI APIs or paid developer tools are required to develop, run, or operate the MaanCamera initial release.**

All software choices must prioritize:
1. Permissive open-source licenses (MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, PostgreSQL License).
2. Self-hostable services and runtimes (FastAPI, Next.js, PostgreSQL + pgvector, Valkey, SeaweedFS, Ollama).
3. Zero mandatory vendor lock-in with swappable abstraction adapters for payments, storage, and AI inference.

---

## 2. Permissible Licenses

| License Category | Status | Allowed Examples | Notes |
| :--- | :--- | :--- | :--- |
| **Permissive** | **Auto-Approved** | MIT, Apache 2.0, BSD-2/3-Clause, ISC, PostgreSQL License | Must retain copyright notices in distributions. |
| **Weak Copyleft** | **Requires Review** | LGPL-2.1, LGPL-3.0, MPL-2.0 | Allowed only as dynamically linked shared libraries/services without internal modifications. |
| **Strong Copyleft** | **Isolated Only** | AGPL-3.0, GPL-3.0 | Permitted only for isolated background support tooling (e.g., Grafana OSS), never in backend core library imports. |
| **Commercial / Paid** | **Forbidden** | Proprietary SDKs with per-seat or paywall fees | Disallowed in core repository. |

---

## 3. Operational Expenses vs. Free Software

Free and open-source software governs the intellectual property and code dependencies. Operational infrastructure (compute, storage volumes, SMS/WhatsApp delivery gateways, domain names, bank gateway transaction fees) represents external utility cost. All third-party services are wrapped behind modular interfaces to ensure zero platform dependency.
