---
type: Runbook
title: Compare memory value on real project handoffs
description: Frozen own-project replay with source parity, chronological sessions, and complete cost accounting.
status: active
authority: procedural
owner: benchmark
last_verified: 2026-10-13
---
# Compare memory value on real project handoffs

This page records the original seven-file ELF preflight. For the executable
private-project trial and daily model profile, use
[the real-project trial runbook](real_project_memory_trial.md). The two workloads
and their budget histories are separate.

Use `config/benchmark/real-project-pilot/workload.json` and its exact Git-backed
source archive for the first ELF project pilot. This is a retrospective replay of
real merged engineering decisions with newly written handoff requests. It is not
a customer deployment or a multi-week natural-use observation.

## Admission before preparation

Read the existing cumulative budget ledger and fresh pricing for the declared
provider. Retain old unresolved reservations. Reserve the full provider output
allowance before each paid extraction, query, or reader request. Stop when it
cannot fit. Do not lower the output allowance, change the provider, remove old
reservations, or silently retry a failed response to obtain a result.

The 2026-10-13 preflight stopped before any native ingestion or model request.
The recorded gate is source and budget evidence only. It is not benchmark
execution. Before resuming, recheck current prices and the ledger; the saved
quote is not a future price guarantee.

## Three conditions

- `no_elf`: a fresh agent has the frozen repository and historical source reader,
  but no ELF query path or stored derived memory.
- `source_only`: the same sources plus persistent source retrieval. Do not expose
  extracted notes, summaries, graph facts, or earlier generated answers.
- `full_elf`: the same source access plus native ELF memory ingestion and recall.
  Use the pinned runtime with PostgreSQL and Qdrant and full 4096-dimensional
  Qwen3-Embedding-8B vectors. Let the normal extractor derive notes from originals;
  do not supply expected answers as hand-written memories.

All groups may access exactly the same source facts. Source indexing can alter
retrieval convenience, not corpus membership. The primary memory-value contrast
is `full_elf` versus `source_only`. The `no_elf` arm measures the wider workflow
against ordinary repository access.

## Chronological execution

1. Verify the archive hashes, source blobs, and checkpoint ancestry with the
   evidence verifier. Restrict every reader to that checkpoint's visible source
   IDs. A current checkout must not expose future commits through another path.
2. For each checkpoint, ingest only newly visible originals. Record native writes,
   extracted notes, vector dimensions, source references, and indexing readiness.
   Source text remains immutable. Verify that preparation jobs completed before
   measuring reads.
3. Run each task in a fresh reader process and conversation. Persist only the
   condition's permitted state. Full ELF retains its native records across
   checkpoints; source-only retains the source index; no ELF retains the Git
   source archive. Do not carry one condition's generated answer to another.
4. Rotate condition order. Apply the same model, provider, reasoning, source-byte
   budget, output ceiling, maximum rounds, and tool budget. Log every model call
   and tool observation, including incomplete and invalid outcomes.
5. Use the normal shared Agent evidence contract. Native tool schemas must be
   actually available when offered. Validate references uniformly after the
   response. Do not reveal the rubric or other conditions' results to the agent.
6. Review all expected obligations and additional claims against the exact sources.
   Count stale decisions, future leakage, unfinished answers, and incorrect state
   classifications separately. Keep failures; do not regenerate for a better score.

The original preflight froze this protocol and verified budget admission. Its
twelve-cell workload was not executed because that budget could not admit a
request. Preparation verification must not be represented as cross-session
acceptance, or combined with results from a different workload.

## Value, timing, and cost

Report each task and condition before pooling. A memory gain requires improved
completion/decision accuracy, or comparable correctness with lower effort, time,
or cost than source-only. Nonempty recall and more graph results are not gains.

Record actual end-to-end resume time, model and tool calls, prompt/output/cached
usage, and settled API cost. Report source ingestion, memory extraction, vector
indexing, and initial setup separately, then include them in amortized totals at
1, 5, and 20 tasks. Never subtract an extra cache discount from provider cost.

All twelve task-condition cells are required for the declared complete pilot.
A budget stop preserves partial cells and costs, but produces no product ranking.
One run per cell is diagnostic. It cannot establish statistical superiority,
customer readiness, or long-term operating reliability.
