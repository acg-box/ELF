---
type: Evidence
title: Frozen memory ablation and retrieval backend comparison
description: Separate memory contribution from cached-vector retrieval latency, recall, throughput, and deployment behavior.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/evidence/2026-10-10-retrieval-laboratory/protocol.json
  - config/benchmark/evidence/2026-10-10-retrieval-laboratory/ablation-summary.json
  - config/benchmark/evidence/2026-10-10-retrieval-laboratory/backend-summary.json
related:
  - docs/evidence/benchmarking/2026-10-10-elf-language-provenance.md
  - docs/runbook/retrieval-laboratory.md
code_refs:
  - scripts/retrieval_lab/ablation.py
  - scripts/retrieval_lab/backends.py
  - scripts/retrieval_lab/followup.py
  - scripts/retrieval_lab/analyze.py
---
# Frozen memory ablation and retrieval backend comparison

The frozen-candidate ablation exposes weaknesses hidden by the previous combined
answer score. Source-only and combined contexts both answer 16/16 scored memory
questions correctly after review. Note text alone answers 9/16. There is no
observed quality gain from adding notes on this small fixture.

Infinity has the lowest unfiltered single-query latency in the 50,000-vector
comparison. Qdrant is faster with the tested scope filter. PostgreSQL has the
highest sustained unfiltered throughput in this client-inclusive experiment,
but its default filtered plan is much slower. No backend wins every measurement.
These results do not justify an immediate storage migration.

## Frozen memory ablation

The experiment reuses the previous native retrieval pools for 20 memory questions.
Each pool contains up to 12 notes and 12 document results. It filters those same
rows into source-only, note-text-only, and combined contexts without reranking.
All 20 combined contexts reproduce the prior reader input exactly. The reader,
model route, maximum reasoning, output allowance, and 4,096-token cl100k_base
context limit remain unchanged. Condition order rotates by question ordinal.
Four development questions per condition remain outside the scored denominator.

| Context | Strict / 16 | Reviewed / 16 | Reviewed including development / 20 | Mean context tokens | Median answer seconds | Paid USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Source only | 13 | 16 | 20 | 840.4 | 3.25 | 0.00668607 |
| Note text only | 5 | 9 | 11 | 628.6 | 6.12 | 0.03074430 |
| Combined | 13 | 16 | 20 | 1469.0 | 3.60 | 0.00801601 |

The 13 review overrides retain the previous rubric: an answer that says no budget
owner has been appointed is valid when its supplied context states that absence.
The frozen oracle expects `unknown`. All other failed answers remain failures.
Every review entry binds to an answer hash. This lane mixes known absence with
unknown-information abstention; it cannot measure the latter cleanly.

Note-only input uses about 25% fewer context tokens than source-only input, but
its 50,148 output tokens exceed the source-only condition's 9,988. Its cost is
about 4.6 times higher. Missing information can increase reasoning work; shorter
context alone does not guarantee lower cost. These are single-run observations,
with provider caching and latency effects, not a universal cost ratio.

### What failed

- Retrieval: `REPLAY-0-632` exists in a persisted note but is absent from the
  selected note pool, including its structured fields and evidence. The reader
  cannot recover that procedure identifier from the supplied note context.
- Persistence or consolidation: some expected identifiers are absent from the
  persisted note bodies, although they remain in the original source records.
- Internal inconsistency: note `882729bf-5f44-4229-b251-6e360891fa9a` has
  `RETRY-0-907` in its body and original quote, but `RETRY-4-907` in its structured
  facts and summary. The original source was not rewritten.

Current source review identifies a compatible mechanism in
`packages/elf-service/src/add_event/materialize/none.rs`: the no-text-change
branch can overwrite structured fields under an existing note identity while
retaining its body and source reference. This is a candidate causal path, not a
newly reproduced unit-test diagnosis. This task does not patch product behavior.
The failures concern distinct business projects in one authorized dataset;
this experiment does not demonstrate a cross-tenant permission failure.

This is an ablation of the existing reader's note-text projection, not all ELF
memory capabilities. It does not exercise graph traversal, external domain
ontologies, or an agent that follows additional source references. The combined
context can conceal note failures because the original records still answer the
questions. The earlier 100/100 fixture result remains historically correct under
its stated protocol; it is not proof of note-store quality.

## Backend controls

