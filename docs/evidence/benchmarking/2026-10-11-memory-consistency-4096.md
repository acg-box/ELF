---
type: Evidence
title: Memory identity and full-dimension retrieval validation
description: Validate safe memory writes and relevance-aware selection with full Qwen3 embeddings.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-11
source_refs:
  - config/benchmark/evidence/2026-10-11-memory-consistency-4096/manifest.json
  - config/benchmark/evidence/2026-10-11-memory-consistency-4096/ablation-summary.json
  - config/benchmark/evidence/2026-10-11-memory-consistency-4096/backend-summary.json
related:
  - docs/evidence/benchmarking/2026-10-10-retrieval-laboratory.md
  - docs/runbook/retrieval-laboratory.md
code_refs:
  - packages/elf-service/src/add_event/service/decision.rs
  - packages/elf-service/src/search/ranking/diversity/selection/enabled.rs
  - scripts/benchmark-elf-matched.py
  - scripts/retrieval_lab/prepare.py
---
# Memory identity and full-dimension retrieval validation

Reviewed note-only accuracy rises from the historical 9/16 to 13/16, but source
text alone still scores 16/16 and the combined context scores 15/16. Memory
consistency and recall improve without establishing an answer-quality advantage
over original evidence. Qdrant is faster than Infinity in this full-dimension
latency and sustained-throughput experiment.

This change retains PostgreSQL and Qdrant. PostgreSQL owns source records,
memory records, provenance, versions, and indexing work. Qdrant serves vector
retrieval. The experiment uses Qwen3-Embedding-8B with all 4,096 dimensions.
It does not truncate, pad, or quantize vectors.

## Write identity

Similarity no longer authorizes a memory replacement. An explicit caller key
identifies an update within the existing tenant, project, agent, scope, and
type boundary. Unkeyed writes deduplicate only byte-identical note bodies.
Other unkeyed writes create independent notes.

An extraction model can emit the same plausible key for unrelated subjects.
The diagnostic run reproduced that behavior. Extracted keys now remain
descriptive hints in provenance; they do not supply update authority. This
rule also applies to existing pinned extraction profiles.

This favors preservation over automatic consolidation. Semantically similar
events can create additional notes. A caller that owns a stable identity can
still use an explicit key; the model cannot invent that authority.

A duplicate is a true no-op. It cannot replace fields or provenance beneath
an unchanged note body. A body update clears obsolete scalar fields in the
same transaction before the new extraction is applied. Source records remain
unchanged. Existing damaged memories require a separate, source-backed repair;
this change does not silently rewrite historical data.

The default extraction profile is version 3. It requests self-contained subject
and incident context while retaining verbatim evidence. Existing pinned and
custom profiles keep their selected version.

## Selection diagnosis

The full-dimension baseline stored the correct current retry policy for Larch.
For the corresponding question, the note ranked fourth at retrieval and second
after reranking. Hard similarity suppression then moved it to position 40,
outside the first 12 notes supplied to the reader. Related notes can contain
complementary facts or different versions; similarity alone does not establish
redundancy.

Selection now uses the continuous MMR relevance and redundancy score. It keeps
the existing lambda of 0.7 and deterministic tie handling. The obsolete hard
similarity threshold and skip-count settings are removed from active contracts.

The query-only rerun moves that retry-policy note into the returned set at
position 7. A separate recovery-procedure note remains outside the first 12:
retrieval rank 18, rerank rank 20, and final position 20. Its text contains the
correct procedure, batch, and outage identifiers, but calls its subject "the
team" without naming Larch or Mara. The self-contained extraction instruction
did not fully prevent subject loss. The preserved source can resolve it, but
note-only retrieval cannot claim success from that source. This is a remaining
representation and ranking limitation, not evidence that a different vector
database would repair the missing subject.

## Experimental boundaries

The initial full run contains 140 answers. A second run reuses the verified
source records, 54 memory notes, and canonical vector hashes. It reruns the 40
affected memory answers and retains 100 document answers with explicit origin
metadata. Reused document answers are not new calls on the second binary.

