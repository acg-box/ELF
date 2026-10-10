---
type: Evidence
title: ELF language-neutral source memory regression benchmark
description: Verify immutable multilingual source capture and typed native extraction on the frozen matched workload.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/evidence/2026-10-10-elf-language-provenance/protocol.json
  - config/benchmark/evidence/2026-10-10-elf-language-provenance/evaluation.json
related:
  - docs/evidence/benchmarking/2026-10-10-elf-matched.md
  - docs/evidence/benchmarking/2026-10-10-final-system-comparison.md
  - docs/decisions/2026-10-10-language-neutral-source-memory.md
code_refs:
  - packages/elf-domain/src/text_validation.rs
  - packages/elf-service/src/add_event.rs
  - packages/elf-service/src/structured_fields/relation_time.rs
  - packages/elf-storage/src/docs/documents.rs
  - scripts/benchmark-elf-matched.py
---
# ELF language-neutral source memory regression benchmark

Both conditions completed all 140 answers. Under the same semantic review rules
as the previous report, each scored 100/100, up from 90/100. The unchanged strict
automatic scorer gives 85.5/100, up from 75.5/100. Chinese questions improved
from 0/10 to 10/10 in each condition. These are fixture results, not a general
product ranking.

| Condition | Previous reviewed | Current reviewed | Current strict | Documents | Memory test |
| --- | ---: | ---: | ---: | ---: | ---: |
| Context Pack + shared reader | 90/100 | 100/100 | 85.5/100 | 50/50 | 16/16 |
| Retrieval + shared reader | 90/100 | 100/100 | 85.5/100 | 50/50 | 16/16 |

Document and memory columns use reviewed correctness.

The score is `50 * document_accuracy + 50 * memory_test_accuracy`.
Each condition has 50 document questions and 20 memory questions; four memory
questions are development cases and do not contribute to the score. There are
140 attempted answers, 132 scored answers, and 70 unique questions across both
conditions. Operational failures remain in the denominator.

## Product changes

- One domain text contract accepts Unicode without language detection or source
  normalization. It retains control-character checks and identifier-format checks.
- Source writes preserve the exact accepted content. A write policy that changes
  original text fails explicitly. A changed source receives a new record identity;
  storage upserts cannot replace its bytes, hashes, ownership, or chunk offsets.
- Derived notes remain separate from Source Library. English summaries are a
  profile preference. Names and evidence quotes retain their source language.
- The built-in profile uses JSON Schema generated from Rust extraction types.
  Shape errors are explicit. Facts and relation surfaces keep the existing
  verbatim evidence checks.
- Relation time accepts RFC 3339 or an ISO date at a documented UTC day boundary.
  The schema and decoder share the date-format description. Original dates remain
  in source evidence; the derived boundary does not claim an exact event time.

See the decision record for configuration, profile, and source-writer migration.
Existing profile pins are preserved; new tenants use built-in profile version 2.
Events remain an extraction API. The benchmark explicitly stores the originals
through Source Library before submitting the same memory records to extraction.

## Native persistence and provenance

| Measurement | Previous ELF run | This run |
| --- | ---: | ---: |
| Source records accepted | 32/34 | 34/34 |
| Event requests processed | 0/20 | 20/20 |
| Persisted memory notes | 0 | 37 |
| Note operations | No successful writes | 37 additions, 21 updates |
| Graph facts / evidence links | No extracted facts | 40 / 40 |
| Rejected candidates | Event parsing failed first | 1 of 59 candidates |

All 34 original UTF-8 values match the frozen inputs byte for byte. Stored content
hashes agree with capture receipts. Every chunk offset resolves to the stored
original bytes. All 34 documents have one chunk in this small fixture. Integration
tests separately verify that changed source versions retain old content and
citations, and that conflicting storage upserts fail.

One model-generated candidate was rejected because its relation subject was
`project Cedar`, while the note used `Project Cedar` and its evidence quote used
only `They`. The verbatim binder did not accept that surface. This rejection is
retained in the evidence; the source record and the other candidate notes remain
available. Candidate acceptance is not an extraction precision or recall score.

The Context Pack selected source documents and no memory notes in all 20 memory
questions. Its score therefore does not demonstrate use of the new note store.
The retrieval condition hydrated 12 notes per memory question, together with
source context. This confirms note retrieval, but it does not isolate the notes'
causal contribution to answer quality. A note-only ablation is outside this run.

## Matched controls

The final benchmark image uses source revision
`3ef9b7d69d6dc3835cdc01b2ba0e928647356e84`. The subsequent product correction only
restores title metadata updates in the document conflict branch. A focused
repeated-capture test validates that correction. The benchmark inserts each
source once, and database timestamps verify that this branch was not used.
The exact delta is recorded in `comparison-controls.json`.

A separate post-measurement change, `59e1e69f680d47e7ee81e943e7d257ba8338764c`,
adds source message IDs, roles, timestamps, original and extraction-input BLAKE3
hashes, and matching write-policy audits to event evidence. It also checks control
characters in these metadata fields. It does not change extraction instructions,
retrieval, or reader behavior. The final unit and integration suites verify it;
the paid benchmark was not repeated after this metadata change. Frozen measured
rows are not backfilled. Events do not automatically archive full original
transcripts: callers must retain them in Source Library or an upstream system.

Frozen inputs, retrieval and reader functions, supporting comparison scripts,
provider routing, and output limits match the previous run. No answer oracle,
OCR annotation, source translation, or model substitution was introduced.
No competitor or OCR calls were repeated. The earlier Hindsight and RAGFlow
measurements remain historical comparisons, not simultaneous reruns.