The 71 stored source/note texts and 70 query texts all match saved embedding
responses exactly. All 141 vectors were reused: zero new embedding requests and
zero new extraction requests. Models and vector dimensions did not change.

The server versions are Qdrant 1.19.2, Infinity 0.7.4, and PostgreSQL 18.6 with
pgvector 0.8.6. Each server receives four CPUs and 4 GiB; the common Python client
receives four CPUs and 2 GiB. All use native ARM64 containers on the same shared
Docker host. Measured server phases run sequentially. Transport is gRPC for
Qdrant, Thrift for Infinity, and the PostgreSQL wire protocol with its NumPy
vector adapter. Reported latency includes those client and transport costs.

All dense tests use the same normalized float32 values, 1,536 dimensions, cosine
distance, HNSW M=16, construction ef=200, and search ef=64/128. The scale sets mix
cached real vectors with seeded noise. They contain 10,000 or 50,000 unique rows,
not that many independently embedded real documents. Exact NumPy top-ten results
are computed after filtering. Three repeats over 70 query vectors produce 210
samples per configuration, or 5,040 base latency measurements in total.

### 50,000 vectors, search ef=128

The filter retains 10% of rows, representing a scope/tenant constraint. It is not
an evaluation of ELF's complete authorization implementation.

| Backend | Filter | Recall@10 | Median ms | p95 ms |
| --- | --- | ---: | ---: | ---: |
| Infinity | None | 99.86% | 1.682 | 2.041 |
| Qdrant | None | 99.86% | 2.068 | 2.703 |
| PostgreSQL | None | 99.57% | 3.040 | 3.864 |
| Infinity | 10% retained | 100.00% | 4.537 | 7.605 |
| Qdrant | 10% retained | 100.00% | 1.329 | 1.678 |
| PostgreSQL | 10% retained | 100.00% | 20.721 | 22.126 |

All base measurements return ten distinct results and respect the tested filter.
All three backends pass the synchronous deletion/readback assertion. The full
10,000/50,000 and ef=64/128 matrix is in the evidence; this table is one matched
parameter slice, not each engine's independently tuned optimum.

### Sustained unfiltered throughput

The initial 280-query burst lasted less than 0.3 seconds and gave a misleading
impression of the steady-state ranking. It remains in the raw evidence but is
not used for the sustained comparison. The follow-up uses eight independent
clients and three ten-second rounds over the same warm 70-query set. All engines
have 49,999 rows after the matched deletion probe.

| Backend | Median QPS | Three rounds, QPS | Successful requests in accepted rounds |
| --- | ---: | --- | ---: |
| Infinity | 1395 | 1386, 1425, 1395 | 42080 |
| Qdrant | 2496 | 2496, 2470, 2681 | 76502 |
| PostgreSQL | 3072 | 3072, 3067, 3101 | 92434 |

Infinity's separate ten-second CPU probe reproduces about 1,355 QPS. The server
approaches its four-core limit while the client uses about 0.4 core. A saturated
Python client is not supported as the explanation for Infinity's limit in that
probe. These repeated warm queries and API clients still do not establish raw
engine limits, cold-query throughput, or results on x86/AVX hardware.

Qdrant's first sustained attempt completes two rounds, then fails in the Python
gRPC response-deserialization path. The server shows no OOM or restart. Explicit
client closure and per-round evidence retention were added before the next
attempt, which completes all three rounds without errors. The cause remains
unconfirmed; the failure log is retained. The earlier successful PostgreSQL
rounds are preserved rather than retroactively relabeled as that later harness.

### PostgreSQL plan diagnosis

The default 50,000-row filtered plan uses a B-tree/bitmap scope filter followed
by exact distance sorting. A separate connection discourages bitmap scans,
sequential scans, and sorts, causing an ordered HNSW scan with strict iterative
filtering. Its median falls to about 1.72 ms and p95 to about 4.13 ms, but recall
falls to 98.43%. This demonstrates a planner/recall tradeoff, not a reason to set
those planner switches globally. It is not mixed into the default-plan table.

### Small native hybrid probe

There are 420 retrieval-only observations: 70 queries, dense/hybrid modes, and
three backends. No reader calls are added here. Each backend receives the same
materialized lexical tokens; a common client RRF(k=60) combines dense and native
lexical ranks. Qdrant and Infinity use BM25-style retrieval. PostgreSQL uses its
built-in `simple` FTS and `ts_rank_cd`, with no additional BM25 extension.

