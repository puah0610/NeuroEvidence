# CHAPTER 4: RESULTS AND DISCUSSION

## 4.1 Overview

This chapter evaluates NeuroEvidence against three research objectives: retrieval and evidence grounding, citation verification and hallucination mitigation, and system performance and observability. It combines implementation findings with quantitative evaluation of the end-to-end system and its natural language inference (NLI) component. The discussion distinguishes an implemented capability from an experimentally demonstrated improvement.

The available end-to-end results comprise 44 responses to 11 validation questions across four operating modes. Although the evaluation dataset also contains 26 locked test questions, results for that split are not present in the reviewed artifacts. Consequently, the findings in this chapter are preliminary validation findings rather than final held-out estimates. Separate NLI evaluations contain 120 pairs per benchmark. These component-level results do not, by themselves, demonstrate the clinical reliability of generated answers.

## 4.2 Experimental Setup

NeuroEvidence uses a Python backend with FastAPI, ChromaDB for evidence storage and retrieval, and a React interface. The dependency specification includes sentence-transformers for model-based processing and Langfuse for tracing. Dependency ranges describe the intended software environment; they are not an exact record of the installed versions used during evaluation. The archived evaluation files do not establish the original CPU, RAM, GPU, Python version, or complete package versions. These details require the original run environment record before final submission.

Table 4.1 describes the four modes using the model identifiers in the saved response traces. Two responses per mode were produced by the shared `safety-rules-v1` route rather than a language model.

**Table 4.1: Evaluated operating modes**

| Mode | Recorded generation model | Configuration and interpretation |
|---|---|---|
| `baseline` | `models/gemini-3.1-flash-lite` | Cloud generation without retrieval, with shared safety routing |
| `ollama_baseline` | `llama3.1:8b` | Local generation without retrieval, with shared safety routing |
| `ollama_rag` | `llama3.1:8b` | Local generation through the grounded pipeline |
| `rag_verified` | `models/gemini-3.1-flash-lite` | Cloud generation through the grounded and verified pipeline |

The current service implementation routes `ollama_rag` through verification and bounded revision as well as retrieval. Therefore, it should not be described as a clean retrieval-only ablation. Furthermore, comparing `ollama_rag` with `rag_verified` changes the generation model and deployment environment. Differences between these modes cannot be attributed exclusively to NLI verification. The archived traces do not contain a source revision identifier that would establish whether every current implementation detail was identical at evaluation time.

Correctness is scored from 0 to 2, representing an incorrect response, a partially correct response, and a correct, appropriately qualified response. The reported unsupported-claim rate is the proportion of responses containing at least one unsupported claim; it is not the proportion of individual claims that are unsupported. Mean unsupported-claim count is reported separately. Citation precision measures support among cited claims and is averaged across responses with available citation ratings. When no citation ratings exist, precision is undefined rather than zero. Citation existence measures whether a response includes citations.

Abstention precision, recall, and F1 are calculated from response-level abstention decisions. Latency is the recorded end-to-end response time in milliseconds. Estimated inference cost is taken from trace fields and must be distinguished from measured billing, electricity consumption, and hardware ownership costs. The aggregate summary provides percentile bootstrap confidence intervals based on 2,000 resamples. With only 11 questions, these intervals are exploratory; a zero-width interval for an all-zero or all-one sample does not establish certainty in the wider population.

The intended evaluation protocol combines automated checks, LLM-as-a-Judge scoring, and blinded human review. The available judge review identifies `models/gemini-3.1-flash-lite` as the evaluator, which is also the cloud generation model. This creates a possible evaluator-related bias. The blinded review file contains 44 response records, but none has a completed correctness rating. Thus, independent human assessment has been prepared but has not yet been demonstrated. No new model evaluation or test-suite execution was performed in preparing this chapter.

## 4.3 Data and Evaluation Query Profile

The evaluation suite contains 37 questions: 11 validation questions and 26 test questions. Table 4.2 summarizes the categories directly from the dataset.

**Table 4.2: Evaluation question distribution**

| Category | Validation | Test | Total |
|---|---:|---:|---:|
| Answerable | 6 | 15 | 21 |
| Unanswerable | 2 | 4 | 6 |
| Out of scope | 1 | 4 | 5 |
| Personal medical advice | 1 | 2 | 3 |
| Emergency | 1 | 1 | 2 |
| **Total** | **11** | **26** | **37** |

