---
type: Spec
title: "Source-Backed Project Memory Product Contract v1"
description: "Define the ELF source-backed project memory product contract, roadmap, phase gate, and claim boundaries."
resource: docs/spec/agent_memory_knowledge_system_v1.md
status: active
authority: normative
owner: spec
last_verified: 2026-10-15
tags:
  - docs
  - spec
  - agent-memory
  - project-memory
source_refs:
  - https://linear.app/hack-ink/issue/XY-1150/elf-final-source-backed-project-memory-execution-program
code_refs:
  - Makefile.toml
related:
  - docs/reference/product-direction.md
  - docs/evidence/external_memory/2026-10-15-product-alignment.md
  - docs/decisions/2026-10-10-language-neutral-source-memory.md
  - docs/evidence/benchmarking/2026-06-22-p1-memory-authority-closeout-report.md
  - docs/evidence/benchmarking/2026-06-23-p4-quality-hardening-productization-readiness-report.md
  - docs/runbook/benchmarking/real_world_agent_memory_benchmark.md
  - docs/spec/real_world_agent_memory_benchmark_v1.md
  - docs/spec/system_elf_memory_service_v2.md
  - docs/spec/system_consolidation_proposals_v1.md
  - docs/spec/system_knowledge_pages_v1.md
  - docs/spec/system_context_pack_v1.md
  - docs/spec/system_recall_debug_panel_v1.md
  - docs/spec/system_graph_memory_postgres_v1.md
  - docs/spec/system_memory_summary_v1.md
  - docs/spec/system_work_journal_v1.md
  - docs/spec/system_model_ladder_background_organizer_v1.md
  - docs/evidence/benchmarking/2026-07-03-source-backed-quality-benchmark-harness.md
  - docs/evidence/benchmarking/2026-07-03-qmd-candidate-replay-comparability-gate.md
  - docs/evidence/benchmarking/2026-07-03-final-source-backed-project-memory-closeout-report.md
drift_watch:
  - docs/spec/agent_memory_knowledge_system_v1.md
  - docs/spec/system_model_ladder_background_organizer_v1.md
  - docs/evidence/benchmarking/2026-06-23-p4-quality-hardening-productization-readiness-report.md
  - docs/evidence/benchmarking/2026-07-03-source-backed-quality-benchmark-harness.md
  - docs/evidence/benchmarking/2026-07-03-qmd-candidate-replay-comparability-gate.md
  - docs/evidence/benchmarking/2026-07-03-final-source-backed-project-memory-closeout-report.md
  - docs/runbook/benchmarking/real_world_agent_memory_benchmark.md
  - Makefile.toml
---
# Source-Backed Project Memory Product Contract v1

Purpose: Define the ELF source-backed project memory product contract, roadmap,
phase gate, and claim boundaries.
Status: normative
Read this when: You are shaping product work, implementing a change, or reviewing
source-backed project memory claims. Read the product contract and stable principles
first, then the relevant subsystem section.
Not this document: Low-level service API semantics, benchmark fixture schemas,
operator run commands, or implementation details for one subsystem.
Defines: `elf.source_backed_project_memory/v1` product boundary, stable principles,
agent-facing surfaces, benchmark metrics, and claim boundaries. The July execution
program is retained below as historical context, not a current task queue.

## Product Contract

ELF is open-source, source-backed project memory for AI agents.

The outcome is reliable continuity: agents can resume authorized project work,
apply the right decisions and conditions, and reuse experience across sessions
without making the user repeat the project context. ELF must earn its capture,
maintenance, retrieval, and operating cost through measured task benefit.

Project materials, decisions, progress, constraints, preferences, and reusable
procedures can all support this outcome. Knowledge is part of durable memory;
its storage format does not make it current authority. An observation, a derived
lesson, an accepted instruction, and a historical decision have different roles.
Model knowledge can help interpret evidence but does not prove a private project's
current state or permission to act.

Every important memory must have source provenance, freshness or lifecycle status,
history, reviewability, correction or rollback support, recall debugging, and
benchmark coverage for the claims made about it. These are product obligations,
not a claim that every integration currently satisfies them.

Knowledge pages, Work Journal entries, Dreaming proposals, Context Packs, recall
routing, Recall Debug, and benchmarks exist to support source-backed project memory.
They are not separate product categories and must not expand ELF into a generic
Knowledge OS, broad RAG platform, Notion/OpenKB clone, hosted memory SDK, graph
database, or document-search replacement.

