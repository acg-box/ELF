---
type: Evidence
title: Complex PDF and OCR comparison
description: Compare native RAGFlow parsing with a free parser feeding ELF and Hindsight.
status: draft
authority: informative
owner: benchmark
last_verified: 2026-10-09
source_refs:
  - config/benchmark/fixtures/complex-documents-v1/oracle-source.json
code_refs:
  - scripts/benchmark_deep/complex_documents.py
  - scripts/benchmark_targets/ragflow.py
related:
  - docs/evidence/benchmarking/2026-10-09-ragflow.md
  - docs/runbook/benchmarking/ragflow.md
---
# Complex PDF and OCR comparison

## Scope

This is a new screening condition. It does not change the previous text-only
RAGFlow evidence. Eight controlled synthetic PDFs contain 24 questions: sixteen
supported questions and eight questions whose requested value is absent.

| Source layout | Sources | Pages | Questions |
| --- | ---: | ---: | ---: |
| Table, historical column, footnote, missing cell | 2 | 2 | 6 |
| Adjacent signed and archived columns | 2 | 2 | 6 |
| Clause continued across pages and a revised value | 2 | 4 | 6 |
| Image-only table scan, slight skew and blur | 2 | 2 | 6 |

The oracle is separate from ingestion data. Source names are opaque evidence
identifiers. Scan answers differ from digital-table answers, so retrieval from
a digital sibling cannot satisfy the scan question. All ten pages received a
visual layout check. Scans have no text layer.

## Conditions

RAGFlow receives original PDF bytes through its native upload API. Its `general`
ingestion pipeline selects DeepDOC for PDF files. The official pinned
`v1.0.0-rc1` image uses the Go server and Infinity. This remained the latest GitHub
release when checked on 2026-10-09. The image runs with AMD64 emulation on an ARM
host. DeepDOC models are included in the image; no paid vision model is configured.

ELF and Hindsight receive the same sources after a free parser stage in Docker:
Poppler `pdftotext -layout`, then Tesseract at 200 DPI with `--psm 3` only when the
PDF has no extractable text. No human corrects the extracted text. Parser versions,
source checksums, and extraction times are retained with the fixture. Every
expected answer identifier occurs in this extracted text. That check does not
establish correct row, column, or clause interpretation.

These are complete pipeline comparisons. Neither the ELF nor the Hindsight
condition tests a native PDF upload API. The shared reader, embedding model,
embedding dimensions, questions, and scoring protocol remain the same. RAGFlow
uses five contexts, similarity threshold 0.2, vector weight 0.3, and no reranker.
ELF and Hindsight retain their registered native retrieval behavior.

## Interpretation limits

This small synthetic set can expose a concrete failure but cannot establish
broad product superiority. It does not measure handwritten forms, multilingual
OCR, photographed pages, charts, dense financial statements, or long customer
contracts. The exact identifier scoring checks omissions and incorrect bindings;
it is not a full semantic answer-quality evaluation.

Attribute failures by checking native parse status, parsed chunks, supplied
contexts, and the reader answer in that order. Do not report a missing parser
prerequisite or ingestion timeout as an incorrect answer. Do not convert
successful abstention after failed ingestion into a quality success.

The RAGFlow deployment uses Infinity because this release's Go server rejected
OpenSearch in the preceding experiment. This is not an Infinity versus OpenSearch
benchmark. Document parsing happens before search indexing; a parsing advantage
does not establish an advantage for the index engine.

## Protocol corrections and retained diagnostics

The first native RAGFlow client reached its 600-second ingest limit before all
PDFs completed. All 24 queries were blocked by ingestion; none are scored as
wrong answers. The service continued processing the same dataset. The recovery
condition waits for these retained native documents and asks all 24 questions.
It does not upload or parse the corpus again. Its deadline is 1,800 seconds.

The original reader protocol concatenated passage text and omitted native source
identities. That is insufficient when a system returns a title as one fact and
the corresponding table row as a separate fact. The primary comparison uses the
opt-in `source_labeled_case_v1` protocol for all three products. Each native
passage retains its opaque evidence ID in the reader input. The formatter does
not consult the oracle, add source titles, or restore missing content. The
12,000-character context cap and reader model stay unchanged. The initial labeled
condition keeps the 4,096-token output limit.
Hindsight and ELF reuse their frozen retrieval responses for the labeled-reader
condition; the raw conditions remain available as diagnostics.

Four questions ask for an explicitly empty West overflow cell. The initial
oracle required unsupported `unknown`, but a supported answer such as "no
published overflow queue" can also be semantically correct. Cases `complex-002`,
`complex-005`, `complex-020`, and `complex-023` are therefore excluded from the
primary score for every product. This is a post-run evaluator correction, not a
product failure or a selective removal of wrong answers. Preserve the original
24-row scores. The primary denominator is 20: sixteen answerable questions and
four genuinely absent-field questions. The four empty-cell cases remain visible
as diagnostic observations.

The initial RAGFlow attempt inherited the text manifest's "OCR not measured"
metadata. That metadata does not describe the uploaded PDF workload. The
recovery uses `ragflow-pdf-v1.json`, which explicitly declares original PDF
parsing. Image, models, embedding dimensions, and the retained sources are
unchanged. No historical manifest or score file is rewritten.

The labeled ELF condition had two reader output-limit errors. A missing-output
retry preserved all 22 completed answers, including wrong answers, and retried
only the two missing outputs under the same 4,096-token limit. One core question
still exceeded the limit. The final primary comparison therefore replays all
24 questions for each of the three products with the same 8,192-token limit.
Only the output limit changes; model, reasoning effort, prompt, contexts, and
source labels stay fixed. No native parsing, ingestion, or retrieval is repeated.
These attempts remain separate conditions. No best-of-attempt answer selection
is used in the primary score.
