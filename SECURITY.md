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

- **Password, Session & 2FA Security**: Argon2id password hashing (`time_cost=2`, `64 MiB` memory cost), SHA-256 hashed HTTP-only session cookies (`SameSite=Lax`, forced `Secure` when `ENVIRONMENT=production`), refresh token rotation (`/auth/refresh`), device session listing/revocation (`/auth/sessions`), progressive exponential account lockout after failed attempts, and RFC 6238 TOTP 2FA support (`/auth/totp/*`).
- **Verification & Account Recovery**: Single-use hashed verification tokens (`24h` email links, `10m` HMAC-SHA256 6-digit phone OTPs with attempt cap, and `30m` password reset links that revoke all prior active sessions).
- **CSRF, CORS & HTTP Security Headers**: Origin/Referer verification (restricting `http://testserver` strictly to `ENVIRONMENT=test`) + HMAC-signed double-submit `mc_csrf` / `X-CSRF-Token`, explicit CORS method/header allowlists, and `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`, and production HSTS headers across FastAPI and Next.js.
- **Proxy-Aware Rate Limiting**: Valkey-backed `slowapi` rate throttling with trusted proxy IP resolution (`TRUSTED_PROXY_IPS` / `--proxy-headers`) on auth routes (`5/minute`) and per-user AI routes (`10/minute`).
- **Payment Integrity**: Server-side order amount computation, fail-closed HMAC-SHA256 verification for payments and webhooks, `SELECT ... FOR UPDATE` row locking on booking updates, and unique idempotency constraint on `(provider, provider_event_id)`.
- **Media Upload Hardening**: Strict MIME (`image/jpeg`, `image/png`, `image/webp`) and extension allowlisting, server-generated S3 keys with signed `Content-Length` bounds (`15 MiB` max), and asynchronous Pillow format verification + EXIF metadata stripping before public publishing.
- **Database Isolation (PostgreSQL RLS)**: Non-owner runtime role (`maancamera_app`, `NOBYPASSRLS`) with `ENABLE` + `FORCE ROW LEVEL SECURITY` on `bookings`, `enquiries`, `payments`, and `quotations`, fail-closed default-deny policies, and SQLAlchemy `after_begin` transaction-level `app.current_user_id` / `app.current_user_role` injection across commits, paired with a single-transaction-per-request session lifecycle (`get_db`).
- **DPDP Privacy & Log Hygiene**: Versioned consent capture (`consent_records`), personal data export (`/users/me/export`), PII-scrubbing account deletion (`/users/me`), and regex-based email/phone masking in application logs (`PiiScrubbingFilter`).
