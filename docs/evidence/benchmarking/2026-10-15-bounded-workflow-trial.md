---
type: Evidence
title: Bounded maintenance trial without attributable memory benefit
description: Record the two stopped maintenance batches, integration limits, and unscored reporting repairs.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-15
related:
  - docs/decisions/2026-10-15-workflow-pilot.md
  - docs/reference/product-direction.md
  - docs/evidence/benchmarking/2026-10-15-qualified-memory-evidence.md
code_refs:
  - scripts/benchmark_pilot/report.py
  - scripts/benchmark_pilot/export.py
  - scripts/benchmark_pilot/verify_export.py
---
# Bounded maintenance trial without attributable memory benefit

This trial did not establish an incremental memory benefit. Every formal reader
used ordinary file tools; none called native source retrieval or memory. The
first batch also violated its tool-output budget contract. The second batch had
one local request-size stop and no completed handoff files. Its functional test
results must not be presented as a memory ranking or customer acceptance.

The paid experiment is closed. No third batch will repair these scores. The
finite workflow adapter is removed from active commands. Its recorded code,
inputs, patches, traces, and receipts remain available for audit. The existing
product APIs, extractor, memory-first reader, PG+Qdrant stores, and memory limits
are unchanged.

## What was attempted

Two maintenance tasks used the current ELF checkout at
`da5b18e53469f082a20cfde36f5f8fd7cae108de`:

1. Carry an opening settlement through public budget reporting and verification.
   The second session clarified treatment of unknown, invalid, and cached costs.
2. Verify budget-stopped evidence without changing planned counts. The second
   session clarified symmetric treatment of missing or runtime-failed pairs and
   retention of invalid answers in the comparison.

Each batch had three arms and two repetitions. Each trajectory had two fresh
processes and conversations. Six calibration sessions and 24 formal sessions
were recorded, including one interrupted formal session. Every arm could read a
complete current checkout, edit files, run Python checks, and save `HANDOFF.md`.
Native arms also had document search; the full-ELF arm had derived memory tools.
They ran in isolated Docker checkouts without network or host credentials.

These were authored, prospective maintenance episodes. They were not natural
customer sessions, and their scripted clarifications were not measured human
corrections. They added requirements rather than testing withdrawal of an earlier
business decision. The prototype used optional tool selection, which differs
from the shipped memory-first reader. It therefore did not validate that formal
Agent integration.

## Observed results

“Functional pass” means that the frozen, host-owned program accepted the final
patch. It does not mean that the complete workflow, the patch's own tests, or a
customer task passed. No functional check was run for the interrupted trajectory.

| Batch | File tools | Files plus source index | Files plus source index and memory | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Opening settlements | 0/2 | 0/2 | 0/2 | All six trajectories encountered a runner budget defect; diagnostic only. |
| Partial evidence | 1/2 | 1 pass, 1 local stop | 2/2 | Functional results only; no native tools were used and no handoff was completed. |

The second repetition in the partial-evidence batch has an unavailable source
arm. Excluding that repetition symmetrically leaves one matched trajectory per
arm: file tools failed, source availability passed, and memory availability
passed. Both passing agents used file tools. This does not isolate a source-index
or memory effect from model variation or the different offered tool schemas.

Only one of the twelve formal trajectories produced a handoff before the second
session; it was in the diagnostic first batch. No second-batch trajectory left a
handoff at closure. One passing functional patch also reported failing self-tests.
The report retains these distinctions rather than upgrading functional passes to
complete workflow acceptance. Natural human-correction rate was not measured.

| Partial-evidence arm | Paid cost, including preparation and the stopped attempt | Sum of two-session Agent time |
| --- | ---: | ---: |
| File tools | $0.032980485 | 381.8 s |
| Source index available | $0.037996960 | 441.3 s |
| Full ELF available | $0.033554560 | 339.8 s |

Times exclude native preparation and are descriptive. The interrupted arm is not
an equivalent completed-work denominator. Provider latency, cache state, and
shared-host load were not controlled. The public bundle also records preparation
and available trajectory times. Identical command counts include necessary
checks and do not independently measure wasted investigation.

## Failure boundaries and protocol deviations

