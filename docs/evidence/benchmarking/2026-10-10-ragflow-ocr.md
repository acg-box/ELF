---
type: Evidence
title: RAGFlow document parser intervention
description: Compare free-parser and Mistral OCR text with the historical DeepDOC document baseline.
status: verified
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/fixtures/complex-documents-v1/oracle-source.json
code_refs:
  - scripts/benchmark-document-ocr.py
  - scripts/benchmark-ragflow-parsers.py
related:
  - docs/evidence/benchmarking/2026-10-10-native-memory-comparison.md
---
# RAGFlow document parser intervention

Both new input pipelines answer all 20 diagnostic questions correctly in both
answer modes. All 80 new outputs completed without retries or missing answers.
The free parser matches Mistral OCR on this workload. These results do not show
an accuracy benefit from paid OCR over the retained free-parser text. This
experiment tests RAGFlow only; it does not rerun Hindsight or change ELF behavior.

## Results

| Document input | Shared reader after retrieval | Native RAGFlow chat | Evidence |
| --- | --- | --- | --- |
| Original PDF through DeepDOC | 14/20 | 16/20 | Historical baseline from the previous report |
| Fixed Poppler/Tesseract text | 20/20 | 20/20 | New complete run |
| OpenRouter Mistral OCR text | 20/20 | 20/20 | New complete run |

Each new condition scores 4/4 on digital tables, 4/4 on scanned tables, 6/6 on
columns, and 6/6 on cross-page questions. Strict scoring and semantic review
agree on all 80 outputs; no scoring overrides were needed. Source identities
were known for all returned chunks. For each of the 64 supported answers, the
requested identifiers occur in returned chunks from the expected source. All
32 supported shared-reader answers also retain those identifiers within the
actual reader context. The other 16 answers correctly return `unknown`.

The four digital-table failures from the historical native-chat condition are
absent in both new conditions. The two additional historical shared-reader
revision failures are also absent. This supports a limitation in the original
DeepDOC-to-answer pipeline, not a general deficit in RAGFlow retrieval or memory.
It does not isolate a single parser subcomponent or establish which pipeline is
best on unseen documents.

The free text produces 28 native chunks; Mistral text produces 37. Maximum
shared-reader contexts are 2,560 and 2,815 common tokens respectively, with no
truncation. The corpus is small enough to fit within the context budget. This
is not a large-corpus retrieval benchmark.

Mistral preserves the `Revision 4` footer in all eight documents. It does not
attach `Historical - do not use` as a whole-table HTML caption. However, it puts
`Approved routing` and `Historical - do not use` on separate text lines above
the Markdown table; it does not fully preserve the original spanning-header
geometry. Correct final answers do not prove perfect document reconstruction.

The measured native-chat query medians are 6.56 seconds for free text and 5.94
seconds for Mistral text. Shared-reader medians are 6.18 and 5.95 seconds. These
are observed timings, not evidence of a reproducible speed advantage.

For this fixture, retain free parsing as the economical baseline. Mistral OCR
is a low-cost alternative to evaluate on harder real documents, but this result
does not justify paying for it to improve these 20 answers. Do not carry the
previous configuration scores forward as a product-wide Hindsight/RAGFlow rank.

## Comparison boundary

The previous DeepDOC condition remains immutable. It used original PDFs,
RAGFlow 1.0.0-rc1, reranked hybrid retrieval, and DeepSeek V4.1 Flash. This run
keeps that RAGFlow image digest, reader model, embedding model, reranker, and
query settings. It creates two separate native datasets:

- Free parser: the exact previously retained Poppler/Tesseract text.
- Mistral OCR: original text annotations from OpenRouter's `mistral-ocr` file
  parser, extracted from the same eight PDFs. Assistant-generated text is never
  used as the OCR output. The response does not expose the underlying OCR model
  version; this is not a claim to run Mistral OCR 4.1.

Both new datasets receive text/plain files with the same opaque source names.
RAGFlow applies its General text parser and creates chunks and embeddings.
This intervention changes the source representation and downstream chunking as
well as the PDF parser. It is an external pre-parser, not a native DeepDOC model
replacement. It cannot by itself attribute every score change to OCR accuracy.