Across the full suite, 15 questions concern Parkinson's disease and 17 concern epilepsy; five are out-of-scope controls. The neurological subset is therefore 46.9% Parkinson's disease and 53.1% epilepsy, rather than exactly balanced. The six answerable validation questions are balanced at three per topic. Queries address symptoms, diagnostic concepts, treatment roles, impossible guarantees, scope boundaries, personal advice, and emergency presentations. The two emergency questions concern prolonged seizures, not acute stroke. Explicit DDI comparison prompts appear in a separate comparative evaluation script, but they are not part of this 37-question CSV.

The two NLI benchmark files each contain 120 claim–evidence pairs. The corresponding result records report 40 supported, 40 contradicted, and 40 insufficient pairs per benchmark. The local SciFact-labelled file should be described as the project's 120-pair evaluation set, not the complete original SciFact benchmark. Its extraction, transformation, and sampling provenance should be documented before making claims of direct comparability with published SciFact results. The neurology benchmark provides a domain-focused complement. Annotation independence and separation from development data remain relevant limitations.

## 4.4 Results and Discussion

### 4.4.1 Objective 1: Retrieval and Evidence Grounding Performance

The implemented retrieval architecture organizes foundational material, clinical guidelines, and empirical studies into three knowledge layers. Hybrid retrieval and cross-encoder reranking are intended to improve the evidence supplied to generation. However, implementation evidence alone cannot establish that reranking improves relevance or removes noise.

All evaluation questions have unpopulated `gold_source_ids` fields. Accordingly, the aggregate evaluation marks retrieval as unannotated and provides neither Recall@5 nor mean reciprocal rank. No measured layer-specific hit rate or controlled before-and-after reranking comparison is established by these artifacts. Objective 1 can therefore be assessed through citation availability and support, but direct retrieval effectiveness remains incompletely measured.

Verified RAG produced citations in 9 of 11 responses, giving a citation existence rate of 81.8% with a bootstrap 95% interval of 54.5–100%. Its mean citation precision across nine rated responses was 88.89%, with a 95% interval of 66.67–100%. The other modes had no recorded citations and no defined citation precision. This distinction matters: absence of citations demonstrates missing source attribution, not automatically incorrect content.

These findings support the system's ability to expose evidence for inspection. They do not demonstrate superior retrieval recall, and citation presence must not be treated as proof that an answer addresses the user's question.

### 4.4.2 Objective 2: Citation Verification and NLI Hallucination Mitigation

**Table 4.3: End-to-end validation results, 11 responses per mode**

| Mode | Mean correctness / 2 | Responses with unsupported claims | Mean unsupported claims | Citation precision | Abstention F1 |
|---|---:|---:|---:|---:|---:|
| Cloud baseline | 2.000 | 0.0% | 0.000 | N/A | 1.0000 |
| Local baseline | 1.909 | 9.1% | 0.091 | N/A | 0.8889 |
| Local grounded pipeline | 0.818 | 18.2% | 0.909 | N/A | 0.5333 |
| Verified RAG | 1.818 | 9.1% | 0.455 | 88.89% | 0.8889 |

Verified RAG did not improve correctness or unsupported-response rate relative to the cloud baseline in this sample. Its mean correctness was lower by 0.182 points, while its unsupported-response rate was higher by 9.1 percentage points. The saved paired correctness interval spans −0.545 to 0.000, and the unsupported-rate interval spans 0.000 to 0.273. These small-sample findings do not establish superiority. Compared with the local grounded mode, verified RAG had fewer responses containing unsupported claims, but this comparison also changes the generator and cannot isolate verification's contribution.

The local grounded mode also exhibited excessive abstention: its recorded confusion matrix contains six false-positive abstentions. This helps explain its low correctness and F1. More restrictive grounding can reduce usefulness if answerable questions are rejected. The correct interpretation is a trade-off requiring further analysis, rather than an assumption that adding retrieval must improve every model.

**Table 4.4: Recorded NLI benchmark performance**

