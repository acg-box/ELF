---
type: Evidence
title: Bounded native benchmark calibration on 2026-10-07
description: Measured DeepSeek costs, native lifecycle observations, and three question repairs from a small competitor screen.
status: historical
authority: informative
owner: benchmark
last_verified: 2026-10-07
tags: [benchmark, calibration, cost, retrieval]
source_refs:
  - config/benchmark/evidence/2026-10-07/summary.json
  - config/benchmark/evidence/2026-10-07/results.json
  - config/benchmark/evidence/2026-10-07/usage.jsonl
code_refs:
  - scripts/benchmark_runner/cli.py
  - scripts/benchmark_runner/answers.py
  - scripts/benchmark_contract/metrics.py
related:
  - docs/runbook/benchmarking/benchmark_modes.md
---
# Bounded native benchmark calibration

The small screen establishes low API cost and basic lifecycle behavior. It does
not establish that ELF is better than file search or other memory products.
Most retrieval systems return both the correct evidence and old distractors in
these small corpora. A capable shared reader can hide that retrieval weakness.

## Scope and accounting

Native runs used source `194b3a5d40123c574dc700c3818e645cabf8afca`, with local wiki
edits present. The screen used all 18 named measure scenarios for ELF and the two
local baselines. GBrain covered the same 18 questions through separate native
probes. Mem0 covered 10 applicable questions; QMD covered 10. This was not the full
48-scenario matrix or a complete agent workflow trial.

The shared reader was `deepseek/deepseek-v4.1-flash`, low reasoning, routed to
DeepSeek without fallback. Embeddings used `qwen/qwen3-embedding-8b`. ELF and
GBrain follow-ups used 1,536 dimensions. The existing Mem0 store required 4,096;
the earlier ELF core run also used 4,096. Embedding providers varied initially;
from gateway request 243, routing was fixed to DeepInfra. These differences and
one sample per case prohibit a product latency ranking.

Total provider-reported spend was **$0.016648811**, approximately **1.66 cents**,
against a **$10 cumulative ceiling**. It includes all earlier calibration calls,
preflights, native embedding calls, shared readers, and targeted follow-ups.
It excludes local compute, image downloads, Codex usage, and CI.

| Usage | Count |
| --- | ---: |
| Paid requests with returned accounting | 393 |
| Chat requests | 35 |
| Chat input tokens, including cached input | 15,974 |
| Cached chat input tokens | 2,937 |
| Chat output tokens, including reasoning | 24,356 |
| Reasoning tokens included in output | 19,013 |
| Embedding requests | 358 |
| Embedding input tokens | 6,419 |
| Requests with unknown cost at completion | 0 |

A local gateway admitted requests only after it reserved a conservative input
and output allowance. It limited each invocation to $0.50 of new reservations
and the cumulative allowance to $10. It retained uncertain reservations, bounded
output and request size, and applied provider price ceilings. Consumers received
a local gateway token; the upstream key stayed in the gateway process. This
serial diagnostic is not an account spending limit or a shipped product feature.
Retained gateway reservations were $0.532099836; that amount is not the bill.
No paid consumer or test container remained active when evidence was exported.

The checked-in [summary](../../../config/benchmark/evidence/2026-10-07/summary.json)
records source pins and hashes of local artifacts. The
[request ledger](../../../config/benchmark/evidence/2026-10-07/usage.jsonl)
allows the reported total to be recalculated. The
[observations](../../../config/benchmark/evidence/2026-10-07/results.json)
retain per-question answers, retrieved evidence, metrics, and stage boundaries.
Raw provider responses and temporary credentials are not published.

## Original-question observations

The following values use the original, strict required-fact matcher. Three
questions had requirements that the wording did not explicitly request; see the
repair below. These numbers must not be used as a leaderboard.

| System and mode | Common, 6 | Lifecycle, 4 | Knowledge, 4 | Repository, 4 |
| --- | ---: | ---: | ---: | ---: |
| No memory | 1/6 | 0/4 | 1/4 | 0/4 |
| File token-overlap search | 6/6 | 4/4 | 2/4 | 3/4 |
| ELF note ingestion and retrieval | 6/6 | 4/4 | 2/4 | 3/4 |
| GBrain hybrid search, after explicit vector refresh | 6/6 | 4/4 | 3/4 | 3/4 |
| Mem0 with automatic extraction disabled | 6/6 | 4/4 | Not run | Not run |
| QMD lexical-only adapter | 1/6 | Not run | Not run | 0/4 |

