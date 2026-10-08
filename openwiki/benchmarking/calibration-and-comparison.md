---
type: Reference
title: Benchmark calibration and fair product comparison
description: Verified API spend, native index readiness, real repository repairs, and limits of product comparison.
tags: [benchmark, memory, cost]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-08T21:07:20.478Z
sources:
  - id: openwiki-source-edb430929cfea30c15990b19
    resource: repo://apps/elf-eval/src/bin/real_world_live_adapter/service_runtime.rs
  - id: openwiki-source-f9893d4d96c3b652824d1444
    resource: repo://config/benchmark/evidence/2026-10-07-repository-replay/accounting.json
  - id: openwiki-source-dd90a0a1f5aa2e36fb27d874
    resource: repo://config/benchmark/evidence/2026-10-07/summary.json
  - id: openwiki-source-41de5f94ac6ea55c66eee31a
    resource: repo://config/benchmark/evidence/2026-10-08-full-native/accounting/summary.json
  - id: openwiki-source-f84e324a6d6a488fafbdcb87
    resource: repo://config/benchmark/scoring-contract-v5.json
  - id: openwiki-source-87dc0453116a4d53c0b0b603
    resource: repo://config/local/elf.docker.toml
  - id: openwiki-source-bf14920f8fd4acd0704573b1
    resource: repo://docker/benchmark/Dockerfile
  - id: openwiki-source-5d25cf64aa8cc1e9b1be09b8
    resource: repo://docs/evidence/benchmarking/2026-10-07-bounded-calibration.md
  - id: openwiki-source-bb1247307c8794ccbd2882d5
    resource: repo://docs/evidence/benchmarking/2026-10-07-repository-replay.md
  - id: openwiki-source-0e54ac6a76b520718715ada9
    resource: repo://docs/runbook/benchmarking/full_comparison.md
  - id: openwiki-source-390a5c4cc8f0dab92d64cc55
    resource: repo://scripts/benchmark_budget.py
  - id: openwiki-source-0330dc1965b65f2f9996851a
    resource: repo://scripts/benchmark_contract/metrics.py
  - id: openwiki-source-2b4143a3accf3db4bcdc9c12
    resource: repo://scripts/benchmark_deep/drivers.py
  - id: openwiki-source-56065a3815cb963d127dfd71
    resource: repo://scripts/benchmark_replay/agent.py
  - id: openwiki-source-3d2fd903bddb24ccbdd4a26f
    resource: repo://scripts/benchmark_runner/runtime.py
  - id: openwiki-source-6b5cd37890aeb4683d1169fe
    resource: repo://scripts/benchmark_targets/gbrain.py
  - id: openwiki-source-0f6d21abbbdb7165769b4e32
    resource: repo://scripts/benchmark_targets/graphrag.py
  - id: openwiki-source-14ccfc508395d22c8419395c
    resource: repo://scripts/benchmark_targets/hindsight.py
  - id: openwiki-source-1bc3f7c329b3996edfa5ef00
    resource: repo://scripts/benchmark-deep-unit.py
  - id: openwiki-source-b58326f8c77c6ba9d4f7544d
    resource: repo://scripts/benchmark-qmd-host.py
  - id: openwiki-source-24b7ca16c2008e1ef8843ea9
    resource: repo://scripts/tests/test_benchmark_graphrag.py
generated: { by: "codex", at: "2026-10-08T21:07:20.478Z" }
---

# Benchmark calibration and fair product comparison

For the closed October 8 campaign, use [full native results](full-native-results.md).
The pilot observations below remain historical evidence.

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
on a failed job or an indexing deadline. The default is 180 seconds;
`ELF_REAL_WORLD_INDEX_TIMEOUT_SECONDS` can set a longer deadline, and the deep
profile defaults to 5,400 seconds. Direct pilot readback showed 222/222 note jobs
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

Cumulative API spend through this pilot, including the earlier screen, failed calls, both native
preparations, and all 48 repair trials, is **$0.094396915** against the **$10**
ceiling. This pilot contributed $0.077748104 across 955 accounted calls. Of its
556,834 chat input tokens, 439,168 were cache hits. There are no unsettled request
costs. Local compute, Codex usage, and CI are excluded.

Use the [repair evidence report](../../docs/evidence/benchmarking/2026-10-07-repository-replay.md)
for boundaries and the [accounting artifact](../../config/benchmark/evidence/2026-10-07-repository-replay/accounting.json)
for phase costs, case results, and ledger links. The
[runbook](../../docs/runbook/benchmarking/repository_memory_replay.md) owns execution.

## Pilot limits and current full protocol

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

That pilot did not measure complete native workflows for Agent Memory Repo,
Hindsight, MemOS, OpenViking, or graph systems. Knowledge bases remain eligible
when their tasks match. Do not choose or reject products by category labels alone.

