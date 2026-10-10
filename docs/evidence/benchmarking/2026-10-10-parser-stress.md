---
type: Evidence
title: Mixed-page, Chinese, and table parser comparison
description: Compare page-wise Poppler/Tesseract, DeepDOC, and Mistral OCR in one RAGFlow runtime.
status: verified
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/fixtures/parser-stress-v1/oracle-source.json
code_refs:
  - scripts/benchmark_deep/page_ocr.py
  - scripts/benchmark_deep/parser_stress.py
  - scripts/benchmark-ragflow-parsers.py
related:
  - docs/evidence/benchmarking/2026-10-10-ragflow-ocr.md
---
# Mixed-page, Chinese, and table parser comparison

Mistral OCR is the most reliable pipeline on this fixture. The free page-wise
extractor fixes mixed-document omissions but still loses Chinese scan content.
DeepDOC preserves the Chinese content but damages some literal codes and table
row relationships. Increasing the answer model to its highest reasoning setting
and provider-maximum output does not remove those differences.

The capability cohort completed all 180 answers without a retry, missing answer,
or output-limit failure. The reviewed scores below require copyable identifiers
and accept supported statements that information is absent. The frozen automatic
scores remain separate.

| Parser pipeline | Shared reader | Native RAGFlow chat |
| --- | ---: | ---: |
| Page-wise Poppler/Tesseract | 28/30 (93.3%) | 28/30 (93.3%) |
| DeepDOC | 26/30 (86.7%) | 26/30 (86.7%) |
| Mistral OCR annotations | 30/30 (100%) | 30/30 (100%) |

Each category below contains 10 questions. Cells show shared-reader / native-chat
reviewed correct counts.

| Parser pipeline | Mixed | Chinese | Table |
| --- | ---: | ---: | ---: |
| Page-wise Poppler/Tesseract | 10 / 10 | 8 / 8 | 10 / 10 |
| DeepDOC | 7 / 8 | 10 / 10 | 9 / 8 |
| Mistral OCR annotations | 10 / 10 | 10 / 10 | 10 / 10 |

These are conditional diagnostic results, not general product scores. No ELF
product or Hindsight memory behavior is changed or measured.

## What changed

The free extractor now visits every PDF page. It keeps Poppler layout text on
digital pages and applies Tesseract to empty text pages, replacement characters,
or pages with at least 20% raster-image coverage. This also catches a live text
header above a scanned body. It renders at 300 DPI and uses the packaged
`eng+chi_sim` recognition models with page segmentation mode 3. Each receipt
records the page decision, source digest, output digest, and tool versions.

The old whole-document test found some digital text in each mixed PDF and
therefore did not OCR its scanned content. It retained only 3/9 selected spans
in each mixed document. The page-wise extractor retains 9/9 in both. Its modes
are Poppler, Tesseract, Tesseract for both three-page files. This is a verified
repair of the mixed-document omission, not proof of universal OCR accuracy.

The 20% threshold is a heuristic. A small embedded scan can be missed, and a
large decorative image can trigger OCR. Summing displayed image areas can
overcount overlap. Whole-page OCR can also degrade valid text. No dictionaries,
oracle facts, name corrections, model changes, or answer-based parser tuning
are applied to the primary pipeline after the fixture is frozen.

The image contains Poppler 22.12.0 and Tesseract 5.3.0 with Debian-packaged
traineddata. These are the recorded runtime versions, not a claim that all
underlying free tools are the latest upstream versions. The native RAGFlow
release is checked separately.

An additional offline diagnostic changes the language selection on all six
PDFs after the primary outputs are examined. `chi_sim+eng` still retains 56/58
spans and does not repair the two names or the currency label. `chi_sim` alone
repairs the currency label but still misses both names and loses two English
approval codes, retaining 54/58 spans. These are post-hoc extraction probes,
not additional answer-score rounds. They do not replace the frozen primary
configuration or incur API charges. Tesseract documents that language order can
affect output in its [command-line guide](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage).

## Frozen workload and comparison

Six PDFs contain 12 pages, 30 questions, and 58 key spans:

| Category | PDFs | Pages | Questions | Coverage |
| --- | ---: | ---: | ---: | --- |
| Mixed | 2 | 6 | 10 | Digital page, full scan, live header over scanned body |
| Chinese | 2 | 2 | 10 | Digital and scanned simplified Chinese, names, amounts, conditions |
| Table | 2 | 4 | 10 | Spanning headers, merged region cells, continuation, dated footnote |

Twenty-four questions have supported answers; six require `unknown`. The scans
use 180 DPI, slight rotation, and light blur. All 12 pages were rendered and
visually reviewed before answer calls. The PDF hashes and questions are frozen
in `parser-stress-v1`. No question is excluded. The three parser conditions each
answer all 30 questions through a shared-reader path and native RAGFlow chat.
These are 180 outputs from 30 questions, not 180 independent test items.

All three conditions are new runs in RAGFlow 1.0.0-rc1, the latest GitHub release
verified for this run. DeepDOC receives the original PDFs with the General
pipeline's default `DeepDOC` PDF method. Free and Mistral conditions upload
plain text to the same General pipeline. Therefore this compares complete
parser-to-answer pipelines, including different chunking. It does not isolate
OCR alone. Plain-text upload also does not preserve native PDF bounding boxes
for source navigation. Earlier evidence is unchanged.

Mistral text comes only from original OpenRouter file annotations. The short
assistant acknowledgement is never used as OCR output. The engine is
`mistral-ocr`; its underlying model version is not exposed. This does not claim
to test a specific numbered Mistral OCR release.

Both answer paths use DeepSeek V4.1 Flash and Qwen3 Embedding
8B at 1,536 dimensions. The reranker is
`cross-encoder/ms-marco-MiniLM-L-6-v2`. Retrieval uses page size 64, threshold 0,
vector weight 0.3, and top-k 1,024. The shared reader has a 4,096 `cl100k_base`
token budget. Native chat uses top 20. Automatic keyword, question, and summary
extraction are disabled in all datasets.

The first cohort used low reasoning and 8,192 output tokens. It produced 179
completed answers and one repeated output-limit failure. After the user asked
for the best available model configuration, a separate cohort reused the parsed
datasets and generated all answers with `reasoning_effort=max` and a 943,718
output-token limit. This is the maximum completion limit in the captured
OpenRouter catalog, with a 1,048,576-token context. The gateway, reader, native
chat, and model registration use the explicit new settings. Per-request usage
receipts record the effective output limit and reasoning effort. The shared
reader still has 4,096 context tokens; its actual inputs fit that budget.

A maximum limit permits long output; it does not require the model to generate
that many tokens. The monetary gateway reserves the worst-case charge before
each request and keeps the cumulative USD 20 ceiling. The capability cohort
runs serially to fit those reservations. Its gateway transport timeout is
3,600 seconds, with 3,660 seconds at the consumer. It changes both reasoning
and output settings, so any difference cannot be assigned to only one setting.
It is one sample per question and path, not a search over repeated generations.

Before the formal cohort, one low-reasoning probe answered the previously
truncated table question correctly with 6,833 completion tokens. Because that
is below the old 8,192 cap, the probe does not prove a causal benefit from
removing the cap. A short low-reasoning maximum-output smoke run was then
stopped to use the highest reasoning setting for the formal cohort. Its saved
answers and all charges are retained separately and excluded from the score.
One in-flight smoke response was not saved after the consumer was stopped;
its completed provider charge and token usage remain in the ledger. The first
cohort also retains a native-chat failure's generic error and timing, but not
that old error's raw response body. The runner now retains raw native error
receipts for subsequent failures.

The pinned Hindsight image supplies only the local tokenizer and reranker.
No Hindsight memory service or ELF product runs. RAGFlow runs through AMD64
emulation on ARM. The first cohort used concurrent parser lanes; the capability
cohort uses one lane. Timings are observations, not an
isolated throughput or production-speed ranking.

## Scoring and source audit

The strict answer rubric removes citations, normalizes Unicode and whitespace,
and checks all requested facts without forbidden alternatives. Numeric facts
use digit boundaries, so `42` does not match `420`. Unsupported questions must
return `unknown`. All answers also receive semantic review with the previous
comparison's rule for explicit, supported statements of missing information.
That rule applies only to questions whose original source has no answer. A
refusal caused by lost OCR content on a supported question remains a pipeline
failure. Strict and reviewed scores remain separate. The reviewer is this
Codex agent, not an independent blinded human panel.

