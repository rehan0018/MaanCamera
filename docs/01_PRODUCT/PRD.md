# Product Requirements Document (PRD)

**Document ID:** MC-PRD-001  
**Version:** 2.0  
**Status:** Approved  

---

## 1. Product Scope

### In Scope for MVP
- Customer & Professional registration and session management.
- Multi-category professional profiles (photography, cinematic films, aerial, editing).
- Structured portfolio projects and media asset management.
- Location-based discovery and advanced multi-facet search.
- 4-way professional comparison matrix.
- AI natural language requirement parsing & 7-factor recommendation engine.
- Structured enquiry creation with multi-recipient distribution.
- Quotation builder with versioning and immutable acceptance rules.
- State-machine booking lifecycle management.
- Payment gateway adapter integration (Mock & Razorpay).
- Verified customer reviews (strictly restricted to completed bookings).
- Admin & moderation dashboard for identity and content audits.

### Out of Scope for MVP
- Native mobile applications (PWA/responsive mobile web first).
- International multi-currency split settlements.
- Large in-browser video rendering/editing suite.

---

## 2. User Stories & Acceptance Criteria

| ID | User Story | Acceptance Criteria |
| :--- | :--- | :--- |
| **MC-001** | Register as customer | Customer can create and verify account with email/phone. |
| **MC-002** | Register as professional | Professional can configure profile, skills, cities, and services. |
| **MC-003** | Publish portfolio | Authorized professionals can upload and publish project media. |
| **MC-004** | Discover professionals | Search returns matching candidates filtered by city and category. |
| **MC-005** | Filter professionals | Filters correctly narrow results by budget, styles, and verification. |
| **MC-006** | Compare professionals | Customers can compare up to 4 shortlisted profiles side-by-side. |
| **MC-007** | AI recommendations | AI extracts requirements and ranks candidates with match explanations. |
| **MC-008** | Send enquiry | Customers can submit structured requirement to one or more professionals. |
| **MC-009** | Send quotation | Professionals can submit pricing, deliverables, and terms. |
| **MC-010** | Confirm booking | Customer acceptance generates confirmed booking record. |
| **MC-011** | Make payment | Cryptographic server callback verification updates payment status. |
| **MC-012** | Submit review | Only completed eligible bookings can receive customer reviews. |
| **MC-013** | Manage business | Professionals can track leads, quotes, and active bookings. |
| **MC-014** | Moderate content | Admin can audit verification documents and resolve dispute reports. |
