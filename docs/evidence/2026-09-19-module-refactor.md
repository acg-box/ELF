---
type: Drift Audit
title: "Module Refactor Validation"
description: "Record preserved behavior, source ownership, and local validation for the ELF module refactor."
resource: docs/evidence/2026-09-19-module-refactor.md
status: active
authority: evidence
owner: codebase
last_verified: 2026-09-19
code_refs:
  - Makefile.toml
  - makefiles/test.toml
  - packages/elf-service/src/context_pack.rs
  - scripts/tests/test_benchmark_entrypoints.py
related:
  - docs/reference/module_ownership.md
---
# Module Refactor Validation

Purpose: Record the evidence and limits of this local refactor.
Read this when: You need to review the changed module boundaries or validation scope.
Not this document: A release, deployment, live benchmark, or security-audit result.

## Scope and decision

The source baseline was `0a4f1dd5`. The initial main checkout was clean. Inventory
used tracked source files, crate manifests, task definitions, public imports,
callers, and tests. Existing worktrees and temporary external source checkouts were
excluded from the refactor.

The product crate boundaries remain proportionate: they own transport, policy,
persistence, providers, chunking, service use cases, and worker lifecycles. The
main mixed-responsibility files were Context Pack and the host/container benchmark
scripts. These now have separate behavior owners, as listed in
[Module Ownership](../reference/module_ownership.md).

| Entry file | Before | After | Extracted owners |
| --- | ---: | ---: | --- |
| `packages/elf-service/src/context_pack.rs` | 1239 | 70 | Types, validation, routing, assembly, tests |
| `scripts/benchmark-runner.py` | 925 | 10 | CLI, runtime, providers, Docker, answers, execution |
| `scripts/benchmark-report.py` | 936 | 33 | Metrics, coverage, roadmap, decisions, rendering |
| `scripts/benchmark-unit.py` | 840 | 251 | Mem0, LightRAG, Rust targets, unit runtime |

These numbers describe relocation, not deleted capability. The 734-line contract
module became a package with fixture, metric, evaluation, and answer owners. The
1296-line benchmark test file became focused test modules with shared fixture
builders. All 43 original test names remain exactly once. Two entrypoint tests were
added for import and packaging regressions.

## Preserved contracts and retirement

- Context Pack keeps its public names, serialized fields, required anchors,
  override precedence, scope delegation, freshness filters, item ordering, and
  source-reference gates. No public visibility was added for tests.
- Benchmark command paths, flags, output schemas, evidence identity, scoring
  denominators, native mutation receipts, cleanup checks, and typed failures remain.
- The unused LightRAG branch in the generic Rust-target executor was removed.
  The existing dedicated LightRAG executor still owns per-job cold/warm isolation,
  query modes, native artifacts, and state reuse.
- OpenKB's query program moved from a string to source without changing its AST
  or the pinned interpreter's `-c` invocation contract.
- An existing acceptance-test error enum stored a large Qdrant error inline.
  Strict Clippy rejected three helper return types. The Qdrant variant now uses
  `Box`, with the same conversion and transparent error display.
- Benchmark contract tests now run under the normal `test` dependency of `checks`.
  The original public benchmark test task is retained with test discovery.
- Reverse scans found no references to the removed test filename, flat contract
  filename, or OpenKB program constant in repository source and documentation.
  Dockerfiles still copy the complete `benchmark_targets` directory.

No persistence schema, production data, provider configuration, external resource,
branch, or worktree was removed. Historical evidence and target-specific lifecycle
protections remain.

## Local evidence

- `cargo make checks`: passed format, docs, all-target/all-feature compilation,
  strict Clippy, vstyle, Rust tests, and Python benchmark tests.
- Rust: 453 passed; 92 skipped under the repository's default test selection.
- Benchmark: 45 passed, including host entrypoints from a different working
  directory and a unit entrypoint assembled from the Docker COPY inputs.
- One-off baseline comparison: all 75 moved host-runner, report, and contract
  functions/classes retained identical ASTs. The native OpenKB query AST also
  remained identical.
- One-off differential checks across 48 synthetic suite/target units: evaluation
  and answer-context results matched the source baseline. The report text matched
  exactly for four suite bundles. These are refactor checks, not live product scores.
- `git diff --check`: passed.

## Evidence limits

The installed `decodex` command rejects `docs check` as an unknown subcommand.
The repository-native `cargo make check-docs` passed. Full OKF tool validation is
therefore unavailable in this host environment; no tool was installed or replaced.

External-service integration tests, provider calls, Docker image builds, and live
competitor benchmarks were not run. The packaging test checks Python import inputs;
it does not claim a container-runtime pass. This work has not established a merge,
release, deployment, or live retrieval-quality result.
