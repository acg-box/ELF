---
type: Evidence
title: Complex PDF and OCR comparison
description: Compare native RAGFlow parsing with a free parser feeding ELF and Hindsight.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/fixtures/complex-documents-v1/oracle-source.json
  - config/benchmark/complex-documents-v1.json
  - config/benchmark/evidence/2026-10-09-complex-documents/evaluation.json
  - config/benchmark/evidence/2026-10-09-complex-documents/accounting.json
code_refs:
  - scripts/benchmark_deep/complex_documents.py
  - scripts/benchmark_targets/ragflow.py
related:
  - docs/evidence/benchmarking/2026-10-09-ragflow.md
  - docs/runbook/benchmarking/ragflow.md
---
# Complex PDF and OCR comparison

RAGFlow shows useful table structure and strong dual-column results, but it does
not show an overall advantage in this controlled sample. Under the final shared
reader protocol, ELF scores **15/20**, RAGFlow **13/20**, and Hindsight 0.10.3
**8/20**. All three complete all 24 queries and reader calls. Four ambiguous
empty-cell questions are diagnostic only. These are pipeline results on eight
synthetic PDFs, not a general product ranking.

| Scored capability | ELF + free parser | RAGFlow 1.0.0-rc1 | Hindsight 0.10.3 + free parser |
| --- | ---: | ---: | ---: |
| Digital table rows and footnotes | 3/4 | 0/4 | 1/4 |
| Signed versus archived columns | 2/4 | 4/4 | 0/4 |
| Cross-page clauses and revision lookup | 4/4 | 3/4 | 2/4 |
| Scanned table rows and footnotes | 2/4 | 2/4 | 1/4 |
| Genuinely absent fields | 4/4 | 4/4 | 4/4 |
| **Total** | **15/20** | **13/20** | **8/20** |

The primary conditions are `elf-reader8k-v1`, `ragflow-reader8k-v1`, and
`hindsight-provenance-v2`. The latter uses the corrected, source-faithful formatter
for frozen Hindsight 0.10.3 native responses. The formatter correction does not
increase its overall score in this run; it removes an attribution defect and
makes the comparison interpretable. No best-answer selection across attempts is
used. Each row in the table has only two source documents behind it; do not claim
statistical significance from these small differences.

Machine-readable evidence is under
`config/benchmark/evidence/2026-10-09-complex-documents/`. Start with
`evaluation.json`, `conditions.json`, `cases.jsonl.gz`, and `accounting.json`.
The manifest hashes every exported artifact. Twelve conditions produce 288 raw
case rows, including repeats and failed attempts; they are not 288 independent
questions.

## Findings and next decisions

- RAGFlow preserves all target identifiers in parsed chunks, but five of its
  seven primary failures lack the needed identifier in the supplied top-five
  context. The other two retain the value but have a misleading whole-table
  caption or missing revision metadata. The exact reader decision is not inferred
  from the score alone. The parsed-source defects remain visible independently.
- ELF misses the expected fact in four of its five failed reader contexts,
  including three South overflow lookups that instead return another document's
  queue. Its remaining failure abstains despite both identifiers being present.
  First investigate source selection and parent-document context in the measured
  note-backed adapter; do not assume these results describe the separate document
  API.
- Hindsight 0.10.3 still mixes observations supported by several documents with
  document-specific facts. The corrected formatter preserves those distinctions,
  but this default retain/recall pipeline does not reliably answer source-specific
  questions in this sample. This is not a conclusion about native `reflect` or a
  workflow that explicitly fetches the original document.

The next useful work is source-bound retrieval, complete table/footnote context,
and retention of revision metadata. The results do not justify adding a full
RAGFlow stack solely for this document-QA workload. A broader adoption decision
needs representative customer documents and a native x86 performance check.

## Cost, runtime, and cleanup

All 741 provider requests added by this experiment have completed accounting.
Incremental API cost is **USD 0.247585571**. Cumulative recorded API cost is
**USD 15.334747948**; cumulative exposure, including earlier unresolved reserves,
is **USD 15.649529948**, below the authorized USD 20 ceiling. This includes failed
reader attempts, full replays, and the latest-version run. Host compute, GitHub
Actions, and Codex orchestration costs are excluded.