All three cover the expected document facts on this tiny 14-document corpus.
For the 12 answerable scored memory questions, dense top-ten contexts cover all
expected facts in 10/12 cases for each backend. Hybrid reaches 12/12 for Infinity
and Qdrant, and 8/12 for PostgreSQL's tested FTS configuration. This is context
fact coverage, not answer accuracy. Different lexical scoring semantics matter;
it does not establish a general limit for PostgreSQL extensions.

## Deployment and measurement limits

Infinity's official 0.7.4 ARM64 image fails startup: its binary requires glibc
2.38 while the bundled Ubuntu 22.04 runtime provides 2.35. The test preserves
that binary and its resources in a Debian trixie runtime. The binary SHA-256 is
identical before and after repackaging. These are repaired-runtime results,
not successful deployment of the unmodified upstream image.

The experiment does not test million-scale real corpora, tensor/ColBERT search,
quantization, distributed operation, production durability, or end-to-end ELF
with a substituted backend. PostgreSQL here is a retrieval prototype, not a
newly delivered single-database ELF deployment mode. Qdrant and Infinity would
still need authoritative source/permission readback in ELF; that application
path is outside this database-only comparison. Index-build times use each
adapter's recorded insertion/index workflow, not an optimized bulk-load contest.

## Helix Foundry and DuckDB

The inspected Helix Foundry revision is
`84899851d845d1db98f9e328634f14e0ed4ad7b7`. Its object schema maps datasets,
primary keys and properties; relationships map source/target columns. DuckDB
executes declared-input SQL over versioned Parquet snapshots, while HelixDB
holds metadata, jobs, proposals, ontology objects and edges. Publication checks
input versions and proposal hashes, and edited overlays retain audit history.
See the [repository](https://github.com/HelixDB/helix-foundry) and its
[guide](https://github.com/HelixDB/helix-foundry/blob/84899851d845d1db98f9e328634f14e0ed4ad7b7/docs/GUIDE.md).

The useful ELF boundary is external entity identity, typed relation ownership,
and versioned source references. Business definitions, connector joins, metrics
and actions belong to the application. Stable external entity IDs could help
separate similarly worded project memories, but adopting a graph database alone
would not repair the observed consolidation inconsistency. Foundry itself was
reviewed from source; it was not deployed or performance-tested here.

DuckDB 1.5.6 actually aggregates the retained latency and answer rows in this
experiment. The two published SQL files reproduce 24 latency groups and three
ablation groups. It helps distinguish filtered regressions, recall tradeoffs,
context size, output tokens and cost without asking an LLM to calculate them.
The local analytical database is disposable; raw JSON remains authoritative.
This does not add DuckDB to ELF's production request path.

## Cost, validation and next decision

The 60 reader calls cost USD 0.045446385. The cumulative ELF ledger is
USD 0.319882517 of the original USD 10 ceiling. All 952 cumulative requests are
settled. Embedding reuse and all database experiments add no model charges.
The reader's maximum output allowance remains 943,718 with maximum reasoning.

Five focused reference tests, repository tooling checks, documentation/format
checks, public DuckDB SQL execution, and offline evidence verification pass.
Only experiment code and documentation change; no production storage migration
or fix for the newly identified memory inconsistency is included.

Prioritize memory-field consistency and entity-aware consolidation, then note
recall. Keep source fallback while measuring any proposed repair. Retain Qdrant
as the current default until a product-level replacement proves equivalent
filtering, source readback, updates and hybrid quality. Infinity remains a useful
candidate for the observed unfiltered-latency case, while a PostgreSQL-only mode
needs deliberate planner and lexical-index choices. None of these decisions
should rely on database branding or the previous saturated answer score.

Task-owned benchmark containers, anonymous volumes and runtime images were
removed after evidence collection. Shared services, base images and build caches
were preserved. The exact cleanup readback is retained in the evidence directory.

## Evidence

`config/benchmark/evidence/2026-10-10-retrieval-laboratory/` contains raw answers,
review hashes, cached vectors, provider receipts, backend observations, sustained
rounds, deployment/client failures and SQL. Its `verify.py` uses only Python's
standard library and checks historical embedding witnesses without paid calls.
Run the SQL from that directory with DuckDB, or follow the repository's Docker
laboratory runbook. The manifest binds every public artifact. Historical reports
and their measurements remain unchanged.
