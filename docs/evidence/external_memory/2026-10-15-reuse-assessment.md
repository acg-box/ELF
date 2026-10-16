---
type: Evidence
title: "Reuse assessment for unified knowledge and agent memory"
description: "Reconcile the full comparison history with current upstream versions and recommend a bounded reuse direction."
status: completed
authority: informative
owner: product
last_verified: 2026-10-15
source_refs:
  - config/benchmark/evidence/2026-10-15-reuse-assessment/upstreams.json
  - config/benchmark/evidence/2026-10-15-native-kb-memory/results-summary.json
  - config/benchmark/benchmark-v3.json
  - https://github.com/volcengine/OpenViking/releases/tag/v0.5.0
  - https://github.com/vectorize-io/hindsight/releases/tag/v1.0.0
code_refs:
  - packages/elf-service/src/docs/source_capture.rs
  - packages/elf-service/src/evidence/reference.rs
  - packages/elf-service/src/update_resolution.rs
  - config/agent/evidence-reader.md
related:
  - docs/spec/agent_memory_knowledge_system_v1.md
  - docs/reference/product-direction.md
  - docs/evidence/external_memory/research_projects_inventory.md
  - docs/evidence/external_memory/2026-10-15-product-alignment.md
  - docs/evidence/benchmarking/2026-10-08-full-native-comparison.md
  - docs/evidence/benchmarking/2026-10-09-recovery.md
  - docs/evidence/benchmarking/2026-10-09-ragflow.md
  - docs/evidence/benchmarking/2026-10-10-final-system-comparison.md
  - docs/evidence/benchmarking/2026-10-15-complete-memory.md
---
# Reuse assessment for unified knowledge and agent memory

Purpose: Recommend what to reuse and what to retain from ELF, using current source
review and the tests already completed.
Read this when: Deciding whether to continue an ELF subsystem or select a replacement.
Not this document: An accepted migration, a new benchmark, or proof of production
quality. The current deployment and product contract remain in force.

## Recommendation

The later [ELF addition](../benchmarking/2026-10-15-elf-native-kb-memory.md) narrows
the reuse decision further. Under the same frozen cases and reader, unchanged
ELF gives 13/13 semantically complete answers and 12/13 with valid quotes; both
competitors give 11/13. Keep the current working implementation while comparing
specific replacement mechanisms. This small result supports source hydration and
citation checking, not the necessity of every custom engine or a general product
lead. A full replacement still needs contract and maintenance evidence.

Keep **OpenViking 0.5.0 as a deployment candidate, not a confirmed replacement**.
Its resource store, session memory, progressive retrieval, and optional knowledge
compilation fit the requested boundary. The standalone configuration can keep
content and vector storage local to one service.

The later [native knowledge and memory test](../benchmarking/2026-10-15-native-kb-memory.md)
qualifies the original fit-based preference: OpenViking and RAGFlow each complete
11 of 13 answers. OpenViking also replaces two derived records across project
subjects; its original archives remain intact. RAGFlow preserves the tested
originals and direct memory-parent links but misses an earlier valid decision.
Do not select OpenViking on a quality-lead claim. If a suitable RAGFlow deployment
already exists, test reuse of its native Memory before adding another system.
For a new deployment, require subject-safe updates and bounded source recovery
before accepting either candidate.

Keep **Hindsight 1.0.0 as the alternative** when native memory consolidation,
evidence-supported observations, and maintained knowledge pages matter more than
broad resource organization. Its PostgreSQL deployment is a useful operational
alternative, but consolidation cost and the 4096-dimensional index path need
explicit acceptance.

GBrain is a serious candidate, not an obsolete project. It is especially close to
ELF on explicit facts, corrections, source identity, and cross-agent use. It is
not the first choice under the retained Qwen3-Embedding-8B 4096-dimensional
requirement: its current pgvector policy omits HNSW indexes above the supported
dimension limit and uses exact scans. This preserves dimensions, but does not
preserve the indexed-search performance measured at 1536 dimensions.

Do not combine OpenViking, Hindsight, GBrain, and RAGFlow into a new permanent
stack. Select one main system. Add a document parser or another specialist only
for a demonstrated input requirement. For short repository tasks with current
files available, continue to use file tools and an explicit handoff.

Pause general feature expansion without an observed workflow need. Continue
bounded reliability work when a real failure justifies it. Retain original
evidence, the working implementation, and the acceptance contract. Do not retire
a working service or destroy its data on this review.

