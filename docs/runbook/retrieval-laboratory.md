---
type: Runbook
title: Frozen memory ablation and retrieval laboratory
description: Compare source selection and database retrieval with cached embeddings and bounded reader costs.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-10
code_refs:
  - scripts/retrieval_lab/cli.py
  - docker/retrieval-lab/Dockerfile
---
# Frozen memory ablation and retrieval laboratory

## Responsibility and runtime

This is an isolated experiment. It does not replace ELF's storage or retrieval
implementation. Python owns the experiment because Infinity's official native
Thrift SDK and NumPy's exact vector reference run in the same process. This is a
scoped SDK exception to the default script-language policy. Dependencies run in
the repository-defined Docker image; no host packages are installed. Reconsider
the boundary if the native SDK is removed. Do not migrate unrelated scripts.

Build with `cargo make build-retrieval-lab`. Set `ELF_LAB_ARTIFACTS` to an absolute
artifact directory. `cargo make benchmark-retrieval-lab PHASE --root PATH` mounts
that directory at `/artifacts`. Paths supplied to this command are container
paths. Phases are `prepare`, `ablation`, `backend`, `followup`, and `analyze`.
Run reference checks with `cargo make test-retrieval-lab`.

The Compose file records the equivalent server settings used in the measurement.
Start one server at a time, for example:

```sh
docker compose -f docker/retrieval-lab/compose.yaml --profile infinity up -d --build infinity
cargo make benchmark-retrieval-lab backend --backend infinity --root /artifacts/retrieval-ablation
cargo make benchmark-retrieval-lab followup --backend infinity --root /artifacts/retrieval-ablation
docker compose -f docker/retrieval-lab/compose.yaml stop infinity
```

Repeat for `qdrant` and `postgres`; both have published images and need no build.
The PostgreSQL password in this isolated fixture is `lab-only-local`. It is not
a production credential. Infinity's recorded image is ARM64; do not present an
emulated run on another architecture as a native performance comparison. Use a
fresh artifact root for a new trial, and preserve old attempts. After collection,
`docker compose -f docker/retrieval-lab/compose.yaml down -v` removes only this
Compose project's containers, network and anonymous volumes. Check ownership and
active use before removing task-built images. The measured run used equivalent
individual Docker commands on the default bridge; Compose is a reproduction aid,
not a claim that its network topology was measured.

## Input and cost controls

A public reproduction can import the checked-in receipt bundle directly:

```sh
cargo make benchmark-retrieval-lab prepare --root /artifacts/retrieval-ablation --receipts /repo/config/benchmark/evidence/2026-10-10-elf-language-provenance/provider-receipts.jsonl.gz
```

`prepare --receipts PATH` reads a receipt directory or that gzip JSONL bundle, matches exact
embedding input text, and records each receipt hash. It fails if a vector is
missing. The ablation reuses the previous native candidate order and asserts that
its combined context reproduces all 20 previous contexts exactly. It filters
that pool into source-only, memory-only, and combined conditions, using the same
4,096-token cl100k_base budget and unmodified shared reader function. It rotates
condition order by question ordinal. It does not re-extract notes or regenerate
embeddings. This is a frozen-candidate ablation, not a new native API benchmark.

Only `ablation` needs provider access. Invoke it through `cargo make
benchmark-budget` with the existing cumulative USD 10 ledger. Inject the actual
provider key only into that gateway. Pass its ephemeral proxy variables into
the consumer container. Keep the previous maximum output allowance of 943,718
and maximum reasoning. Reserve enough for one maximum-length response; do not
lower the model's output allowance to fit a smaller reservation tranche.
Retain failed receipts before an explicit retry. Keep strict scores and semantic
review corrections separate, using the previous report's review rubric.

## Full-dimension memory regression

The matched ELF runner uses Qwen3-Embedding-8B with all 4,096 dimensions.
Default extraction profile v3 preserves subject and incident context. Existing
pinned profiles stay pinned. Model-generated keys are retained as
`source_ref.extracted_key` hints; only caller-authorized `add_note` keys can
replace a note. Automatic extraction uses unkeyed, exact-text deduplication.
Do not repair old derived notes by guessing from their corrupted fields. Use
accepted original sources and retain prior evidence when re-extracting them.
Keep PostgreSQL as the source of truth and Qdrant as the production index.
Do not truncate, pad, or reuse a 1,536-dimensional vector as a 4,096-dimensional
vector. Old receipts remain valid only for their recorded configuration.