| Benchmark | Model | Accuracy | Macro-F1 | Mean latency per pair (ms) |
|---|---|---:|---:|---:|
| SciFact-labelled set | Lexical baseline | 44.17% | 0.3465 | 0.02 |
| SciFact-labelled set | PubMedBERT-MNLI-MedNLI | 84.17% | 0.8417 | 63.81 |
| SciFact-labelled set | DeBERTa NLI | 75.83% | 0.7508 | 137.23 |
| Neurology set | Lexical baseline | 54.17% | 0.4515 | 0.03 |
| Neurology set | PubMedBERT-MNLI-MedNLI | 81.67% | 0.8096 | 63.87 |
| Neurology set | DeBERTa NLI | 90.83% | 0.9091 | 150.33 |

The neural benchmark records use minimum confidence 0.55 and minimum margin 0.10. PubMedBERT outperformed the lexical baseline on both sets and achieved the strongest SciFact-labelled result. DeBERTa achieved the strongest neurology result, at a higher recorded inference latency. Thus, biomedical specialization did not guarantee the best domain-set performance.

PubMedBERT's recall for insufficient evidence on the neurology set was 60.0%: it correctly classified 24 of 40 such pairs, while assigning seven to supported and nine to contradicted. Mistakenly treating insufficient evidence as support is particularly relevant to an evidence-grounding system. These errors show why a verification score cannot be interpreted as a guarantee of factual correctness.

Bounded revision is implemented as a limited regeneration-and-reverification step. However, the reviewed evaluation artifacts do not establish a paired pre/post revision experiment. The proposed change from 0.939 to 0.898 is therefore excluded from the quantitative findings. If these values refer to a higher-is-better evidence score, they indicate a decrease of 0.041, not an improvement. A defensible revision analysis needs the corresponding traces, metric definition, claim counts, and answer coverage before and after revision.

### 4.4.3 Objective 3: System Performance, Latency and Observability Telemetry

**Table 4.5: Recorded response latency**

| Mode | Mean latency (ms) | Median latency (ms) | Bootstrap 95% interval for mean (ms) |
|---|---:|---:|---|
| Cloud baseline | 5,346.6 | 5,217 | 3,214.6–8,078.4 |
| Local baseline | 29,363.8 | 34,048 | 20,309.8–37,701.4 |
| Local grounded pipeline | 84,778.5 | 97,288 | 59,268.7–106,098.8 |
| Verified RAG | 21,812.4 | 25,436 | 14,149.8–28,821.4 |

Medians were calculated directly from the 11 response traces for each mode; means and confidence intervals are from the aggregate summary. Each mode includes two shared safety-rule responses, so these values describe the mixed workload rather than generation-only latency. Verified RAG took approximately 4.08 times the cloud baseline's mean response time. The additional work is consistent with retrieval and verification overhead, but stage-level traces are required to allocate that overhead quantitatively.

All saved estimated-cost fields are zero. This is a recorded accounting result, not evidence that inference has no economic cost. The proposed dashboard figures of 7.57 seconds P50 and USD 0.0185 have not been reconciled with these evaluation traces and are not used as benchmark measurements here. A separate dashboard cohort would need its time window, model mix, request count, and cost definition reported explicitly.

Trace identifiers, model identifiers, tokens, latency, citations, and claim checks provide an inspectable record of system behavior. The service also contains tracing instrumentation for revision. This supports the implementation aspect of observability, while complete stage-level latency decomposition requires a corresponding telemetry export.

The saved validation emergency response uses the deterministic safety route and directs the user to emergency assistance. This represents one emergency prompt per mode, not a broad emergency benchmark. For verified RAG, overall abstention F1 is 0.8889 and the summary's overall routing/abstention accuracy is 90.91%. Neither value supports a claim of 100% acute-stroke routing performance. A separate stroke-specific evaluation would be needed for that claim.

### 4.4.4 Qualitative Clinical Case Studies: Parkinson's Disease and DDI Safety

The saved Parkinson's disease case `VAL-PD-03` asks about the role of levodopa. Its verified answer includes source markers linked to its treatment discussion. As a qualitative interface example, this case can illustrate how a reader moves from a generated statement to supporting evidence. The case demonstrates the presentation of provenance; independent review is still needed to establish whether every cited passage supports its associated statement.

