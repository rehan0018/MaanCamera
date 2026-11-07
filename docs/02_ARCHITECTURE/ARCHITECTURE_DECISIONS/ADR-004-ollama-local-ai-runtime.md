# ADR-004: Ollama & Local Sentence Transformers for AI Runtime

**Status:** Accepted  
**Date:** 2026-11-07  

---

## Context
Commercial AI APIs (OpenAI, Anthropic, Gemini) impose recurring API subscription fees and external data transmission risks for private user queries.

## Decision
Adopt **Ollama (MIT License)** running local quantized open-weight models (e.g. Qwen 2.5, Gemma, or Mistral) wrapped behind an abstract `AIProvider` Python interface. Use `sentence-transformers` with `BAAI/bge-small-en-v1.5` for text vector embeddings.

## Consequences
- Zero paid API token charges during development, CI, and initial operations.
- Data privacy is preserved on self-hosted infrastructure.
- Abstract interface allows swapping or cascading models transparently without altering domain services.
