---
type: Runbook
title: RAGFlow native Docker benchmark
description: Run RAGFlow document retrieval through the shared bounded benchmark profile.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-09
source_refs:
  - config/benchmark/ragflow-v1.json
code_refs:
  - scripts/benchmark-ragflow.py
  - scripts/benchmark_targets/ragflow.py
  - scripts/benchmark_deep/documents.py
  - docker/benchmark/compose.yml
related:
  - docs/runbook/benchmarking/full_comparison.md
---
# RAGFlow native Docker benchmark

Use the pinned RAGFlow 1.0.0-rc1 image in `config/benchmark/ragflow-v1.json`.
The server and benchmark client run in Docker. The host starts the budget
gateway and the controller. Do not install the RAGFlow runtime on the host.

## Native service

Use the official Docker deployment at source revision
`14bb02ee4584c1ab18f0c722c48beecd6bbf9860`. Keep the image pinned to digest
`sha256:31ccf0336d8910f6d90ac7d4fff766cc0483ec10042b906a377f27bfe09f818b`.
This image is Linux AMD64. Record emulation when the host uses ARM.

Use an isolated Compose project and volumes. The measured deployment uses
Infinity, MySQL, Kvrocks, NATS, object storage, and ClickHouse. RAGFlow's Go
server rejects `DOC_ENGINE=opensearch` in this release, despite its presence
in the Compose configuration. Do not report that startup failure as a
retrieval result. Keep the API on loopback; do not publish database ports.

The official Go entrypoint requires the API server, ingestion worker, and
admin server. Enable the admin server and initialize its local superuser.
The benchmark uses a separate ordinary user. Disable datasource synchronization
for this synthetic experiment. Wait for migrations and service readiness.

Connect the benchmark client to the server network. Its default network is
`elf-ragflow-benchmark_ragflow`; set `RAGFLOW_NETWORK` for another project.
The server must have the `ragflow-cpu` network alias. Copy `conf/public.pem`
from the pinned server image for the registration API's password encryption.

## Bounded run

Run `cargo make benchmark-ragflow` inside `cargo make benchmark-budget` with
Personal Infisical injection. The provider key goes only to the budget gateway.
The gateway supplies an ephemeral token to the native model configuration.
Use the existing cumulative ledger, its authorized ceiling, and a small tranche.

```sh
acg secret --env prod --path /profitpilot \
  --inject OPENROUTER_API_KEY=OPENROUTER_API_KEY -- \
  cargo make benchmark-budget \
  --ledger /absolute/path/to/budget-ledger.json --ceiling 20 --tranche 0.50 \
  --embedding-provider nebius --embedding-dimensions 1536 \
  --embedding-429-retries 3 -- \
  cargo make benchmark-ragflow \
  --public-key /absolute/path/to/public.pem \
  --artifact-root /absolute/path/to/new-condition \
  --workload-group documents
```

The controller creates a fresh native user and model instance. Use the
`OpenAI-API-Compatible` driver for the local gateway. The ordinary OpenAI
driver rejects private addresses. Do not disable its address guard.
The shared gateway fixes Qwen3 Embedding 8B at 1,536 dimensions. The native
model reference includes its instance: `model@instance@provider`.

The `behavior` group reuses the existing 42-query deep workload. The `documents`
group uses eight synthetic text sources and twelve questions about complete
exception lists, table rows, and absent facts. It is not a PDF, OCR, or native
spreadsheet parsing test. Existing `all` workloads remain unchanged.

## Interpretation and cleanup

Retain every failed condition separately. Check `ingestion_status`, native
chunks, contexts, shared-reader answers, and source identity. Map citations
through native document IDs; never infer identity from an answer match.
RAGFlow source replacement here uses native delete plus upload. It is not an
atomic update. Dataset filtering is not proof of authorization revocation.
Native Memory, Agent, knowledge compilation, and synthesis are not measured.

Client cleanup does not stop the separately managed server. After the last
condition, preserve sanitized evidence and provider accounting, then remove
the task-owned server containers, network, and volumes. Remove images downloaded
only for this experiment after checking that no other container uses them.
Preserve unrelated projects and caches whose ownership is not established.