All 20 existing diagnostic questions are selected before the answer calls.
The four ambiguous empty-cell questions remain excluded uniformly. There is no
new held-out dataset. Each parser condition runs a shared-reader lane and a
native-chat lane, for 80 new outputs. The prior DeepDOC results are historical
reference rows, not a simultaneous control. No statistical significance is
claimed for eight synthetic documents.

## Fixed settings

Use DeepSeek V4.1 Flash with low reasoning and Qwen3 Embedding 8B at 1,536
dimensions. The CPU reranker is `cross-encoder/ms-marco-MiniLM-L-6-v2` from the
same pinned Hindsight image used by the prior run; no Hindsight memory service
runs here. Native retrieval uses page size 64, similarity threshold 0, vector
weight 0.3, and 1,024 candidates. The shared reader receives at most 4,096
`cl100k_base` tokens. Native chat uses top 20 and the same evidence instruction.
Both answer paths allow 8,192 output tokens.

The two parser lanes run concurrently on one host. RAGFlow uses AMD64 emulation
on ARM. Query timings do not establish isolated or production performance.

## OCR accounting

Eight OCR requests parsed ten pages. Their total reported cost is USD
0.0205301. In each receipt, `usage.cost` minus
`usage.cost_details.upstream_inference_cost` is USD 0.002 per page; the aggregate
OCR component is USD 0.02, and the accompanying short DeepSeek calls cost USD
0.0005301. The model completion can end at its 16-token limit because only the
original file annotations are consumed. No answer is extracted from that short
completion.

The OCR command reserves USD 0.02 per page plus bounded-model input/output
headroom. Those conservative reserves remain in the cumulative ledger. The
following native benchmark gateway has a separate USD 0.15 tranche. All phases
share the existing USD 20 cumulative ceiling. A repeated command reuses saved
OCR text and completed answer rows; it does not select better completed answers.

## Interpretation

Audit table-heading placement, row/column binding, footnote conditions, page
revision markers, and source identity before assigning a cause to a wrong
answer. Score requested values separately from correctness of all extra prose.
Apply the previously frozen semantic rubric to all outputs and retain strict
scores. Review is by the Codex agent, not an independent blinded human reviewer.

## Sources

- [OpenRouter PDF processing and file annotations](https://openrouter.ai/docs/guides/overview/multimodal/pdfs)
- [RAGFlow 1.0.0-rc1 parser configuration](https://ragflow.io/docs/v1.0.0-rc1/dataset_configuration)

## Final cost and delivery evidence

| Accounting item | Value |
| --- | ---: |
| New provider requests | 200 |
| OCR requests / pages | 8 / 10 |
| Chat requests | 80 |
| Embedding requests | 112 |
| OCR and acknowledgement calls | USD 0.020530100 |
| Answer model calls | USD 0.052403736 |
| Embeddings | USD 0.000072140 |
| Total new paid cost | USD 0.073005976 |
| Cumulative paid cost | USD 15.801065036 |
| Cumulative conservative exposure | USD 16.420148436 |
| Cumulative ceiling | USD 20.00 |

New answer-model usage is 306,672 input tokens, including 32,512 cached input
tokens, and 18,637 output tokens. OCR acknowledgement calls use another 3,022
input and 128 output tokens; embedding input is 7,214 tokens. All API calls
returned successfully. The eight OCR ledger rows retain the conservative
`completed_cost_unknown` accounting status because the per-page reserve was
not released; this is not a failed parse. The fee calculation above is supported
by all eight usage receipts. No claim is made about future engine pricing.

The native controller and budget gateway exited successfully. The gateway is
closed. Cleanup removed all eight task containers and the task network and
volumes. Newly pulled images were removed after checks for other users;
unrelated containers were preserved. No global prune was used. Temporary native
credentials and the task environment file were deleted.

[Retained artifacts](../../../config/benchmark/evidence/2026-10-10-ragflow-ocr/)
include all 80 answers, original OCR annotations, both parser outputs, native
chunks, source audits, usage receipts, protocol, runtime identities, cleanup,
and a SHA-256 manifest. The historical baseline and scoring rubric remain
unchanged. Source hashes describe the final checked-in scripts.

Validation: `cargo make test-benchmark-runner-contract` passed 139 tests;
`cargo make check-docs` and the evidence integrity checks passed.
