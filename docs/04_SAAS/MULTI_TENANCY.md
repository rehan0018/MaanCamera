# SaaS Multi-Tenancy Architecture

**Document ID:** MC-SAAS-001  
**Version:** 1.0  

---

## 1. Organization-Based Isolation

MaanCamera supports solo freelancers, collaborative teams, and full-scale production studios through an Organization-based boundary model:

```
Organization: Aura Weddings Studio
├── Owner (Full administrative access, billing, and membership management)
├── Studio Manager (Enquiry dispatch, quotations, and scheduling)
├── Principal Photographers (Portfolio publishing, gear assignment)
├── Cinematographers / Drone Pilots (Project assets management)
└── Editors / Colorists (Post-production asset delivery)
```

---

## 2. Resource Scoping & RBAC

| Role | Browse Marketplace | Submit Enquiries | Publish Portfolio | Issue Quotations | Access Organization Financials |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer** | Yes | Yes | No | No | No |
| **Individual Professional** | Yes | Yes | Yes (Own) | Yes (Own) | Yes (Own) |
| **Studio Member** | Yes | Yes | Yes (Assigned) | Yes (Assigned) | No |
| **Studio Owner** | Yes | Yes | Yes (All Studio) | Yes (All Studio) | Yes (All Studio) |
| **Platform Moderator** | Yes | No | Read-Only Audit | Read-Only Audit | Read-Only Audit |

---

## 3. SaaS Subscription Plans

- **Free Tier**: Public profile, basic portfolio (up to 3 projects), receive direct customer enquiries.
- **Creator Plan**: High-resolution gallery storage (10GB), detailed profile metrics, up to 10 projects.
- **Pro Studio Plan**: AI Proposal Assistant, automated calendar sync, video portfolio derivatives, 50GB storage.
- **Enterprise Studio Plan**: Multi-member organization seats, custom contracts, advanced analytics, dedicated account verification.