Native RAGFlow processing finished about 27 minutes after upload on this ARM host
with AMD64 emulation. The free parser completed extraction in 1.22 seconds on the
local parser container. These are different implementations and execution
architectures; do not turn this observation into a production speed ratio. All
native products and the free parser ran in Docker. The budget gateway and shared
reader controller ran on the host. Most of the RAGFlow delay occurred in parsing,
before vector indexing, so it is not evidence about Infinity versus OpenSearch.

The RAGFlow stack's seven containers, six volumes, network, and eight new images
(including the free-parser image) were removed. The separately downloaded
Hindsight 0.10.3 image was also removed. All five native benchmark Compose projects
have no remaining containers, networks, or volumes. The dedicated 37.08 MB parser
build layer and the temporary native API session file were removed. Eight existing
named services retained their original start times. One extra transient container
in the initial inventory was absent at final readback; it was outside the task's
cleanup targets and its lifecycle was not verified. No global Docker prune ran.

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

All conditions use `deepseek/deepseek-v4.1-flash` with low reasoning through
DeepSeek and `qwen/qwen3-embedding-8b` at 1,536 dimensions through Nebius.
The budget gateway fixes these routes.

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
condition tests a native PDF upload API. ELF uses the existing note-backed
`add_note` and `search_raw` adapter with 220-character adapter chunks under its
measured note limit. The separate ELF document-ingestion API is not tested.
Hindsight uses `retain` and `recall` after consolidation; native `reflect`,
explicit document lookup, and original-document fetching are not tested. The shared reader, embedding model,
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

## Version audit

The original Hindsight comparator used the retained 0.10.2 image. A live release
check found [0.10.3](https://github.com/vectorize-io/hindsight/releases/tag/v0.10.3),
published on 2026-10-08, with recall and consolidation changes.
The latest-version condition starts a new bank in the official ARM64 0.10.3
image. It uses the same sources, models, retrieval settings, source labels, and
8,192-token reader limit. The original 0.10.2 conditions remain diagnostic;
they do not stand in for the latest release in the primary table.

The common profile is `config/benchmark/complex-documents-v1.json`. The deep runner
uses its Hindsight native image pin when it starts Compose. Reader replay rejects
a changed product pin, so old retrieval cannot be relabeled as a newer version.
The actual running image ID is checked against the selected digest.

The ELF image records source commit `8bbd4930db0b26dec165365153c7b67acce4e492`.
Its Rust files, Cargo manifest, and lockfile match task-start main
`88520a28b1e2bbbbc77017bc081ee03d68b3ffb7`. This is a pinned binary comparison,
not a new release deployment.

## What the parsed sources show

Both DeepDOC and the free parser preserve all twenty unique answer identifiers
in the source files. Identifier presence alone is not enough for a correct answer.
DeepDOC produces HTML table rows and cells, with a caption that includes the
scanned table's footnote. This is a useful structural output that the plain-text
baseline does not provide.

DeepDOC also turns the digital table's "Historical - do not use" column heading
into a caption for the entire table, removes the `Revision 4` page footer, and
reads the East response window as `B` instead of `8` in both scans. The East hours
field is outside the fixed question set; this observation is not added to the
score after the run. The dual-column output interleaves text from the two columns.
Keep these losses visible even when the shared reader returns a correct answer.

Some native chunk-list responses contain chunks from other documents in the
same owned dataset. The parsing audit therefore matches `docnm_kwd` to the
opaque uploaded filename before it counts identifiers. It does not infer source
identity from the request path. This is not a cross-user authorization test.

## Native response formatting audit

A final adapter audit found that the Hindsight formatter repeated an observation
for every supporting source fact and assigned each combined passage that source's
ID. A derived statement about several documents was thus presented below each
individual source label. This is an adapter attribution error, not evidence that
the native system made each statement in each source document.

The corrected formatter emits each derived observation once, lists its native
supporting source IDs, and emits each source fact once under its own document ID.
It uses the same top-five native hits and the same returned `source_facts`; it
never reads the fixture corpus or oracle to fill gaps. A full 24-question replay
uses these corrected contexts. The raw API payloads, native rankings, and native
execution remain unchanged. Earlier Hindsight scores are diagnostic, not the
primary product result.

For Hindsight 0.10.3, the median reader input falls from 2,390 to 1,381 characters.
Neither presentation reaches the 12,000-character cap in this condition. Thus the
observed defect concerns source attribution and redundant text; it is not a
measured truncation failure. The new formatter leaves every measured ELF and
RAGFlow reader input unchanged.