### Stable principles

1. **Keep originals and interpretations separate.** Preserve exact accepted source
   versions and their identities. A changed source creates a new version. Notes,
   summaries, graph relations, translations, and indexes are derived records.
   Correction must preserve the evidence chain. Authorized deletion and access
   revocation still apply; immutability does not require perpetual readability.
2. **Keep authority explicit.** Identify the project, subject, owner, scope, and
   provenance of a claim. Retrieved text is data, not a new instruction or access
   grant. Derived confidence, repetition, or model strength cannot grant authority.
   Promotion follows the existing policy; a valid citation does not prove meaning.
3. **Represent change without erasing history.** Separate source capture time from
   effective time. Preserve applicable conditions, exceptions, correction links,
   and unresolved conflicts. Newer text alone does not establish supersession.
   Historical evaluation must not use evidence unavailable at its cutoff.
4. **Make context useful to the consuming agent.** Return bounded, inspectable
   evidence with a path to the original. Choose memory or direct source access for
   the task. Do not require every query to use every layer. Domain ontology and
   live action semantics belong to the application that supplies them; ELF can
   retain their evidenced identities and relations without inventing a universal
   world model.
5. **Accept source languages without rewriting evidence.** Storage and interfaces
   are language-neutral. Extraction can use a configured presentation language;
   original names and quotes stay intact. Multilingual quality still needs tests.
6. **Measure incremental value and remove unsupported complexity.** Compare against
   capable file, native-memory, and long-context alternatives where relevant. Count
   preparation, maintenance, failures, query work, and operating burden. Prefer a
   simpler mechanism when it meets the same obligations. A benchmark win, valid
   binding, merged change, or newer dependency is not customer acceptance.

The working loop is source capture, evidence-bound derivation, policy-controlled
memory update, task-scoped recall, agent use, and outcome-driven correction.
Recall can go directly to sources. A stored memory must not turn a tentative
observation or a successful past attempt into an unconditional future rule.

Models, databases, embedding dimensions, chunk sizes, MMR, graph depth, and tool
routing are revisable design decisions. The current accepted implementation stays
in force until a supported change is accepted; this separation does not authorize
an unplanned migration. Use [current direction](../reference/product-direction.md)
for the active hypotheses and next evidence boundary. New capabilities can justify
removing a workaround as well as adding one.

### Development and review ownership

This document owns ELF's intent. Subsystem specs own detailed behavior; dated
decisions own accepted rationale; evidence reports preserve what was measured.
The current-direction reference links those owners rather than defining a second
product contract. Update conflicting current guidance together when a decision
changes. Do not rewrite historical benchmark conclusions.

