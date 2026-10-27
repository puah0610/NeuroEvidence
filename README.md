# NeuroEvidence

**NeuroEvidence** is an educational and health informatics research copilot for neurological inquiries (focusing on Parkinson's disease and epilepsy). It combines a curated **3-Layer Triad Knowledge Base**, **Selective Multi-Hop Query Decomposition**, **Hybrid Dense-Sparse Retrieval with Neural Cross-Encoder Reranking**, **Agentic Live PubMed Retrieval**, **Biomedical NLI Claim Verification**, and a **Drug-Drug Interaction (DDI) Safety Engine**.

> [!IMPORTANT]
> **Educational & Research Software Only:** NeuroEvidence is designed strictly for academic evaluation and clinical informatics research. It is **not** a certified medical device and must never be used for clinical diagnosis or direct patient treatment.

---

## 🌟 Key Capabilities & Architectural Innovations

- 🏛️ **Curated 3-Layer Triad Knowledge Base**: Pre-indexed clinical knowledge base spanning three hierarchical evidence tiers:
  - **Layer 1 (Foundational Knowledge):** NCBI Bookshelf / StatPearls (etiology, pathophysiology, seizure classification, Hoehn & Yahr staging).
  - **Layer 2 (Clinical Guidelines):** NICE NG217 (Epilepsies) and NICE NG71 (Parkinson's Disease) first-line treatment and safety algorithms.
  - **Layer 3 (Empirical Evidence & Trials):** High-impact comparative RCTs (e.g., Lancet SANAD II) and Cochrane meta-analyses.
- ⚡ **Dual-Provider LLM Engine (Gemini & OpenAI)**: Native integration with **Google Gemini** (default: `gemini-3.8-flash` / `gemini-3.1-flash-lite`, with `gemini-2.5-pro` for evaluation) and OpenAI (`gpt-4.1-mini`, `gpt-4o`). Includes zero-cost tier handling, candidate model fallbacks, and a fully offline local demo mode.
- 🧩 **Selective Multi-Hop Query Decomposition**: Automatically analyzes query complexity. Atomic queries retrieve directly, while complex multi-part questions (e.g., causes + guideline evidence) are selectively decomposed into targeted Triad subqueries with constraint preservation and deduplicated evidence fusion.
- 🎯 **Hybrid Retrieval & Neural Cross-Encoder Reranking**: Combines BM25 lexical matching with dense semantic embeddings (`pritamdeka/S-PubMedBert-MS-MARCO` or Gemini/OpenAI embeddings) via Reciprocal Rank Fusion (RRF), followed by a neural cross-encoder re-ranking stage for high clinical precision.
- 🌐 **Agentic Live PubMed Retrieval**: When local knowledge base evidence is sparse or insufficient, the engine autonomously executes real-time NCBI PubMed searches via E-utilities, enforces Strategy A clinical pre-rules (clinical trials, systematic reviews, humans, 2015+), neural re-ranks candidates, and auto-indexes fresh evidence into ChromaDB.
- 🛡️ **Biomedical NLI Claim Verification**: Sentence-level natural language inference (`pritamdeka/PubMedBERT-MNLI-MedNLI`) classifies generated claims as *Entailed*, *Contradicted*, or *Insufficiently Supported*, calculating a composite evidence score and highlighting ungrounded claims.
- 💊 **Drug-Drug Interaction (DDI) Checker**: Real-time rule engine detecting critical neurological drug-drug interactions and contraindications (e.g., sodium valproate + lamotrigine SJS risks, metoclopramide + levodopa D2 antagonism).
- 👤 **Human-in-the-Loop Literature Curation**: Protocolized literature discovery (`discover`) and verified human promotion (`accept-candidates`) into the immutable corpus manifest.
- 💻 **Modern Clinical Copilot UI**: Built with React, Tailwind CSS, and Lucide icons; features session folders, source excerpt inspectors, NLI verification badges, latency/token cost metrics, and user feedback tracking.

---

## 🚀 Quick Start

> [!NOTE]
> The repository ships **pre-configured with the bundled Triad knowledge base**. You can run the entire system immediately in local demo mode without needing external API keys or GPU compute.

### 1. Environment Configuration

Copy the example environment configuration:

```powershell
Copy-Item .env.example .env
```

Configure your provider in `.env`:
- **Default (Zero-Cost / Gemini):** Keep `LLM_PROVIDER=gemini` and provide your `GEMINI_API_KEY`.
- **OpenAI:** Set `LLM_PROVIDER=openai` and supply `OPENAI_API_KEY`.
- **Offline Demo Mode:** Keep `DEMO_MODE=true` to run completely offline without calling external LLM APIs.

### 2. Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

- API Server: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### 3. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

- Web Interface: `http://localhost:5173`

### 4. Docker Compose (Alternative)

```powershell
docker compose up --build
```

Access the application at `http://localhost:5173`. Persistent state and SQLite traces are stored in `./data`.

---

## 🩺 The 3-Layer Triad Knowledge Base

The clinical knowledge base is organized into three distinct evidence tiers catalogued in `data/corpus_manifest.csv`:

| Layer | Tier Name | Primary Sources | Clinical Scope |
| :---: | :--- | :--- | :--- |
| **Layer 1** | Foundational Knowledge | NCBI Bookshelf, StatPearls | Core pathophysiology, ILAE 2017 seizure classifications, Hoehn & Yahr progression staging, cellular mechanisms of action. |
| **Layer 2** | Clinical Guidelines | NICE NG217, NICE NG71 | Treatment algorithms, first-line monotherapies, sodium valproate safety protocols, specialist referral criteria. |
| **Layer 3** | Empirical Evidence | PubMed Central, Lancet, Cochrane | Head-to-head RCTs (e.g. SANAD II), systematic reviews, long-term neurostimulation (DBS) outcomes, adverse events. |

---

## 👤 Human-in-the-Loop Ingestion Pipeline

To extend the research corpus with new PubMed Central publications:

### Step 1: Candidate Discovery
Search and harvest open-access candidates matching high-precision clinical filters:
```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion discover --per-topic 30 --topics "Parkinson's disease,epilepsy"
```
This updates `data/corpus_candidates.csv` while preserving existing entries and creating an automatic backup.

### Step 2: Human Review & Manifest Promotion
Review candidates against inclusion/exclusion criteria, verify license compliance, and promote accepted candidates into `data/corpus_manifest.csv`:
```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion accept-candidates --candidates data/corpus_candidates.csv --manifest data/corpus_manifest.csv
```
*(Or use `--auto-accept` during discovery for immediate promotion).*

### Step 3: Fetch & Index XML Articles
Download full-text JATS XML and index chunks into ChromaDB:
```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion fetch --manifest data/corpus_manifest.csv
python -m app.ingestion index --manifest data/corpus_manifest.csv
```

---

## 📊 Comprehensive Evaluation & Benchmarking Suite

NeuroEvidence includes two primary, rigorous evaluation tracks designed for academic thesis defense:

### Track 1: End-to-End Clinical Benchmark (RAG vs. Baseline & LLM-as-a-Judge)

Evaluate the locked 37-question evaluation set (`data/evaluation_questions.csv` — 11 validation, 26 locked test) across both baseline LLM and grounded RAG modes:

```powershell
$env:PYTHONPATH = "backend"
# Run evaluation split
python -m app.evaluate --split validation

# Run with automated LLM-as-a-Judge review (evaluates Correctness, Hallucinations, Citation Precision, Abstention)
python -m app.evaluate --split validation --run-judge
```

To run the judge independently on existing trace files:
```powershell
python -m app.evaluate_judge --traces data/evaluation/results.jsonl --output-csv data/evaluation/judged_review.csv --judge-model gemini-2.5-pro
```

To compute non-parametric bootstrap 95% confidence intervals, formal abstention precision/recall, and paired significance statistics for dissertation reporting:
```powershell
python -m app.evaluate_metrics --judge-csv data/evaluation/judge_review.csv --traces data/evaluation/results.jsonl
```

### Track 2: Dual-Track Biomedical NLI Calibration

Validates the NLI verifier against external biomedical benchmarks (SciFact) and a domain-specific 120-pair neurology benchmark:

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate_nli --benchmark all --model pritamdeka/PubMedBERT-MNLI-MedNLI --min-confidence 0.55 --min-margin 0.10
```
Metrics and confusion matrices are saved to `data/evaluation/nli_benchmark_results.json`.

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Main query endpoint; supports `rag_verified` and plain `baseline` modes. |
| `GET` | `/api/sources/{source_id}` | Retrieves full metadata and excerpt for a specific cited source. |
| `POST` | `/api/feedback` | Records clinician thumbs up/down ratings and free-text critique into SQLite. |
| `GET` | `/api/evaluation/summary` | Aggregates recorded trace metrics, latency averages, and helpfulness rates. |
| `GET` | `/api/health` | Inspects backend status, LLM provider readiness, ChromaDB, and NLI model. |

---

## 🧪 Testing & Verification

Run the full automated test suite (81 tests covering cross-encoders, triad layers, HyDE, DDI, query decomposition, live PubMed, and Gemini integration):

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests
```

---

## ⚠️ Important Limitations

1. **Research Prototype:** NeuroEvidence is designed strictly for academic evaluation in health informatics; it does not replace the diagnosis, management, or clinical judgment of a licensed neurologist.
2. **NLI Verification Calibration:** The biomedical NLI model (`pritamdeka/PubMedBERT-MNLI-MedNLI`) provides probabilistic claim entailment scores to detect ungrounded statements, but should not be treated as absolute clinical truth.
3. **Evidence Score Semantics:** The composite evidence score reflects the proportion of claims supported by the retrieved literature; an answer with high support may still reflect limitations present in the underlying publications.
4. **API Key Security:** All API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) reside exclusively in the backend `.env` and are never exposed to client browsers.