Changing the engine is a maintenance decision, not a demonstrated answer-quality
improvement. An engine change does not resolve a reader omission when the required
source text was already delivered. Keep those failures in the host acceptance
cases instead of attributing them to the old database.

## Method and evidence boundaries

This review checked the historical project inventory, native benchmark profiles,
October recovery results, later native system comparisons, and the current ELF
source contract. It collected GitHub release and default-branch metadata, package
versions where the repository tag names another distribution, current READMEs,
and selected source and documentation files. The
[upstream receipt](../../../config/benchmark/evidence/2026-10-15-reuse-assessment/upstreams.json)
records exact revisions, URLs, content hashes, failed lookups, and release-file
checks.

Release tags and moving default branches are different evidence. For example,
the reviewed OpenViking session and compilation guides match 0.5.0; its embedding
configuration has later branch changes. Hindsight's knowledge-page and retain
guides match 1.0.0; its configuration has later changes. GBrain's inspected vector
index policy matches its release, while its trust guide has subsequent changes.
Feature presence in current source does not prove that the installed release
passes the ELF contract.

The source-review phase installed no competitor and made no provider or embedding
calls. The later bounded runtime test is separate evidence linked above; it does
not replace the historical scores below. Maintenance assessments in this inventory
are engineering estimates from deployment and code responsibilities, not measured
monthly costs. Stars and vendor benchmark scores do not determine the recommendation.

## What the previous tests establish

| Evidence | Useful result | Limit |
| --- | --- | --- |
| June research and adapters | Covered capture tools, local files, memory lifecycle, graph navigation, knowledge pages, and consolidation patterns. | Many rows were research or adapter tests. An old blocked adapter is not a current product limitation. |
| October 8 core campaign | Four suites, 48 questions each, 14 products including ELF, plus file and no-memory baselines. Strict results included ELF 46/48, OpenViking 46/48, GBrain 45/48, PageIndex 48/48, and files 47/48. | Shared-reader answers and selected native paths, not complete product acceptance. Most external embeddings used 1536 dimensions. |
| October 8 deep conditions | QMD 57/62, GBrain 55/62, files 53/62. GBrain's independent mutation recovery completed 12/12. ELF's separate behavior condition completed 41/42. | Different conditions and denominators must stay separate. These are small deterministic workloads. |
| October 9 recovery | Scale-1000 queries were eventually completed: ELF 10/10, Hindsight 9/10, SAG 8/10, Mem0 7/10. | These were separate provider/recovery conditions. Earlier timeouts, failed attempts, and costs remain. Do not report those products as still missing every scale result. |
| October 9 RAGFlow | The default retrieval profile missed all six authority and all six temporal-correction questions. The separate corrected mutation adapter passed 12/12. | Native Memory, Agent, and knowledge compilation were not tested. The misses do not establish that every RAGFlow configuration fails. |
| October 10 matched systems | Hindsight and RAGFlow each answered all 50 document and 16 memory questions under the declared semantic rubric, with the same retained Mistral annotations. | Small inspected corpus, maximum reasoning, 1536 dimensions, and different product paths. RAGFlow used native retrieval-chat; this was not a native Memory lifecycle test. The fixture reached its ceiling. |
| Latest ELF replay | Complete candidates were retained; the original four readers covered 22/24 obligations and completed 2/4 checklists. | This is neither a fresh external comparison nor repeatable proof that ELF adds value over capable source access. Both remaining omissions had supporting text in the returned context. |

The old ELF adapter also split sources into 220-character notes under the then
240-character admission limit. That adapter is not a description of current ELF.
Honcho used hybrid message search, not peer reasoning or dreaming. OpenViking used
native resource ingestion and hierarchy-aware search, not its full session-memory
and compilation loop. Letta's six native repair trials were a separate workflow.
These distinctions prevent both unfair rejection and unsupported promotion.

Sources: [core campaign](../benchmarking/2026-10-08-full-native-comparison.md),
[recovery](../benchmarking/2026-10-09-recovery.md),
[RAGFlow behavior](../benchmarking/2026-10-09-ragflow.md),
[matched systems](../benchmarking/2026-10-10-final-system-comparison.md), and
[latest ELF evidence](../benchmarking/2026-10-15-complete-memory.md).

## Main candidates

