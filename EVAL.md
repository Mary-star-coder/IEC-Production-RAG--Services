# RAG Evaluation

## 1. Evaluation Dataset

The evaluation dataset contains 25 questions:

- 20 answerable questions
- 5 unanswerable questions

The dataset is stored in `app/evaluation/golden_dataset.json`.

The existing threshold experiment values are historical results from the
Sentence Transformer implementation. They do not measure the current Gemini
embedding model and should be re-run before tuning the deployed threshold.

Five answerable questions (Q1–Q5) have manually verified relevant chunk IDs. These questions are used for retrieval ranking evaluation.

## 2. Evaluation Method

The system retrieves the top 5 chunks using Gemini embeddings and Qdrant.

A similarity threshold determines whether the system abstains:

- Similarity below threshold: abstain
- Similarity at or above threshold: accept retrieved context

The current configured similarity threshold is 0.30.

Evaluation includes:

- Threshold-based abstention experiments.
- Chunking configuration comparison.
- Hit Rate@5.
- Recall@5.
- Mean Reciprocal Rank (MRR).
- Average retrieval latency.

## 3. Threshold Experiments

Two experiments were performed using the same dataset and `top_k = 5`.

| Metric | Threshold 0.30 | Threshold 0.20 |
|---|---:|---:|
| Total questions | 25 | 25 |
| Answerable questions | 20 | 20 |
| Unanswerable questions | 5 | 5 |
| Total abstentions | 6 | 2 |
| Answerable questions rejected | 1 | 0 |
| Unanswerable questions rejected | 5 | 2 |
| Unanswerable questions incorrectly accepted | 0 | 3 |

Results are stored in:

- `app/evaluation/evaluation_results_030.json`
- `app/evaluation/evaluation_results_020.json`

### Threshold Analysis

At threshold 0.30, the system abstained on all five designated unanswerable questions but also rejected one answerable question.

At threshold 0.20, the system accepted all answerable questions but also accepted three designated unanswerable questions.

This demonstrates the trade-off between answer coverage and safe abstention.

## 4. Retrieval Ranking Metrics

Retrieval ranking metrics were calculated using the five manually verified questions (Q1–Q5) with the existing 800/150 chunk configuration.

| Metric | Result |
|---|---:|
| Verified questions | 5 |
| Hit Rate@5 | 1.000 (100%) |
| Recall@5 | 1.000 (100%) |
| Mean Reciprocal Rank (MRR) | 0.667 (66.7%) |

### Metric Interpretation

- **Hit Rate@5:** All five evaluated questions retrieved at least one relevant chunk in the top five results.
- **Recall@5:** All manually identified relevant chunks for these five questions were retrieved in the top five.
- **MRR:** The average reciprocal rank of the first relevant result was approximately 0.667.

These results apply only to the five-question manually verified subset. They should not be interpreted as performance across the complete dataset.

## 5. Chunking Configuration Comparison

Two chunking configurations were evaluated using the same source PDF (`main_notes.pdf`) and the same 25 golden questions.

The recorded configurations used:

- Sentence Transformer embeddings.
- Qdrant cosine-similarity retrieval.
- Top 5 retrieved results.
- Similarity threshold of 0.30.

| Setting / Metric | Config A | Config B |
|---|---:|---:|
| Chunk size | 800 | 500 |
| Chunk overlap | 150 | 100 |
| Total chunks | 863 | 1,313 |
| Hit Rate@5 | 100% | 100% |
| Recall@5 | 100% | 90% |
| MRR | 0.6667 | 0.7067 |
| Average retrieval latency | 0.0208 sec | 0.1265 sec |

### Configuration Analysis

**Config A: 800 characters, 150 overlap**

- Produced 863 chunks.
- Achieved 100% Hit Rate@5 and 100% Recall@5 on the verified subset.
- Recorded an average retrieval latency of 0.0208 seconds in this run.
- Uses fewer chunks than Config B.

**Config B: 500 characters, 100 overlap**

- Produced 1,313 chunks.
- Achieved 100% Hit Rate@5.
- Recall@5 was 90% on the verified subset.
- MRR was approximately 0.707.
- Recorded an average retrieval latency of 0.1265 seconds in this run.

### Relevance Mapping and Limitations

The original manually verified relevant chunk IDs belong to the existing 800/150 configuration.

For the comparison, these original chunk IDs were mapped to their source page numbers. Retrieved chunks from both configurations were then evaluated using page-level relevance.

Therefore, the comparison uses a page-level relevance proxy rather than independently verified exact chunk IDs for each configuration.

Only five questions have manually verified relevance labels. The comparison is useful as an initial experiment but is not a complete retrieval benchmark.

Latency values are from a single experiment run and may vary with hardware, model warm-up, and system load. Repeated runs are needed for a more reliable latency comparison.

The reported experiment values predate the Gemini migration and do not
characterize Gemini embedding quality or latency. Re-run the evaluation with a
configured Gemini API key and a Qdrant collection populated with the current
3072-dimensional Gemini vectors before drawing conclusions about the current
retrieval stack.

### Configuration Decision

Config A (800/150) is retained as the current default configuration.

It achieved 100% Recall@5 on the verified subset and had lower measured latency in this experiment. Config B achieved a slightly higher MRR, but lower Recall@5.

This is a provisional engineering choice based on the current limited evaluation, not proof that Config A is universally better.

Results are stored in:

`app/evaluation/chunking_comparison_results.json`

The comparison is implemented in:

`app/evaluation/run_evaluation.py`

## 6. Evaluation Scripts and Results

The evaluation scripts and generated results are stored in `app/evaluation/`.

Important files:

- `golden_dataset.json` — evaluation questions and manually verified relevance labels.
- `run_evaluation.py` — chunking configuration comparison.
- `evaluation_results.json` — baseline retrieval evaluation.
- `evaluation_results_020.json` — threshold 0.20 results.
- `evaluation_results_030.json` — threshold 0.30 results.
- `chunking_comparison_results.json` — chunking comparison results.

## 7. Limitations

- Threshold experiments measure retrieval and threshold-based abstention, not generated-answer correctness.
- The unanswerable labels are based on the intended dataset and should be checked against the uploaded corpus.
- Retrieval ranking metrics are currently calculated for only five manually verified questions.
- The remaining answerable questions need manually verified relevant chunk IDs before full-dataset ranking metrics can be reported.
- The chunking comparison uses source-page relevance as a proxy, not exact chunk-level relevance for both configurations.
- Latency measurements are from a single run and require repeated trials.
- Faithfulness and answer correctness require separate evaluation.
- Similarity scores alone do not establish whether an answer is correct.
- A high retrieval score on a small verified subset does not guarantee general retrieval quality.

## 8. Conclusion

The threshold experiments demonstrate a trade-off between answer coverage and safe abstention. Threshold 0.30 was more conservative than threshold 0.20 on the current dataset.

The chunking experiment compared two configurations using the same document and golden questions. Config A (800/150) achieved 100% Hit Rate@5 and Recall@5 on the verified subset, while Config B (500/100) achieved 100% Hit Rate@5 and 90% Recall@5.

Config A is retained as the current default based on its measured recall and latency in this experiment.

However, the evaluation remains limited by the five-question manually verified subset and page-level relevance mapping. Additional relevance annotations, repeated latency experiments, and answer-quality evaluation are needed before making broader performance claims.