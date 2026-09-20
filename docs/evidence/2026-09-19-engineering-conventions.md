---
type: Drift Audit
title: "Engineering Conventions Adoption"
description: "Record the source, workflow, task, integration, and release evidence for vibe-mono alignment."
resource: docs/evidence/2026-09-19-engineering-conventions.md
status: active
authority: evidence
owner: codebase
last_verified: 2026-09-19
code_refs:
  - Makefile.toml
  - .github/actions/setup-rust/action.yml
  - .github/workflows/release.yml
related:
  - docs/reference/engineering_conventions.md
  - docs/evidence/2026-09-19-module-refactor.md
---
# Engineering Conventions Adoption

Purpose: Record what changed, what was checked, and which results remain unmeasured.
Read this when: You review the CI and repository configuration alignment.
Not this document: Hosted optimization acceptance, deployment evidence, or a release record.

## Authority and initial findings

Reference: [vibe-mono 3ec54864bfc4004783541c01b2518689339073da](https://github.com/acg-box/vibe-mono/tree/3ec54864bfc4004783541c01b2518689339073da),
read through GitHub's API as the current main revision. ELF source HEAD was
`0a4f1dd58441e3077d94c8bb615b2f42c9f07b56`, with the preceding local refactor retained.

The inventory covered all seven checked-in workflows, including scheduled, manual,
and tag-only lanes, plus dynamic Dependabot/CodeQL workflow records and inherited
rules. No remote rules, schedules, releases, or repository settings were changed.

The latest Language Checks run returned by the API was
[34419867504](https://github.com/acg-box/ELF/actions/runs/34419867504).
It failed in the floating vibe-style installer before repository checks.
The latest release run returned by the API was
[22316352695](https://github.com/acg-box/ELF/actions/runs/22316352695), from February
2026. Neither run supplies current hosted performance evidence for this patch.
The September 19 integration and nightly runs were successful at the baseline SHA.

The local ruleset exports named `hack-ink/vibe-mono` and obsolete checks. Live API
readback instead showed inherited enterprise rules, including signatures and a
merge-based PR policy; classic main branch protection returned 404. The obsolete
local exports were removed without changing those live rules.

## Implemented changes

- Minimal stable toolchain with Clippy; nightly rustfmt is owned by formatting setup.
- Explicit root cargo-make defaults, singular complete gate, action-owned tasks,
  and lockfile enforcement. All 141 pre-existing task responsibilities remain,
  with five explicit command renames documented in the engineering reference.
- Benchmark families replace the arbitrary `a/b` file partitions. A semantic
  comparison retained task commands, arguments, dependency ordering, fixtures, and
  output paths apart from explicit lockfile enforcement. Two registration tests now
  use the existing catalog helper instead of a removed filename.
- TOML formatting includes task files and preserves their argument/dependency
  ordering. Editor rules cover the actual Python code. Unused Prettier/UI settings
  and stale ruleset exports are removed. Canonical repository URLs are updated.
- One shared CI tool owner with pinned cargo-make, nextest, Taplo, actionlint, and
  digest-verified vibe-style. Trusted main/tag contexts own cache writes.
- The source gate no longer runs a separate compiler pass already covered by
  strict Clippy with the same target, feature, and lockfile contract.
- PR/push/merge-group integration jobs run the external-service subset; daily and
  manual jobs retain full tests. E2E, trace, stability, radar, and release evidence
  stay separate. Workflow names, job names, and schedules remain.
- Harness and release builds select only the binaries used by their consumers.
  Release checks source/target identity, exact archive membership, and download
  digest before publication. Permissions are scoped and tag runs are not canceled.
- The unsupported Decodex docs subcommand is removed from active documentation
  policy. Manual structure/source review and the repository link/task checker remain.

No new runtime, npm project, linker, LTO policy, registry publication, or release
platform was introduced. The detailed retained/adopted decisions are in
[Engineering Conventions](../reference/engineering_conventions.md).

## Verification

| Check | Result |
| --- | --- |
| `cargo make check` | Passed: formatting, docs, actionlint, strict Clippy/vstyle, 453 Rust tests and 45 Python tests. The default suite skips 92 external-service tests. |
| `cargo make test-rust-integration` | All 92 tests passed against task-owned temporary Postgres/pgvector and Qdrant containers. |
| `cargo make build-release --target aarch64-apple-darwin` | Passed for all four shipped binaries. |
| Workflow/composite YAML parsing | All seven workflows and shared setup parsed successfully. |
| Linux vibe-style archive | Download digest matched `ed2cac495e8beb882decc2e65163773ed4680e0ac510f305f96bafd9f9930da3`; both installer member paths existed. No host tool was replaced. |
| Task inventory and semantic comparison | All original responsibilities retained; benchmark/research/smoke argument and dependency contracts preserved. |
| Release packaging assertions | The actual macOS build passed the workflow's version/identity and ZIP packaging step. The archive verifier accepted a complete fixture set and rejected extra members and a missing archive. |
| `git diff --check` | Passed. |

The macOS binaries reported version 0.2.0, baseline Git SHA
`0a4f1dd58441e3077d94c8bb615b2f42c9f07b56`, and target `aarch64-apple-darwin`.
The build includes local uncommitted changes; the embedded SHA is not a claim that
those changes are present in that commit or a published release.

The temporary containers carried this task's ownership label. They were stopped
and their removal was verified. No pre-existing container or application data was
used for integration tests. Downloaded image layers remain in Docker's normal cache.

Reverse scans retained old command strings only in historical evidence and frozen
benchmark corpus/report fixtures. Those strings are data, not executable callers.
No references to the removed makefile partitions or old style-installer URL remain.

## Limits and rollback

Status: **implemented, not yet measured**. Hosted Actions have not run this patch.
There is no measured claim for runner minutes, cost, cache hit rate, energy, or
carbon. Linux and Windows release binaries were not built or executed locally.
The non-macOS archives in the negative packaging checks were fixtures, not products.
The host used vibe-style 0.2.4; CI's pinned 0.2.5 complete invocation remains unverified.
The E2E, ranking, and trace runtime harnesses were not rerun in this pass. Their
existing acceptance assertions and dedicated CI lanes remain.

Rollback boundaries are independent: task/configuration adoption, shared CI setup
and test selection, and release packaging. Revert the affected boundary if required
checks stop reporting, any preserved test is omitted, source identity differs,
archive membership changes, or a supported release platform fails. Keep the prior
source/module refactor independent of that rollback. Measure matched hosted cold
and warm runs before accepting resource savings or a linker/profile change.

## September 20 follow-up

The follow-up repairs add a fail-closed integration prerequisite task, task catalog
traversal through actual extensions, a shared DSN between trace fixture loading and
evaluation, and direct ranking harness binary execution. Local regression coverage
now includes two task-catalog tests and three tooling tests. Tooling tests invoke
cargo-make itself because its variable interpolation can alter shell expressions.

Fresh external-service verification passed all 92 tests; nextest marked one HTTP
English-input test as leaky on this local run. This is a process-output cleanup
warning, not evidence of a memory leak or a clean teardown pass. It remains visible
rather than being hidden with a retry. The context misranking E2E passed with
baseline recall@1 of 0 and contextual recall@1 of 1. The trace gate passed on a
non-default local port, proving that both halves used the configured database.

The first hosted PR run exposed unsupported actionlint installation through the
pinned generic installer. Setup now downloads the native upstream archive with a
verified digest. A subsequent formatter failure identified an import regrouping
left by vstyle; formatting was applied after the style repair. These failures are
part of the rollout record, not successful prior validation.