| Candidate | Knowledge and memory integration | Provenance and decision changes | Maintenance for the selected mode | Disposition |
| --- | --- | --- | --- | --- |
| OpenViking 0.5.0 | Resources, session memory, skills, and optional Wiki/graph compilation under one URI model. | Session archives and before/after memory diffs; resource links. Exact immutable version-and-byte citations still require acceptance. | Medium: one service with separate content and vector persistence, background jobs, and an optional compilation runtime. | First candidate for the unified system. |
| Hindsight 1.0.0 | Retained documents/facts, observations, mental models, and searchable knowledge pages. | Source facts/chunks and supporting quotes; evolving observations. Default document replacement deletes previous content and associated memories. | Medium: API/background work plus PostgreSQL; 4096 requires an appropriate vector extension. Consolidation adds model work. | Alternative for memory-led use. |
| GBrain 0.60.248.0 | Pages, explicit facts, decisions, corrections, graph links, and agent access. | Strong explicit source/trust/revision mechanisms; retention and withdrawal differ from immutable original preservation. | Low to medium for local PGlite/Bun use; embedding refresh, Git/database backup, and managed write coordination remain. Full 4096 search uses exact scans. | Strong reference and small-corpus option; not first choice for the retained indexed-vector requirement. |
| MemOS 2.0.34; reviewed server commit unchanged from our native profile | Knowledge cubes, conversation/tool memory, feedback, and graph-based retrieval. | Source metadata and memory updates; exact original-version retention and correction acceptance remain unproved. | Medium to high for the tested server: application, Neo4j, and Qdrant. Local SQLite plugins are a different product mode. | Keep as a candidate if cube composition becomes a concrete need. |
| RAGFlow 1.0.0-rc1 | Document ingestion, knowledge compilation, and a separate native Memory module. | Raw conversation storage plus extracted memory; valid/invalid times and enable/forget controls. No completed native decision-update acceptance here. | High for our tested Go/Infinity stack: several stateful services and background ingestion. | Specialist for document-heavy work; not the default replacement. |
| Mem0 Python 2.2.1 / TypeScript 3.3.1 | Useful memory SDK and optional graph path; application owns much of the knowledge workflow. | Update history exists. History of extracted memory is not an exact archive of all original material. | Medium: SDK integration, vector store, history persistence, and host capture. Optional graph adds more operation. | Reuse when embedding memory in an existing application; less complete for this unified product. |
| Honcho 3.3.0 | Peer/session models and reasoning over changing people, agents, groups, and projects. | Messages support evidence; native reasoning was not exercised by our old message-search adapter. | Medium: PostgreSQL plus reasoning/background services; host integration remains. | Secondary candidate. Its historical strict score must not be used to dismiss its untested main strength. |

### OpenViking: why it is first

The selected product combines resources and session-derived memory, so the
application does not need to keep a separate document system and memory system
in agreement. Its session commit archives messages, queues extraction, and emits
a memory change log. Updates can edit, merge, create, and delete derived memory.
This is more than a document search interface.

The optional compilation path reads resources or session records and produces
linked knowledge output. Wiki compilation uses a configured Agent Runtime,
including the built-in VikingBot option. It therefore has its own model and
operating cost; it is not a free index refresh.

The inspected collection schema uses the configured vector dimension and checks
existing collection compatibility. It does not prove a current 4096-dimensional
runtime result. A bounded index/query check is still required. Existing ELF
vectors are reusable only when model identity, query/document instructions,
normalization, dimensions, and the exact embedded bytes match. Newly generated
summaries and facts usually require new embeddings.

Its file interface can write and delete content. An archive URI or a memory diff
does not by itself establish ELF's hash-bound immutable-source contract. Keep
captured originals and versioned identities outside any mutable derived page.
Backup must cover both content and indexes.

