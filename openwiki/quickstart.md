---
type: Reference
title: ELF documentation and benchmark entrypoints
description: Navigate source documentation, bounded benchmark commands, and measured calibration evidence.
tags: [navigation, benchmark, documentation]
sources:
  - id: openwiki-source-b538bf9444154fadde51c713
    resource: repo://makefiles/benchmark-core.toml
  - id: openwiki-source-f60eab131a2a5ca64cad7bb0
    resource: repo://scripts/benchmark_replay/cli.py
  - id: openwiki-source-6edf395d285ada6626e2d809
    resource: repo://scripts/benchmark_runner/cli.py
generated: { by: "codex", at: "2026-10-07T16:08:29.830Z" }
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T16:08:29.830Z
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
scenarios. Compare selects the full suite set with target-specific eligibility.
Time and unit limits do not cap every product's internal API cost.

The October 7 diagnostic overrode the chat model with DeepSeek V4.1 Flash and
used a temporary budget gateway. It did not replace the checked-in provider
configuration or install that gateway as a repository feature. A successful
execution or offline check is not evidence of product superiority.

## Repository memory replay

`cargo make benchmark-repository-memory` runs the bounded repair pilot. Its
phases are `prepare`, `validate`, `learn`, `retrieve`, `run`, and `report`. Start
with frozen source and offline oracle validation before provider access:

```sh
cargo make benchmark-repository-memory prepare --out /absolute/run-directory
cargo make benchmark-repository-memory validate --out /absolute/run-directory
```

The runbook defines the required Docker image, provider environment, phased
execution, and immutable trial directories. Paid phases require an authorized
budget control; this command itself does not impose an account spending limit.
The October 7 run kept the $10 cumulative ceiling and finished at $0.094396915,
including the earlier calibration and diagnostic failures.

The corrected pilot used three task families and two repeats. No memory passed
5/6; file search, Git notes, and ELF each passed 6/6. This is a small real-edit
calibration, not proof of ELF superiority or complete competitor coverage. Keep
native indexing readiness separate from task success, and include memory setup
cost when comparing conditions.
