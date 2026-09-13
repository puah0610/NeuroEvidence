# NeuroEvidence MVP implementation

The project has been implemented in the workspace root. It includes the FastAPI backend, React/Tailwind frontend, demo corpus, Chroma/OpenAI/NLI research path, PMC ingestion, SQLite traces, safety routing, citation and claim verification, a local dashboard, Docker configuration, automated tests, and a locked 60-question evaluation file.

## Start without API charges

1. Install Python 3.12, Node.js 20 or newer, and optionally Docker Desktop.
2. Copy `.env.example` to `.env`; keep `DEMO_MODE=true`.
3. Follow the backend and frontend commands in `README.md`.
4. Open `http://localhost:5173`.

## Move to the research configuration

1. Generate corpus candidates with `python -m app.ingestion discover` as documented in the README.
2. Review every candidate with your supervisor. Only accepted, licence-checked rows belong in the final manifest.
3. Fetch and index the accepted corpus.
4. Set `DEMO_MODE=false`, supply the server-side OpenAI key, and set `ENABLE_NLI=true`.
5. Tune only on the 15 validation questions.
6. Freeze prompts and the evidence threshold before running the 45 final-test questions.

## Verification status

Static consistency checks passed: the project contains 60 evaluation questions with the intended 15/45 split, configuration JSON parses, there are no empty source files, and the implementation structure is complete. Runtime tests could not be executed in the current workspace because Python, Node.js, Docker, and Git are not installed or available on PATH.

