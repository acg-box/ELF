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

## Complex PDF comparison

Use `--workload-group complex-documents --manifest
config/benchmark/ragflow-pdf-v1.json --ingest-seconds 1800 --source-labels --reader-max-tokens 8192` with
`cargo make benchmark-ragflow`. The fixture has eight PDFs and 24 questions.
RAGFlow receives binary PDF uploads. ELF and Hindsight receive the corresponding
fixed Poppler/Tesseract text when the same workload group and `--source-labels` are used with
`cargo make benchmark-deep`. See
`config/benchmark/fixtures/complex-documents-v1/README.md` for generation,
parser versions, and scope limits. This compares complete pipelines; it does
not imply native PDF support in the two text-input conditions.

If the client ingest deadline expires while the native RAGFlow server still
processes files, retain the failed condition. To continue, keep the same server,
dataset, user, models, workload, and oracle. Keep the provider gateway active or
update the native model instance to the next bounded gateway before it submits
more requests. Never give the native service the provider key.

Use `cargo make benchmark-deep --target ragflow --resume-ragflow ORIGINAL`
with a new artifact directory and the same complex-document workload. Supply
the retained user's native API key only to this client. The continuation checks
source identities and input equality, waits for the retained documents, and
reruns every question. It does not upload the sources again. Record any explicit
restart of a failed native document separately. An expired provider gateway can
cause a document failure even when local parsing succeeds.

Use `--reader-max-tokens 8192` with `cargo make benchmark-deep` for the final
complex-document comparison, or replay retained native output with
`--reanswer ORIGINAL --source-labels --reader-max-tokens 8192`. Apply the same
output limit to every compared product. The default remains 4,096 tokens for
existing workloads. Replay inherits the retained limit and context protocol
unless an explicit override is supplied.

For a missing reader output, `--reanswer ORIGINAL --retry-answer-errors` retains
all completed answers, including incorrect ones. It cannot change the output
limit or context protocol. Use a full replay when either setting changes. Keep
the original condition, recovery metadata, and paid requests in the evidence.

For this version of the fixture, exclude the four ambiguous empty-cell cases
listed in the evidence report from the primary score. Keep all 24 raw rows and
report the 20-case primary denominator explicitly.

The continuation records original and recovery durations. Native processing can
continue between the two client runs, so use native event timestamps or the full
wall-clock interval for end-to-end latency. Do not present the recovery wait as
a cold ingestion measurement. Preserve every failed condition.

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
