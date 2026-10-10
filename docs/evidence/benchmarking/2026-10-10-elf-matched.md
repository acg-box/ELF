---
type: Evidence
title: ELF matched document and memory comparison
description: Measure the formal ELF API on the frozen Hindsight and RAGFlow workloads.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/evidence/2026-10-10-elf-matched/protocol.json
  - config/benchmark/evidence/2026-10-10-final-system-comparison/frozen-workloads.json
code_refs:
  - scripts/benchmark-elf-matched.py
  - scripts/benchmark_deep/elf_runtime.py
related:
  - docs/evidence/benchmarking/2026-10-10-final-system-comparison.md
---
# ELF matched document and memory comparison

**ELF scores 90/100 in both conditions on this workload.** All 140 planned
case attempts have a result: 120 completed answers and 20 native Chinese-input
rejections. The English document answers and scored memory answers are all
correct under the same disclosed semantic rubric as the previous comparison.
The 10 Chinese questions fail in each condition.

| System and condition | Documents | Memory test | Weighted score |
| --- | ---: | ---: | ---: |
| Hindsight native, previous matched run | 50/50 | 16/16 | 100/100 |
| RAGFlow native, previous matched run | 50/50 | 16/16 | 100/100 |
| ELF Context Pack + shared reader | 40/50 | 16/16 | 90/100 |
| ELF retrieval + shared reader | 40/50 | 16/16 | 90/100 |

The previous Hindsight and RAGFlow shared-reader conditions also scored 100/100.
Within the English-only subset, ELF answers 40/40 document and 16/16 memory test
questions correctly. This is parity on an easy, small fixture, not evidence
that ELF leads. More importantly, **ELF persisted zero extracted memory notes**:
all 20 event ingestions failed. The final memory answers rely on the separately
submitted Source Library records. An event-only deployment would not have that
backup in this run.

The next priority is the extractor schema and error handling, followed by an
explicit multilingual input path that retains original evidence. Rerunning the
whole suite is not needed to establish these two defects.

## Scope

This run tests ELF source revision
`45663eb4c04e5bb3082b8f7463b0deb48404fe00` through its formal HTTP API and worker
in Docker. No ELF product code changes are included. Both conditions use the
same DeepSeek V4.1 Flash reader as the previous comparison. ELF has no native
final-answer endpoint; neither condition is a native reflect implementation.

The input is exactly the previous frozen workload: 14 retained Mistral OCR
annotations, 50 document questions, 20 dated memory records, and 20 memory
questions. Four memory questions are development cases and do not contribute
to the score. No OCR or competitor calls are repeated. The two ELF conditions
produce 140 outputs, which represent 66 scored questions plus four development
questions tested twice. The previous competitor results are historical matched
inputs, not simultaneous reruns.

- **Context Pack + reader:** native Context Pack selection with a limit of 32.
  The harness resolves only the selected document or note references through
  native APIs. No additional context truncation is applied to that selection.
- **Retrieval + reader:** native Source Library retrieval and memory search,
  with 12 hits and 60 candidates per source. The shared reader receives at most
  4,096 `cl100k_base` tokens, as in the previous retrieval comparison.

The weighted score is `50 * document_accuracy + 50 * memory_test_accuracy`.
Operational failures remain in the denominator. Costs and observed times are
reported separately. The suite is small, synthetic, and already known; the
scores do not establish a general product ranking.

## Configuration and input handling

The service uses `elf.example.toml` defaults, Qwen3 Embedding 8B at 1,536
dimensions, and the same CPU cross-encoder service as the earlier comparison.
Each product retains its own retrieval implementation: configuring the shared
reranker does not mean every ELF retrieval surface calls it. Document search
uses its native Source Library path. The configured word tokenizer is the
pinned GPT-2 tokenizer recorded in the evidence, with native 512-token chunks
and 128-token overlap. This tokenizer is a chunking unit, not a claim about
DeepSeek's tokenizer.

The two suites have separate authenticated ELF projects. All source text goes
through `/v2/docs`. Memory records also go through `/v2/events/ingest` with their
original timestamps. The harness explicitly submits each memory record to both APIs; ELF event
ingestion does not automatically provide this Source Library backup. The answer
oracle is used only for evaluation. The
harness waits for native indexing to finish before queries.

The gateway requests maximum reasoning and 943,718 output tokens for internal
and reader calls, matching the previous run. The previous provider inspection
reported a lower route maximum of 393,216; the harness does not apply a smaller
local output cap. Requested limits are distinct from provider behavior and
actual token usage. The independent cumulative ceiling for this run is USD 10.

## Observed ingestion defects

ELF accepted 32 of 34 source records. Its mandatory English input policy rejected
the two Chinese documents. Their original OCR text is unchanged and retained in
the frozen workload. Upstream translation is part of ELF's documented contract,
but it is absent from this matched-input condition. Adding translation would
be a separate intervention, with separate fidelity checks and costs.

