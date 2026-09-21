---
type: Runbook
title: "Bounded Benchmark Modes"
description: "Run offline checks, ELF baseline measurements, and explicit competitor comparisons."
resource: docs/runbook/benchmarking/benchmark_modes.md
status: active
authority: procedural
owner: benchmarking
last_verified: 2026-09-21
code_refs:
  - scripts/benchmark_runner/cli.py
  - scripts/benchmark_runner/profiles.py
  - scripts/benchmark_runner/checkpoints.py
  - scripts/benchmark_runner/baselines.py
  - scripts/benchmark_runner/runtime.py
  - scripts/tests/test_benchmark_modes.py
related:
  - docs/reference/benchmark-target-lifecycle.md
  - docs/research/2026-09-20-elf-value-review.md
---
# Bounded Benchmark Modes

Purpose: Obtain bounded, reproducible feedback without running the entire competitor matrix.
Read this when: Checking a change, measuring ELF against simple baselines, or resuming a run.
Not this document: Proof of superiority, production acceptance, or a full agent-task benchmark.

## One entrypoint

Run all commands from the repository root. The existing Python benchmark owner is
retained under the repository engineering conventions; no new runtime is required.

```sh
cargo make benchmark-competitors --plan
cargo make benchmark-competitors --mode quick --max-seconds 240
cargo make benchmark-competitors --mode measure --max-seconds 1800 --max-units 12
cargo make benchmark-competitors --mode compare --only-target qmd --max-seconds 900
```

The default is now `quick`. `compare` explicitly selects the former full competitor
scope, plus the two baselines. Use `--plan` to inspect all scheduled jobs and pins
without reading provider configuration, building images, or creating artifacts.
`--only-target` selects one maintained product or baseline; it does not bypass
suite eligibility. `--job-limit` is an explicitly diagnostic deterministic subset,
not a representative quality claim. Zero and out-of-range limits fail.

| Mode | Execution | Default sample | Result authority |
| --- | --- | --- | --- |
| quick | `cargo make test`, then no-memory and persisted-file search | 18 named scenarios across four suites; 8 baseline units | Source tests and offline pipeline integrity. No ELF runtime or model answers. |
| measure | ELF, no-memory, files-search; one shared answer model and fixed suite inputs | Same 18 scenarios; 12 units | A small product retrieval/lifecycle comparison, not end-to-end agent task utility. |
| compare | Ten retained products plus both baselines | All 48 scenarios with per-product suite eligibility; 32 units | Frozen-version comparative evidence; execution failures remain visible. |

The selected sample includes direct lookup, synthesis, correction, work resumption,
scope traps, abstention, update, delete, combined mutations, document structure,
repository changes, and citation boundaries. `report.md` lists every selected job.
A passing sampled run cannot claim coverage of omitted jobs.

## Baseline boundaries

`no-memory` supplies no retrieved context. `files-search` writes each task's input
records to disk, applies explicit update/delete operations, reads them back, and
ranks by case-folded query-token overlap. It has no learned memory, ACL engine,
semantic index, or inferred updates. It is a transparent lexical baseline, not a
replacement for native host memory plus maintained project files.

Only opaque product fixtures enter either baseline. Expected answers, qrels,
privacy labels, and scoring rules remain in the central evaluator. Offline runs
leave answers absent; they do not manufacture answers from gold data. Live runs
use the same answer stage as ELF. Source preparation/curation cost and multi-session
agent behavior are not measured by these baselines.

## Budgets and timing

`--max-seconds` bounds external subprocess and shared-answer request waits.
Command timeouts terminate their process group. Cleanup has a separate 180-second
reserve so a time limit does not intentionally leave containers behind. Cleanup
failure fails acceptance. Small in-process JSON operations are not preempted.

`--max-units` bounds newly attempted units. Reused results do not consume a unit.
Unstarted scheduled units are explicitly recorded as timeout failures; they never
vanish from the denominator. No unbounded automatic retry is performed.

The report bundle records preflight, build, total, and unit duration. Container
units also record runtime, log/cleanup, shared-answer, and evaluation duration;
product payloads retain ingest/query measurements where supplied. Shared-answer
usage is retained when the provider supplies it. This is not a dollar cap: native
product adapters may make multiple model calls within a unit. Do not claim a cost
or speed improvement without matched repeated measurements. Image preparation can
consume the full budget on a cold host. ELF uses the `elf-runtime` build stage
and does not prepare qmd or mem0 dependencies for an ELF-only measurement.
Products remain serial to preserve the existing provider contention boundary.

## Resume safely

```sh
cargo make benchmark-competitors --mode measure --resume tmp/benchmark-v5/PRIOR_RUN --max-seconds 1800
```

Each run writes to a new directory. Receipts are atomic and bind source state,
manifest, exact selected suites, mode, provider routes/models, and built image IDs.
Only complete units with successful cleanup, replay, and coverage can be reused.
The raw result is evaluated again and must match the recorded evaluation. Changed
identity, malformed receipts, and failed units cause execution rather than reuse.
The hashes detect accidental modification; these are trusted local artifacts, not
signed evidence from an untrusted contributor.

Reused rows name the original receipt and remain historical timing samples. The
current implementation still prepares providers/images before reuse, and it does
not reuse live mutable product databases across scenarios. `--skip-build` is an
operator option for existing images; their image IDs are recorded. The shared ELF image must also declare the current Git HEAD in its source label;
an older or missing label is rejected. Dirty-source runs remain diagnostic only.

## Acceptance and limits

Execution acceptance checks exact scheduled target coverage, both phases, typed
completion, cleanup, and deterministic replay. Empty/partial/failed runs fail.
Quality is separate: recall, nDCG, answer correctness, and seeded invariant failures
remain in the bundle/report. ELF seeded forbidden-content and mutation violations
return a nonzero exit code even when execution completed. Baseline quality failures
remain comparison evidence; they do not make an otherwise valid run disappear.

Unmeasured in this sample: native host memory, autonomous task completion, Chinese
inputs, actual tenant ACL enforcement, restart recovery, and large-corpus behavior.
Use the existing integration and E2E tasks for their supported contracts. Adding
these benchmark dimensions requires new scenarios and independent outcome checks;
renaming the old fixtures does not supply that evidence.

Live execution requires the existing embedding and LiteLLM configuration. Missing
configuration produces a failed report with value-free prerequisite status. Never
put secret values in CLI arguments or published artifacts. Private run artifacts
remain local. A provider-backed run is not implied by successful offline tests.
