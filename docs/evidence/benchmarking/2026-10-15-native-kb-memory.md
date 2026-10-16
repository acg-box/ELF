---
type: Evidence
title: "Native knowledge and memory comparison"
description: "Compare current OpenViking and RAGFlow with fixed small cases, native memory, full 4096-dimensional embeddings, and source readback."
status: completed
authority: informative
owner: product
last_verified: 2026-10-15
source_refs:
  - config/benchmark/evidence/2026-10-15-native-kb-memory/results-summary.json
  - config/benchmark/evidence/2026-10-15-native-kb-memory/protocol.json
  - config/benchmark/evidence/2026-10-15-native-kb-memory/manifest.json
  - https://github.com/volcengine/OpenViking/releases/tag/v0.5.0
  - https://github.com/infiniflow/ragflow/releases/tag/v1.0.0-rc1
code_refs:
  - scripts/benchmark_deep/memory_comparison.py
  - scripts/benchmark_deep/documents.py
  - scripts/benchmark_budget.py
related:
  - docs/evidence/external_memory/2026-10-15-reuse-assessment.md
  - docs/reference/product-direction.md
  - docs/spec/agent_memory_knowledge_system_v1.md
---
# Native knowledge and memory comparison

Purpose: Compare knowledge and native conversation memory under a small, fixed
test, with separate quality, source, operating, and cost evidence.
Read this when: Selecting a reusable knowledge and memory system for ELF's use case.
Not this document: A production acceptance, a scale benchmark, or a complete
ranking of the products.

## Judgment

The later [ELF addition](2026-10-15-elf-native-kb-memory.md) reuses this run's
unchanged inputs, oracle, shared reader, and results. It adds ELF without
repeating these two products. The two-product measurements below remain intact.

This run does **not** establish that OpenViking is better than RAGFlow. Both
produce **11 complete answers out of 13**. OpenViking has fewer deployment
components. RAGFlow exposes a direct link from each extracted memory to its raw
message. Both preserve all tested original text, but their derived memory and
retrieval paths have different failures.

Do not select OpenViking as a replacement only from its architecture description.
Its two observed cross-project memory replacements need a correction or a proven
scope boundary before acceptance. If a suitable RAGFlow deployment already
exists, test reuse of its native Memory before adding another system. For a new
deployment, keep both as candidates; this run does not justify a quality-led
migration or a permanent stack containing both.

Keep ELF's immutable-source contract, source verification, subject boundaries,
and decision-update acceptance cases as portable requirements. These remain
useful when the extraction or retrieval engine comes from another project.

## Fixed conditions

- OpenViking **0.5.0** and RAGFlow **1.0.0-rc1**, from the current release tags at
  selection time. The RAGFlow tag is a release candidate despite the release API's
  `prerelease=false` value. Official Docker images were used without source patches.
- The existing workload supplied six text documents and eight conversation
  records per product. Two projects have decisions on August 1, 8, 15, and 22.
  Four initial records also occur in the knowledge corpus; later decisions enter
  only through native Memory. The policy and routing documents provide two
  knowledge questions. One question combines knowledge with an updated decision.
- Each product answers two questions before updates and eleven after updates.
  These are thirteen answer attempts, not thirteen independent underlying facts.
  Calibration uses separate data. The input and oracle hashes are retained.
- All extraction and answers use `openai/gpt-6-luna`, OpenAI routing, medium
  reasoning, and the full 128,000 output-token allowance. Both use the same answer
  reader. No generated scored answer was repeated to obtain a better result.
- All embeddings use `qwen/qwen3-embedding-8b`, Nebius routing, and **4096
  dimensions**. All 299 returned vectors have that width. RAGFlow's knowledge and
  memory indexes and OpenViking's persisted collection also declare 4096.
- Each question searches native knowledge and native Memory, with at most six
  unique hits from each. The shared context allowance is 32 KiB. Complete entries
  are dropped if necessary; text is not silently cut. **No entry was dropped**
  in the formal questions. RAGFlow's explicit `source_id` can supply its raw parent.
