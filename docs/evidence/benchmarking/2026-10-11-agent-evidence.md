---
type: Evidence
title: ELF agent source and graph evidence recovery
description: Separate memory recall, source tracing, graph traversal, and agent termination over frozen extraction.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-12
source_refs:
  - config/benchmark/evidence/2026-10-11-agent-evidence/manifest.json
  - config/benchmark/evidence/2026-10-11-agent-evidence/analysis.json
related:
  - docs/evidence/benchmarking/2026-10-11-memory-consistency-4096.md
  - docs/runbook/elf-agent-evidence-benchmark.md
code_refs:
  - scripts/benchmark-elf-agent.py
  - scripts/benchmark_agent/tools.py
  - scripts/benchmark_agent/analysis.py
  - packages/elf-service/src/update_resolution.rs
  - packages/elf-service/src/graph_ingestion.rs
  - apps/elf-mcp/src/app/server/tools/core/search.rs
---
# ELF agent source and graph evidence recovery

ELF can recover the requested facts through its existing tools, but evidence
identity and bounded agent completion remain separate weaknesses. Source
access helps this fixture. The current extracted graph does not add a measured
net quality gain. Fix source occurrence identity, temporal representation, and
agent evidence flow before changing the storage backend.

## Experiment

The native runtime is revision b8e6eb14f8b6122f5e2a5f963e34137d67b057b1,
from merged PR 403. This change adds measurement tools and evidence; it does not
change Rust product behavior. PostgreSQL and Qdrant remain the backend.

Twenty frozen memory questions cover current configuration, recovery across
sessions, historical state, and explicit absence of an appointed owner.
Sixteen questions are test cases; four are development cases. Four rotated
conditions share the same twelve initial notes and derived structured fields:

| Condition | Available tools |
| --- | --- |
| Notes | Search and read derived notes |
| Source | Note tools, original-document search, and verified excerpts |
| Graph | Note tools and outgoing graph queries, including object and evidence-note links |
| Both | Note, source, and graph tools |

Initial contexts omit original provenance quotes. Source-enabled agents must
read a note to obtain its provenance. Notes and graph conditions remove the
entire `source_ref`, including source IDs, hints, and original quotes; this is
an intentional ablation, not the normal full ELF API response. Source-enabled
conditions therefore add provenance metadata and quoted evidence as well as
document tools. Their effect cannot be attributed to document reads alone.
The later initial-context control uses
exactly the same prompt and initial note projection with no tools. It separates
richer structured context from iterative retrieval, with a prompt caveat: the
shared prompt still requests tool verification. Some no-tool responses imitate
nonexistent tool calls. These remain failures; the control is not a clean
estimate of reading ability independent of that prompt interaction.

Preparation uses native APIs and exact receipt-replayed extraction. It preserves
all 54 prior note bodies and reuses exact Qwen3-Embedding-8B inputs at 4,096
dimensions. Only new query embeddings need provider calls. This is retrieval
evaluation over frozen extraction, not a new extraction-model trial. Native
identifiers and ingestion timestamps are new. The sidecar image supplies only
a pinned local reranker; this is not a Hindsight rerun.

All reader calls use DeepSeek V4.1 Flash through the official DeepSeek route,
maximum reasoning, and the selected endpoint's maximum output allowance of
393,216 tokens. Temperature is omitted, so the provider default applies.
The old model-directory allowance and price ceiling rejected
the first request before any successful answer. The routing snapshot and failed
attempt remain in the evidence bundle.

## Results

| Condition | Autonomous factual success, test | With evidence-only finalization, test | Autonomous, dev | With finalization, dev |
| --- | --- | --- | --- | --- |
| Notes | 13/16 (81.2%) | 16/16 (100.0%) | 2/4 (50.0%) | 4/4 (100.0%) |
| Source | 15/16 (93.8%) | 16/16 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| Graph | 11/16 (68.8%) | 15/16 (93.8%) | 1/4 (25.0%) | 4/4 (100.0%) |
| Both | 13/16 (81.2%) | 16/16 (100.0%) | 3/4 (75.0%) | 4/4 (100.0%) |


These are factual-answer scores, not complete provenance scores. In the test
split, source access improves observed autonomous completion from 13/16 to
15/16. Graph access does not show a net benefit in this run. Tool use is real:
source-enabled agents read documents on every test case, and graph-enabled
agents traverse returned objects and evidence-note links. Nevertheless, the
small single-run sample and tool-directed prompt do not establish a causal or
general product ranking.

The initial-context/no-tool control scores 11/16 (68.8%) on test and
0/4 (0.0%) on development. Across all twenty controls, 8 responses
imitate nonexistent tool calls instead of returning an answer. One completed
answer omits the required concrete recovery identifier. Keep these distinct
from ELF retrieval failures. Three test recovery identifiers and one development
retry identifier are absent from the initial twelve-note context.

