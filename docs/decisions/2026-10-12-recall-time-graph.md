---
type: Decision
title: Supplement recall without inventing graph identity or time
description: Combine original-text, derived-text, and graph-incidence discovery with one source binding contract.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-12
code_refs:
  - packages/elf-service/src/evidence/recall.rs
  - packages/elf-service/src/evidence/source_recall.rs
  - packages/elf-service/src/graph_query/service.rs
related:
  - docs/decisions/2026-10-12-evidence-context.md
---
# Supplement recall without inventing graph identity or time

## Obligations

The Cedar August 15 original exists but has no derived note in the frozen corpus.
A note-only recall repair cannot recover it. Entity-name variants and missing
semantic edges also obstruct graph-only navigation. Historical graph queries
select facts at `as_of` but previously classified their temporal status at wall
clock time. These are separate defects with separate mechanisms.

Keep original bytes, provenance, current permissions, PG plus Qdrant, and full
4096-dimensional embeddings. Do not turn a lexical match, shared alias, or
co-occurrence into identity or causality. Do not require another database or
re-extraction to read originals that already exist.

## Maintained mechanisms

The [Hindsight recall architecture](https://hindsight.vectorize.io/developer/retrieval)
combines semantic, keyword, graph, and temporal candidates. The
[Graphiti temporal model](https://help.getzep.com/facts) separates fact validity
from recording time. These current first-party descriptions were inspected on
2026-10-12. The prior decision records pinned source reviews of Hindsight,
Graphiti, RAGFlow, LightRAG, and LlamaIndex.

ELF adopts complementary recall channels and explicit temporal interpretation.
It retains its existing permission and source-binding authority. It does not
copy automatic entity merging or infer missing validity dates.

## Decision

Add `elf_evidence_recall` and `POST /v2/evidence/recall`. The caller supplies one
to four literal subjects and an optional `as_of`. This is an on-demand supplement
to vector retrieval, not a replacement for it.

- Search readable derived text and incoming/outgoing facts through canonical
  names and aliases. Keep candidate entity IDs separate, including ambiguous
  aliases. Include historical facts as evidence candidates.
- Select at most twelve notes from at most 128 candidates. Prefer distinct
  source documents before additional notes from a covered source.
- Search original text independently of extraction. Resolve at most twelve
  matching source windows through the existing Source Library read path.
  Prefer these direct matches within the shared 32768-byte source budget.
- Return the existing evidence-pack contract. Recheck document access, exact
  bytes, and hashes. Preserve missing/truncated signals. Neither signal proves
  answer coverage. A document created later can report an earlier event.
- Classify graph-query facts at the requested `as_of`. A validity interval that
  contains a historical query time is `current` at that time even if it has
  ended today. Permission and lifecycle checks still use current access.

The reader must distinguish a continuing authorized state from a new approval
at a meeting, and distinguish both from a later decision. It must cite the
original statements that establish those distinctions. No timestamp parser
infers fact validity from source or ingestion time.

## Proportionality and alternatives

Postgres `strpos`, prepared parameters, existing UUID/time types, and existing
source selectors own matching and parsing. A bounded greedy document-coverage
pass prevents duplicate notes from using all selected slots. The service owns
this policy; callers do not reconstruct source pointers.

The fallback SQL uses literal substring matching, not a new full-text ranker.
It can scan the tenant/project-visible corpus; result limits do not bound scan
work. It is suitable for explicit recovery, not a demonstrated high-throughput
search path. Measure production latency and query plans before making it the
default. An indexed lexical arm is the replacement trigger if corpus growth
makes this path too costly. The service owner must revalidate this choice when
that access pattern changes.

Adding a search engine or tokenizer now would add operational and language
semantics without evidence that this bounded recovery needs them. Automatic
fuzzy merging could cross North/South boundaries. LLM edge repair would incur
cost and could certify unsupported causality. Neither is needed to recover
source context, so neither is included.

This improves navigation across graph fragments and absent edges. It does not
rewrite the graph into a complete ontology or assert that a missing causal edge
has been established. Future structured applications can supply reviewed entity
IDs and relations through the existing caller-authorized write contract.

## Verification boundary

The benchmark keeps the original questions, sources, notes, and vectors. A
batch planner receives only questions and corpus years, never oracle answers.
The consumer keeps only subject strings present in each question and records
rejected additions. Initial candidates remain frozen; supplemental retrieval
and historical-reader instructions form the new condition. No factual answer
is retried to improve a score. The repository-owned Python benchmark remains
under its checked-in Makefile and module-ownership authority.
