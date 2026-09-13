# NeuroEvidence

NeuroEvidence is a research MVP for a RAG-based neurology assistant with citation verification, claim-level hallucination checks, evidence scoring, safety routing, feedback, and evaluation traces. It is educational software, not a diagnostic or treatment system.

## What is included

- React + Tailwind chat interface and evaluation dashboard
- FastAPI endpoints for chat, sources, feedback, metrics, and health
- OpenAI Responses API generation and embedding adapters
- Persistent ChromaDB retrieval with deterministic ingestion
- SQLite experiment traces and feedback
- Crossref DOI metadata checks
- Optional CPU NLI using `cross-encoder/nli-deberta-v3-base`
- Zero-cost demo mode with a small clearly labelled bundled corpus
- PMC JATS XML ingestion tool and versioned corpus manifest template
- Backend tests, Dockerfiles, and Docker Compose

## Quick start

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

## Build the research corpus

1. Generate 30 recent PMC Open Access candidates per topic:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion discover
```

The generated `data/corpus_candidates.csv` deliberately marks every row `included=no`. Review relevance, article type, quality, retraction status, duplicates, and the exact licence with your supervisor. Copy accepted rows into `data/corpus_manifest.csv` and change only those rows to `included=yes`. This human gate prevents an automated search result from silently becoming the research ground truth.

2. Fill `data/corpus_manifest.csv` with the accepted PMC Open Access records whose licences you have checked.
3. Download and parse the approved PMC JATS XML service:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion fetch --manifest data/corpus_manifest.csv
```

4. Index the parsed documents:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingestion index --manifest data/corpus_manifest.csv
```

The ingestion command is idempotent: chunk identifiers are derived from the source, section, paragraph range, and preprocessing version.

## API overview

- `POST /api/chat` — run `baseline` or `rag_verified`
- `GET /api/sources/{source_id}` — inspect source metadata and excerpt
- `POST /api/feedback` — save user feedback
- `GET /api/evaluation/summary` — aggregate local research traces
- `GET /api/health` — dependency status

## Evaluation workflow

The evaluation template is in `data/evaluation_questions.csv`. Keep validation and final-test rows locked. Run the two modes with the same question set and model configuration, export traces from SQLite, blind the answers, and score them using the rubric in `docs/evaluation-protocol.md`.

With the API running, execute the validation split first:

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluate --split validation
```

After prompts and the evidence threshold are frozen, run `--split test`. The runner stores full JSONL traces and creates a separate CSV with mode labels removed for blinded review.

## Important limitations

- The bundled corpus is only a UI/demo fixture and must not be reported as the research corpus.
- The NLI checkpoint is general-domain and is an experimental signal, not a clinically validated verifier.
- The evidence score ranks evidence support; it is not the probability that an answer is medically correct.
- DOI existence is not the same as claim support. Metadata and NLI results are intentionally displayed separately.
- API keys must only be placed in the backend `.env`; never expose them through the frontend.