Across the eighty primary runs, 62 finish autonomously and 18 exhaust the tool
budget. All requested concrete identifiers are present in the evidence of those
exhausted traces. A separate final answer recovers most of their factual scores.
One graph-only finalization answers the requested Sable identifiers correctly
but adds a Cedar incident as its background. It fails semantic review despite
passing the required-keyword check. The wrong clause remains in
`factual-issues.json`. The other conditions' 16/16 finalization scores therefore
show evidence recoverability on this fixture, not perfect autonomous behavior or
perfect citation attribution.

Each primary agent has twelve model rounds and twenty-four tool calls. An
exhausted agent is an unsuccessful autonomous workflow, not automatically a
failed retrieval. The separate finalization phase makes one final model call
from the same recorded evidence, with no additional retrieval. Keep its results
separate. It does not replace wrong answers or resample completed answers.

Strict substring scores remain unchanged. Semantic reviews are bound to answer
hashes. They distinguish explicitly superseded historical values from incorrect
current states, and known absence from missing information. This fixture's
unknown-only rule does not adequately score explicit absence.

| Condition | Tool calls, 16 test cases | Document reads in cases | Verified provenance follow in cases | Graph object follow in cases | Graph evidence-note follow in cases | Median seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Notes | 235 | 0 | 0 | 0 | 0 | 63.3 |
| Source | 216 | 16 | 12 | 0 | 0 | 39.7 |
| Graph | 295 | 0 | 0 | 12 | 13 | 63.2 |
| Both | 245 | 16 | 10 | 8 | 10 | 37.9 |


Identifier presence is a diagnostic, not proof of the correct subject binding.
A verified provenance follow requires a prior note read, a matching source
identity and content hash, and a verified original excerpt containing its quote.
An object-entity follow can lead to an empty node; it is not automatically useful
multi-hop reasoning. End-to-end latency includes the model, embeddings, native
retrieval, and the wrapper's verbose diagnostic payloads. It is not database
latency. Two original wall timers were lost during retained-attempt recovery;
those primary samples are excluded rather than estimated. A recovered invalid
initial-control response also lacks a wall timer.

The literal unseen-citation diagnostic needs interpretation. Two primary
answers concatenate real document and chunk IDs, and one development answer
cites a returned message ID. These are not invented sources. One evidence-only
finalization does truncate a note UUID, so that citation cannot resolve as
written. The checks are retained in `citation-format-diagnostics.json`.

## Existing cached search expansion

The primary wrapper returns only twelve notes and omits the initial search ID.
ELF already exposes `elf_searches_get`, which can widen the cached session.
Native traces show that all 54 notes reached recall and reranking in the four
initial contexts with missing identifiers. The missing identifiers occur at
positions 20, 23, 19, and 19 in the retained result order. Expanding the same
session exposes them without a new embedding request.

This is a wrapper limitation, not a missing ELF feature. A targeted follow-up
adds the existing session tool and its native initial search ID. It uses the
same initial twelve notes, no source or graph tools, and recommends cached
expansion before a new query. Its four cases were selected after inspecting
initial identifier coverage: three test cases and one development case. Do not
fold this selected subset into the primary score or treat it as an unbiased
new suite.

| Selected case | Initial missing identifier | Autonomous result | Tool calls | With evidence-only finalization |
| --- | --- | --- | --- | --- |
| memory-0-1 | REPLAY-0-632 | tool_budget_exhausted | 24 | Correct |
| memory-2-1 | REPLAY-2-632 | tool_budget_exhausted | 24 | Correct |
| memory-3-1 | REPLAY-3-632 | completed | 19 | Correct |
| memory-4-0 | RETRY-4-907 | completed | 14 | Correct |

Two of four selected cases still exhaust the tool budget after expansion. The
missing facts become available cheaply, but that alone does not stop excessive
verification. This diagnostic does not establish an overall paging speedup.

## Data and representation findings

All twenty original source contents match their input bytes. The before/after
canonical vector fingerprints match: 54 note vectors, 54 note-chunk
vectors, 217 field vectors, and 20 document-chunk vectors, all 4,096-dimensional.
Native note hit counters remain zero; these reads do not train later conditions
through usage counts.

A remaining identity gap is directly reproduced. Sable's August 8 event and
Larch's August 8 event produce the same generic note body: "At the 2026-08-08
meeting, no change of delivery mode was approved." The native write returns
`IGNORE_DUPLICATE` for Sable. The retained note points only to Larch's source.
The original Sable document remains intact, but its derived occurrence loses
that source association. The current exact-body match is within one ELF tenant,
project, agent, scope, and type; it does not distinguish business subjects or
source occurrences. Fixture symmetry can conceal this defect in answer accuracy.
All four primary conditions cite that Larch-only note while answering the Sable
historical-state question. The required delivery-mode answer is factually correct,
but the supporting citation has the wrong subject provenance. The confirmed
examples are retained in `citation-issues.json`; they are not an exhaustive
claim-by-claim citation precision estimate.