The no-memory common and knowledge successes were correct refusals. QMD returned
no ranked context in these natural-language query runs. Its adapter used only
native lexical query mode without embeddings or reranking; these results do not
measure full QMD retrieval. Zero forbidden hits from an empty result are not
proof of access control or useful deletion behavior.

ELF, file search, GBrain, and Mem0 each returned forbidden or stale distractors
in 5 of the 6 common questions. Their shared answers avoided forbidden answer
facts. ELF execution acceptance passed, while its seeded quality gate failed.
This is evidence about these fixtures, not evidence of a real tenant ACL breach.

Mem0 was pinned to `mem0ai==2.0.12`. QMD was pinned to
`e428df76bc0274d9e93eb7ca3e95673315c42e90`. GBrain was pinned to
`5b5891069413b28b2fe3a50675116d67d5a1e145` and ran with Bun 1.4.0 and PGlite.
These are version-specific observations, not a claim about every current release.
GBrain did not use LLM query expansion, reranking, or agent maintenance. ELF and
Mem0 did not use automatic LLM memory extraction.

## GBrain update visibility

GBrain `put` returned a committed write with `embedding_state=queued`. Direct
page readback contained the replacement text. Immediate hybrid search still
missed the updated evidence in two lifecycle cases: answers were 2/4 and strict
update readback passed for 1 of 3 update cases. Both deletion cases excluded the
deleted evidence.

A separate follow-up ran the native `embed --stale --max-usd 0.05 --json` command
against the preserved databases, then repeated search and the shared reader.
Lifecycle answers became 4/4, all 3 update checks passed, and both deletion checks
remained successful. The refresh follow-up added 15.510 seconds for lifecycle
and 12.764 seconds for repository cases. These include queries and shared answers.

This separates committed storage from search readiness. It is not evidence that
the product permanently loses updates. GBrain deletion was soft deletion, with
a native recovery window; it does not prove physical erasure from all copies.
ELF and Mem0 passed their measured update and search-exclusion checks, but this
screen did not test their complete retention or backup policies either.

## Question repairs and controlled reader replay

Three original questions omitted required parts of the scoring contract:

- Orion asked for approvals and evidence, while scoring also required the team
  that supplies the release owner.
- Juniper asked who receives an alert, while scoring also required its depth
  threshold.
- Solstice asked what remains to do, while scoring also required already
  completed packaging and checksum work.

The questions now explicitly ask for those facts. The required facts, forbidden
facts, corpus, and scoring algorithm are unchanged. Historical results above
retain their original meaning.

A diagnostic replay used the clarified questions with exactly the previously
retrieved native contexts. File search scored 4/4 in both knowledge and repository.
ELF scored 3/4 in knowledge and 4/4 in repository. In the remaining ELF case, the
shared reader wrote “final checksum” and omitted “manifest”, which the strict
matcher requires. That failure is retained. No repeats were selected to obtain
a passing score.

This replay validates the wording repair and exposes reader/matcher sensitivity.
It does not remeasure native retrieval with the changed questions. It must not be
combined with old-query retrieval to claim a new end-to-end product score.
The repository benchmark contract tests passed: 55 tests.

## Timing and next decision

Measured run wall times, excluding initial image builds:

- ELF plus baselines, initial common core: 131.278 seconds.
- ELF-only common core at 1,536 dimensions: 61.495 seconds.
- ELF plus baselines, remaining 12 cases: 264.609 seconds.
- GBrain initial common stages: 74.979 seconds; other 12 cases: 200.087 seconds.
- Mem0, 10 cases: 67.200 seconds.
- QMD lexical mode, 10 cases: 25.448 seconds.

These runs have different setup, cold/warm, routing, and reader boundaries. Do not
rank product speed from their totals. The API cost is already small; repeated
embedding round trips and environment setup dominate elapsed time at this scale.

Use these small fixtures for regression and readiness checks. Before a product
investment decision, add a frozen real-repository replay with competing sources,
ordered changes, source authority, and representative context size. Measure
immediate and settled search visibility separately. Add the agent-maintained Git
memory baseline and full native workflows before claiming capability coverage
for Agent Memory Repo, Hindsight, MemOS, OpenViking, or graph-based systems.
Those products and workflows were not measured in this batch. Knowledge bases
remain eligible when their tasks match; category labels do not exclude them.

ELF's measured update/delete behavior works, but this screen shows no answer
advantage over the simple file baseline. Prioritize evidence selection and
source freshness, and require task-level evidence before adding more graph or
memory architecture. Spending the remaining budget is not a completion target.
