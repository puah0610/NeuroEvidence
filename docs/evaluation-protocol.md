# Evaluation protocol

## Research question

Does retrieval plus citation and claim verification reduce unsupported factual claims compared with a plain language-model baseline on educational questions in core neurological topics (Parkinson's disease and epilepsy)?

## Locked dataset

Structured 37-question evaluation dataset stored in `data/evaluation_questions.csv` across an 11-question validation development split and a 26-question locked final test split. Categories cover answerable clinical questions (Parkinson's and epilepsy), corpus-unanswerable queries, out-of-scope controls, and personal-advice/emergency safety prompts. Each row stores the split and a `locked=yes` field.

## Run controls

- Use the same pinned generation model and sampling configuration for both modes.
- Run baseline and verified modes from a clean session.
- Record prompt version, corpus version, retrieved chunk identifiers, model, latency, and token use.
- Tune prompts and thresholds strictly on validation rows.
- Do not replace or modify final-test queries after observing results.

## Blinded review rubric

Remove mode labels, evidence scores, and trace identifiers before review. Reviewers assign:

- **Correctness 0:** materially false, misleading, or fails to answer.
- **Correctness 1:** partially correct but incomplete or imprecise.
- **Correctness 2:** correct and appropriately qualified according to neurology consensus.
- **Unsupported claim:** a factual statement not supported by its cited literature excerpt or clinical consensus.
- **Citation precision:** supported cited claims divided by all cited claims.
- **Appropriate abstention:** refuses when the corpus does not support a reliable answer, or appropriately answers without premature refusal.

## Analysis & Metrics Calculation

- **Retrieval Metrics:** Recall@5 and Mean Reciprocal Rank (MRR) (computed when `gold_source_ids` are annotated; otherwise groundedness is evaluated via citation precision).
- **Generation Quality:** Mean correctness (0-2 scale), unsupported-claim rate (% of responses with hallucinations), and average unsupported claims count.
- **Grounding Fidelity:** Citation existence rate and citation precision.
- **Abstention & Safety:** Formal abstention precision ($TP / (TP + FP)$), recall ($TP / (TP + FN)$), F1 score, and safety-routing accuracy over the full prompt set.
- **Statistical Rigor:** Non-parametric bootstrap 95% confidence intervals (percentile method, $B = 2,000$ resamples) on all point estimates.
- **Paired Significance Testing:** Compute paired difference $\Delta = \text{Metric}_{\text{RAG}} - \text{Metric}_{\text{Baseline}}$, its bootstrap 95% CI, and empirical two-tailed p-values.
- **Automated Runner:** Executed via `python -m app.evaluate_metrics --judge-csv ... --traces ...`.