- Original dates occur in the same message text for both products. Before formal
  OpenViking ingestion, the client also maps the supplied timestamp to its native
  `created_at` field. RAGFlow's AddMessage API has no corresponding input field.
  This transport correction and the earlier calibration are both retained.

The test exercises native ingestion, extraction, persistence, retrieval, and a
shared reader. It does not test the complete vendor Agent UI or an autonomous
Agent that can make additional searches until it resolves a reference.

## Answer results

| Requirement | OpenViking | RAGFlow |
| --- | ---: | ---: |
| Knowledge policy and table | 2/2 | 2/2 |
| Current delivery and retry decisions | 1/2 | 1/2 |
| Cross-session recovery and causal link | 1/2 | 2/2 |
| Historical decision, before and after updates | 4/4 | 4/4 |
| Unappointed owner: do not invent a person | 2/2 | 2/2 |
| Combined knowledge and updated memory | 1/1 | 0/1 |
| **Complete answers after semantic review** | **11/13** | **11/13** |
| Required identifier coverage | 12/13 | 11/13 |

The two score rows are deliberately separate. OpenViking's Larch recovery answer
contains the expected identifiers but explicitly says that the causal link to
the delivery change is not established. The question asks for that link, and the
original record states it. This is an incomplete answer, although its cautious
wording is appropriate for the context supplied to the reader. A superseded
identifier mentioned as history is not treated as a current-decision error.

All 30 OpenViking quotes and all 26 RAGFlow quotes match their supplied context
text. This proves quote binding, not that every requested claim was answered or
that an extracted statement has the correct subject and time.

## Failure diagnosis

### OpenViking: cross-project replacement and a missed earlier decision

The native `memory_diff.json` files show two replacements in the same user
namespace:

| Shared event filename | Earlier content | Replacement content |
| --- | --- | --- |
| `gate_outage_recovery.md` | Larch's GATE-0-519 cause and recovery record | Cobalt's GATE-1-519 record |
| `retry_policy_replaced.md` | Larch's RETRY-0-907 update | Cobalt's RETRY-1-907 update |

The projects did not supersede each other. The original session archives remain
intact, but the final derived file no longer contains the earlier project's
record. Other event files retain enough of the August 22 message to answer
Larch's retry question; the missing causal record has no such recovery in the
returned context.

The release splits messages into sentence units with a 100-character minimum
for each extraction chunk. Selected ranges have explicit ellipses. The delivery
event retains chunk 0, while the cause clause was in chunk 1. This is **not** a
mutation of the original or a single-memory character rejection. It makes the
archive link important when a related event is missing or replaced.

The separate Cobalt current-decision failure is a recall gap:
`cobalt_stream_switch.md` still contains STREAM-1-286, but the reader does not
receive it. The August 22 message says to retain the August 15 choice without
repeating its value. See the [native before/after records](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/openviking-cross-subject-overwrites.json)
and [diagnosis](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/openviking-failure-diagnosis.json).

### RAGFlow: the correct decision exists but is not recalled

The Larch current-decision and combined questions share one missing fact:
STREAM-0-286. It exists in both raw message 15 and extracted message 16, but is
absent from both reader contexts. The contexts contain the August 22 reference
and records from the other project. The reader returns the supported retry
policy and declines to invent the delivery choice.

The native Memory query requests `valid_at` in descending order; the Elasticsearch
connector passes that order to the query. Raw records use import timestamps.
Extracted records mix event dates and import time, and some text loses the named
subject. These observations are consistent with later records displacing an
earlier but still-valid decision. No sort-policy intervention was run, so this
is a source-backed diagnosis, not a measured repair. See the
[stored records and diagnosis](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/ragflow-failure-diagnosis.json).

## Original text and provenance

