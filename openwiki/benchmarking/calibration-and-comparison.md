---
type: Reference
title: Benchmark calibration and fair product comparison
description: Verified API spend, native index readiness, real repository repairs, and limits of product comparison.
tags: [benchmark, memory, cost]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T16:08:29.830Z
sources:
  - id: openwiki-source-edb430929cfea30c15990b19
    resource: repo://apps/elf-eval/src/bin/real_world_live_adapter/service_runtime.rs
  - id: openwiki-source-f9893d4d96c3b652824d1444
    resource: repo://config/benchmark/evidence/2026-10-07-repository-replay/accounting.json
  - id: openwiki-source-dd90a0a1f5aa2e36fb27d874
    resource: repo://config/benchmark/evidence/2026-10-07/summary.json
  - id: openwiki-source-5d25cf64aa8cc1e9b1be09b8
    resource: repo://docs/evidence/benchmarking/2026-10-07-bounded-calibration.md
  - id: openwiki-source-bb1247307c8794ccbd2882d5
    resource: repo://docs/evidence/benchmarking/2026-10-07-repository-replay.md
  - id: openwiki-source-0330dc1965b65f2f9996851a
    resource: repo://scripts/benchmark_contract/metrics.py
  - id: openwiki-source-56065a3815cb963d127dfd71
    resource: repo://scripts/benchmark_replay/agent.py
generated: { by: "codex", at: "2026-10-07T16:08:29.830Z" }
---

# Benchmark calibration and fair product comparison

The initial October 7 native calibration cost **$0.016648811** for **393 provider requests**,
including earlier samples and follow-ups. The cumulative admission ceiling was
$10. All request costs were known when the paid processes stopped. The local
gateway was a diagnostic, not a shipped account spending limit.

Use the [dated evidence report](../../docs/evidence/benchmarking/2026-10-07-bounded-calibration.md)
for interpretation and the [machine-readable summary](../../config/benchmark/evidence/2026-10-07/summary.json)
for exact accounting and source pins. The report links the per-request ledger and
per-question results. These checked-in records survive temporary-directory cleanup.

## What the sample establishes

- ELF and the file baseline completed 18 fast scenarios. Mem0 and QMD each ran
  10 applicable scenarios. GBrain had 18 native probes, with an additional
  settled-index follow-up for mutation suites.
- ELF, Mem0, and settled GBrain passed their measured update and search-exclusion
  checks. This does not prove physical erasure, tenant ACLs, or backup retention.
- GBrain committed updates before their embeddings were ready. In its lifecycle
  group, immediate answers were 2/4; after native vector refresh they were 4/4.
  Report write completion and search readiness separately.
- Common-core answers were 6/6 for ELF, file search, Mem0, and GBrain. Each also
  retrieved forbidden or stale distractors in 5/6 cases. A correct reader answer
  does not prove good evidence filtering.
- QMD's lexical-only adapter returned no ranked context. Its full hybrid and
  reranking capabilities were not measured.

The sample does not establish an ELF advantage over simple file search. ELF and
Mem0 disabled automatic extraction. GBrain did not use query expansion, reranking,
or agent maintenance. Small synthetic corpora and differing invocation boundaries
also prevent a latency ranking.

## Question and scoring contract

The shared reader answers from native retrieved context. The deterministic
scorer requires specified fact strings and checks forbidden facts separately.
It does not use a paid judge. This keeps evaluation inexpensive, but omissions
and wording differences can change the strict score.

Three questions now explicitly request all their scored facts: the Orion owner's
team, the Juniper alert threshold, and Solstice's completed release preparation.
The scoring facts and algorithm did not change. A clarified-question replay kept
the original retrieved contexts, so it validates the reader prompt repair but
is not a new native retrieval measurement. The remaining ELF reader omission
of “manifest” remains a failure in the evidence.

## Repository repair pilot

The subsequent pilot ran actual edits against three historical defects: chained
receipt provenance, Ctrl-C subprocess cleanup, and the Rust container channel.
Four conditions used the same model, source tools, task text, six-turn cap, and
maximum 12,000 recalled characters. Each condition had two repetitions.

The first 24 trials exposed two measurement defects. The native adapter ran only
eight worker passes before search, although each source packet produced 37 notes.
The agent also stopped dialogue immediately on invalid JSON. These diagnostic
results remain in the evidence; they are not a product ranking.

The adapter now waits for its dedicated worker queues to reach `DONE`, and fails
on a failed job or a 180-second timeout. Direct readback showed 222/222 note jobs
complete. Cold and warm retrieval both returned context in 6/6 episodes after
this correction. Invalid model JSON now consumes a turn and receives format
feedback within the same six-turn budget. The final isolated test determines
repair success even if the model does not emit a completion message.

All four conditions were rerun under the corrected protocol:

| Condition | Repairs passed | Total turns | Repair chat cost |
| --- | ---: | ---: | ---: |
| No memory | 5/6 | 32 | $0.011493624 |
| File search | 6/6 | 25 | $0.007959090 |
| Git memory | 6/6 | 28 | $0.007931652 |
| ELF note retrieval | 6/6 | 25 | $0.007423434 |

These costs exclude setup. Six successful Git note writers added $0.009180660;
a failed learner added $0.001668750. Correct ELF native preparation added
$0.000248200 and 428.820 seconds. The setup made 456 small embedding requests;
their summed gateway duration was 392.721 seconds. The repair timing difference
is not a stable product speed ranking.

Cumulative API spend, including the earlier screen, failed calls, both native
preparations, and all 48 repair trials, is **$0.094396915** against the **$10**
ceiling. This pilot contributed $0.077748104 across 955 accounted calls. Of its
556,834 chat input tokens, 439,168 were cache hits. There are no unsettled request
costs. Local compute, Codex usage, and CI are excluded.

Use the [repair evidence report](../../docs/evidence/benchmarking/2026-10-07-repository-replay.md)
for boundaries and the [accounting artifact](../../config/benchmark/evidence/2026-10-07-repository-replay/accounting.json)
for phase costs, case results, and ledger links. The
[runbook](../../docs/runbook/benchmarking/repository_memory_replay.md) owns execution.

## Next useful work

The file and ELF conditions both passed 6/6 with 25 turns. This small pilot does
not establish an ELF advantage over file recall. The explicit target path and
small source packet limit difficulty. Git notes are a model-maintained file
baseline, not the complete Agent Memory Repo product. The ELF adapter retrieves
five small, whitespace-normalized note chunks; it does not represent every ELF
document or knowledge workflow.

Use offline contracts for regression and reuse frozen prepared contexts for
agent-only iteration. Before increasing the competitor matrix, add independent
unseen tasks that require prior decisions, ordered source changes, and competing
authority. Preserve immediate versus settled indexing boundaries. Batch or reuse
embedding requests with an explicit cache boundary before a larger native run.

Complete native workflows for Agent Memory Repo, Hindsight, MemOS, OpenViking,
and graph systems remain unmeasured. Knowledge bases remain eligible when their
tasks match. Do not choose or reject products by category labels alone.

See [quickstart](../quickstart.md) for repository commands and documentation owners.
