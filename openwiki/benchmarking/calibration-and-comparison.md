---
type: Reference
title: Benchmark calibration and fair product comparison
description: Verified API spend, native update visibility, scoring boundaries, and the next useful comparison work.
tags: [benchmark, memory, cost]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T14:59:10.952Z
sources:
  - id: openwiki-source-dd90a0a1f5aa2e36fb27d874
    resource: repo://config/benchmark/evidence/2026-10-07/summary.json
  - id: openwiki-source-5d25cf64aa8cc1e9b1be09b8
    resource: repo://docs/evidence/benchmarking/2026-10-07-bounded-calibration.md
  - id: openwiki-source-0330dc1965b65f2f9996851a
    resource: repo://scripts/benchmark_contract/metrics.py
generated: { by: "codex", at: "2026-10-07T14:59:10.952Z" }
---

# Benchmark calibration and fair product comparison

The October 7 calibration cost **$0.016648811** for **393 provider requests**,
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

## Next useful work

Keep quick mode for offline regression and use short, bounded provider screens
for changed capabilities. Before increasing the matrix, add a frozen real-repository
replay with competing source authority, ordered changes, and realistic context
size. Measure immediate and settled visibility separately.

Add an agent-maintained Git memory baseline and complete native workflows before
claiming coverage of Agent Memory Repo, Hindsight, MemOS, OpenViking, or graph-based
systems. None was measured in this batch. Knowledge bases remain part of the
comparison when their tasks match. Do not choose or reject products by category
labels alone.

See [quickstart](../quickstart.md) for repository commands and documentation owners.
