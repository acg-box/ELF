---
type: Evidence
title: Native Hindsight and RAGFlow comparison
description: Compare token-budget retrieval and native answers on document and conversation tasks.
status: draft
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/fixtures/complex-documents-v1/oracle-source.json
code_refs:
  - scripts/benchmark-native-comparison.py
  - scripts/benchmark_deep/memory_comparison.py
  - scripts/benchmark_deep/native_sidecar.py
related:
  - docs/evidence/benchmarking/2026-10-09-complex-documents.md
---
# Native Hindsight and RAGFlow comparison

This follow-up tests Hindsight and RAGFlow only. It does not test or rank ELF.
Results are pending. Do not use this draft as a completed comparison.

## Reason for the follow-up

The previous adapter took five Hindsight hits after the native API had returned
its token-budget results. A fact is not equivalent in size to a document chunk.
The retained 0.10.3 responses contain the required identifiers for seven
answerable questions outside the five-hit presentation. This proves information
was removed by the adapter. It does not prove that the reader would answer all
seven questions correctly with more context.

The historical score remains unchanged. This experiment has a separate protocol,
new native stores, and separate evidence.

## Frozen protocol

The official release APIs still report Hindsight 0.10.3 and RAGFlow 1.0.0-rc1 as
the latest releases. Both servers run in Docker. RAGFlow uses its official Go
server and Infinity. It runs with AMD64 emulation on an ARM host; do not use its
latency as a production hardware comparison.

There are two distinct comparisons:

- Retrieval: Hindsight recall with `budget=high`, without a five-hit cut, versus
  RAGFlow hybrid retrieval with a local cross-encoder reranker. Both feed the same
  reader. Source labels and context consume at most 4,096 `cl100k_base` tokens.
  This is a common measurement tokenizer, not the DeepSeek model tokenizer.
- Native answers: Hindsight `reflect` with `budget=mid`, versus RAGFlow native
  retrieval-chat with reranking. Each product controls its internal retrieval
  and synthesis. This is not a claim to test every RAGFlow Agent workflow or
  every Hindsight feature. Internal context and model-call counts can differ;
  report their costs with the result.

Both use DeepSeek V4.1 Flash at low reasoning, Qwen3 Embedding 8B with 1,536
coordinates, and the same budget gateway routes. The local reranker is
`cross-encoder/ms-marco-MiniLM-L-6-v2`, from the Hindsight image. A small local
Jina-compatible endpoint makes it available to RAGFlow without another paid
provider. Its scores are checked before product queries.

RAGFlow retrieval requests up to 100 chunks with similarity threshold 0, vector
weight 0.3, and 1,024 candidates. Native chat uses top 20. Hindsight recall
requests 4,096 tokens plus up to 8,192 tokens of supporting source facts; the
common reader budget is applied to the complete labeled presentation afterward.
The maximum reader/native answer output is 8,192 tokens. The native call timeout
is 600 seconds. The gateway has a cumulative USD 20 limit and an additional
USD 1.50 tranche for this run.

## Workloads and scoring

The previous eight PDFs contribute 20 diagnostic questions. Their four ambiguous
empty-cell cases remain excluded for both products. These questions have already
been inspected and are not a fresh test set. RAGFlow receives original PDFs;
Hindsight receives the fixed, uncorrected free-parser text.

The new fixture contains 20 dated records for five independent people/projects.
Four questions for one person are development cases. Sixteen questions for the
other four people are held-out test cases. They cover changed decisions,
cross-session synthesis, historical state, and abstention. Both products receive
the same record text. Hindsight also receives the dates as native timestamps.
The answer oracle is never ingested.

The scoring rubric is frozen before scored calls. Automatic strict matching is
retained as a diagnostic. Review all completed answers for meaning and source
support. A correct answer can mention an old value when it clearly marks that
value as historical. A correct abstention can say `unknown` or state that the
requested information is absent. The budget-owner case also permits the explicit
source statement that no owner was appointed. Record each change from the strict
score, with a reason. Do not count API/schema errors as incorrect answers; retain
the attempts and report missing outputs separately.

This is a small synthetic comparison. It does not reproduce the full LongMemEval,
LoCoMo, or a representative customer-document benchmark. Four related questions
per person are not independent samples. No statistical significance is claimed.

## Official method references

- [Hindsight recall and reflect](https://hindsight.vectorize.io/blog/2026/07/24/recall-vs-reflect)
- [Hindsight 0.10.3](https://github.com/vectorize-io/hindsight/releases/tag/v0.10.3)
- [RAGFlow retrieval testing](https://github.com/infiniflow/ragflow/blob/v1.0.0-rc1/docs/guides/dataset/retrieval_testing.md)
- [RAGFlow 1.0 API reference](https://github.com/infiniflow/ragflow/blob/v1.0.0-rc1/docs/references/http_api_reference.md)
