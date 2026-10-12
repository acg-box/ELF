---
type: Decision
title: Keep source context and citation identity together
description: Compose bounded source expansion and native citation resolution without a new storage authority.
status: proposed
authority: normative
owner: elf-service
last_verified: 2026-10-12
---
# Keep source context and citation identity together

## Evidence and scope

PR #408 retained 132 answers. Exact quote binding passed for every initial-memory
control, but only 4/16 contrast answers passed the combined factual and semantic
checks. A real quote can belong to the wrong project. Source-enabled readers
also copied source text onto derived-note identifiers. The next change must
keep context with evidence and reduce manual citation assembly.

Original text remains immutable. PostgreSQL owns records; Qdrant remains a
derived index. Do not merge identities from co-occurrence, infer validity from
ingestion time, or claim that a mechanical citation check proves entailment.

## Maintained project mechanisms

Repository metadata and pinned source were inspected on 2026-10-12. All five
repositories are unarchived and had pushes between October 8 and October 12.
Activity is maintenance evidence, not proof of retrieval quality.

| Project | Inspected mechanism | ELF adaptation and boundary |
| --- | --- | --- |
| [Hindsight](https://github.com/vectorize-io/hindsight/blob/3abbc60681c09ef196128c7a1af6badc35adc1ef/hindsight-api-slim/hindsight_api/engine/memories/pg/recall.py) | Recall keeps text, context, event times, document IDs, and chunk IDs together. | Preserve source context and declared source time in the read result. Do not copy its timestamp fallback into fact validity. |
| [Graphiti](https://github.com/getzep/graphiti/blob/0a3b1711b018e5590cf5c44a3ee3e67d6733ee13/graphiti_core/prompts/extract_edges.py) | Edges retain episode provenance and distinguish assertion validity from a future event date. | Keep source timestamp, capture time, and effective time distinct. Do not add automatic contradiction resolution. |
| [RAGFlow](https://github.com/infiniflow/ragflow/blob/b596773abf01bc2942c4693e03b6fc7c334f1667/docs/guides/dataset/configuration.md) | Small child chunks retrieve larger parent context. | Use notes as retrieval candidates and resolve their bounded original windows. Do not re-chunk or re-embed the frozen corpus. |
| [LightRAG](https://github.com/HKUDS/LightRAG/blob/4d0afc1bc36e6a34d4a5895b68efe9413748627a/lightrag/operate.py) | Entity and relation source IDs lead back to text chunks; references are assembled from retrieved chunks. | Treat graph edges as evidence navigation candidates. A shared source is not a newly asserted semantic edge. |
| [LlamaIndex](https://github.com/run-llama/llama_index/blob/6dd2f3cdd9ce7ff927ea8d46ccee08875bb00f95/llama-index-core/llama_index/core/query_engine/citation_query_engine.py) | Citation nodes receive explicit source labels; split-node IDs and offsets must match the actual cited text. | Generate native, hash-guarded source references. Resolve exact bytes on the server instead of asking the model to copy IDs, hashes, and text independently. |

## Selected composition

Add a bounded evidence-pack read over existing note-evidence expansion. The pack
keeps derived notes separate from deduplicated original windows and links each
note to its windows. Source text preserves explicit subjects, dates, negatives,
and qualifications that extraction can omit. Source timestamps are labels for
the records, not inferred effective dates. Missing context stays incomplete.

Add a source-reference citation form to the existing claim checker. A reference
identifies a document, its content hash, and a byte span. It grants no access:
resolution uses current tenant, project, agent, profile, and source lifecycle
checks. Legacy quote citations continue to work. The checker returns resolved
citations and still reports semantic support as not evaluated.

This combination is an ELF integration decision, not a claim of a new research
algorithm. It requires no new database, secret, model pass, or entity resolver.
The existing Context Pack continues to select references; the evidence pack
materializes selected notes into bounded readable evidence.

## Graph diagnosis

The frozen graph has 119 facts and 123 evidence links. Ninety-seven facts have
unknown validity. For Larch, the project points to a delivery mode and that mode
points to an incident. The recovery procedure points only to the scalar
`missing updates`. No stored semantic edge joins the incident and procedure.
More traversal depth cannot repair this missing relation. Name fragments and
directed-only traversal are separate questions and must be measured separately.
Inspect incidence, scalar endpoints, name variants, and source-note connectivity
before selecting a graph change. Never repair the benchmark graph with oracle
identifiers or synthesize causal edges from shared provenance.

## Validation and cost

Keep the original 36 questions, source corpus, extraction, initial note IDs,
reader model, full output allowance, and 4096-dimensional embeddings frozen.
Test the new read path over every question if the ledger admits it. Report its
prefetch work explicitly; this is not a repeat of all five prior ablation arms.
Old answer replay is offline evidence only, not a new model result.

The starting paid total is $7.906963426. Conservative exposure is $8.990763826,
including two unsettled reservations. Keep the cumulative $10 gate and do not
clear these reservations without settlement evidence. Complete local contract,
permission, source-integrity, and graph diagnostics before paid calls. Retain
all failures and distinguish factual, semantic, and mechanical results.

## Mechanism proportionality

Use existing serde, UUID, BLAKE3, and Source Library primitives. A versioned
bounded locator format is sufficient for a reference; a token service, signing
key, registry table, or new citation dependency would add lifecycle work without
granting needed authority. Test malformed locators, hashes, UTF-8 boundaries,
revoked access, partial packs, and unchanged originals. The service owner must
revisit the format if sources become mutable or reference requirements change;
remove custom formatting if a canonical Source Library locator becomes available.
