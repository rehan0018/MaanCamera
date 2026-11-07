# India Privacy & DPDPA 2023 Compliance Specification

**Document ID:** MC-COMP-001  
**Version:** 1.0  
**Jurisdiction:** India (Digital Personal Data Protection Act, 2023)  

---

## 1. Compliance Architecture

MaanCamera implements privacy-by-design to adhere to India's **Digital Personal Data Protection Act, 2023 (DPDPA)**:

1. **Purpose Limitation**: Customer contact information (phone, email, event address) is disclosed to a professional only after the customer deliberately sends an enquiry or confirms a quotation.
2. **Consent Architecture**: Granular, revocable consent recorded with timestamp, purpose ID, and notice version.
3. **Data Principal Rights**:
   - Right to Access summary of personal data processed.
   - Right to Correction and Erasure of outdated or incorrect profile records.
   - Right to Grievance Redressal via a nominated Data Protection Officer (DPO).
4. **Media & EXIF Data Stripping**:
   - Original RAW and high-resolution JPEG/PNG files are stored privately in non-public object storage buckets.
   - Public derivatives served on the marketplace have sensitive GPS location tags and camera serial metadata stripped to protect client and venue privacy.
5. **Copyright & Model Releases**:
   - Professionals must check a legally binding copyright and model release declaration before publishing client photography publicly.
   - Customers and models have a 1-click takedown reporting mechanism (`POST /reviews/{id}/report` or media dispute workflow).