The [full comparison runbook](../../docs/runbook/benchmarking/full_comparison.md)
owns the expanded protocol. Its core matrix assigns all 48 cases to fourteen
products and two baselines: 64 product/suite units and 768 logical cases, with
cold and warm phases. Deep workloads add 100- and 1,000-document corpora,
cross-session recall, competing authority, corrections, shared namespaces,
and mutation readback. The default deep workload has 62 scored questions. Defined
scope is not completed coverage; use published execution evidence for results.

The deep runner can select fixed scale, session, conflicts, isolation, or mutation
groups. The `behavior` group contains the 42 non-scale questions. Group selection
preserves source text, question IDs, and operation order; isolation keeps both
namespaces in one store. Separate groups can avoid an earlier scale-index backlog,
but they are distinct conditions. Keep the original combined attempt and costs.
An extended `--ingest-seconds` deadline measures eventual readiness; it does not
convert a default-deadline timeout into a success. Action timeouts terminate the
native process group and retain logs, so orphaned children cannot keep making
provider calls after the client exits.

Deep adapter helpers must use the declared action budgets. GBrain imports receive
`INGEST_TIMEOUT_SECONDS`, while ordinary CLI calls retain their 180-second default.
Hindsight waits for background operations with the ingestion budget after retain
and the 1,200-second action budget after mutations. Its ordinary readiness default
remains 180 seconds. The outer process deadline still bounds the complete action;
these helper limits do not add time to that deadline. A returned retain receipt
and an empty background queue are separate readiness observations.

The ELF deep subprocess starts at the image root, `/`, so the container config can
resolve `config/local/tokenizer.wordlevel.json`. The deep launcher itself can run
from `/opt`; inheriting that directory would make the local tokenizer path invalid.
This setup requirement does not change the tokenizer or retrieval profile.

GraphRAG records cold and warm failures for each independent case and continues
other cases. A failed cold case has no warm index reuse. A failed warm reindex or
query preserves the cold result and completed operation evidence. Any case failure
keeps the containing unit in a failed state. Index hashes still protect cold-to-warm
reuse. Native extraction failures, including missing entities or relationships,
remain failures; continuing the suite does not convert them into successful cases.
The focused deep and GraphRAG contract tests cover these boundaries.

The current scoring contract is revision 5. Revision 4 accepts valid English
month-name dates as ISO-equivalent dates in required and forbidden fact checks.
Revision 5 accepts the Cinder module identity without a repository path prefix
and removes the unrequested Lumen case identifier from required facts. Retain
original answers and prior scores; apply scoring revisions uniformly with
`--rescore`, without new provider calls. These remain deterministic fact checks,
not a general semantic judge. QMD reanswer applies the reviewed contract before
checking retained suite equality, so scoring changes can reuse native retrieval
while changed questions or source text still fail validation.

The final reader receives one case per request. Earlier batches remain protocol
diagnostics because a model could use a neighboring case's context. Deep scoring
requires the expected value to occur in that case's supplied context. Native
retrieval, reader correctness, and execution failures remain separate. Core
negative retrieval fixtures do not establish access-control behavior.

Use `cargo make benchmark-budget` for paid execution. The checked-in gateway
fixes the model routes and keeps cumulative actual costs and conservative
reservations under a configurable ceiling, including prior pilots. The CLI default is USD 10; the completed October 8 campaign used an explicitly authorized USD 20 ceiling. Eight-case core suites and repair
phases admit at most USD 0.50 of new exposure. The 24-case common-core suite
admits USD 1.50; a full deep invocation admits USD 1. These are separate phase
limits inside the selected cumulative ceiling. Unknown costs retain their reservations. Buffered SSE does not
measure time to first token.

Profiles matter when comparing results. ELF uses native note ingestion, worker
indexing, and raw search, not its separate document-ingestion API. QMD's host
hybrid profile uses local models. The manifest records native extraction,
hierarchy, graph, transport, and maintenance deviations for other products.
A timeout or broken adapter remains incomplete execution. A legacy exact-text
update metric can fail even when delete-and-insert replacement succeeds; retain
operation acknowledgements, actual readback, and reader answers separately.

The deep GBrain adapter refreshes stale update embeddings with the supported
`embed --source` flag before readback; other source-scoped commands retain
`--source-id`. The deep Mem0 adapter searches with `filters={"user_id": scope}`
and `top_k=5`, matching the pinned native SDK. Its ingestion uses native
extraction (`infer=True`) and retains progress plus extracted memory IDs.
These adapter boundaries differ from the initial extraction-disabled pilot.

See [quickstart](../quickstart.md) for repository commands and documentation owners.
