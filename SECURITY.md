# Security Policy — MaanCamera

**Document ID:** MC-SEC-002  
**Status:** Enforced  

---

## 1. Supported Versions

| Version | Supported |
| :--- | :--- |
| 2.x (Current MVP) | :white_check_mark: |
| < 2.0 | :x: |

---

## 2. Reporting a Vulnerability

The MaanCamera engineering team takes application and data security seriously. If you discover a security vulnerability, please **DO NOT** open a public GitHub issue.

Instead, please send an encrypted or direct email to:
**security@maancamera.com** (or rehanwshaikh918@gmail.com)

Please include:
1. Description of the vulnerability.
2. Steps to reproduce or proof-of-concept payload.
3. Affected endpoints or components.
4. Estimated impact.

We commit to:
- Acknowledge receipt within **48 hours**.
- Provide a validation assessment and remediation plan within **5 business days**.
- Credit researchers in release notices following responsible disclosure.

---

## 3. Security Controls Implemented

- **Password & Session Security**: Argon2id password hashing (`time_cost=2`, `64 MiB` memory cost) and SHA-256 hashed HTTP-only session cookies (`SameSite=Lax`, forced `Secure` when `ENVIRONMENT=production`, fail-fast config validation for secrets and payment provider).
- **CSRF & Origin Protection**: Middleware validation of `Origin`/`Referer` headers alongside HMAC-signed double-submit `mc_csrf` / `X-CSRF-Token` verification on cookie-authenticated `POST`/`PATCH`/`PUT`/`DELETE` requests.
- **Rate Limiting**: Valkey-backed `slowapi` rate throttling on authentication (`5/minute` per IP on login/register) and AI endpoints (`10/minute` per user).
- **Payment Integrity**: Server-side order amount computation, fail-closed HMAC-SHA256 verification for payments and webhooks, `SELECT ... FOR UPDATE` row locking on booking updates, and unique idempotency constraint on `(provider, provider_event_id)`.
- **Media Upload Hardening**: Strict MIME (`image/jpeg`, `image/png`, `image/webp`) and extension allowlisting, server-generated S3 keys with signed `Content-Length` bounds (`15 MiB` max), and asynchronous Pillow format verification + EXIF metadata stripping before public publishing.
- **Authorization & Database Isolation**: Application-layer RBAC dependencies and resource ownership checks across all mutating endpoints, reinforced by PostgreSQL Row-Level Security (RLS) policies on `bookings`, `enquiries`, and `payments` bound to transaction-local `app.current_user_id` / `app.current_user_role` session configuration.