Primary sources:
[session lifecycle](https://github.com/volcengine/OpenViking/blob/v0.5.0/docs/en/concepts/08-session.md),
[compilation](https://github.com/volcengine/OpenViking/blob/v0.5.0/docs/en/context-compilation/01-overview.md),
[storage](https://github.com/volcengine/OpenViking/blob/6006fc3403b52f52ef8c01f128691b5a10a01e99/docs/en/concepts/05-storage.md),
[deployment](https://github.com/volcengine/OpenViking/blob/6006fc3403b52f52ef8c01f128691b5a10a01e99/docs/en/guides/03-deployment.md),
[collection schema](https://github.com/volcengine/OpenViking/blob/6006fc3403b52f52ef8c01f128691b5a10a01e99/openviking/storage/collection_schemas.py).

### Hindsight: credible alternative, with explicit costs

Knowledge pages are maintained views over consolidated memory, not merely a
chat-history window. Observations retain supporting facts and quotes, and native
reflection can consult source material. This fits knowledge plus memory.

The retain API's default replacement mode deletes the old document and its
memories. Append mode reprocesses a growing document. Neither is a substitute for
keeping every accepted original version. Use distinct source-version identities
and an independent original archive if this system is selected.

The default pgvector HNSW path is not a 4096-dimensional acceptance result.
Hindsight also implements VectorChord and other PostgreSQL index options. Its
checked-in VectorChord deployment and cosine index clause are credible routes to
evaluate; no new dimension/performance claim is made here.

Our October 9 scale continuation took substantial consolidation work: its retained
v4 plus v5 path was 370.35 minutes and USD 2.746521970, excluding the separate v3
attempt. This is historical workload evidence, not a forecast for version 1.0.
Count ingestion and maintenance as well as cheap page reads.

Primary sources:
[knowledge pages](https://github.com/vectorize-io/hindsight/blob/v1.0.0/hindsight-docs/docs/developer/knowledge-pages.mdx),
[retain semantics](https://github.com/vectorize-io/hindsight/blob/v1.0.0/hindsight-docs/docs/developer/api/retain.mdx),
[observations](https://github.com/vectorize-io/hindsight/blob/9a499b1759084a86598eff8af30ed59f7354e76c/hindsight-docs/docs/developer/observations.mdx),
[vector indexes](https://github.com/vectorize-io/hindsight/blob/9a499b1759084a86598eff8af30ed59f7354e76c/hindsight-api-slim/hindsight_api/_vector_index.py).

### Why the other main candidates are not first

- **GBrain:** The released index policy caps vector HNSW at 2000 dimensions and
  halfvec HNSW at 4000. It preserves wider embeddings through exact search.
  Lowering dimensions to make a comparison convenient would violate the present
  requirement. Its explicit memory/source boundaries are worth adopting, but
  managed write journals and source coordination also need operation.
  [Index policy](https://github.com/garrytan/gbrain/blob/v0.60.248.0/src/core/vector-index.ts),
  [memory boundaries](https://github.com/garrytan/gbrain/blob/ea93c770b6133c887eb11472c8912b1e15943b54/docs/guides/memory-boundaries.md).
- **MemOS:** The server we tested already combines knowledge and memory. Reusing
  it would preserve a graph database plus a vector database and application
  workers. The current reviewed server commit matches the historical profile;
  plugin claims do not establish a new server result.
  [Compose](https://github.com/MemTensor/MemOS/blob/a7367d07e55db61099f7b4e2c1108bc5831a24f3/docker/docker-compose.yml),
  [memory model](https://github.com/MemTensor/MemOS/blob/a7367d07e55db61099f7b4e2c1108bc5831a24f3/docs/en/open_source/modules/memories/tree_textual_memory.md).
- **RAGFlow:** Raw, semantic, episodic, and procedural memory are real documented
  features. The configuration also describes capacity-based FIFO forgetting.
  Storage of raw messages therefore must not be treated as perpetual version
  retention. Its four memory types and Wiki/Graph outputs do not prove that
  source authority and decision supersession work across those paths.
  [Released configuration](https://github.com/infiniflow/ragflow/blob/v1.0.0-rc1/docs/guides/memory/configure_memory.md),
  [Agent connection](https://github.com/infiniflow/ragflow/blob/26ec6912865fa0553f0d3ad2f30b887c7966c873/docs/guides/memory/connect_to_an_agent.md).
- **Mem0 and Honcho:** Both remain useful, active candidates. Mem0 is attractive
  as an application memory component; Honcho needs a fair native-reasoning
  assessment. Neither has an existing acceptance result for this complete
  knowledge, immutable-source, and decision-change contract. Do not infer
  incapability from that gap.

## Complete historical candidate disposition

The observed version is a release or package identity, not a claim that all
reviewed branch features ship in that release. The receipt records branch SHAs.
For monorepos, the component name matters.

| Project or reference | Observed version on October 15 | Existing evidence and reuse decision |
| --- | --- | --- |
| OpenViking | 0.5.0 | Core 46/48 at 0.4.23. First unified replacement candidate; session/compilation acceptance remains. |
| GBrain | 0.60.248.0 | Core 45/48, deep 55/62, separate mutation recovery 12/12 at an older revision. Retain as a serious alternative and source-policy reference. |
| Hindsight | 1.0.0 | Core/deep and later native reflect evidence at 0.10.x. Alternative; do not transfer those scores to 1.0 without qualification. |
| MemOS | 2.0.34 release; a7367d07e55d reviewed server | Core 43/48; current reviewed server matches the benchmark pin. Defer adoption unless cube composition justifies its stack. |
| RAGFlow | 1.0.0-rc1 | Later document, retrieval-chat, and behavior evidence. Reuse for document-heavy needs; native Memory and compilation remain unmeasured here. |
| Mem0 / OpenMemory | Python 2.2.1; TS release 3.3.1 | Core 42/48 and separate scale 7/10; older history/lifecycle evidence. Useful memory SDK; hosted Platform and OpenMemory UI are separate evidence. |
| Honcho | 3.3.0 | Core 41/48 at 3.2.2 using message search. Do not reject peer reasoning/dreaming on this score. Secondary candidate. |
| QMD | 2.8.3 release; 86d2365d17fc branch | Core 43/48, deep 57/62. Keep as a strong optional search baseline, not a complete decision-memory lifecycle. |
| PageIndex | 0.4.0 | Core 48/48 at 0.2.21. Specialist for document-tree retrieval; this score is not full memory acceptance. |
| OpenKB | 0.4.5 release; ff54396e575e branch | Core 45/48. Useful document-to-Wiki system; not the first choice for the complete session-memory contract. |
| Graphiti / Zep | Graphiti 0.31.1 | Core 21/48 under the fixed older model/profile; schema failures remain. Strong temporal/provenance library reference. Zep hosted behavior was not tested. |
| LightRAG | 1.5.7 | Original core 43 correct of 43 answered, five missing; retain separate repeats. Specialist graph-assisted document retrieval. |
| Microsoft GraphRAG | 3.3.0 | Original core 24 correct of 32 answered, 16 missing; later lifecycle failures remain. Use only for a demonstrated graph-summary workload. |
| SAG | Python engine 0.14.0; app repo 56f073c1c0c3 | Core 38 correct of 40 answered; separate behavior 42/42 and scale 8/10 at 0.13.0. Active specialist, not retired SAG v1. Old engine repo URL is unavailable; current app is Zleap-AI/SAG. |
| Letta | Letta Code 0.34.15 | Separate native repair 6/6. Current Agent runtime is not interchangeable with a standalone memory service. The old V1 server is retired on the archive branch. |
| agentmemory | 0.9.30 | Early mock/durable-adapter gaps do not describe today's SQLite-based product. Keep as a capture/host integration alternative; no current complete acceptance. |
| claude-mem | 13.39.0 | Earlier durable lifecycle and detail-hydration passes, with retrieval misses and unmeasured hooks. Reuse only if its host workflow is the requirement. |
| memsearch | 0.4.21 | Early Markdown reindex/update/delete/reload passes. Current source also has capture, durable-note maintenance, and skill distillation. Lightweight file-based alternative; full update/provenance contract unproved. |
| graphify | 0.9.91; now Graphify-Labs/graphify | Earlier tiny graph/report runtime evidence. Use as a code/knowledge graph tool, not the primary memory service. |
| llm-wiki | 0.25.1 | Earlier workflow research; current source includes checkpoints and source/version metadata. Useful Wiki workflow, with lifecycle correctness delegated to its Agent and file process. |
| LangGraph | Latest repository release is prebuilt 1.1.1 | Checkpoint/replay reference. This component tag is not a whole-system version or standalone memory product. |
| nanograph | 1.3.0 | Typed local graph, ledger, and time-travel mechanism reference. Adopting it would still leave a memory application to build. |
| Cognition Agent Memory Repo | No release; 8798cb26c817 | File/Git memory pattern and baseline, not the hosted Devin product. Keep its small entry point and portable source-linked entries; do not import autonomous write policy by default. |
| Gemini CLI Auto Memory | CLI 0.64.0 | Harness-specific consolidation/review reference, not a neutral service replacement. |
| Google Always-On Memory Agent | No component release; parent repo 4fc5a2fa1384 | Example for ingestion and consolidation; not equivalent to a supported general-purpose memory product. |
| OpenAI ChatGPT Memory Dreaming | Hosted feature; no self-hostable release identity | Product/research reference for consolidation. No ELF adapter or interchangeable server was verified. |
| Claude Managed Agents Dreams | Managed API documentation; no self-hostable release identity | Reference for reviewing derived outputs separately from input memory; not a drop-in ELF backend. |
| Direct files / explicit handoff / no-memory | Controlled baselines, not versioned products | Keep strong baselines. File access can be sufficient; no-memory isolates the benefit of access, not the benefit of ELF over alternatives. |

Qdrant, Infinity, PostgreSQL, Redis, DuckDB, Helix Foundry, and OCR engines are
adjacent mechanisms, not additional complete memory products. Their earlier
storage/parser/ontology results do not select the replacement system. No new
database or ontology layer follows from this assessment.

The current
[OpenViking](https://github.com/volcengine/OpenViking),
[GBrain](https://github.com/garrytan/gbrain),
[MemOS](https://github.com/MemTensor/MemOS),
[memsearch](https://github.com/zilliztech/memsearch),
[SAG](https://github.com/Zleap-AI/SAG), and
[Letta](https://github.com/letta-ai/letta)
sources were read for the changed boundaries above. The receipt supplies the
same source identity for every other repository row. License identifiers are
recorded there; OpenViking reports AGPL-3.0, GBrain and Hindsight report MIT,
and MemOS and RAGFlow report Apache-2.0. This is metadata, not a license review.

## What to retain from ELF

| Asset | Retain | What not to carry forward automatically |
| --- | --- | --- |
| Original evidence | Accepted bytes, content hashes, source-version identities, exact span coordinates, and access/deletion obligations. | A mutable page URL as the only source identity. |
| Decision records | Subject/project, accepted authority, effective time, conditions, explicit correction links, and unresolved conflicts. | Model confidence or a more recent timestamp as authority to replace a decision. |
| Evidence read contract | Bounded original reads, hash verification, complete-claim handling, explicit omissions, and citation checks. | The whole Rust service when a small host integration or native capability meets the contract. |
| Evaluation assets | Frozen inputs, rejected candidates, failed answers, source digests, real workflow cases, and accounting receipts. | Old rankings applied to new versions, or another large suite to seek a favorable result. |
| Agent integration lessons | Verify actual capture and memory use; keep retrieved content separate from instructions; let direct source access remain available. | A mandatory memory lookup on every task or a second universal Agent framework. |
| Current service and data | Keep available until export, source resolution, and replacement readback are accepted. | Permanent duplicate indexing, consolidation, and synchronization across two main memory engines. |

These are portable assets and requirements. They are not proof of an exclusive
competitive advantage. ELF's current source-capture code binds hashes and offsets;
its evidence resolver checks the returned original. Its update-resolution code
requires an explicit key for replacement. Preserve those semantics where needed,
but use a native replacement mechanism when it proves the same behavior.

Do not expand ELF's extractor, retriever, Wiki renderer, graph, or organizer solely
to match another product's feature list. The later matched test supports retaining
the working path and its source guarantees while assessing specific mechanisms.
Do not add a generic multi-provider backend abstraction to preserve the ELF name.
A source contract can be implemented by a small integration if that integration
proves the required behavior and reduces total maintenance work.

## Small acceptance boundary before migration

The selection above is sufficient to choose one candidate. It is not sufficient
to migrate customer or project evidence. The next authorized trial should use
existing failure cases and a small fixed source set, not repeat the full matrix.

1. Capture a source, correct it, restart, and retrieve both exact versions by
   hash and byte range.
2. Apply a decision change for one subject/project while preserving the old
   historical answer, the effective date, and an exception condition.
3. Read knowledge and conversation-derived memory in a fresh Agent session;
   verify that the final answer used and cited the relevant original.
4. Configure Qwen3-Embedding-8B at 4096 dimensions. Verify stored width, actual
   index/query behavior, and model/input identity. Do not silently reduce width.
5. Confirm bounded maintenance, cancellation, export, and restore. Count model
   work for ingestion, consolidation, compilation, and query use together.

Failure of one candidate is a reason to inspect that specific gap or select the
alternative, not an automatic reason to restart broad ELF development. Reopen
self-development only for an important requirement that existing mechanisms
cannot meet at acceptable total cost.

## Verification of this assessment

This report preserves historical measurements. Current capability claims are
separated from historical runtime results and from recommendation judgments.
Public metadata and source hashes are saved in the receipt. The documentation
check, cargo make check-docs, passed. Git diff whitespace validation also passed.
These checks validate the local report and links; they do not validate an
upstream runtime or approve migration.