The frozen scorer has a material limitation: removing all whitespace credits
split identifiers such as `NIG HT-A-864` as `NIGHT-A-864`. A uniform, post-hoc
literal-identifier audit therefore checks every answer that requests a queue or
approval code. It uses the unchanged oracle values. Original automatic scores
remain intact; the reviewed usability score rejects a code that cannot be
copied as its stated value. This audit is a disclosed scoring correction, not
a pre-registered metric. The complete capability cohort repeats every question
under the new user-requested settings, regardless of its previous answer.

Key-span retention is checked separately in original pre-parser text and in
native indexed chunks. For numeric table spans, whitespace does not join
adjacent numeric cells. HTML markup is removed without merging cells. Chunks
are deduplicated by chunk ID and bound to their actual `docnm_kwd`; the chunk
list endpoint can return other documents despite a document-specific route.
Source attribution is therefore not inferred from the request URL.

This metric checks selected values, not full character error rate, exact page
coordinates, or complete table structure. A correct answer does not prove that
all unasked fields survived. All returned source IDs map to known uploaded documents. The requested owner
name is absent from the free pipeline's indexed chunks and both answer inputs.
Other selected answer values are present, including the numeric amount whose
currency label was lost. All 180 old/new input pairs match after removal of
RAGFlow's post-answer timing trailer. No shared-reader context is truncated;
the largest retained contexts are 1,730 tokens for free, 1,963 for Mistral, and
1,998 for DeepDOC under the common tokenizer.

| Parser | Low/8,192 shared, normalized | Low/8,192 native, normalized | Max/943,718 shared, normalized | Max/943,718 native, normalized |
| --- | ---: | ---: | ---: | ---: |
| Free | 28/30 | 27/30 | 28/30 | 26/30 |
| DeepDOC | 28/30, one incomplete | 27/30 | 29/30 | 27/30 |
| Mistral | 30/30 | 29/30 | 30/30 | 30/30 |

Under the reviewed usability rubric, the old cohort scores were free 28/28,
DeepDOC 25/26, and Mistral 30/30, with each number out of 30 for its answer path.
The capability profile changes DeepDOC's shared-reader score to 26/30; the other
reviewed totals remain unchanged. These differences are small and are not a
statistical estimate of the effect of reasoning effort.

## Failure analysis

The free pipeline's two content errors persist in both model profiles and are
in the scanned Chinese document:
`周宁` becomes `周末`, and `人民币` becomes `AEST`. Both answer paths repeat the
wrong name and decline to give the RMB amount. The number `6200` itself survives,
so a value-only span check does not capture the lost currency label. The second
lost key span is the unasked alternate name `许岚`. These results demonstrate why
selected-span retention alone is insufficient.

DeepDOC preserves the Chinese names and currency correctly. In the mixed PDFs,
its indexed text contains `NIG HT-A-864`, `NIG HT-B-864`, and `SIG N-B-529`.
In the first cohort, both answer paths repeat all three split identifiers. Its 58/58 normalized
span result therefore does not mean character-exact fidelity. The exact-code
audit passes 3/6 requested identifiers per answer path for DeepDOC and 6/6 for
each other pipeline in that first cohort.

The DeepDOC-to-index path also changes table structure in both table PDFs.
The first-page source has four data rows. Indexed HTML combines East Basic,
East Pro, and West Basic into lists in one row, merges the region cell as
`East West`, and places column-header labels inside that row. The HTML has only
two rows with data cells. This is a source-backed qualitative observation, not
a new aggregate layout score. It locates a problem in the parser-to-index
representation; it does not isolate one OCR recognizer or table model.

In the first cohort, the scanned table also causes answer failures. Native
chat returns `1310` for the East Pro fee whose source value is `1420`. The
shared reader hits the 8,192-token limit twice on that question and returns
`6` instead of `8` for the West Basic on-call limit. The values themselves are
present in the indexed text, but their row relationships are damaged. This
separates retained values from usable table semantics.