All 54 event-derived notes carry message provenance rather than a direct
`elf_doc_ext/v1` document resolver. ELF already supports document pointers; this
fixture's event-ingestion path does not automatically link the separately
archived Source Library record. Agents can still search by quote or subject and
verify matching metadata. This is an ingestion-to-source integration gap, not
an absence of original-document retrieval in ELF.

The graph contains 47 entities and 37 facts. Twenty-three facts default to the
ingestion timestamp when extraction omits `valid_from`. Thus Larch has two facts
at the current time but none for an August 22 query. The separate graph-report
API exposes these facts as future facts; it is available in ELF but is not an
agent tool in the primary experiment. The missing business-effective time is a representation problem. The reader
applies the recorded validity window; this is not evidence of a faulty SQL
time filter. Separate observation time from validity and retain uncertainty
when the source does not establish an effective time.

Four of five projects have separate entities such as `Cobalt` and `project
Cobalt`. Only sixteen of the thirty-seven fact objects are entity references;
twenty-one are scalar values. Scalars are valid for dates and quantities, so
this count alone is not a defect. The material problem is that none of the five
projects, even when both project-name variants are used as starting points, has
an entity-edge path to its recovery procedure. Some needed associations remain
only in prose or lack extracted relations.

All seventeen extracted predicates are pending and have multi-valued
cardinality. That is a deliberate boundary against silently promoting model
output into authoritative current state. This run provides no preconfigured
application ontology. Do not describe its free-form extraction as a configured
domain graph, or fix it by blindly activating all predicates.

## Priorities

1. Preserve source occurrences when derived text is identical. Idempotency must
   identify the same occurrence, not merely the same sentence. Keep explicit
   caller authority for updates and retain every supporting source association.
   Test equal note bodies from different subjects and different original records.
2. Carry existing Source Library record and span pointers through event
   extraction. Use the existing resolver and hash checks so a note can lead to
   its original evidence without fuzzy rediscovery. Keep originals immutable.
3. Separate observation time from asserted validity, and resolve entity identity
   with source-backed aliases or caller-owned IDs. Preserve ambiguity instead of
   merging entities by approximate names. Test historical queries and a complete
   project-to-incident-to-recovery path with evidence on each edge.
4. Improve the agent adapter before changing storage: expose existing cached
   expansion, return compact evidence payloads, and stop when requested facts
   have sufficient evidence. Keep diagnostic traces outside the model context
   where possible. Measure this on asymmetric, contradictory, and multilingual
   cases in addition to the current repetitive fixture.

## Cost, validation, and limits

This task adds **$1.712384** in known provider charges.
The existing ledger now totals **$2.289233**, including
$0.576849 paid before this task. The first route rejection has
no usage receipt; its $0.569178 reservation remains unsettled. Conservative
cumulative exposure is **$2.858410**, below the
unchanged **$10** ceiling. No requests remain in flight.

The new requests include 479 chat attempts and
544 embedding requests. Chat usage totals
12,297,750 input tokens,
8,077,952 cached input tokens, and
554,320 output tokens. Provider receipts
report output unit rates of both $1.20 and $0.60 per million during collection.
Cache hits and billing rates vary with execution order. Use actual charges for
accounting, but do not attribute per-condition dollar differences solely to the
algorithm. Full requested output allowance does not mean all reserved output
tokens were consumed.

The retained local 413 failure occurred before provider dispatch. The resumed
case uses exactly its first five recorded turns and twenty-four completed tools;
no earlier calls were repurchased. Its subsequent tool request remains a primary
budget-exhausted outcome. A no-tool format failure also uses its original saved
response, without a replacement factual answer.

The benchmark contract suite passes 170 tests. Documentation and TOML checks
pass. The offline evidence verifier checks 100 primary/control cases, four
selected paging cases, twenty finalizations, 124 hash-bound reviews, native
source slices, provider-response identity, model settings, 4,096-dimensional
vectors, resumed history, and cumulative usage. It recomputes the reported
analysis from the frozen bundle without Docker or credentials:

```sh
python3 config/benchmark/evidence/2026-10-11-agent-evidence/verify.py
```

All twenty original records pass the final byte, hash, and chunk-offset checks.
Five task-owned Docker containers, one anonymous database volume, the dedicated
network, and two unused task image references were removed. PostgreSQL/Qdrant
base images and ten unrelated containers were preserved. A local synthetic
fixture dump and raw results remain available; no global Docker prune ran.

This is one trajectory per condition on a small synthetic fixture. It is not
an OCR, large-corpus, concurrency, permission-isolation, or full MCP-server
acceptance test. The primary agent uses selected public REST operations through
an external tool adapter; it does not exercise every ELF interface. No competitor
was rerun. Earlier flat-note scores and source-hydrated product scores measure
different capabilities and cannot establish general product superiority.