- DeepSeek V4.1 Flash, maximum reasoning, with the same requested maximum output
  of 943,718 tokens. The harness applies no smaller output cap. Requested limits
  remain distinct from provider limits and actual usage.
- Qwen3 Embedding 8B, 1,536 dimensions, through the same Nebius route.
- The same CPU cross-encoder sidecar and frozen GPT-2 tokenizer. Native document
  search retains its own retrieval path and does not use this reranker.
- Context Pack: 32 selected references, hydrated through native APIs, with no
  extra reader-context truncation. Secondary retrieval: 12 hits / 60 candidates
  per source and a 4,096-token shared-reader context limit.

Correction to the previous report: it described the global 512/128 chunk setting.
The document API actually uses its knowledge-document profile, 2,048 tokens with
256-token overlap, in both runs. This correction does not change the historical
scores or artifacts. All documents fit one chunk, so this fixture does not test
long-document chunk selection at scale.

## Cost and execution

| Phase | Paid USD | Requests |
| --- | ---: | ---: |
| Previous ELF baseline | 0.118841296 | 393 |
| Stopped schema probe | 0.008427126 | 9 |
| Final complete run | 0.147167710 | 490 |
| This change, including probe | 0.155594836 | 499 |
| Cumulative ELF ledger | **0.274436132** | **892** |

All requests are settled. Conservative exposure equals paid cost; no request
remains in flight.

All usage belongs to the same cumulative USD 10 ledger as the previous ELF run.
The earlier Hindsight/RAGFlow USD 20 ledger is separate. Token counts, cache hits,
provider receipts, and conservative exposure are included in the evidence.

An early probe was stopped before questions. Date parsing succeeded but exposed
incorrectly wrapped relation subjects and unsupported structured facts. Three
recorded event responses rejected eight candidates. The gateway settled the
in-flight call and all nine paid probe requests. The probe cost is included above;
its receipts are retained. The final run started with a fresh database after the
schema correction. Probe results are not mixed into the 140 final answers.

The final benchmark command took 32 minutes 14.20 seconds, excluding the image
build. The 490 final requests used 611,705 prompt tokens and 165,563 completion
tokens. Reported cached prompt tokens total 284,160. Usage includes ingestion,
extraction, embeddings, and reader calls; token definitions vary by endpoint.

| Condition | Median seconds | p95 seconds | Reader cost USD |
| --- | ---: | ---: | ---: |
| Documents, Context Pack | 4.27 | 19.56 | 0.036013880 |
| Documents, retrieval | 4.31 | 20.29 | 0.017250686 |
| Memory, Context Pack | 8.48 | 25.34 | 0.010242110 |
| Memory, retrieval | 9.10 | 33.71 | 0.014288180 |

## Review and limits

The review retains every raw answer and strict score. It changes 14 judgments,
including two development cases, under the previous report's rubric:

- Four numeric answers correctly return 420 or 930. The strict matcher detects
  forbidden 42 or 93 as a substring of those valid values.
- Ten memory answers state that no budget owner has been appointed. The retrieved
  source explicitly states this absence. The reader marks the answer supported;
  the frozen oracle expects unsupported. No answer invents an owner's name.

The second group exposes an oracle limitation: known absence is not the same as
unknown information. This lane cannot cleanly measure abstention on unknown facts.
The raw weighted score remains 85.5/100. Review entries bind each judgment to its
answer hash and state the reason. No oracle or original result was overwritten.

This is a small, synthetic, already-known fixture. It validates the repaired
boundaries and observed end-to-end answers. It does not prove general superiority,
large-corpus retrieval quality, extraction precision, or equal quality across all
languages. The Chinese cases test document ingestion and retrieval; separate
integration tests exercise Chinese event quotes and relation persistence.

ELF has no native final-answer endpoint. Both conditions use an external shared
reader. Source records and extracted notes can both contribute to memory answers;
a successful answer alone does not isolate the contribution of the note store.
The source-integrity and native-persistence measurements are reported separately
for this reason. Latencies are observations from a shared host and provider, not
controlled throughput claims.

Final code validation passed 454 unit tests and 94 integration tests (548 unique
tests), including immutable source versions, Chinese event provenance, transformed
input audit mapping, date-only relations, and extraction schema descriptions.
Focused provenance regressions also passed. Clippy and repository style checks
passed. The unchanged benchmark harness passed 156 contract tests and three tooling
tests. Validation receipts record the checked revisions and log hashes.

All task-owned benchmark and test containers, the benchmark network, anonymous
volumes, four task-owned images, and private runtime credential files were removed.
Shared services, images, and build cache were preserved.

## Evidence and reproduction

The evidence directory is
`config/benchmark/evidence/2026-10-10-elf-language-provenance/`.
Run its `verify.py` for offline input, answer, review, cost, and hash checks.
The manifest binds public-safe receipts, native persistence, source integrity,
matched controls, and cleanup readback. Private authentication and runtime secret
files are excluded.

Build the `elf-service-runtime` target in `docker/benchmark/Dockerfile` at the
recorded revision and set its `ELF_SOURCE_COMMIT` label. Invoke
`cargo make benchmark-elf-matched --image IMAGE --artifact-root ROOT` through
`cargo make benchmark-budget`, using the recorded provider settings and the same
cumulative ledger. The artifact root's parent must contain
`cost-calibration/budget-ledger.json`. Use a fresh root and fresh owned Docker
resources when changing the product revision; preserve all attempted outputs.