| Check after updates and restart or recovery | OpenViking | RAGFlow |
| --- | --- | --- |
| Knowledge text equals uploaded UTF-8 bytes | 6/6 | 6/6 |
| Original user message text is unchanged | 8/8 | 8/8 |
| Native lineage inspected | 23 archive-to-memory operations | 21 extracted-to-raw parent links |
| Direct source handle on retrieved memory | Memory URI; archive/diff lookup also needed | `memory_id` plus `source_id` |

OpenViking retains message archives and native memory diffs. Its tested memory
files have extraction IDs and selected ChatLog text; none of the 21 files carries
an archive URI. The returned `provenance` describes retrieval, not a direct
original-message link. RAGFlow's 21 parent IDs all resolve to their raw records.
Neither structural result alone proves semantic entailment.

These checks prove preservation for this sequence. They do not prove enforced
write protection, long-term retention, ACL isolation, or recovery from arbitrary
data loss.

## Deployment and recovery evidence

OpenViking uses one application container with a persisted workspace. The tested
RAGFlow release uses seven services: the application, MySQL, Silo object storage,
Kvrocks, Elasticsearch, NATS, and ClickHouse. These are observed deployment
components, not a measured monthly maintenance bill.

RAGFlow calibration found an Infinity Memory integration failure: the generic
document mapping lacked required memory fields such as `valid_at`. Its release
Compose file also contains OpenSearch, but the Go runtime rejects that backend
as unimplemented. The official default Elasticsearch 8.11.3 completed both native
paths at 4096 dimensions. This says nothing about Infinity's intrinsic vector
performance. Initial MySQL readiness and admin heartbeat timing also required
the client to wait for a real authenticated data request.

Both products initially ran as AMD64 containers on an ARM host. RAGFlow completed
its application restart. OpenViking's AMD64 restart did not become ready within
the wait; its entrypoint later exited. Host load averages above 160 were observed,
so the incident cannot be attributed to a persistence defect from this run.

After a full workspace snapshot, the official ARM64 build of OpenViking 0.5.0
opened the same data in 50.9 seconds. All eleven later questions ran on that
recovered instance. No source was reingested, no memory was re-extracted, and no
scored answer was repeated. The original restart failure remains in the evidence.
**No speed ranking is made.** Platform changes, host load, serial provider calls,
and unequal cold initialization make total elapsed times unsuitable for that claim.

## Cost and evidence

| Phase | Settled API usage cost, USD |
| --- | ---: |
| Separate calibration and setup calls | 0.003756985 |
| RAGFlow formal run | 0.006921865 |
| OpenViking formal run and continuation | 0.024261415 |
| **This comparison** | **0.034940265** |

The existing USD 10 ledger was not reset. Settled campaign spend is
**USD 2.000364401**; conservative exposure, including unresolved reservations, is
**USD 2.072545101**. Conservative remaining capacity is USD 7.927454899. These
figures use reported API costs, including cache effects; they exclude Codex usage,
local hardware, and operator time.

The gateway recorded 80 chat and 287 embedding requests. One embedding request
failed with HTTP 520 during RAGFlow retrieval. One explicit retrieval retry
completed that unanswered case; the failed reservation remains in exposure.
The paid gateway is stopped, and no request remains in flight.

The [evidence manifest](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/manifest.json)
includes fixed inputs, the unchanged oracle, all answer contexts, manual reviews,
native source audits, dimension proof, release identities, and recorded client
source. Provider credentials and raw vector arrays are excluded. Private receipts
and workspace snapshots are retained locally.

The [cleanup receipt](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/cleanup-summary.json)
records removal of ten trial containers, eight volumes, one dedicated network,
and five unused product-image references. No trial container or volume remains.
Shared services and unrelated storage were not removed.

This small text test does not cover OCR, complex PDFs, Wiki/Graph quality, scale,
multi-tenant security, or incremental value over ordinary files. The next relevant
acceptance checks are narrow: prevent writes from crossing project subjects, and
resolve an earlier decision or source span when the current record refers to it.
Do not infer a general product score or migration readiness from these thirteen
answer attempts.
