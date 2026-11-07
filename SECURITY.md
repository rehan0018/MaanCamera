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

## 3. Security Standards Enforced
- Argon2id password hashing with time cost 2 and 64MB memory cost.
- Secure, HTTP-only SameSite cookie session management.
- Cryptographic HMAC-SHA256 signature verification on payment provider webhooks.
- EXIF metadata sanitization on all publicly served client photos.
- Row-Level Security (RLS) and ownership validation on all mutate operations.