In the capability cohort, the shared reader completes the formerly truncated
East Pro question with 8,399 output tokens, including 8,378 reasoning tokens,
and `finish_reason=stop`. It answers `620`, not `1420`. Native chat answers
`1620` on that question and `12` instead of `8` for a different table's on-call
limit. One of those native questions was correct in the earlier cohort. More
reasoning is therefore not a reliable repair for damaged row relationships.
The experiment does not isolate a causal effect of reasoning effort from
sampling variation.

The shared reader still copies all three split codes. Native chat repairs
`NIGHT-B-864` but still returns `NIG HT-A-864` and `SIG N-B-529`. Literal-code
fidelity is thus 3/6 for DeepDOC shared reading and 4/6 for its native chat in
the capability cohort. Free and Mistral remain 6/6 in each path. This is why a
normalized 29/30 must not be presented as 29 directly usable answers.

## Cost and limits

The full task adds USD 0.215445472 in reported charges, including OCR, both
answer cohorts, failed attempts, and interface probes. Cumulative reported
spend is USD 16.016510508. Conservative exposure is USD 17.004390808 under the
unchanged USD 20 ceiling; unresolved historical reserves remain in place.
The experiment does not include unrelated account usage or local CPU costs.

Mistral's six OCR requests cover 12 pages and report USD 0.0243606. The engine
component is USD 0.024, or USD 0.002/page; USD 0.0003606 is the acknowledgement
model component. Original annotations supply the parsed content. The short
acknowledgement's output budget does not truncate the OCR annotations.

The formal capability cohort adds USD 0.085909908 for 180 answer calls and 180
query embeddings. It uses 377,690 chat input tokens, including 100,096 cached
input tokens, and 73,229 output tokens. These are provider-reported charges
with cache savings included, not uncached list-price estimates.

| Parser | API cost for both answer paths, 60 answers | Shared-reader output tokens, 30 answers | Native-chat output tokens, 30 answers |
| --- | ---: | ---: | ---: |
| Free | USD 0.02107146 | 7,636 | 5,995 |
| DeepDOC | USD 0.042775668 | 36,208 | 10,649 |
| Mistral | USD 0.02206278 | 6,334 | 6,407 |

This table excludes document ingestion and OCR. DeepDOC's shared reader uses
about 5.7 times Mistral's output tokens in this run. That is an observed cost
of answering this fixture from these representations, not a universal pricing
comparison. The serial capability controller takes 1,430 seconds (23 minutes
50 seconds), excluding the earlier PDF parsing and review.

The fixture is small, synthetic, and uses related layouts. It does not cover
handwriting, damaged scans, photographs, vertical text, multilingual mixtures,
or large-corpus retrieval. The packaged Tesseract models are one free baseline;
this is not an exhaustive comparison of free OCR engines. Do not generalize a
clean-table score to all complex enterprise documents or a whole-product rank.

## Delivery evidence

The new [fixture](../../../config/benchmark/fixtures/parser-stress-v1/README.md)
and [public receipts](../../../config/benchmark/evidence/2026-10-10-parser-stress/manifest.json)
retain source hashes, per-page extraction, original OCR annotations, native
chunks, both complete case sets, failure attempts, scoring reviews, model
limits, runtime versions, usage, and cleanup evidence. The old cohort retains
its incomplete answer explicitly; the capability cohort is complete.
`best-profile/` contains the capability results. `output-limit-probes/` contains
the excluded interface checks. Export uses an explicit allowlist and scans for
the private native credential and credential fields.

Run the offline receipt verifier from the repository root:

```sh
python3 config/benchmark/evidence/2026-10-10-parser-stress/verify_receipts.py
```

It checks manifest hashes, answer identities, frozen scores, and review bindings.
It does not replace semantic source review. `cargo make test-benchmark-runner-contract` passes all 150 tests. Fixture regeneration
matches the frozen PDF hashes; all 12 rendered pages were visually inspected.
`cargo make check-docs` validates the final documentation.

Cleanup removed eight owned containers, six volumes, one network, nine new
images, and the task's 66.74 MB build-cache record. No global prune was used.
Docker-reported image size fell from 14.82 GB to 8.916 GB, and volume size from
21.38 GB to 19.74 GB. These are Docker category totals, not a measurement of
unique physical host bytes. All pre-existing service names remain present;
one unrelated helper already had a replacement container identity, recorded
in the cleanup receipt. Private native tokens and stack credentials were
removed after the export check.