A contrasting failure is `VAL-OOS-01`, which asks about cardiac output in chronic heart failure. The judge records that verified RAG instead discussed epilepsy and failed to address the question. This case shows that an evidence-backed answer may still be irrelevant. Scope recognition, question coverage, and citation support must therefore be evaluated separately.

The implementation also includes a DDI rule engine and a separate comparative script containing a valproate–lamotrigine interaction question. However, the reviewed end-to-end results contain no corresponding completed DDI case. A DDI interface example should therefore be labelled as an implementation demonstration until its response, detected interaction, evidence, and review are archived. The proposed Figure 3.5 screenshots were not available among the reviewed project files, so their contents and numbering are not asserted here.

## 4.5 Comparison with Existing Studies

Lewis et al. introduced RAG as a combination of parametric generation and non-parametric retrieved memory. NeuroEvidence follows this general approach and adds domain-organized evidence and explicit post-generation checks. The comparison is architectural: the original RAG paper does not establish a universal 15–30% unsupported-claim rate for modern RAG implementations. Such a percentage should not be used without a directly applicable study and matching metric definition. [Lewis et al., 2020](https://arxiv.org/abs/2005.11401).

Med-PaLM 2 investigates medical question answering with domain adaptation and extensive evaluation. Its published work also describes retrieval-based grounding, so it would be inaccurate to characterize cloud medical systems collectively as incapable of source-grounded answers. NeuroEvidence emphasizes inspectable evidence and optional local generation, but its 11-question validation results are not directly comparable with Med-PaLM 2's published benchmarks. [Singhal et al., 2025](https://www.nature.com/articles/s41591-024-03423-7).

BioGPT is a biomedical generative language model rather than a synonym for a proprietary cloud medical service. Its research concerns biomedical text generation and mining, whereas NeuroEvidence evaluates an application pipeline combining retrieval, verification, and safety routing. These are different levels of contribution and should not be ranked using unmatched evaluation scores. [Luo et al., 2022](https://arxiv.org/abs/2210.10341).

NeuroEvidence's contribution is the integration of three-layer evidence organization, citation checking, NLI verification, bounded revision, and traceable interaction within a neurological research prototype. The available evidence supports describing this as a system integration contribution; it does not establish that the combination is unprecedented. Ollama provides a local generation option, but fully local operation additionally depends on embedding configuration and disabling or controlling external retrieval and telemetry. The evaluated `rag_verified` mode used cloud generation and should not be presented as a fully local experiment.

## 4.6 Chapter Summary

The validation results demonstrate evidence presentation, measurable NLI behavior, and inspectable response telemetry. Verified RAG achieved mean citation precision of 88.89% across nine rated responses, while PubMedBERT achieved accuracies of 84.17% and 81.67% on the two 120-pair benchmark sets. These findings support parts of the intended functionality.

The evidence does not establish that all three objectives have been fully validated. Retrieval effectiveness lacks gold-source annotations; verified RAG did not outperform the cloud baseline on correctness or unsupported-response rate; and independent blinded review remains incomplete. Its mean latency was 21.81 seconds, with a median of 25.44 seconds in the saved validation workload. Final conclusions require held-out test results, completed human review, controlled component comparisons, and a reproducible environment and telemetry record.

---

### Evidence record for thesis preparation

This draft was prepared from the following project artifacts without modifying evaluation data:

- `data/evaluation_questions.csv`: question categories, topic counts, and split membership.
- `data/evaluation/results.jsonl`: 44 validation responses, recorded models, safety routes, and calculated latency medians.
- `data/evaluation/judge_review.csv` and `judge_summary.json`: automated ratings and evaluator identity.
- `data/evaluation/comprehensive_evaluation_summary.json`: aggregate metrics and bootstrap intervals.
- `data/evaluation/blinded_review.csv`: 44 unscored review records.
- `data/evaluation/nli_benchmark_results.json` and `data/benchmarks/`: NLI results and local benchmark composition.
- `backend/app/service.py`, `evaluate.py`, and `evaluate_comparative.py`: pipeline behavior, trace export, and separate comparative experiment definition.
- `backend/requirements.txt` and `docs/evaluation-protocol.md`: declared dependencies and intended evaluation protocol.

The evidence record is an editorial aid and can be moved to an appendix. Hardware details, figures, original benchmark provenance, and final-test results should be added only when their supporting records are available.