Agentry owns the shared alignment method and cross-project review coordination;
see [Agentry issue 25](https://github.com/acg-box/agentry/issues/25). That issue is
pending work, not an installed or running integration. ELF supplies its intent,
decision evidence, and upstream signals. This contract creates no review schedule.

## System Boundary

The following typed capabilities support the source-to-memory authority chain.
They are an existing capability map, not a requirement to expand every subsystem
or load every surface for each task. Each used capability must keep its authority
boundary visible in API, MCP, UI, benchmark, and report surfaces.

| Capability | Authority | Required boundary |
| --- | --- | --- |
| Source Library | Captured project documents, excerpts, imports, source snapshots, and source refs. | Sources remain evidence. Derived memory, pages, proposals, and packs must cite sources instead of replacing them. |
| Memory Authority | Notes, core blocks, ingest decisions, history, corrections, and rollback evidence. | Current memory writes are policy-gated, evidence-linked, auditable, and reversible. |
| Source-to-Memory Authority Loop | Candidate creation, review, approval, promotion, correction, and rollback transitions. | A source, journal row, page section, graph fact, or proposal is not current memory until promoted through the authority path. |
| Knowledge Workspace | Derived project, entity, concept, issue, decision, author, and timeline pages. | Pages are rebuildable supporting artifacts with citations, lint, and stale-source detection; they are not authoritative memory hits. |
| Work Journal | Source-adjacent session logs, handoff briefs, janitor reports, next steps, and rejected options. | Journal-only facts can answer continuity questions but must not become current project authority without accepted promotion evidence. |
| Dreaming Review | Reviewable consolidation, summary, brief, tag, correction, routing, and promotion proposals. | Dreaming may propose and organize; it must not silently mutate sources or current memory. |
| Context Pack v1 | Bounded, cited bundles assembled for an agent task from current readable sources, memory, pages, traces, and proposals. | Context Packs are transport artifacts, not shadow memory; they expire or rebuild from authorities and must not create facts by packaging them. |
| Automatic Context Routing | Deterministic or constrained model-assisted selection of which authority layers and pack scopes a task should inspect. | Routing may choose surfaces and pack budgets; it must expose rationale and must not bypass scope, lifecycle, review, or evidence rules. |
| Recall Engine | Search, expansion, rerank, relation context, source/page/journal retrieval, and pack assembly. | Recall returns typed context with freshness and authority labels; derived or blocked context must not be narrated as current authority. |
| Recall Debug | Search traces, dropped candidates, source/doc/page/journal/graph/proposal rows, replay aids, and pack/routing explanations. | Recall must expose why context was selected, dropped, stale, unavailable, blocked, or not requested. |

Existing subsystem specs own their detailed contracts. This document owns how those
subsystems fit into the source-backed project memory product boundary.

## Non-Goals

- Do not build or position ELF as a generic Knowledge OS, broad RAG clone, generic
  Notion/OpenKB clone, hosted memory SDK, graph database, or document-search
  replacement.
- Do not make Memory Experts the user-facing product concept. User-facing language
  should name source-backed project memory and the typed supporting capabilities.
- Do not let Dreaming silently mutate sources, current memory, authority history,
  corrections, or published knowledge pages.
- Do not treat journal-only facts as current project authority.
- Do not let Context Packs become shadow memory or an uncited source of durable facts.
- Do not make broad market-leadership, universal leaderboard, private-corpus,
  provider-backed, hosted, UI/export, graph/RAG, core/archive, context-trajectory, or
  long-document parity claims without comparable product-runtime evidence for the
  exact claim.
- Do not turn ELF into a broad RAGFlow, OpenKB, PageIndex, mem0, Zep, Letta, qmd,
  OpenViking, agentmemory, claude-mem, memsearch, Graphiti, Zep, GraphRAG, or
  LightRAG replacement.
- Do not weaken source authority, source-ref, evidence-binding, language-neutral
  text validation, scope, lifecycle, or review boundaries to match another
  product's ergonomics. See the accepted
  [language-neutral decision](../decisions/2026-10-10-language-neutral-source-memory.md).
- Do not collapse `blocked`, `incomplete`, `not_encoded`, `wrong_result`, or
  `unsupported_claim` states into pass claims.
- Do not queue later phases while the current accepted phase is still under review.

## Data Model Direction

All implementation phases must preserve the source-to-memory authority chain:

1. Sources are captured as documents, excerpts, event audits, issue/PR records, or
   other source refs with stable provenance.
2. Candidate project memory is derived from sources as proposals, page sections,
   journal entries, graph facts, summaries, routing evidence, Context Pack inputs, or
   memory candidates.
3. Promotion into memory records an explicit policy decision, source refs, actor,
   confidence, importance, lifecycle state, and audit trail.
4. Correction and rollback create durable history instead of silently rewriting the
   evidence chain.
5. Recall reads from typed authority or support surfaces and returns enough trace data
   to debug selection, demotion, filtering, staleness, routing, pack assembly, and
   missing anchors.

Postgres remains the authority for notes, docs metadata, graph-lite facts, derived
pages, Work Journal entries, Dreaming review state, Context Pack manifests, routing
traces, recall traces, and audit history. Qdrant and any future retrieval index
remain derived and rebuildable.

## Agent-Facing Surfaces

Agent-facing tools must be thin MCP or HTTP facades over typed service behavior.
Business logic and policy remain in `elf-api` and `elf-service`.

Current and future source-backed project memory work should use these surface
families:

| Surface family | Examples | Boundary |
| --- | --- | --- |
| Source capture and hydration | `elf_docs_put`, `elf_docs_search_l0`, `elf_docs_excerpts_get` | Capture and retrieve source evidence without promoting it to memory by default. |
| Memory write and readback | `elf_notes_ingest`, `elf_events_ingest`, `elf_searches_create`, `elf_searches_notes`, `elf_core_blocks_get`, `elf_entity_memory_get` | Writes must preserve policy and evidence decisions; reads must honor scopes and lifecycle. |
| Source-to-memory review | Memory candidate, consolidation proposal, correction, and review surfaces | Promote or correct current memory only through explicit accepted authority transitions. |
| Work continuity | Work Journal capture and readback surfaces | Answer continuity from source-adjacent evidence while keeping journal-only facts out of current authority. |
| Provenance and history | `elf_admin_note_provenance_get`, `elf_admin_memory_history_get`, trace bundle tools | Debug memory authority without raw database access in normal workflows. |
| Knowledge and graph context | Knowledge page search/readback, `elf_graph_query`, graph report surfaces | Expose derived pages and graph facts as labeled context, not authoritative note hits. |
| Dreaming review | Dreaming review queue and proposal review surfaces | Keep proposals reviewable; auto-apply is limited to explicitly accepted low-risk derived organization cases. |
| Context Packs and routing | Context Pack v1 creation/readback and automatic routing traces | Assemble bounded cited context for a task without creating shadow memory or bypassing authority. |
| Recall and Recall Debug | Recall Engine readback, `elf_recall_debug_panel`, trace and trajectory readback | Show selected, dropped, available, reviewable, blocked, and not-requested context. |

New MCP tools must name the underlying authority layer, link to the owning spec, and
preserve read/write boundaries. A readback tool must not become a hidden mutation path.

## Operator UI Role

The UI is an operator console for source review, memory authority, knowledge pages,
proposal review, graph/topic inspection, and recall debugging.

The UI must:

- label authoritative notes, derived pages, graph facts, proposals, and trace rows
  differently;
- show citations, lint state, review state, lifecycle state, and rollback/correction
  affordances where applicable;
- prefer typed service readback over raw store inspection;
- avoid presenting derived pages or proposals as current memory unless they have been
  promoted through the relevant authority path.

The UI is not the source of truth and must not bypass API, MCP, scope, review, or
write-policy contracts.

## Execution Program

Historical scope: this section, the P0-P5 roadmap, the R1/first-phase constraints,
and the Decodex phase gate record the July 2026 program. They do not restart that
program, prescribe the next implementation, or authorize queue operations.
Use [current direction](../reference/product-direction.md) for present priorities.
Detailed subsystem contracts remain in force independently of the old phase order.

The execution program is split into Decodex-trackable implementation slices so
cold-start lanes can work from their issue briefs plus this spec. The source issue
for this program is `XY-1150`.

| Issue | Slice | Required result |
| --- | --- | --- |
| XY-1151 | Product contract | Specs state the final source-backed project memory positioning, supporting capabilities, and non-goals. |
| XY-1152 | Source Library and Memory Authority | Implement the lifecycle model for source evidence, authoritative memory, source-to-memory promotion, correction, and rollback. |
| XY-1153 | Knowledge Workspace, Work Journal, and Dreaming | Implement derived knowledge, source-adjacent continuity, and reviewable proposal boundaries without silent authority mutation. |
| XY-1154 | Context Pack v1, automatic routing, Recall Engine, and Recall Debug | Implement cited task packs, routing rationale, typed recall, and trace/debug readback. |
| XY-1155 | Benchmark harness | Produce executable tests, executable benchmarks, and benchmark artifacts for source-backed memory quality. |
| XY-1156 | qmd candidate-replay comparability gate | Preserve qmd replay/debug comparability until ELF emits comparable artifacts. |
| XY-1157 | Independent review and closeout | Run independent review/skeptic gates, fix P0/P1 findings, and publish final readiness evidence. |

These issues may execute independently only within their accepted issue scope. They
must not use Program graph ids, queue labels, or private runtime state as execution
authority.

## Roadmap

The roadmap phases below are product phases. They are not broad permission to queue or
implement every item in a phase at once.

| Phase | Name | Scope | Gate to leave phase |
| --- | --- | --- | --- |
| P0 | Product contract and phase gate | Codify source-backed project memory positioning, capability boundaries, competitor absorption rules, validation expectations, and closeout checklist. | Docs are reviewed, repo docs validation passes, claim boundaries reject generic Knowledge OS/RAG clone positioning, and the main thread accepts the next phase. |
| P1 | Source Library and Memory Authority loop | Deliver one source-backed memory-authority vertical slice: capture source evidence, create/review one proposal through a proposal inbox, record the authority ledger, apply/correct/rollback, recall through agent-facing tools, and debug stale/correction behavior. | The slice has service tests, provenance/history evidence, recall/debug readback, and at least one real-world stale/correction benchmark job. |
| P2 | Knowledge, Journal, and Dreaming boundaries | Promote source-linked project/entity/concept/issue/decision/author/timeline pages, Work Journal continuity, and Dreaming proposal review with rebuild/lint/watch/search/version-diff readback where applicable. | Pages stay derived, journal-only facts stay non-authoritative, Dreaming does not silently mutate authority, stale-source lint runs, and benchmark reports publish citation/staleness metrics. |
| P3 | Context and Recall | Deliver Context Pack v1, Automatic Context Routing, Recall Engine behavior, and Recall Debug traces. | Packs are bounded and cited, routing exposes rationale, recall labels authority and freshness, and debug traces preserve selected/dropped/blocked/not-requested evidence. |
| P4 | Benchmark and quality hardening | Expand executable benchmarks, qmd candidate-replay comparability, adversarial jobs, public comparison grammar, quality metrics, latency/cost/resource reporting, and unsupported-claim detection. | Reports preserve job/suite/project typed states, expected evidence recall, irrelevant context ratio, unsupported claims, qmd replay comparability, and resource metrics. |
| P5 | Productization | Improve local setup, agent/MCP recipes, operator UI, privacy/delete/export boundaries, and production-quality workflows. | Operator workflows have documented setup, privacy/delete/export semantics, and validation evidence without weakening source authority. |

### R1 Model Ladder Constraint

R1 introduces the model ladder and the first local/background organizer benchmark
gate. The R1 slice is narrower than a product phase: it proves only a proposal-only
local organizer path. It must not make small/local models authoritative for Memory
Authority writes.

R1 is governed by `docs/spec/system_model_ladder_background_organizer_v1.md` and
validated by `cargo make real-world-memory-r1-local-organizer`. A passing R1 report
may claim only that ELF defines L0/L1/L2/L3/L4 tiers and that L2 local/small models
can draft low-risk structured proposals under schema, provenance, lifecycle,
escalation, latency, cost, and source-immutability gates. Strong models or explicit
policy gates remain required for conflict resolution, multi-source synthesis,
promotion review, important corrections, benchmark judging, and public claims.

### First Implementation Phase Constraint

The first implementation issue after P0 must be the smallest coherent P1 vertical
slice. It may touch only the surfaces needed to prove one source-linked
memory-authority loop end to end.

The first P1 issue must not build the full Knowledge Workspace, broad operator UI,
external adapter pack, hosted memory behavior, graph/RAG parity, or product-wide
rewrites. Those are later phases unless a main-thread decision explicitly narrows and
accepts a different next slice.

## Decodex Phase Gate

Decodex execution for this project is single-phase gated:

- Only the next accepted phase may carry the service-scoped queue label
  `decodex:queued:elf`.
- Later-phase issues must remain unqueued while the current phase is running, under
  review, or waiting for main-thread acceptance.
- After each phase lands, the main thread must review evidence, tests, benchmark
  results, claim boundaries, and next-phase readiness before any later issue receives
  `decodex:queued:elf`.
- `decodex:active:elf` means runtime ownership of an active lane. It is not a request
  to start additional phases.
- `In Review` is a PR-backed handoff state. It is not phase acceptance by itself.

As of the July 2026 XY-1150 source issue, the accepted execution direction is an
open-source, source-backed project memory system for AI agents. Generated Decodex
issues XY-1151 through XY-1157 are the implementation slices for that direction.

Earlier Agent Knowledge OS, P1, P2, P3, and P4 reports remain evidence anchors for
specific measured capabilities only. They do not authorize generic Knowledge OS
positioning, broad RAG clone scope, or unsupported product-leadership claims.

## Competitor Absorption Rules

External projects are references for targeted improvements. They are not hidden
dependencies and are not automatic proof that ELF is weaker or stronger.
The table below retains the July comparison categories. Its unresolved comparisons
are dated evidence boundaries, not current rankings. Use the
[October review](../evidence/external_memory/2026-10-15-product-alignment.md) for
recent source review and [target lifecycle](../reference/benchmark-target-lifecycle.md)
for executable competitor status.

| Competitor/reference | Strength to absorb | Claim boundary |
| --- | --- | --- |
| qmd | Transparent expansion, fusion, rerank, top-k, and compact replay ergonomics. | Preserve qmd's debug edge until ELF emits comparable replay artifacts. |
| VectifyAI PageIndex | Long-document tree retrieval and PageIndex MCP ecosystem direction. | No win/tie/loss claim until a same-corpus adapter compares tree artifacts, cited node paths, and MCP readback with ELF source ids and source refs. |
| VectifyAI OpenKB | Compiled Markdown wiki, concept/entity pages, lint, watch, and recompile workflows. | Absorb into Knowledge Workspace only through source-id-mapped wiki, index, lint, and watch/recompile artifacts; derived wiki pages must not become source memory. |
| OpenViking | Filesystem-like context URIs, hierarchy selection, staged trajectory, and recursive expansion. | Keep trajectory/hierarchy claims blocked until same-corpus staged artifacts exist. |
| mem0/OpenMemory | Entity-scoped history, hosted ecosystem, UI/export, and optional graph memory direction. | Separate local SDK history evidence from hosted, UI/export, and optional graph-memory parity. |
| Letta | Core/archive memory split and export/readback model. | No core/archive parity claim until contained Letta export/readback artifacts include source ids. |
| Graphiti/Zep and graph/RAG projects | Temporal graph validity, citation/navigation, and graph retrieval references. | Graph-lite reports are ELF-native evidence, not broad graph/RAG parity. |
| agentmemory and claude-mem | Capture hooks, local viewers, continuity UX, and progressive disclosure. | Improve operator UX and capture audit without dropping evidence, scope, or write-policy gates. |
| memsearch | Markdown-first canonical store, incremental reindex, and local hybrid retrieval. | Treat as workflow inspiration; ELF's source-of-truth remains Postgres plus typed source refs. |

Allowed claims:

- ELF is open-source, source-backed project memory for AI agents when the claimed
  surface has implementation, tests, and source-backed evidence.
- ELF has checked-in evidence for specific measured slices named by their reports,
  such as Memory Authority, Source Library, Knowledge Workspace, Work Journal,
  Dreaming review, Recall Debug, production-readiness gates, and public quantitative
  scoreboard rows.
- Competitor strengths remain optimization inputs and comparison targets.

Disallowed claims:

- ELF broadly beats every competitor on every competitor-owned strength.
- ELF is a generic Knowledge OS, generic RAG platform, generic wiki compiler, Notion
  clone, hosted managed memory platform, or broad knowledge-everything product.
- Reference-only, blocked, incomplete, wrong-result, or not-tested evidence is a pass.
- Public-proxy or local fixture evidence proves private-corpus or provider-backed
  production quality.

## Benchmark Metrics

Phase closeout and comparison reports must use the real-world benchmark vocabulary
instead of broad leaderboards.

Required quality dimensions are:

- `answer_correctness`
- `evidence_grounding`
- `trap_avoidance`
- `uncertainty_handling`
- `workflow_helpfulness`

Use optional dimensions when the phase touches them:

- `lifecycle_behavior`
- `debuggability`
- `latency_resource`
- `personalization_fit`

Reports must preserve typed outcomes:

- `pass`
- `wrong_result`
- `lifecycle_fail`
- `incomplete`
- `blocked`
- `not_encoded`
- `unsupported_claim`

Relevant phase reports should also publish expected evidence recall, irrelevant context
ratio, unsupported-claim counts, stale-answer counts, source-ref coverage, citation
coverage, freshness/rationale coverage, proposal lineage completeness, source mutation
count, trace explainability counters, and latency/cost/resource metrics when those
metrics apply to the touched phase.

## Validation

Repository-native validation is authoritative.

- Use `Makefile.toml` as the source of truth for task names.
- For docs-only phase work, run at least `cargo make check-docs` before claiming the
  docs are validation-ready.
- Before a PR handoff or any push that refreshes a PR head, run the registered
  Decodex workflow gate: `cargo make fmt`, `cargo make lint-fix`, then
  `cargo make check`.
- If a phase changes commands, schemas, config, runtime behavior, status semantics,
  or benchmark claims, update the owning docs and include drift evidence as required
  by `docs/policy.md`.

## Phase Closeout Checklist

Every phase closeout must answer these checks before the next phase can be queued:

- Evidence: source refs, artifacts, traces, screenshots, or reports prove the claims
  made by the phase.
- Tests: repo-native validation ran, and failures are either fixed or recorded as
  explicit blockers.
- Benchmark: relevant real-world jobs or typed benchmark reports exist, or untouched
  areas are explicitly `not_encoded` or out of scope.
- Claim boundary: the closeout does not convert blocked, incomplete, wrong-result,
  not-tested, public-proxy, local fixture, or reference-only evidence into parity or
  production claims.
- Next-phase readiness: the next phase has one accepted issue narrow enough for
  Decodex to execute without broad rewrites, and no later issue is queued.
