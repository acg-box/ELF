---
type: Reference
title: ELF documentation and benchmark entrypoints
description: Navigate source documentation, bounded benchmark commands, and measured calibration evidence.
tags: [navigation, benchmark, documentation]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T14:59:10.952Z
sources:
  - id: openwiki-source-6edf395d285ada6626e2d809
    resource: repo://scripts/benchmark_runner/cli.py
generated: { by: "codex", at: "2026-10-07T14:59:10.952Z" }
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
- [October 7 evidence](../docs/evidence/benchmarking/2026-10-07-bounded-calibration.md):
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