All 20 event ingestions failed before note persistence. The first failure was
retried once; later failures were retained. The raw memory records remained
available through Source Library. Thus a correct memory answer can demonstrate
retrieval from dated original text while structured memory extraction is broken.
It does not establish that ELF's extracted memory or graph performed correctly.

Provider receipts contain a `notes` array. Relation dates such as `2026-08-01`
conflict with the RFC 3339 deserializer in
`packages/elf-service/src/time_serde/option.rs`. The built-in extraction example
specifies only `string|null` for these dates. The event handler discards the
serialization error and reports `Extractor output is missing notes array.`
This is a product contract and diagnostics defect, not an OCR defect. The
benchmark does not repair or normalize model output before passing it to ELF.

## Cost, timing, and review

The independent ledger contains 393 completed, explicitly priced requests.
Confirmed cost and conservative exposure both equal **USD 0.118841296**; there
are no unsettled requests. This is separate from the previous USD 20 ledger.
The final continuous command took 23 minutes 20 seconds, including service
restart, ingestion, index drain, and questions; earlier image build and setup
attempts are excluded from that elapsed figure but their paid calls remain in
the cost ledger.

| Phase or condition | Confirmed USD | Median query seconds | p95 query seconds |
| --- | ---: | ---: | ---: |
| Ingestion and earlier failed attempt | 0.038776814 | — | — |
| Document Context Pack + reader | 0.036203300 | 4.00 | 14.95 |
| Document retrieval + reader | 0.022000952 | 4.16 | 9.26 |
| Memory Context Pack + reader | 0.014635040 | 12.32 | 31.27 |
| Memory retrieval + reader | 0.007225190 | 10.62 | 38.19 |

Document latency includes the fast Chinese rejections; it must not be compared
as if all questions succeeded. Memory costs and latency include the four
development cases per condition. The failed extraction path also reduces
stored work, so this bill does not establish a functional cost advantage.

Chat used 458,516 input tokens (including 130,432 cached tokens) and 115,209
output tokens across 161 calls, costing USD 0.118729296. The 232 embedding calls
used 11,200 input tokens and cost USD 0.000112. Actual provider usage receipts,
not an uncached price estimate, determine the bill.

Strict matching gives 38/50 document and 12/16 memory test answers per
condition. Review corrects two numeric substring false negatives (`42` inside
`420`, `93` inside `930`) and accepts explicit source-backed absence of a budget
owner. Reviewed scores are 40/50 and 16/16. The rejected Chinese cases remain
incorrect; they are not excluded or translated after seeing the outcome.

All five owned containers, their anonymous volumes, the owned Docker network,
and two task-owned images were removed. Shared images, shared build cache, and
unrelated services remain. Temporary runtime credential files were removed.
The final database readback confirms 32 source documents, 32 source chunks,
zero memory notes, and zero pending document indexing jobs.

All completed answers are retained. Semantic review checks requested values,
identifiers, temporal qualification, and supported absence under the previous
rubric. It is not an independent blinded evaluation. The strict matcher remains
available alongside reviewed results; no answer is rewritten to improve a score.

The Context Pack condition runs before the retrieval condition, so caches and
order can affect timing. ELF and the shared sidecar run on ARM64; the previous
RAGFlow run used AMD64 emulation. Observed latency is not a production hardware
ranking. The API bill excludes local Docker compute and storage.

## Reproduction and evidence

Build the `elf-service-runtime` target in `docker/benchmark/Dockerfile`, set
`ELF_SOURCE_COMMIT` to the tested revision, and tag it
`elf-matched-service:20261010`. Run `cargo make benchmark-elf-matched` under
`cargo make benchmark-budget` with an independent ledger, USD 10 ceiling,
1,536-dimensional Nebius embeddings, maximum reasoning, forced 943,718 output
request, and DeepSeek price caps of USD 0.15/0.60 per million input/output tokens.
Use `--receipt-dir` to retain private request/response receipts; authentication
headers are not recorded. Inject the provider key into the gateway only.

The artifact root must be a `run` directory whose sibling
`cost-calibration/budget-ledger.json` is the same ledger given to the gateway.
The runner fetches the pinned tokenizer and starts isolated, labeled containers.
It requires Docker and host-managed repository tools. Source Library rejection
and event failure records are preserved alongside successful ingestion receipts.

Public evidence is in
`config/benchmark/evidence/2026-10-10-elf-matched/`. The manifest binds frozen
inputs, output receipts, manual review, provider usage, runtime identity, and
cleanup readback. Run its `verify.py` for an offline consistency check. Private
runtime configuration and authentication files are not published. The first
three provider requests predate optional full receipt capture; their usage
records are retained in the ledger.