- Calibration repaired an owner mismatch in the prototype runtime and corrected
  generated work records from fictitious Git locators to the existing chat-source
  contract. No recorded model conversation was repeated.
- The live source policy rejected `scripts/benchmark_budget.py`. The heuristic
  matches dynamic assignments such as `token = secrets.token_hex(24)` and
  `API_KEY=token`; those expressions are not literal credential values. Before
  the first formal native reader, the controller was changed to retain this
  refusal and allow the unchanged file access already available to all arms.
  This was a protocol deviation after the first file-only trajectory. The index
  remained incomplete. The source bytes and product admission policy were not
  changed.
- The first batch counted raw shell output before JSON escaping, which could
  exceed its declared 65536-byte limit. Exhausting that budget also blocked file
  actions. All six first-batch trajectories were affected. Before the second
  batch, serialized output was bounded and file actions could continue with
  output omitted. Control-only acknowledgements are recorded separately.
- Git snapshot operations moved inside the isolated container before the second
  batch. A filter-canary check confirmed the boundary. No result depended on an
  intentional Git filter; this was a prototype isolation repair.
- One second-batch conversation reached the unchanged 196608-byte local request
  limit. The gateway returned HTTP 413 before a provider invocation. It was not
  an upstream model failure. Its recorded work was retained; only unstarted
  trajectories continued.

The task requests, hidden functional programs, source checkout, model route,
output-token allowance, and repetition count did not change. These retained
inputs do not remove the effects of the protocol deviations. The first batch
must not be pooled with the second to claim improvement.

The capture policy indexed selected base files, staged requests, and a handoff
when the agent wrote one. It did not ingest complete session transcripts, and
it did not refresh the indexed code with each uncommitted working-copy edit.
Working copies remained available through the common file tools. Generated
records used the base checkpoint timestamp, so this run does not validate
real-world effective-time or correction semantics.

## What this changes

Stop this synthetic maintenance optimization line. For these short repository
maintenance tasks, use the current checkout and explicit file handoffs as the
working approach. This is a scoped operating choice under unproved benefit; it
is not evidence to remove memory from unrelated workflows or change the shipped
memory-first contract.

Do not add fields, graph layers, models, or databases to rescue these outcomes.
A future value test needs an actual continuity need, the intended production
Agent integration, observed capture and memory use before comparison, and a
capable baseline with realistic context limits. If calibration only proves that
an API works while the agent never uses it, stop before the formal comparison.
This trial exposed that distinction too late.

The maintenance defects were then fixed directly, outside the scored trial:
opening balances and unknown costs reconcile with the gateway; public exports
include frozen task counts; partial verification keeps original plans and excludes
unavailable pairs symmetrically. Invalid answers remain scored outcomes. These
repairs and their regression checks are not attributed to any benchmark arm, and
no saved answer or score was replaced.

## Cost, integrity, and delivery

The run made 377 new paid provider requests. It added **$0.195383370** to the
existing ledger. Cumulative settled cost is **$1.882564841** and conservative
exposure is **$1.953049641** of the authorized $10. The historical unresolved
$0.0704848 reservation remains. Calibration, extraction, indexing, failed work,
and cache charges are included; local compute and Codex session usage are not
priced in this ledger.

The reader and extractor remained OpenRouter `openai/gpt-6-luna`, standard OpenAI
route, medium reasoning, with the full 128000 output-token allowance. The
[endpoint metadata](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints)
was checked before execution. Embeddings remained Qwen3-Embedding-8B through
Nebius at 4096 dimensions. The prototype's tool-output and request-size limits
were separate from the model's native context and output capacity.

All ten native stores passed isolated PostgreSQL/Qdrant restores, source-hash
comparison, and stored-vector checks. Their containers and volumes were removed
only after lossless compressed archives were verified. Original inputs, model
traces, patches, and failed attempts remain private. Existing historical evidence
bundles were not edited.

The [public bundle](../../../config/benchmark/evidence/2026-10-15-bounded-workflow-trial/manifest.json)
contains de-identified measurements, incremental provider charges, input hashes,
protocol deviations, restore metadata, and a standalone verifier. It checks
integrity and arithmetic; it does not independently reproduce private task
judgments or prove product value.
