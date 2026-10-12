---
type: Decision
title: Preserve source occurrences and unknown graph validity
description: Repair evidence identity and agent evidence flow without replacing the storage backend.
status: accepted
authority: informative
owner: elf-service
last_verified: 2026-10-12
source_refs:
  - docs/evidence/benchmarking/2026-10-11-agent-evidence.md
code_refs:
  - packages/elf-service/src/update_resolution.rs
  - packages/elf-service/src/docs/event_sources.rs
  - packages/elf-service/src/graph_ingestion.rs
  - sql/tables/018_graph_facts.sql
related:
  - docs/spec/system_source_ref_doc_pointer_v1.md
  - docs/spec/system_graph_memory_postgres_v1.md
---
# Preserve source occurrences and unknown graph validity

PostgreSQL owns original documents, provenance, notes, and graph assertions.
Qdrant remains the retrieval index. This change requires no new service,
ontology engine, identity table, or storage backend.

| Obligation | Mechanism | Proof required |
| --- | --- | --- |
| Equal prose must not erase another source occurrence | Resolve unkeyed notes by body and stable source identity; ignore batch position and extractor explanation | Distinct sources and concurrent retries |
| Only the caller may authorize replacement | Preserve explicit-key authority; extractor keys remain hints | Existing key-authority regression |
| A source link must identify original bytes | Caller supplies the existing document and span; Source Library checks access, scope, hash, and bytes | Wrong owner, scope, hash, span, and immutable-source checks |
| Unknown effective time must remain unknown | Nullable `valid_from`; separate stored observation time; explicit unknown state | Historical reads, unknown-state counts, and no implicit supersession |
| Repeated assertions must retain time and owner identity | Active-fact uniqueness includes owner agent and validity start, with nulls not distinct | Different owners and effective times remain separate |
| Declared aliases must not split an existing identity | Resolve exact canonical/alias candidates before insert; reject conflicting candidates | Shared identity and ambiguity checks |
| Tool access must lead to an answer within its budget | Cached session expansion, direct source selectors, compact search results, and a reserved final response | Tool counts, terminal answer, and retained provider receipts |

Note identity uses the existing provenance envelope, so older event sources can
be compared without a backfill. Anonymous messages with identical content and
metadata cannot be distinguished without caller identity. The resolver uses a
transaction advisory lock over the candidate identity and holds it through the
write. It uses the existing BLAKE3 dependency for the lock key; a hash collision
only adds serialization and does not equate identities.

Graph ingestion serializes identity resolution within one tenant/project while
it checks declared surfaces. No fuzzy name matching or automatic merging of
existing entities is introduced. Extracted aliases must occur in supplied
evidence. Named identifiers and relation chains remain extractor assertions;
source occurrence and lexical validation do not prove semantic equivalence.
Pending predicates are not automatically promoted to authoritative vocabulary.

The graph table is owned by the existing declarative-first `sql/init.sql` entry
point and its table module. Its repeatable upgrade drops the effective-start
NOT NULL constraint and rebuilds the existing active-fact indexes. This needs a
coordinated schema/application upgrade: old clients that require a non-null
start must update before new unknown-time facts are written. Existing timestamps
are retained; the transition does not guess which old values were ingestion-time
fallbacks. Large shared environments must assess index rebuild locks separately;
this task exercises isolated Docker fixtures, not a production rollout.

The benchmark keeps the same source documents, questions, splits, model route,
4,096-dimensional embeddings, and original round/tool ceilings. Current native
extraction is necessary to exercise the changed schema and extraction guidance;
old extracted answers are not silently substituted. Exact embedding inputs are
reused. Agent-policy changes are recorded alongside native changes, so the result
is a system iteration and does not isolate one change's causal effect. The
existing repository-owned Python CLI and receipt format remain the benchmark
contract; product persistence and validation remain Rust-owned.
