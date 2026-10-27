# Evidence-Verification Annotation Protocol & Solo Research Defense

This document specifies the formal guidelines for the **120-pair Neurology Evidence-Verification Benchmark** and provides the academic defense protocol for solo-annotated Final Year Projects.

---

## 1. Task Formulation

The evidence verification task evaluates whether an indexed literature excerpt ($E$) provides sufficient factual basis to validate a declarative neurological claim ($C$).

Following the Natural Language Inference (NLI) paradigm adapted for biomedical claims (FEVER / SciFact / MedNLI), each claim–evidence pair $(E, C)$ is mapped to one of three mutually exclusive classes:

$$\mathcal{Y} = \{\text{supported}, \text{contradicted}, \text{insufficient}\}$$

---

## 2. Classification Criteria

### 2.1 Label: `supported` (Entailment)
A claim is labeled **`supported`** if a medical reader can reasonably infer the truth of the claim solely from the evidence text without making speculative assumptions.
* **Direct Entailment:** The core clinical entities, pharmacological actions, and direction of causality in the claim are explicitly stated in the excerpt.
* **Lexical Variation:** Synonyms and standardized medical terminology are acceptable (e.g., *"slow movement"* $\equiv$ *"bradykinesia"*, *"substantia nigra cell death"* $\equiv$ *"dopaminergic neurodegeneration"*).
* **Threshold of Support:** The passage must support the *entire* claim, not merely an isolated fragment.

### 2.2 Label: `contradicted` (Contradiction / Refutation)
A claim is labeled **`contradicted`** if information in the evidence text directly conflicts with, refutes, or invalidates the assertion in the claim.
* **Polarity Negation:** The claim asserts an effect that the evidence explicitly negates (e.g., Claim: *"Levodopa accelerates neurodegeneration"*; Evidence: *"Levodopa does not accelerate disease progression"*).
* **Clinical Inversion:** Therapeutic indication is inverted to a contraindication, or a protective factor is framed as a risk factor.
* **Entity Swapping:** Swapping anatomical locations (e.g., cerebral cortex vs. cerebellum), electrophysiological signatures (e.g., 3 Hz spike-wave vs. 10 Hz spikes), or medication classes (e.g., dopamine agonist vs. neuroleptic).

### 2.3 Label: `insufficient` (Neutral / Not Enough Info)
A claim is labeled **`insufficient`** if the evidence snippet does not contain sufficient facts to determine whether the claim is true or false.
* **Unmentioned Neurological Fact:** The claim is clinically true in general neurology (e.g., *"Pramipexole has high D3 receptor affinity"*), but the provided excerpt discusses only diagnostic criteria and makes no mention of receptor affinities.
* **Under-specified Evidence:** The evidence mentions the general topic (e.g., *"constipation occurs in Parkinson's disease"*), but the claim asserts a specific unproven mechanism or diagnostic test (e.g., *"gastric breath tests diagnose Parkinson's"*).
* **Cross-Topic Distractor:** An accurate statement regarding a different condition (e.g., an epilepsy statement paired with a stroke excerpt).

---

## 3. Perturbation Taxonomy

To eliminate subjective ambiguity in ground truth labels, candidate claims are generated using explicit perturbation mechanisms:

| Label | Perturbation Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `supported` | `direct_entailment` | Preserves semantic truth of snippet | Excerpt states bradykinesia is required $\to$ Claim: Bradykinesia is a mandatory feature. |
| `contradicted` | `clinical_inversion` | Inverts clinical outcome or safety profile | Excerpt states DBS reduces medication need $\to$ Claim: DBS increases daily medication need. |
| `contradicted` | `entity_swap` | Replaces biological entity or frequency | Excerpt specifies 4–6 Hz rest tremor $\to$ Claim specifies 10–12 Hz action tremor. |
| `contradicted` | `polarity_negation` | Explicit linguistic negation of statement | Excerpt confirms loss of putaminal dopamine $\to$ Claim asserts putaminal dopamine increases. |
| `insufficient` | `unmentioned_phenotype` | Clinically plausible detail not in snippet | Pairing a general Parkinson excerpt with specific MRI iron accumulation cutoffs. |
| `insufficient` | `out_of_scope_distractor` | Valid external fact paired out-of-context | Pairing an ILAE definition with PNES video-EEG diagnostic criteria. |

---

## 4. Academic Defense Protocol for Solo Annotation

When institutional review board (IRB) or clinical co-annotators are unavailable for an undergraduate/master's FYP, the following three-part methodology guarantees peer-review standard rigor:

### 4.1 Dual-Track Evaluation Strategy
Rather than relying solely on self-annotated data, the evaluation uses two complementary tracks:
1. **Track 1 (Public External Ground Truth — SciFact):**
   * 120 claim–evidence pairs curated from AllenAI's peer-reviewed SciFact biomedical dataset.
   * Because this benchmark is internationally validated, examiners cannot dispute the ground truth.
2. **Track 2 (Domain Application Benchmark — Neurology 120):**
   * 120 domain-specific pairs focused on Parkinson's disease and epilepsy.
   * Demonstrates applied effectiveness on the actual project scope.

### 4.2 Intra-Annotator Reliability Study (Test–Retest Protocol)
To prove annotation consistency over time:
1. **25% Sample Reservation:** 30 pairs (10 supported, 10 contradicted, 10 insufficient) are marked with `washout_sample=yes` in `data/benchmarks/neurology_nli_120.csv`.
2. **Two-Week Washout Period:** After initial dataset creation, the researcher waits a minimum of 14 days without viewing the benchmark.
3. **Blinded Re-Annotation:** The 30 pairs are stripped of labels, randomized, and re-annotated from scratch.
4. **Cohen's Kappa ($\kappa$) Calculation:**
   Intra-rater agreement is computed as:
   $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
   where $p_o$ is the observed percentage agreement and $p_e$ is the expected chance agreement across the 3 classes.
   * **Target:** $\kappa \ge 0.75$ indicates substantial to near-perfect internal consistency under Landis & Koch (1977) criteria.

### 4.3 Dissertation Defense Framing

> [!NOTE]
> **Dissertation Template Notice:** The value $\kappa = 0.83$ in the excerpt below is an illustrative example of defense phrasing. In your dissertation, replace `\kappa = 0.83` with your empirical test–retest calculated kappa (if the 14-day washout study is executed), or frame Section 4.2 as a pre-specified quality assurance protocol if unmeasured.

Suggested text for your FYP methodology chapter:

> *"Due to medical resource constraints, domain dataset curation followed a single-rater protocol with strict operational guidelines (Appendix B). To mitigate subjective bias, a dual-track validation methodology was adopted: (1) an established external biomedical benchmark (SciFact, $N=120$) provided an objective baseline, and (2) an intra-annotator reliability study across a 25% blinded sample ($N=30$) after a two-week washout period confirmed substantial internal annotation stability ($\kappa = 0.83$)."*

