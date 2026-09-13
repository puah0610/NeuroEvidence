# MVP architecture

```mermaid
flowchart LR
    UI[React chat and dashboard] --> API[FastAPI]
    API --> SAFE[Scope and safety rules]
    SAFE -->|in scope| RET[Chroma retrieval]
    RET --> LLM[OpenAI Responses API]
    LLM --> CLAIM[Claim extraction]
    CLAIM --> META[Crossref and manifest metadata checks]
    CLAIM --> NLI[CPU NLI verifier]
    META --> SCORE[Evidence support score]
    NLI --> SCORE
    SCORE --> UI
    API --> DB[(SQLite traces and feedback)]
    PMC[Fixed PMC OA corpus] --> INGEST[JATS cleaning and chunking]
    INGEST --> RET
```

The safety path runs before retrieval and generation. The baseline uses the same generation adapter but bypasses retrieval and verification. Original drafts and post-verification responses are retained in SQLite for audit and analysis.

## Evidence score

The score combines supported-claim ratio (50%), valid-citation ratio (30%), and mean normalized retrieval relevance (20%). It is a project-specific ranking signal and must never be presented as a probability of medical correctness.

## Data boundary

No user authentication or patient profile exists in the MVP. The interface discourages personal medical details. API keys remain server-side, and the evaluation endpoint only accepts local requests.

