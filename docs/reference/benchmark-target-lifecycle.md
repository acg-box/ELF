---
type: Reference
title: "Benchmark Target Lifecycle"
description: "Separate current benchmark targets from retired product implementations."
resource: docs/reference/benchmark-target-lifecycle.md
status: active
authority: current_state
owner: benchmarking
last_verified: 2026-09-21
source_refs:
  - https://github.com/Zleap-AI/SAG
  - https://github.com/letta-ai/letta/blob/main/SECURITY.md
code_refs:
  - config/benchmark/benchmark-v3.json
  - scripts/benchmark_contract/fixtures.py
  - scripts/benchmark_runner/cli.py
related:
  - docs/research/2026-09-21-legacy-workspace-disposition.md
---
# Benchmark Target Lifecycle

Purpose: Define the current default comparison set and its historical boundary.
Read this when: Running `cargo make benchmark-competitors` or interpreting old results.
Not this document: A fresh measurement or a claim that retained target pins are latest.

## Current set

The competitor manifest retains ten targets: ELF, mem0, qmd, LightRAG, OpenViking,
Graphiti, GraphRAG, PageIndex, OpenKB, and Honcho. The four suite definitions,
scoring rules, and PageIndex eligibility boundary are unchanged. A reduction in
the matrix is not an improvement in measured performance. Do not compare an
aggregate from the new set directly with a twelve-target historical aggregate.

## Retired implementations

| Target | Removed implementation | Reason | Candidate replacement |
| --- | --- | --- | --- |
| SAG | June 26 revision `84a5b8c9bd45944b8a3cd76e0ba4762ce68ccc72`, TypeScript internal-service adapter and its database/container setup | Upstream replaced the architecture on July 14 and states that its old v1 branch is no longer maintained. | Current `zleap-sag` application/API, after an independent adapter review and measured run. |
| Letta | Legacy `letta/letta` Python server, archival-passage adapter and client lock | Upstream explicitly retires the V1 Python server and associated Docker images, including security updates. | `letta-ai/letta-code`, after checking whether its current product boundary matches the suite. |

Neither project is declared inactive. OpenKB and GraphRAG remain available:
slower development alone does not prove retirement. Other retained pins still
need separate freshness reviews; this change does not silently upgrade them.

The competitor manifest, target dispatcher, build list, Compose services, Dockerfiles,
and retired adapter dependencies no longer expose these two old implementations.
Explicit selection of a retired target fails before provider access or artifact
creation. Retired implementation-specific tests are removed; shared provenance,
mutation, failure classification, and scoring tests remain.

## Historical reproduction

Use repository revision `a996918ffba45d4055aba0508477b82b4246152b` or the exact
source revision recorded in an old result to inspect the previous manifest,
adapters, containers, and locks. Dependency availability is not guaranteed.
Historical reports and older fixture/smoke lanes remain dated evidence, not the
current competitor entrypoint or a statement that a retired server is supported.
Never run a retired server as a production service.

Preserve original bundle contents and matrix identities when rendering old
reports. Do not remove rows from a historical result or relabel an old SAG/Letta
measurement as a measurement of its replacement. This cleanup performs no paid
provider calls and produces no new competitor-quality results.

## Execution modes

The command now defaults to offline quick checks. Use `--mode compare` for this
competitor set. The measure and compare modes also include two local baselines.
See [bounded benchmark modes](../runbook/benchmarking/benchmark_modes.md).
