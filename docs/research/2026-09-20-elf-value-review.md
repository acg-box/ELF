---
type: Research Contract
title: "ELF Value Review: September 2026"
description: "Assess ELF's value against native agent memory and define evidence-driven product priorities."
resource: docs/research/2026-09-20-elf-value-review.md
status: proposed
authority: exploratory
owner: product
last_verified: 2026-09-20
code_refs:
  - packages/elf-service/src/access.rs
  - packages/elf-service/src/context_pack/types.rs
  - packages/elf-service/src/context_pack/validation.rs
  - packages/elf-service/src/memory_corrections.rs
  - packages/elf-service/src/provenance.rs
  - config/benchmark/benchmark-v3.json
  - scripts/benchmark_contract/evaluation.py
  - docs/runbook/agent-setup.md
---
# ELF Value Review: September 2026

Purpose: Decide what ELF should prove before its next product expansion.
Read this when: You select memory product work or interpret old competitor reports.
Not this document: An accepted roadmap, a measured superiority claim, or authorization
for private-session ingestion, model calls, or an automatic memory migration.

## Judgment

ELF remains a plausible product for teams that need an independently controlled,
source-backed project memory across tools. Its value is unproven as a general
personal memory service. Maintaining a second memory system must improve actual
work enough to pay for capture, review, latency, setup, and operational cost.

Do not compete on the existence of persistence, vector search, background memory
consolidation, or context compaction. These are now baseline capabilities in major
agent products. Cross-harness portability also has existing implementations.
The narrower candidate is a shared project record with explicit authority,
correction history, revocation, and reproducible evidence under different agents.
This is an inference from the sources below and the current ELF code, not a market
share, user-demand, or competitor-quality measurement.

## What changed

