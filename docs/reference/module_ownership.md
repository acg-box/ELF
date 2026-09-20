---
type: Reference
title: "Module Ownership"
description: "Map ELF code responsibilities and the boundaries retained by the September 2026 refactor."
resource: docs/reference/module_ownership.md
status: active
authority: descriptive
owner: codebase
last_verified: 2026-09-19
code_refs:
  - Cargo.toml
  - Makefile.toml
  - packages/elf-service/src/context_pack.rs
  - packages/elf-service/src/access.rs
  - scripts/benchmark_runner/cli.py
  - scripts/benchmark_contract/evaluation.py
---
# Module Ownership

Purpose: Locate the owner of a behavior before changing or splitting code.
Read this when: You need to change a module boundary or find the benchmark execution path.
Not this document: A new product contract, a release record, or benchmark quality evidence.

## Product boundaries

| Owner | Responsibility | Boundary to preserve |
| --- | --- | --- |
| `apps/elf-api` | HTTP routing, identity extraction, public/admin surfaces, OpenAPI | Keep transport validation and service behavior separate. |
| `apps/elf-mcp` | MCP tool schemas and HTTP client calls | Do not add a second storage or authorization implementation. |
| `apps/elf-cli` | User commands and HTTP requests | Keep service state and provider work in the service. |
| `packages/elf-cli` | Shared process startup and command metadata | This crate supports the executable applications; it is not the user CLI. |
| `packages/elf-service` | Use cases, grant checks, retrieval, ingest, derived readbacks | Keep orchestration close to each use case. |
| `packages/elf-domain` | Memory policy, write gates, evidence and lifecycle rules | Keep transport and database execution out of these rules. |
| `packages/elf-storage` | Postgres persistence and Qdrant access | Postgres remains the source of truth; Qdrant remains rebuildable. |
| `packages/elf-providers` | Model provider requests and responses | Keep provider contracts separate from retrieval policy. |
| `packages/elf-chunking` | Tokenization and chunk boundaries | Preserve evidence positions and token limits. |
| `apps/elf-worker` | Outbox jobs, indexing, trace persistence, cleanup | Preserve job retries and persistence order. |
| `apps/elf-eval` | Evaluation executables and runtime evidence | Do not treat fixture evidence as a live service result. |
| `packages/elf-testkit` | Isolated test databases and service prerequisites | Keep destructive test setup within test-owned resources. |

These owners have distinct behavior or compatibility obligations. The refactor does
not add a crate, executable, provider, runtime, schema, or deployment boundary.
Small module roots that group routes, search stages, or storage operations remain
navigation and visibility boundaries. They are not runtime forwarding layers.

## Context Pack

`packages/elf-service/src/context_pack.rs` remains the public module and service
entrypoint. Its request and response names remain available through the same public
paths and crate-root exports.

- `types.rs` owns the serialized request and response fields.
- `validation.rs` rejects invalid request text before recall starts.
- `routing.rs` owns layer selection, required anchors, limit bounds, and override
  precedence. Its intermediate state is visible only within Context Pack.
- `assembly.rs` owns row eligibility, ordering, budget truncation, and the matching
  routing trace. Eligibility stays private to this owner.
- `tests.rs` checks routing, source evidence, freshness, pinning, and validation.
  Tests do not require wider production visibility.

Context Pack delegates identity, read-profile, and grant enforcement to the recall
surfaces. `packages/elf-service/src/access.rs` owns shared read-grant keys and note
read eligibility. Private notes require an owner match. Shared reads require the
configured scope and applicable grants. Tenant/project constraints also remain in
the owning queries. A route override must not bypass these checks.

## Competitor benchmark

The public script paths and cargo-make task names stay stable. Python remains the
owner of this existing benchmark. This refactor does not introduce a language
migration or expand the benchmark capability.

| Owner | Responsibility |
| --- | --- |
| `scripts/benchmark-runner.py` | Dispatch the host CLI. |
| `scripts/benchmark_runner/cli.py` | Parse options and assemble one run. |
| `scripts/benchmark_runner/runtime.py` | Resolve the repository root, run host commands, write artifacts, and identify source content. |
| `scripts/benchmark_runner/providers.py` | Prepare provider environment and run preflight. |
| `scripts/benchmark_runner/docker.py` | Build images and inspect, log, and clean up run-owned Compose projects. |
| `scripts/benchmark_runner/execution.py` | Schedule units and preserve timeout, cleanup, and acceptance results. |
| `scripts/benchmark_runner/answers.py` | Request shared answers and preserve typed failures and raw provider evidence. |
| `scripts/benchmark_contract/fixtures.py` | Validate manifests/suites and create opaque, scoring-blind product fixtures. |
| `scripts/benchmark_contract/metrics.py` | Compute the existing metric and mutation-receipt oracles. |
| `scripts/benchmark_contract/evaluation.py` | Apply coverage and eligibility gates before scoring. |
| `scripts/benchmark_contract/answers.py` | Build answer context from ranked native readback, including post-mutation text. |
| `scripts/benchmark-unit.py` | Dispatch a container target and persist its result and exit status. |
| `scripts/benchmark_targets/` | Own each product's native state, identity mapping, operations, and readback. |
| `scripts/benchmark_targets/unit_runtime.py` | Share container process I/O, readiness, and failure classification. |
| `scripts/benchmark_report/` | Render coverage, metric comparisons, decisions, and a roadmap from measured results. |
| `scripts/benchmark-report.py` | Parse the report CLI and write the rendered output. |

The host scheduler can see scoring authority. Product adapters receive opaque
fixtures. Do not move qrels or expected answers into product-side helpers. Typed
failures must remain outside quality denominators.

LightRAG owns per-job cold/warm isolation. The generic Rust-target runner now serves
ELF and qmd only; its unreachable LightRAG path is removed. Mem0 owns its native
memory IDs and mutation receipts in a separate target module. All three receive
input, artifact, and state paths explicitly.

OpenKB's native query program is a source file, `openkb_query.py`, instead of an
embedded string. The adapter still passes its text through the pinned interpreter's
`-c` interface. This preserves argument positions, working directory, imports,
timeout, and output behavior. Existing Dockerfiles copy the entire target directory.

## Retained large files and protections

A line count is a discovery aid, not a reason to split an owner.

- OpenKB, Graphiti, and OpenViking retain target-specific lifecycle code. Native
  evidence identities, post-delete absence checks, provider setup, and warm-state
  reuse differ. A common adapter framework would hide these differences without
  an established shared contract.
- Shell smoke and live-baseline harnesses remain supported command owners. No
  language migration was authorized, and they retain unique runtime checks.
- Benchmark makefiles retain declarative task catalogs. File length alone does not
  justify another task namespace or an alternate command spelling.
- SQL tables, generated evidence, historical reports, and external fixture formats
  are retained. A lack of Rust references would not prove these are unused.
- Existing worktrees and temporary external checkouts are outside this refactor's
  ownership. They are excluded from the tracked-source inventory.

`cargo make check` runs format, documentation, workflow lint, Rust compilation/lint, tests, and
benchmark contract tests. The benchmark task discovers the focused test files under
`scripts/tests/`; shared fixture builders contain no tests. External-service tests
remain separately available through `cargo make test-rust-integration`. Local
contract checks do not establish live provider, container, deployment, or benchmark
quality results.

For task and CI conventions, see [Engineering Conventions](engineering_conventions.md).
