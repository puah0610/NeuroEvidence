# NeuroEvidence

NeuroEvidence is a research MVP for a RAG-based neurology assistant with citation verification, claim-level hallucination checks, evidence scoring, safety routing, feedback, and evaluation traces. It is educational software, not a diagnostic or treatment system.

## What is included

- **Curated 3-Layer Triad Knowledge Base**: Pre-loaded clinical knowledge base covering Parkinson's disease and epilepsy across three evidence tiers (NCBI Bookshelf, NICE Guidelines, Lancet/Cochrane RCTs & Meta-analyses)
- **Hybrid Dense + Sparse Retrieval**: Combines BM25 lexical matching with dense semantic embeddings using Reciprocal Rank Fusion (RRF)
- **React + Tailwind Chat Interface**: Interactive clinical query interface with color-coded layer badges, source inspection drawers, and evaluation dashboards
- **FastAPI Backend Endpoints**: Full API for chat, sources, feedback, metrics, and health checks
- **OpenAI Responses API & ChromaDB**: Modern generation and embedding adapters with persistent vector retrieval
- **Zero-Cost Local Demo Mode**: Instant out-of-the-box local operation with no API key or GPU required
- **Biomedical NLI Verification**: Fine-grained claim entailment verification powered by `pritamdeka/PubMedBERT-MNLI-MedNLI`
- **ASReview Active-Learning Pipeline**: Built-in candidate export (`export-asreview`) and synchronization (`sync-asreview`) for machine-assisted literature screening
- **Dual-Track NLI Benchmark Suite**: External baseline validation against SciFact (Track 1) and a 120-pair neurology domain benchmark (Track 2)
- **Traceability & Safety**: Guardrail classifiers, SQLite experiment traces, Crossref DOI verification, backend unit tests, and Docker Compose

## Quick start

> [!NOTE]
> The application comes **pre-configured with the curated 3-Layer Triad Knowledge Base**. You do **not** need to harvest or build a research corpus to run the application.

### 1. Configure

Copy `.env.example` to `.env`. Leave `DEMO_MODE=true` for the no-cost demonstration. For the research pipeline, set `DEMO_MODE=false`, add `OPENAI_API_KEY`, and set `ENABLE_NLI=true` before the locked evaluation. Keep NLI disabled only while doing lightweight UI and retrieval development.

### 2. Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

The API will be available at `http://localhost:8000`; interactive documentation is at `/docs`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Docker

```powershell
docker compose up --build
```

Open `http://localhost:5173`. Persistent application data is stored in `./data`.

## Curated 3-Layer Triad Knowledge Base

The system ships with a structured, pre-curated **3-Layer Triad Knowledge Base** (see [docs/architecture.md](docs/architecture.md) for full architectural details) catalogued in `data/corpus_manifest.csv`:

1. 🟦 **Layer 1: Foundational Knowledge** (NCBI Bookshelf / StatPearls)
   - *Epilepsy*: 2017 ILAE seizure classification, seizure semiology and cortical pathophysiology, cellular mechanisms of antiseizure medications.
   - *Parkinson's Disease*: Substantia nigra dopaminergic neurodegeneration and alpha-synuclein pathology, Hoehn & Yahr clinical progression staging, core dopaminergic pharmacology.