| Primary source, checked September 20 | Observation | Implication for ELF |
| --- | --- | --- |
| [OpenAI Agents API, September 10](https://openai.com/index/introducing-the-agents-api/) | The public beta provides managed agent execution with compaction, tool use, and subagents. | Use the harness as an integration surface. Building another general harness is not the first priority. |
| [OpenAI Agents SDK memory guide](https://openai.github.io/openai-agents-js/guides/sandbox-agents/memory/) | The SDK documents file-based memory and generation/consolidation controls. | Persistent summaries and memory files must be part of the baseline comparison, not counted as an ELF-only benefit. |
| [Claude projects redesign, September 17](https://claude.com/blog/projects-redesigned) | The limited beta describes project coordination and memory shared across threads. Availability is staged. | Project continuity alone is no longer sufficient differentiation; do not describe the beta as universally deployed. |
| [Letta Trajectory, July](https://www.letta.com/blog/trajectory/) | Letta publishes a common representation for agent sessions and uses it across harnesses for memory formation. | Compare or reuse compatible public formats before inventing another transcript schema. Portability needs fidelity, authority, and deletion guarantees. |
| [Letta memory evaluation, July](https://www.letta.com/blog/evaluating-memory-in-production-agents/) | The evaluation separates memory use from generation and repair, using production-derived scenarios. | Test whether later behavior changes correctly, not only whether a relevant item was retrieved. Vendor results are not independent ELF comparisons. |

## Current ELF assets and friction

| Source-backed observation | Value or unresolved risk |
| --- | --- |
| `access.rs`, sharing operations, and tenant/project-scoped queries | Explicit read authority is a useful foundation for team memory. Existing tests do not prove every future connector preserves it. |
| `memory_corrections`, `provenance`, source refs, review queues, and version history | Corrections can remain attributable and reviewable instead of becoming another disconnected summary. End-to-end invalidation across exported or cached consumer context still needs proof. |
| `context_pack` and progressive retrieval | ELF can expose bounded references and explain routing. The pack budget currently counts items/per-layer rows; it is not an end-to-end token or latency budget. |
| Context Pack text validation | English-only request validation is a concrete friction point for Chinese or mixed-language project work. Do not simply disable validation without replacing its contract. |
| `docs/runbook/agent-setup.md` | The local stack requires Postgres/pgvector, Qdrant, API, and worker, with optional MCP and provider configuration. This is substantial overhead compared with memory files. |
| `benchmark-v3.json` and the contract evaluator | Central scoring, opaque fixtures, and typed failures are useful controls. A broader competitor matrix does not establish adoption value or preference over native memory. |
| Historical checked-in benchmark reports | They document earlier results and bounded claims. They do not prove superiority against September products or current model generations. |

## Priorities and stop conditions

### P0: Prove task-level benefit before adding another subsystem

Run a proposed pilot on roughly 30–50 representative, authorized project tasks over
several sessions. Include decision changes, agent handoff, conflicting sources,
revoked access, corrections, and stale instructions. Keep a held-out task set.

Compare the same source data, model, tool permissions, token budget, and task oracle:

1. No durable memory beyond the task's ordinary context.
2. The host's native memory with maintained project files and search.
3. The same host plus ELF; avoid counting duplicate native/ELF context as a benefit.

Where a hosted beta cannot be controlled, report it as an observational comparison,
not a causal benchmark. Run repeated trials and retain paired task outcomes. Judge
success with executable checks or independently specified outcomes; audit a sample
of any model judgments. Report failure, timeout, and unavailable-product cases.

Measure task completion, user corrections, repeated questions, stale-fact actions,
unauthorized disclosures, retrieval/context tokens, elapsed time, model spend,
service resource cost, and human memory-maintenance effort. Separate memory creation,
selection, and use failures. This review does not claim these measurements exist.

Proposed continuation rule: show a repeatable gain over the best native/file baseline
on the selected workflow with an acceptable total cost, while every seeded access,
delete, and correction invariant passes. Set a minimum useful effect and confidence
method before the pilot. If the gain is absent, narrow ELF to an internal audit and
memory-governance utility instead of funding a broad memory platform.

### P1: Complete one cross-tool correction and handoff workflow

Start with one project and two real agent clients. Build on the existing HTTP/MCP,
source, review, and correction surfaces. Capture only authorized inputs with stable
source IDs, source revisions, producer identity, scope, and ingestion watermarks.
Imports must be idempotent. Compact trajectory formats can be views; retain the
source evidence required to explain a claim. Never turn imported assistant prose
into an authoritative instruction merely because it is stored as memory.

Acceptance: client A records an evidenced decision, client B recalls it, the source
is corrected, and both clients subsequently receive the correction rather than the
old decision. Revoking a grant or deleting a source must suppress it from supported
recall and exported projections. Keep audit-retention semantics explicit. Concurrent
writers need conflict detection and a reviewable version chain, not last-write-wins
promotion of contradictory facts. First trace existing mechanisms before adding tables.

### P1: Make recall fit the host's context and authority boundaries

Add measured byte/token and latency budgets across the assembled pack, not only an
item count. Prefer a compact cited result with progressive detail. Support abstention
when current evidence is unavailable. Distinguish observed facts, user preferences,
project instructions, tentative inferences, and stale history. Source revisions and
invalidation should prevent old procedural memory from silently regaining authority.

Acceptance: correct task outcomes persist under the budget, scope and source labels
survive serialization, and correction/delete tests pass after caching and export.
Protect the existing public API with an explicit compatibility path.

### P2: Reduce adoption friction where the pilot shows demand

- Provide one supported start/health/backup/restore path and a small default agent
  interface. Preserve expert/debug surfaces without loading all of them by default.
- Add Chinese/mixed-language tests for intake, retrieval, correction, and quoted
  evidence. Preserve exact source text and evidence positions; do not silently
  translate the source of truth. This requires an explicit product-contract update.
- Measure whether Qdrant is necessary at the pilot's scale before introducing a
  second storage mode. Preserve Postgres authority and test rebuild/restore either way.

## Work to defer

Defer a new orchestrator, broad Knowledge OS, universal graph expansion, autonomous
high-authority memory rewriting, and more competitor adapters until they answer a
specific pilot failure. Existing features can remain supported without becoming
active expansion priorities. Do not remove them solely because the market changed.

The maintenance PR changes code ownership and validation, not these proposed product
contracts. Next implementation should start with the measured pilot and one handoff
flow, then let actual failures select the next capability.
