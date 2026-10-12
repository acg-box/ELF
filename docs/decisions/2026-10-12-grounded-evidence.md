---
type: Decision
title: Bind agent claims to contextual source evidence
description: Reuse Source Library for bounded parent context, explicit claim citations, and edge evidence.
status: accepted
authority: informative
owner: elf-service
last_verified: 2026-10-12
code_refs:
  - packages/elf-service/src/evidence.rs
  - packages/elf-service/src/graph_ingestion.rs
  - sql/tables/019_graph_fact_evidence.sql
  - scripts/benchmark_agent/runner.py
related:
  - docs/decisions/2026-10-12-evidence-integrity.md
  - docs/runbook/elf-agent-evidence-benchmark.md
---
# Bind agent claims to contextual source evidence

PostgreSQL owns original records, memory, and graph evidence. Qdrant remains a
derived retrieval index. This change adds no service, graph engine, document
copy, or new persistence root. The existing ContextPack memory items carry
`note_id`; clients can expand that identifier through `elf_notes_evidence` or
`GET /v2/notes/{note_id}/evidence`. ContextPack remains a bounded selector view.

## Mechanisms and authority

| Observed obligation | Mechanism | Proof |
| --- | --- | --- |
| A compact note can omit its subject | Read the existing original span with metadata and offsets; keep the derived note distinct | Native source expansion, UTF-8 bytes, hashes, revoked access |
| An answer can cite an unrelated retrieved record | Require per-claim quotes and semantic states in the benchmark reader; expose deterministic binding checks to clients | Frozen full answers, quote-binding checks, separate semantic reviews |
| Missing information is not explicit absence | Distinct supported, absent, unknown, and conflict states | Asymmetric owner and conflict cases |
| Different subjects can share an extracted alias | Automatic extraction resolves canonical names only; aliases remain retrieval hints and can be ambiguous | Two accounts sharing Atlas remain distinct |
| An application can know the exact entity | An existing caller-supplied entity ID selects a node within the project; automatic extraction cannot assign it | Correct ID and missing ID tests; project-scoped lookup |
| An edge needs evidence beyond co-occurring endpoints | Each normalized relation carries a verbatim source quote containing both endpoints | Two-hop chain, persisted edge quotes, readable-note filtering |

The evidence resolver follows at most four distinct supported pointers and uses
Source Library's existing L2 excerpt bound and read-profile checks. It returns
`complete: false` when pointers cannot be resolved or exceed the count budget.
It does not conceal storage failures as missing evidence. No model call is
needed for expansion. An original quote proves what a source says; it does not
prove that the source is correct.

`POST /v2/evidence/check` and `elf_evidence_check` check up to twelve claims,
each with at most eight citations. A source citation requires its original
hash and exact quote. A note citation checks the current derived body. Reads
recheck permissions. The result explicitly says `semantic_support:
not_evaluated`: a real quote from the wrong project is still a semantic error.
This API does not provide an automated entailment oracle or certify an agent's
supported/absent/conflict judgment. Clients must retain those distinctions.

Automatic entity aliases cannot authorize a merge between different canonical
identities. This can retain duplicate nodes. Caller-supplied identities and
explicit caller aliases remain available when the application has stronger
identity evidence. No fuzzy resolver is added. A normalized predicate is an
interpretation backed by a quote, not a verbatim fact string. New predicates
remain pending; existing application-owned predicate policies remain in force.
The optional relation quote is stored on the existing fact/note evidence link.
Graph query returns quotes only for the evidence pairs selected by its existing
access checks. Legacy links can lack a quote.

## References and adaptation

- [Hindsight Reflect](https://hindsight.vectorize.io/developer/reflect): hierarchical
  evidence gathering and context expansion. ELF adds source expansion and explicit
  per-claim bindings; it does not copy disposition or mental-model machinery.
- [RAGFlow parent-child retrieval](https://ragflow.io/blog/ragflow-0.23.0-advanding-memory-rag-and-agent-performance):
  precise retrieval with broader context. ELF reuses the immutable original span.
- [Anthropic contextual retrieval](https://www.anthropic.com/engineering/contextual-retrieval):
  preserve a fragment's source context. ELF initially expands context at read time;
  it does not add a second embedding pass or overwrite original text.
- [Zep entity resolution](https://help.getzep.com/how-graph-creation-works): prefer
  unresolved identity over a wrong merge and retain source episodes. ELF keeps
  deterministic canonical identity and explicit caller authority.

The implementation uses existing Serde, SQLx, Source Library hash/selector
verification, and PostgreSQL transactions. A new entity-resolution library or
LLM judge is not justified for mechanical byte binding. Semantic review remains
a separate benchmark obligation. Reconsider an entailment model only when its
measured benefit exceeds its latency, error rate, and API cost.

## Schema and profile evolution

`sql/init.sql` and its existing `019_graph_fact_evidence.sql` module own the
additive nullable `quote` column. The module supports fresh initialization and
repeatable upgrade. There is no backfill, data rewrite, or second SQL root.
Apply the additive schema before the new application. Older application reads
remain compatible. This task validates isolated Docker databases, not a
production rollout or lock duration at production scale.

Existing merged graph identities are not split automatically. The change prevents
new alias-authorized merges; it cannot reconstruct a lost identity distinction
from an already merged node. A separate source-backed rebuild is needed for
affected historical derived data. The benchmark uses a fresh isolated database.

The changed guidance is built-in profile `default` version 5. Existing stored
versions and default pointers remain unchanged. Existing deployments must
explicitly opt in. Source bytes and historical benchmark results are retained.

## Evaluation owner and limits

The repository-owned Python benchmark remains the execution authority for this
matched experiment. Keeping its request serialization, saved-response replay,
and exact embedding-cache keys is necessary for comparable retained trajectories;
this task does not migrate that protocol into a different runtime. Rust owns
product evidence verification and persistence. Python only orchestrates the
existing public APIs, records receipts, and evaluates outputs.

The original twenty questions remain separate from sixteen new contrast cases,
which were committed before implementation and paid requests. All conditions
use the expanded thirty-six-source corpus. Original-question results therefore
include extra distractors and are not a corpus-identical before/after experiment.
Models, routing,
full 4,096-dimensional embeddings, twelve-response/twenty-four-tool ceilings,
and the cumulative $10 ledger remain fixed. After a final answer, a deterministic
native binding audit may run; it returns no new facts to the reader and cannot
replace or resample the answer. Score answer truth, subject/time attribution,
quote bindings, abstention, graph evidence, and actual cost separately. A
single known fixture is not a general product ranking. Primary cases can use two
independent workers under one locked cost ledger; controls remain serial. The
gateway requires explicit `--maximum-profile-concurrency 2` and reserves the full
input and output cost for each active request. Its default remains one request. Each
case retains the same prompt, output allowance, and tool limits. Report this
execution policy with latency; do not compare concurrent wall times directly
with prior serial measurements.
