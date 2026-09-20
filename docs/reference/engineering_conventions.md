---
type: Reference
title: "Engineering Conventions"
description: "Own ELF task, toolchain, formatting, CI, and release conventions."
resource: docs/reference/engineering_conventions.md
status: active
authority: descriptive
owner: codebase
last_verified: 2026-09-19
code_refs:
  - Makefile.toml
  - rust-toolchain.toml
  - .taplo.toml
  - .github/actions/setup-rust/action.yml
  - .github/workflows/release.yml
---
# Engineering Conventions

Purpose: State the local and CI command contracts and their tool prerequisites.
Read this when: You change tasks, repository configuration, workflows, or release packaging.
Not this document: A runtime architecture change or a measured CI cost report.

## Reference and adoption

The reference is [acg-box/vibe-mono at 3ec54864](https://github.com/acg-box/vibe-mono/tree/3ec54864bfc4004783541c01b2518689339073da),
which was its latest main commit when inspected on September 19, 2026.
Source files govern adoption; generated OpenWiki prose is supporting context.

ELF adopts explicit cargo-make defaults, the singular complete gate, minimal Rust
components, lockfile enforcement, repository-scoped TOML formatting, and verified
release archive handling. ELF keeps its real benchmark catalogs, Python tools,
service tests, four release binaries, and documentation owner.

The template's Node scripts, npm lock, Oxfmt, and Oxlint are not copied because ELF
has no corresponding Node maintenance program. The unused Prettier configuration
and its removed UI paths are retired. No Node runtime is needed for this adoption.
The existing Rust formatter and Clippy configuration already match the reference.

Thin LTO and mold change the produced binaries. They remain separate candidates,
not part of this configuration change. ELF retains its release profile and each
platform's existing linker until target-specific build and runtime evidence supports
a change. Registry publication is not added.

## Commands and prerequisites

`Makefile.toml` owns the complete catalog. `default_to_workspace = false` executes
root tasks once. `skip_core_tasks = true` prevents cargo-make's default build graph
from becoming an undocumented second command owner.

| Command | Contract | Prerequisites |
| --- | --- | --- |
| `cargo make check` | Read-only source gate: formatting, docs links/task references, workflow lint, strict Rust lint, and default tests | Rust stable with Clippy, nightly with rustfmt, cargo-make, Taplo, actionlint, vstyle, nextest, Python 3.11+ |
| `cargo make check-rust` | Focused compile-only diagnosis; the complete gate obtains the same target/feature compilation from Clippy | Rust stable and Cargo.lock |
| `cargo make fmt` | Mutate Rust and repository TOML formatting | Nightly rustfmt and Taplo |
| `cargo make lint-fix` | Apply Rust and vstyle repairs | Stable Clippy and vstyle |
| `cargo make test-rust-integration` | Execute ignored external-service tests | Postgres with pgvector, Qdrant, nextest, and the documented test environment |
| `cargo make test-rust-all` | Execute normal and external-service tests together | The same external services |
| `cargo make test-e2e` | Context misranking runtime evidence | Harness services, psql, jq/jaq, curl, Taplo, Cargo |
| `cargo make test-ranking-stability` | Ranking stability runtime evidence | The same harness prerequisites |
| `cargo make test-trace-gate` | Postgres trace regression evidence | Its dedicated test database, psql, Python, Cargo |
| `cargo make build-harness` | Build only the API, worker, and eval binaries used by harnesses | Stable Rust |
| `cargo make build-release --target TARGET` | Build only the four shipped release binaries | Stable Rust and the requested platform target/toolchain |
| `cargo make clean-release --target TARGET` | Remove cached application/CLI release outputs that embed source identity | The same target; this is a mutating release preparation task |

The complete gate does not install tools, start databases, publish, or deploy.
A missing command is a prerequisite failure. Reuse host-managed developer tools;
do not install or replace them merely because a check needs them.
CI acquisition versions are owned by `.github/actions/setup-rust/action.yml`:
cargo-make 0.37.24, nextest 0.9.143, Taplo 0.10.0, actionlint 1.7.12, and
vibe-style 0.2.5 with a verified Linux archive digest. The repository uses stable
Rust plus Clippy; only the formatting lane adds nightly rustfmt. Stable and nightly
are channels, not immutable compiler pins.

The local adoption checks used the existing host-managed vibe-style 0.2.4. The
pinned 0.2.5 Linux archive digest and executable paths were checked, but its complete
CI invocation still needs a hosted run. This difference is an explicit evidence gap.

The former complete gate name is retired without an alias. Active callers use
`check`; historical evidence and benchmark corpus quotes retain their original
text. Likewise, format assertions now use `check-format`, `check-format-rust`, and
`check-format-toml`; the trace runtime assertion uses `test-trace-gate`.

## Task and formatting ownership

Action files own build, check, format, lint, repair, test, clean, smoke, and research
tasks. Benchmark files group core commands, aggregate memory runs, knowledge,
lifecycle, retrieval, quality, and live materialization. Public benchmark command
names and dependency order are preserved.

All Cargo execution tasks enforce Cargo.lock. The complete gate removes its
separate `cargo check` pass because Clippy uses the same stable workspace,
all-target, all-feature, locked graph and provides the compilation diagnostics.
The focused `check-rust` command remains for callers that only need compilation.

Taplo receives Git's tracked and non-ignored new TOML files. Ignored worktrees,
local service configuration, and caches are outside formatting scope. Task arrays
retain their order; reordering command arguments or dependencies would change
behavior. `.editorconfig` also covers JSON/TypeScript syntax and Python's four-space
indentation. Private service configuration and local tool state are excluded from
Docker build context; `elf.example.toml` remains included.

## Workflow contracts

All seven workflow files remain. Each keeps its existing job display names and
specialized acceptance evidence. Shared setup is a maintenance owner; extracting it
alone does not claim lower compute use.

| Workflow | Preserved evidence and change |
| --- | --- |
| Language Checks | Runs the complete source gate on main pushes, PRs, and merge groups, including documentation changes. |
| Integration Tests | PR/push/merge-group runs execute the ignored service tests; the source gate owns normal tests. Daily and manual runs retain the full suite. |
| Quality Gates | Retains the Postgres trace fixture, result report, and failure semantics. |
| E2E Harness | Retains context misranking and its output/log artifacts. Builds only the three harness binaries. |
| Nightly Harness Signals | Retains both harnesses and cadence; calls their canonical tasks. Duplicate log upload paths are removed. |
| External Memory Pattern Radar | Retains the weekly/manual artifact refresh and validation. |
| Release | Retains three target platforms, four shipped binaries, archive names, SHA256/MD5 files, and GitHub Release publication. |

Invalid `merge_group.paths-ignore` entries are removed. No affected-owner selector
is introduced. Unknown inputs therefore do not suppress the complete source gate.
Cache writes are limited to the trusted main/tag contexts and successful runs.
Feedback and release jobs keep separate cache identities. Cache misses must not
change the source or artifact contract.

The obsolete `.github/rulesets/` exports described another repository and old check
names. Current API readback showed inherited enterprise rules and no classic main
branch protection. The stale exports are removed; no remote rules were changed.
Dependabot's Cargo/Actions scope and daily cadence remain unchanged. No npm update
lane is added without an npm project.

## Release identity and verification

The release build selects `elf-api`, `elf-worker`, `elf-mcp`, and `elf-eval`
explicitly in one Cargo graph. It does not build the other eval executables merely
because they share the package. Application and shared CLI cached outputs are
cleaned before building because they embed Git SHA.

Each binary must report the expected Git SHA and target before packaging. Uploads
use exact archive filenames, fail on missing files, and avoid wrapping an archive
inside another archive. Downloads fail on digest mismatch. The publication job
checks all three archives and their exact four executable members before producing
checksums. Only publication receives write permissions. A tag run is not canceled
by a later run for the same tag.

The gate preserves platform linkers and does not claim macOS signing/notarization,
Windows execution, Linux execution, or a release publication from local checks.
Remote execution and representative cold/warm measurements are still required
before claiming CI resource savings.

## Follow-up validation repairs

Explicit integration tasks require nonblank `ELF_PG_DSN` and a Qdrant gRPC
endpoint before nextest starts. The primary Qdrant variable has precedence over
the legacy alias. Missing prerequisites fail without printing connection values.
The trace harness exports its selected DSN to the evaluator through
`TRACE_GATE_PG_DSN`, so fixture writes and evaluation use the same database.
Task registration tests traverse the root makefile's extension graph, reject cycles
and missing required files, and ignore unregistered files. Ranking stability starts
the already-built API and worker directly.
