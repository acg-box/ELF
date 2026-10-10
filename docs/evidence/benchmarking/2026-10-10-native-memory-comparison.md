---
type: Evidence
title: Native Hindsight and RAGFlow comparison
description: Compare token-budget retrieval and native answers on document and conversation tasks.
status: verified
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
All five conditions completed: 200 final answers, with no missing outputs.
The old top-five comparison does not establish that RAGFlow is better than
Hindsight. With native source chunks or reflect, Hindsight answers all 20 PDF
questions and all 16 new memory test questions correctly. RAGFlow answers all
16 memory questions; its PDF scores are 14/20 for retrieval and 16/20 for native
chat. These are results for this small workload, not a general product ranking.

## Reason for the follow-up

The previous adapter took five Hindsight hits after the native API had returned
its token-budget results. A fact is not equivalent in size to a document chunk.
The retained 0.10.3 responses contain the required identifiers for seven
answerable questions outside the five-hit presentation. This proves information
was removed by the adapter. It does not prove that the reader would answer all
seven questions correctly with more context. The complete corrected presentation
uses 4,076 `cl100k_base` tokens and contains all sixteen answerable cases' target
identifiers. Thus this specific information loss was not necessary to meet the
new 4,096-token context budget. Identifier presence is not proof of correct
source binding or a correct answer.

The historical score remains unchanged. This experiment has a separate protocol,
new native stores, and separate evidence.

## Frozen protocol

At run start, the official release APIs reported Hindsight 0.10.3 and RAGFlow
1.0.0-rc1 as the latest releases. Image digests are retained in the artifacts. Both servers run in Docker. RAGFlow uses its official Go
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
provider. RAGFlow uses its supported VLLM driver for this local endpoint.
Native retrieval invoked the reranker successfully. The separate auxiliary
rerank API rejected the custom model through its catalog lookup; that response
is retained and does not describe the native retrieval path.

RAGFlow retrieval requests up to 64 chunks with similarity threshold 0, vector
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
other four people are test cases fixed before the calls. They cover changed decisions,
cross-session synthesis, historical state, and abstention. Both products receive
the same record text. Hindsight also receives the dates as native timestamps.
The answer oracle is never ingested.

The scoring rubric was frozen before scored calls. Automatic strict matching is
retained as a diagnostic. All 200 completed answers received semantic review by the Codex agent.
This was not an independent, blinded human review. A correct answer can mention an old value when it clearly marks that
value as historical. A correct abstention can say `unknown` or state that the
requested information is absent. The budget-owner case also permits the explicit
source statement that no owner was appointed. Each change from the strict
score has a reason in `evaluation.json`. API/schema errors are failed attempts,
not incorrect final answers. Their costs and recovery history remain recorded.

This is a small synthetic comparison. It does not reproduce the full LongMemEval,
LoCoMo, or a representative customer-document benchmark. Four related questions
per person are not independent samples. No statistical significance is claimed.

## Results

Scores measure the requested values. Partial answers receive no full credit.
The four development questions are excluded from both primary columns.

| Condition | PDF diagnostic | Memory test | Development | Observed median query time |
| --- | --- | --- | --- | --- |
| Hindsight recall, all facts within budget | 20/20 | 12/16 | 3/4 | 7.84 s |
| Hindsight recall, original source chunks | 20/20 | 16/16 | 4/4 | 6.77 s |
| Hindsight native reflect | 20/20 | 16/16 | 3/4 | 26.29 s |
| RAGFlow retrieval with reranking | 14/20 | 16/16 | 4/4 | 7.33 s |
| RAGFlow native chat with reranking | 16/20 | 16/16 | 4/4 | 6.77 s |

There are 36 primary questions and four development questions per condition,
not 200 independent questions. Timings cover primary queries on a shared host
with concurrent lanes, up to three clients during the supplement. They are not
isolated performance measurements and exclude ingestion.

The source-chunk condition was added after initial outputs were inspected. It
is an exploratory check of a supported native feature. It uses the same frozen
questions, reader, scoring rubric, and context limit. Native recall returns the
original chunks; the adapter does not fetch answers from the fixture. All 560
chunk presentations matched their native source identities and original text.
The maximum presented context was 2,519 common tokens, with no truncation.
However, all 20 short conversation records or all eight PDF text records fit.
This result tests source preservation and answering; it does not establish
large-corpus retrieval quality. The new memory test has a ceiling effect.

### What changed the outcome

- Hindsight reflect used native tools: 87 `recall` and 84 `search_observations`
  calls across its 40 answers. Its recall traces include original source text.
  It did not merely pass a short fact list to the shared reader.