For a new matched run, use a fresh artifact directory and retain native state,
source-integrity checks, cases, and provider receipts. Pass `--native-run PATH`
to `prepare` to import that run instead of the historical fixture. Missing exact
inputs stop preparation. `--fill-missing` explicitly permits generation through
the same budget gateway; completed receipts are reused on restart. All backends
use the resulting shared dataset, including its recorded dimensions.

The current laboratory client has a 4 GiB limit to hold 50,000 full-dimensional
vectors and the independent exact reference. Record this change when comparing
with older 2 GiB client runs. Compare Qdrant and Infinity sequentially. Do not run
the ordinary pgvector HNSW adapter at 4,096 dimensions: its vector index limit is
2,000, and the halfvec index limit is 4,000. Do not change dimensions to bypass it.

## Database controls

Use isolated containers, each limited to four CPUs and 4 GiB RAM. Run measured
backend phases sequentially. The client image uses four CPUs and 4 GiB; the historical 1,536-dimensional run used 2 GiB.
Record server image digests, architecture, client versions, resource samples,
and deployment failures. No foreign containers or shared image caches may be
removed. Database containers use these loopback-only host ports:

| Backend | Port | Container name |
| --- | ---: | --- |
| Qdrant HTTP / gRPC | 19865 / 19866 | elf-lab-qdrant |
| PostgreSQL with pgvector | 19867 | elf-lab-postgres |
| Infinity Thrift / HTTP | 19869 / 19870 | elf-lab-infinity |

The Infinity 0.7.4 ARM64 image failed startup because the bundled binary requires
a newer glibc than its Ubuntu 22.04 runtime. `Infinity.Dockerfile` preserves the
official binary and resources in a Debian trixie runtime. Report this separately
from an unmodified upstream-image result; record both binary hashes.

All backends use identical normalized float32 vectors, cosine distance, HNSW
M=16 and construction ef=200. Query ef values are 64 and 128. PostgreSQL keeps
its normal planner and enables strict iterative scans for filtered HNSW queries.
Its FTS path uses built-in `simple` tsvector and ts_rank_cd; it is not a BM25
extension. Qdrant uses native BM25, and Infinity uses native full-text search.
For the small hybrid probe, all receive the same materialized lexical tokens,
and the client combines rank lists with RRF(k=60). This textbook rank sum has
explicit golden tests. It is not a newly proposed ranking algorithm. Backend
lexical scorers still differ, so separate this lane from matched dense retrieval.

The 10,000 and 50,000 vector workloads mix cached real vectors with seeded noise.
They test mechanics and recall/latency tradeoffs, not semantic quality at scale.
The independent NumPy cosine reference filters before selecting top ten. Report
unfiltered and 10%-selectivity results separately, with three repeats per query,
p50/p95, recall@10, underfilled results, eight-client throughput, index-build
wall time, and deletion visibility. Include API transport/client overhead in
latencies; Infinity uses Thrift, Qdrant gRPC, and PostgreSQL its wire protocol.
Results on this shared ARM Docker host are not hardware-general performance claims.

The initial 280-query concurrency burst is a short probe, not sustained throughput.
`followup --backend NAME` measures three ten-second, eight-client rounds against
49,999 rows after the deletion probe. Completed and failed rounds remain in the
artifacts. Each worker owns and closes its client. PostgreSQL also gets a separate
forced-HNSW filtered diagnostic, with planner changes confined to that connection.
Report its recall tradeoff alongside the default-plan result; do not recommend
those switches globally.

## Analysis and retention

`analyze` builds a local DuckDB file and SQL aggregate over retained measurement
rows. Raw JSON remains authoritative. The analytical database is disposable and
can be regenerated. It helps compare latency at equal recall, inspect filtered
regressions, and correlate context length with reader costs. DuckDB is not in
ELF's production request path and does not replace PostgreSQL.

Publish a separate dated evidence report. Preserve earlier reports unchanged.
After collecting receipts and resource measurements, remove only this run's
containers, volumes, images, and temporary credentials. Keep reusable frozen
embedding receipts and the cumulative cost ledger.