The reader remains DeepSeek V4.1 Flash with maximum reasoning and its provider
output allowance. Original workload and oracle files remain frozen. Report
strict and reviewed scores separately. Known-absence questions and substring
checks in the historical oracle require explicit, answer-bound review.

The three-way ablation compares source text, note text, and their combination
within the same selected candidate pool. It does not measure an agent that
traverses graph facts or follows additional source references. Combined answers
can conceal failures in note retrieval.

## Answer and recall results

| Context | Strict / 16 | Reviewed / 16 | Reviewed including development / 20 | Mean context tokens | Median answer seconds | Paid USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Source only | 12 | 16 | 20 | 839.50 | 3.72 | 0.006117720 |
| Note text only | 9 | 13 | 16 | 673.65 | 4.31 | 0.015532269 |
| Combined | 11 | 15 | 19 | 1513.15 | 4.41 | 0.008785116 |

All 60 requests completed. The 14 semantic overrides concern explicit absence
of a budget owner, including case, punctuation, and the subject-qualified
phrase "No budget owner has been appointed for Sable." The frozen oracle asks
for `unknown`. The supplied context states the absence. These overrides follow
the historical known-absence rule; raw answers and support flags remain intact.
The fixture does not measure unknown-information abstention cleanly.

Note text uses about 20% fewer context tokens but costs about 2.54 times as much
as source-only answers in this run. Its larger reasoning output outweighs the
smaller input. Provider caching and single-run variability limit that ratio.

Note-only failures are the recovery identifiers for Larch, Reed, and Sable.
The development set also has a stale Cedar retry-policy answer. The combined
condition fails the Sable recovery identifier even though its source context
contains that identifier. The separate native retrieval run fails the same
question. Both answers repeat a vague note directive instead of the concrete
procedure. Adding notes does not improve this fixture's source-only score.

Compared with the historical 1,536-dimensional run, reviewed note-only accuracy
increases from 9/16 to 13/16. This comparison changes write identity, extraction,
vector dimensions, and selection together; it cannot isolate the effect of
dimensions. Within the matched 4,096-dimensional fixture, removal of hard
similarity suppression increases complete note-body fact coverage from 7/12 to
9/12 supported test questions. Those two candidate pools use the same stored
notes and canonical vectors.

The native Context Pack memory lane scores 12/16 strict and 16/16 reviewed.
Its hydrated reader context contains source documents, so this is not a
note-only result. The native retrieval memory lane scores 11/16 strict and
15/16 reviewed. The 100 reused document answers retain their original scores:
Context Pack 48/50 strict, retrieval 47/50 strict, and both 50/50 reviewed.
Two numeric substring corrections and one explicit bank-routing-number absence
correction remain bound to their original answers. No failed factual answer was
resampled or counted as correct.

## Consistency and cost

The full run retains 34 original documents and 54 active notes. All original
bytes and citation offsets match the frozen inputs. The ingestion result has
54 additions, one duplicate no-op, and zero rejected candidates. The integrity
audit verifies 74 verbatim quotes and finds no identifier mismatch between note
bodies, scalar fields, and their bound sources. Canonical embedding tables hold
54 note, 54 chunk, 217 field, and 34 source-chunk vectors, all with 4,096
dimensions. Their hashes remain unchanged across the selection rerun.

Cumulative provider-reported cost is USD 0.576849154 against the existing USD 10
ceiling. This task adds USD 0.256966637 to the prior USD 0.319882517. It includes
the stopped diagnostic extraction trial, the full baseline, the 40-answer
selection rerun, and all 60 ablation answers. No requests remain unsettled.
The backend dataset reuses all 158 exact-input vectors; it makes no new
embedding calls. Native query APIs still make their normal query-embedding
calls, which are included in the ledger.

One baseline extraction received HTTP 200 with `finish_reason: error` and no
content after an upstream network failure. Its reported customer cost was zero.
The failed attempt is retained and its event was retried successfully. The
provider adapter now treats this envelope as a provider parsing failure before
domain deserialization, using the existing bounded retry path.

## Backend results

