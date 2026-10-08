---
type: Reference
title: ELF documentation and benchmark entrypoints
description: Navigate source documentation, bounded benchmark commands, and measured calibration evidence.
tags: [navigation, benchmark, documentation]
sources:
  - id: openwiki-source-c5e96b968f291ecf02395ce1
    resource: repo://config/benchmark/benchmark-v3.json
  - id: openwiki-source-0e54ac6a76b520718715ada9
    resource: repo://docs/runbook/benchmarking/full_comparison.md
  - id: openwiki-source-b538bf9444154fadde51c713
    resource: repo://makefiles/benchmark-core.toml
  - id: openwiki-source-f60eab131a2a5ca64cad7bb0
    resource: repo://scripts/benchmark_replay/cli.py
  - id: openwiki-source-6edf395d285ada6626e2d809
    resource: repo://scripts/benchmark_runner/cli.py
generated: { by: "codex", at: "2026-10-08T02:56:52.103Z" }
verified:
  - by: openwiki/0.7.1
    at: 2026-10-08T02:56:52.103Z
---

# ELF documentation and benchmark entrypoints

This focused wiki covers benchmark calibration. It is not a complete regeneration
of the existing architecture documentation.

## Find the correct owner

- [Documentation index](../docs/index.md): product specifications, operations,
  architecture, research, and dated evidence.
- [Documentation policy](../docs/policy.md): documentation lanes and evidence rules.
- [Agent setup](../docs/runbook/agent-setup.md): local setup and agent integration.
- [Bounded benchmark modes](../docs/runbook/benchmarking/benchmark_modes.md):
  commands, baselines, replay receipts, and interpretation limits.
- [Full comparison protocol](../docs/runbook/benchmarking/full_comparison.md):
  fixed coverage, native profiles, budget controls, deep workloads, and acceptance.
- [Calibration and comparison](benchmarking/calibration-and-comparison.md): measured
  spend, lifecycle behavior, scoring repairs, and unmeasured workflows.
- [Repository repair runbook](../docs/runbook/benchmarking/repository_memory_replay.md):
  historical source snapshots, four memory conditions, isolated tests, and budget setup.
- [Repository repair evidence](../docs/evidence/benchmarking/2026-10-07-repository-replay.md):
  corrected paired results, all diagnostic failures, and cumulative API accounting.
- [Initial October 7 evidence](../docs/evidence/benchmarking/2026-10-07-bounded-calibration.md):
  the complete dated report and links to checked-in machine-readable observations.

## Benchmark entrypoints

Run from the repository root. `Makefile.toml` extends the focused makefiles and
owns public task behavior. Inspect selection before provider access or builds:

```sh
cargo make benchmark-competitors --plan
cargo make benchmark-competitors --mode measure --plan
cargo make benchmark-competitors --mode compare --plan
```

Quick mode is offline. Measure selects ELF and local baselines over 18 named
scenarios. Compare selects all four suites for fourteen products and two baselines.
The complete core matrix has 64 units and 768 logical cases.
Time and unit limits do not cap every product's internal API cost.

The current manifest fixes DeepSeek V4.1 Flash and the DeepSeek route, with
Qwen3 Embedding 8B through DeepInfra where external embeddings apply. Paid work
must use the cumulative ledger through `cargo make benchmark-budget`. Time
limits alone do not enforce the USD 10 ceiling. Keep prior spend and reservations
for unknown costs in that same ledger.

| Task | Purpose |
| --- | --- |
| `benchmark-budget` | Admit paid requests against the cumulative ledger and a phase tranche |
| `benchmark-deep` | Run scale, cross-session, authority, namespace, and mutation workloads |
| `benchmark-qmd-host` | Run native QMD with an existing host checkout and local models |
| `benchmark-replay` | Run common historical repair trials with a selected native memory target |
| `benchmark-letta` | Run the separate native Letta Code memory and repair condition |

Use each task's `--help` and the full comparison runbook for required paths and
options. Native-only execution has no shared-reader answer result. Reuse retained
native bundles with `--reanswer` when reader responses need regeneration; use
`--rescore` for supported offline scoring revisions. The final reader protocol
isolates each case in its own request. A successful offline check or configured
matrix does not establish completed coverage or product superiority.

For deep follow-ups, `--workload-group` selects a fixed group in fresh state;
`behavior` contains all 42 non-scale questions. Keep an extended-readiness run
separate from its original timeout. For scoring changes, preserve original
answers and apply the current reviewed contract uniformly. See the
[methodology page](benchmarking/calibration-and-comparison.md) for date and
requested-fact corrections and their limits.

## Repository memory replay

`cargo make benchmark-repository-memory` and `cargo make benchmark-replay`
dispatch the same repair CLI. Use `--target` for native preparation and
`--arm` for the matching repair condition. Its
phases are `prepare`, `validate`, `learn`, `retrieve`, `run`, and `report`. Start
with frozen source and offline oracle validation before provider access:

```sh
cargo make benchmark-repository-memory prepare --out /absolute/run-directory
cargo make benchmark-repository-memory validate --out /absolute/run-directory
```

The runbook defines the required Docker image, provider environment, phased
execution, and immutable trial directories. Paid phases require an authorized
budget control; this command itself does not impose an account spending limit.
The historical October 7 pilot kept the $10 cumulative ceiling and finished at $0.094396915,
including the earlier calibration and diagnostic failures.

The corrected pilot used three task families and two repeats. No memory passed
5/6; file search, Git notes, and ELF each passed 6/6. This is a small real-edit
calibration, not proof of ELF superiority or complete competitor coverage. Keep
native indexing readiness separate from task success, and include memory setup
cost when comparing conditions.
