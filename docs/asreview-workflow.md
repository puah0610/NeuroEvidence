# ASReview Active Learning Screening Workflow

This document provides the end-to-end protocol for using **ASReview LAB** to accelerate literature screening for the NeuroEvidence research corpus.

---

## 1. Overview and Motivation

In evidence-based medicine and health informatics, screening hundreds of candidate publications manually is time-intensive. **ASReview LAB** is an open-source active learning tool developed by Utrecht University that re-ranks unlabelled literature based on machine learning (e.g., Naive Bayes or TF-IDF priors), allowing researchers to identify relevant articles significantly faster while minimizing bias.

In NeuroEvidence, ASReview is positioned between **Candidate Discovery** and **Corpus Indexing**:

```mermaid
flowchart LR
    PMC[PubMed Central Candidates] --> DISCOVER[ingestion discover]
    DISCOVER --> EXPORT[ingestion export-asreview]
    EXPORT --> ASREVIEW[ASReview LAB Screening]
    ASREVIEW --> SYNC[ingestion sync-asreview]
    SYNC --> FETCH[ingestion fetch & index]
    FETCH --> CHROMA[(Chroma Vector DB)]
```

---

## 2. Step-by-Step Protocol

### Step 2.1: Discover PMC Candidates
Run candidate discovery across the four target neurology topics (Parkinson's disease, epilepsy, stroke, multiple sclerosis):

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.ingestion discover --per-topic 30
```
This generates `data/corpus_candidates.csv` with 120 candidate papers marked `included=no`.

---

### Step 2.2: Export to ASReview Candidate Pool
Export candidates into an ASReview-optimized CSV containing `title`, `abstract`, `doi`, `topic`, `authors`, and `url`:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.ingestion export-asreview `
  --candidates data/corpus_candidates.csv `
  --asreview-pool data/asreview_corpus_pool.csv
```

*The exporter automatically queries PubMed E-utilities to retrieve abstracts for all records with PMIDs.*

---

### Step 2.3: Install and Launch ASReview LAB
Install ASReview in your environment and launch the browser interface:

```powershell
.\.venv-new\Scripts\pip.exe install asreview
asreview lab
```

Your default web browser will open `http://localhost:5000`.

---

### Step 2.4: Configure the Screening Project in ASReview
1. Click **Create Project** $\to$ Select **Oracle** (Interactive screening).
2. **Dataset:** Upload `data/asreview_corpus_pool.csv`.
3. **Prior Knowledge (Warm-up):**
   * Select **1 Relevant article** (e.g., a high-quality clinical review on Parkinson's motor symptoms or epilepsy classification).
   * Select **1 Irrelevant article** (e.g., a pediatric animal model study or out-of-scope surgical technique).
4. **Model Selection:**
   * Feature extractor: **TF-IDF** (recommended for clinical abstracts)
   * Classifier: **Naive Bayes** or **Logistic Regression**
   * Query strategy: **Max** (certainty-based active learning)
5. Click **Finish** and start screening.

---

### Step 2.5: Active Screening & Stopping Rule
* For each presented paper, review the title and abstract.
* Click **Relevant** (to include in the research corpus) or **Irrelevant** (to exclude).
* **Stopping Rule:** In systematic review literature, screening can stop after **20–30 consecutive irrelevant records** appear, indicating that the vast majority of relevant papers in the pool have been identified.

---

### Step 2.6: Export Decisions from ASReview
1. In ASReview LAB, navigate to the project dashboard.
2. Click **Export Data** $\to$ choose **CSV format**.
3. Save the exported file as `data/asreview_export.csv`.

---

### Step 2.7: Synchronize Decisions into NeuroEvidence Manifest
Run the automated synchronization command to update `data/corpus_manifest.csv`:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.ingestion sync-asreview `
  --asreview-file data/asreview_export.csv `
  --manifest data/corpus_manifest.csv `
  --candidates data/corpus_candidates.csv
```

The script identifies all records marked `included=1` and registers them in `data/corpus_manifest.csv` with `included=yes`.

---

### Step 2.8: Fetch and Index the Verified Corpus
Download the full JATS XML files and index them into ChromaDB:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.ingestion fetch --manifest data/corpus_manifest.csv
.\.venv\Scripts\python.exe -m app.ingestion index --manifest data/corpus_manifest.csv
```

---

## 3. Academic Defense: Thesis Methodology Text

In your FYP dissertation or project report, you can describe this process in the Methodology section as follows:

> *"To establish the domain-specific research corpus while controlling for selection bias and time constraints, an active-learning systematic screening pipeline was implemented using ASReview LAB v1.x. A candidate pool of 120 open-access peer-reviewed neurology papers was retrieved from PubMed Central. Screening was conducted with a TF-IDF feature extractor and Naive Bayes prior model. Screening concluded after reaching a stopping criterion of 25 consecutive irrelevant candidates. Selected publications were synchronized into the immutable corpus manifest and parsed via JATS XML into deterministic chunks for dense retrieval."*