The backend experiment uses the same cached 4,096-dimensional vectors for both
engines. Its larger corpora are seeded synthetic mixtures, not a large real
document collection. Client transport, a shared Docker host, and native ARM64
runtime behavior are part of the measured result. No single measurement can
establish a universal backend winner.

Qdrant 1.19.2 and Infinity 0.7.4 run sequentially on native ARM64, each limited
to four CPUs and 4 GiB. The common client has the same limits. The native ELF
answer fixture retains Qdrant 1.18.0, as in its prior controlled run. The
backend laboratory is a separate engine comparison, not a production adapter
migration. Infinity uses the official ARM64 binary on the repository's Debian
runtime image because the stock image has the previously recorded glibc
compatibility problem. This is not a stock-image deployment acceptance test.

Both engines use normalized float32 cosine vectors, HNSW M=16,
construction ef=200, and query ef=64/128. There are 3,360 dense observations,
280 small-corpus dense/hybrid observations, and three ten-second sustained
rounds with eight clients per engine. The table below uses ef=128, with 210
observations per row and an independent NumPy exact top-10 reference.

| Rows | Filter | Engine | Recall@10 | Median ms | p95 ms |
| ---: | --- | --- | ---: | ---: | ---: |
| 10,000 | None | Qdrant | 1.0000 | 2.038 | 2.626 |
| 10,000 | None | Infinity | 1.0000 | 2.855 | 4.433 |
| 10,000 | 10% scope | Qdrant | 1.0000 | 1.330 | 1.577 |
| 10,000 | 10% scope | Infinity | 1.0000 | 15.356 | 18.857 |
| 50,000 | None | Qdrant | 1.0000 | 2.759 | 3.710 |
| 50,000 | None | Infinity | 1.0000 | 4.208 | 5.641 |
| 50,000 | 10% scope | Qdrant | 1.0000 | 1.618 | 2.009 |
| 50,000 | 10% scope | Infinity | 0.9986 | 11.835 | 22.071 |

At 50,000 rows, median sustained throughput is 1,710.64 QPS for Qdrant and
899.03 QPS for Infinity. All sustained requests return ten candidates
without request failures or underfilled results. Index construction takes
97.02 seconds for Qdrant and 121.62 seconds for Infinity. Scope-filter and
synchronous-delete visibility checks pass for both engines.

The small-corpus hybrid probe has one advantage for Infinity: complete expected
fact coverage on 12/12 supported memory questions, versus 11/12 for Qdrant.
Both cover 8/12 with dense retrieval alone. This probe mixes source and memory
rows and uses each engine's lexical retrieval before reciprocal-rank fusion.
It does not include ELF's reranker or final reader, so it is not an answer score.
Both modes and engines have complete expected fact coverage on supported
document questions.

This experiment supports retaining Qdrant. It does not prove that Infinity is
slower for other dimensions, corpora, hardware, transports, concurrency, or
index settings. The earlier 1,536-dimensional result must not be used as a
substitute for these full-dimension measurements. PostgreSQL ANN is not tested
through dimensionality reduction or an alternate representation.

## Validation and follow-up

The runtime source revision is `7798cc12dd81930e4e10c89bfb5dfc4ae7ac32f1`;
the pre-selection baseline is `cfb1bc8e`. The runtime passes 550 Rust tests with
real PostgreSQL and Qdrant and zero skipped tests. Clippy and formatting pass.
The benchmark contract suite passes 157 tests. Offline verification checks
receipt-backed full vectors, source and note integrity, paired candidate data,
answer hashes, reviewed scores, backend measurements, and cumulative accounting.

Run `python3 config/benchmark/evidence/2026-10-11-memory-consistency-4096/verify.py`
from a clean checkout to verify the evidence package. Repository tooling also
checks that all manifest files are tracked. The original source records and
cached embeddings remain available for future controlled comparisons.

The next quality priority is source-grounded subject and temporal context in
each memory representation, followed by source-reference resolution for vague
directives. A different vector database does not resolve those semantic gaps.
Do not claim that note memory now outperforms original evidence.