- In `memory-0-0`, a consolidated Hindsight observation incorrectly assigns
  Cobalt's `RETRY-1-907` policy to Larch. The facts-only reader repeats this
  error. Native reflect checks the original records and answers with Larch's
  `STREAM-0-286` mode and `RETRY-0-907` policy. Source chunks also recover the answer.
- The other three facts-only memory failures omit a requested replay identifier.
  Two of those identifiers are absent from the final 4,096-token presentation.
  All 20 conversation fact presentations were truncated. The remaining failed
  case contains the identifier but does not bind it to the answer correctly.
- RAGFlow's six retrieval PDF failures contain the required identifiers in the
  returned context. They are not missing-identifier retrieval failures. The
  digital-table parser puts `Historical - do not use` in a caption for the whole
  table. This changes how the reader interprets current columns. The returned
  text also omits the revision-4 footer needed by two revision questions.
- RAGFlow native chat recovers those two revision answers. Four digital-table
  cases remain unsuccessful: two abstentions and two answers that give the
  overflow route category without the requested queue identifier.

Hindsight receives the unchanged Poppler/Tesseract extraction; RAGFlow receives
PDFs for DeepDOC. Thus the PDF result compares these ingestion-to-answer
pipelines. It does not show that Hindsight has its own better PDF or OCR parser.
No Infinity versus OpenSearch comparison was performed.

Requested-value accuracy does not certify every extra sentence or citation.
For example, reflect answers `complex-013` correctly but mentions Page 1 for an
item on Page 2. Its development case `memory-4-1` also omits the requested replay
identifier. Both observations remain in the review. Native reflect improved
primary answers here, with more calls, longer responses, and higher observed
query latency. The available accounting does not isolate exclusive product
costs because ingestion and query lanes overlap.

## Completion, cost, and recovery

The final output contains 200 completed rows and 52 archived failed attempts.
No completed answer was replaced with a better retry. Initial RAGFlow requests
with `page_size=100` failed API validation; recovery used 64 for all frozen
queries. The first source-chunk adapter used the reflect trace's `chunk_text`
field, but the recall API returns `text`; only missing outputs were recovered.
The first shared-reader format error retained failure metadata and its metered
charge, but not its raw response body. The parser now retains raw receipts for
contract errors. This evidence gap is explicit in `completion.json`.

| API accounting | Value |
| --- | ---: |
| New requests | 1,024 |
| Completed / provider failed | 1,021 / 3 |
| Chat input tokens (including cached input) | 1,892,679 |
| Cached chat input tokens | 527,104 |
| Chat output tokens | 311,058 |
| Embedding input tokens | 25,875 |
| New paid cost | USD 0.393311112 |
| New exposure, including failed-request reserves | USD 0.395838612 |
| Cumulative paid cost | USD 15.728059060 |
| Cumulative exposure | USD 16.045368560 |
| Authorized cumulative ceiling | USD 20.00 |

The three provider failures are embedding 429 responses. Their reservations
remain in exposure; earlier reserves were not released. These totals cover
benchmark provider calls, not host, CI, or Codex orchestration costs. Concurrent
case ordinal windows must not be summed as exclusive per-product costs.

The gateway is closed, and the ledger has no active request. Cleanup removed
eight task containers, seven volumes, one network, and eight newly pulled
images. Eight unrelated containers retain their identities and remain running.
No global prune was used. Temporary native session credentials were deleted.

## Retained evidence

The [artifact directory](../../../config/benchmark/evidence/2026-10-10-native-memory-comparison/)
contains final cases, failed attempts, metered requests, the frozen rubric,
per-answer reviews, protocol changes, image identities, source hashes, privacy
checks, and cleanup receipts. `manifest.json` hashes the public evidence files.
`runner-hashes.json` records earlier executed source bytes; `source-digests.json`
records the final source files. Do not treat them as one unchanged execution.

The original protocol and all previous reports remain unchanged. The added
source-chunk protocol is identified separately. The new runner has contract
tests for native source mapping, preserved retrieval hits, frozen inputs, and
reader-response identity. Validation passed: `cargo make test-benchmark-runner-contract` (136 tests)
and `cargo make check-docs`.

## Official method references

- [Hindsight recall and reflect](https://hindsight.vectorize.io/blog/2026/07/24/recall-vs-reflect)
- [Hindsight 0.10.3](https://github.com/vectorize-io/hindsight/releases/tag/v0.10.3)
- [RAGFlow retrieval testing](https://github.com/infiniflow/ragflow/blob/v1.0.0-rc1/docs/guides/dataset/retrieval_testing.md)
- [RAGFlow 1.0 API reference](https://github.com/infiniflow/ragflow/blob/v1.0.0-rc1/docs/references/http_api_reference.md)
