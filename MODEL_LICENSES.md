# MaanCamera — AI Model Licenses & Registry

**Document ID:** MC-AI-GOV-001  
**Status:** Evaluated and Approved Open-Source Models  

To ensure complete legal compliance and independence from commercial closed-source AI APIs, MaanCamera evaluates every open model against commercial use clauses, dataset provenance, and runtime resource requirements.

---

## 1. Approved Local Model Candidates

| Model Identifier | Provider / Family | Parameters | License | Commercial Use | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen2.5-7B-Instruct** | Alibaba Cloud / Qwen | 7B | Apache-2.0 | **Permitted** | Natural-language search parsing, structured customer requirement extraction, quotation drafting |
| **Mistral-7B-Instruct-v0.3**| Mistral AI | 7.2B | Apache-2.0 | **Permitted** | Review summarization, inquiry requirement validation |
| **Gemma-2-2B-IT / 9B-IT** | Google DeepMind | 2.6B / 9B | Gemma Terms of Use | **Permitted** | Low-latency local extraction & professional profile assistant |
| **bge-small-en-v1.5** | BAAI | 33M | MIT | **Permitted** | High-speed text embeddings for search matching (384 dimensions) |
| **OpenCLIP ViT-B/32** | LAION / OpenCLIP | 86M | MIT | **Permitted** | Visual portfolio feature embedding and style tag classification (512 dimensions) |

---

## 2. Model Execution Architecture

- **Local Inference Engine:** Ollama running locally or on self-hosted GPU/CPU instances.
- **Vector Search:** `pgvector` inside self-hosted PostgreSQL (no Pinecone or closed SaaS vector databases).
- **Fallback Guarantee:** In the event of an AI runtime delay or absence of GPU hardware, the system gracefully falls back to PostgreSQL Full-Text Search and Trigram similarity indexing (`pg_trgm`). No core booking or discovery path is hard-blocked by AI downtime.