2. 🟩 **Layer 2: Clinical Guidelines & Consensus** (NICE Guidelines)
   - *NICE NG217 (Epilepsies)*: Referral pathways, first-line monotherapy algorithms (focal vs generalized), sodium valproate safety and the Pregnancy Prevention Programme (Prevent).
   - *NICE NG71 (Parkinson's in Adults)*: Specialist clinical diagnostic criteria (UK Brain Bank), quality-of-life stratified pharmacotherapy, motor fluctuation protocols, and advanced therapies.
3. 🟪 **Layer 3: Empirical Evidence & Trials** (PubMed Central / Cochrane Systematic Reviews)
   - *Comparative RCTs*: SANAD II trial arms in *The Lancet* (levetiracetam vs sodium valproate in generalized epilepsy; levetiracetam vs lamotrigine in focal epilepsy).
   - *Meta-Analyses*: Long-term deep brain stimulation (STN vs GPi) efficacy reviews, adjuvant MAO-B vs COMT inhibitor meta-analyses in levodopa-treated patients.

All chunks are pre-indexed and available immediately for both hybrid demo retrieval and ChromaDB indexing.

---

### (Optional) Corpus Extension & Active-Learning Pipeline

If you wish to discover, screen, or index **additional** literature beyond the curated Triad knowledge base, use the built-in ingestion and active-learning toolchain:

#### 1. Candidate Discovery
Generate recent PMC Open Access candidates (defaults to Parkinson's disease and epilepsy, avoiding duplicates and preserving existing candidates):
```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion discover --per-topic 30
```
This updates `data/corpus_candidates.csv` (and creates a safety backup `.bak.csv`). You can customize topics using `--topics "Parkinson's disease,epilepsy"` (or `--topics all`), or pass `--overwrite` if you want a clean reset.

#### 2. Active-Learning Screening with ASReview LAB
To screen large batches of literature rapidly without manual review fatigue:
1. Export candidates into an ASReview screening pool (retrieves abstracts via PubMed E-utilities):
   ```powershell
   $env:PYTHONPATH = "backend"
   python -m app.ingestion export-asreview --candidates data/corpus_candidates.csv --asreview-pool data/asreview_corpus_pool.csv
   ```
2. Screen in ASReview LAB (see protocol in [docs/asreview-workflow.md](docs/asreview-workflow.md)) and export decisions to `data/asreview_export.csv`.
3. Synchronize screened papers directly back into `data/corpus_manifest.csv`:
   ```powershell
   $env:PYTHONPATH = "backend"
   python -m app.ingestion sync-asreview --asreview-file data/asreview_export.csv --manifest data/corpus_manifest.csv --candidates data/corpus_candidates.csv
   ```

#### 3. Fetch & Index New PMC Articles
Download and parse JATS XML from PMC Open Access, then index into ChromaDB:
```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion fetch --manifest data/corpus_manifest.csv
python -m app.ingestion index --manifest data/corpus_manifest.csv
```

---

## API overview

- `POST /api/chat` — run `baseline` or `rag_verified`
- `GET /api/sources/{source_id}` — inspect source metadata and excerpt
- `POST /api/feedback` — save user feedback
- `GET /api/evaluation/summary` — aggregate local research traces
- `GET /api/health` — dependency status

## Evaluation workflow

### 1. End-to-end RAG vs baseline evaluation

The evaluation template is in `data/evaluation_questions.csv`. Keep validation and final-test rows locked. Run the two modes with the same question set and model configuration (deterministic `temperature=0.0`), export traces from SQLite, blind the answers, and score them using the rubric in `docs/evaluation-protocol.md`.

With the API running, execute the validation split:

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate --split validation
```

To run end-to-end evaluation with automated **LLM-as-a-Judge** scoring (uses **`gemini-2.5-pro`** by default to evaluate Correctness, Hallucinations, Citation Precision, and Abstention):

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate --split validation --run-judge
```

Or run the judge independently on any previously generated trace file, optionally overriding the model:

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate_judge --traces data/evaluation/results.jsonl --output-csv data/evaluation/judged_review.csv --judge-model gemini-2.5-pro
```

After prompts and the evidence threshold are frozen, run `--split test`. The runner stores full JSONL traces, creates a separate CSV with mode labels removed for blinded review, and outputs comparative statistics.

### 2. Dual-track biomedical NLI benchmarking

Evaluate the NLI verifier against the external SciFact biomedical benchmark (Track 1) and the 120-pair Parkinson's and epilepsy domain benchmark (Track 2):

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate_nli --benchmark all --model pritamdeka/PubMedBERT-MNLI-MedNLI --compare-lexical
```

You can also test custom confidence and margin calibration thresholds:

```powershell
python -m app.evaluate_nli --benchmark all --model pritamdeka/PubMedBERT-MNLI-MedNLI --min-confidence 0.55 --min-margin 0.10
```

Results, per-class F1, and confusion matrices are saved to `data/evaluation/nli_benchmark_results.json`.
For solo researcher academic defense guidelines and intra-annotator reliability ($\kappa$), see [docs/annotation-protocol.md](docs/annotation-protocol.md).

## Important limitations

- The curated corpus and assistant are designed strictly for educational and health informatics research; they do not constitute a diagnostic system or clinical decision-support medical device.
- The NLI checkpoint (`pritamdeka/PubMedBERT-MNLI-MedNLI`) is an experimental research grounding model, not a clinically validated diagnostic system.
- The evidence score ranks evidence support; it is not the probability that an answer is medically correct.
- DOI existence is not the same as claim support. Metadata and NLI results are intentionally displayed separately.
- API keys must only be placed in the backend `.env`; never expose them through the frontend.
