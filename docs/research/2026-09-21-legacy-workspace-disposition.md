---
type: Research Contract
title: "Legacy Workspace Disposition"
description: "Retire obsolete workspaces while retaining evidence and bounded repair candidates."
resource: docs/research/2026-09-21-legacy-workspace-disposition.md
status: proposed
authority: exploratory
owner: maintenance
last_verified: 2026-09-21
code_refs:
  - apps/elf-mcp/src/app/server/support.rs
  - packages/elf-service/src/context_pack/assembly.rs
  - scripts/benchmark_contract/evaluation.py
  - apps/elf-eval/src/bin/external_memory_pattern_radar/render.rs
related:
  - docs/research/2026-09-20-elf-value-review.md
---
# Legacy Workspace Disposition

Purpose: Preserve the useful results of retired July and August work without
restoring obsolete product contracts or benchmark implementations.
Read this when: Recovering an old workspace or choosing a follow-up repair.
Not this document: Proof of product safety, a current competitive ranking, or
approval to change public APIs.

## Disposition

| Former branch | Disposition | Retained value |
| --- | --- | --- |
| `xv/benchmark-competitors` | Delivered in PR #381; retire checkout. | Original measured run artifacts and logs. |
| `xv/benchmark-thin-runner` | Retire transitional runner. | Historical disposition inventory and committed source. |
| `xv/product-salvage` | Retain commits `2f12e0ff` and `4840feac` as repair candidates. | Response bounds, source checks, lifecycle propagation, and process cleanup. Do not cherry-pick the combined API changes. |
| `xv/benchmark-contract-refresh` | Retire the experimental implementation. | Historical corrections, source snapshots, and selected test scenarios. |
| `xy/sag-competitor-benchmark-refresh` | Retire the old competitor runner. | Historical run artifacts and evidence of evaluation defects. |
| `xy/final-memory-knowledge-plan` | Supersede the July execution proposal in PR #353. | Source-backed memory principles and valid documentation repairs. |

Archives must include ignored artifacts, untracked files, original tracked files,
and Git history. The local archive manifest records original HEADs, branch names,
file hashes, and any stash commit used to preserve index and working-tree state.
Git bundles are verified before checkout removal. Archives remain local: they can
contain private experiment data and must not be uploaded with a pull request.

## Changes that must not return as cleanup

The contract-refresh experiment changes document read/search/excerpt routes to
404 responses and removes public search-session and recall-debug routes. It also
restricts model-facing context to notes and documents. Those changes alter public
contracts; archive them instead of silently adopting them.

Its source resolver requires the assertion to equal the source quote and accepts
only a specific v2 source-binding shape. This can reject summaries and existing
source formats. Reuse source revision and scope checks only after a compatible
design and migration analysis.

The SAG mem0 adapter builds output claims from `expected_answer.must_include` and
its expected evidence links. This does not establish independent answer quality.
Its report status fallback can label out-of-scope-only results as pass while
listing that state separately. Do not restore this scoring path. The current
benchmark evaluator separately checks execution, coverage, and score eligibility.

## Historical claim corrections

Retain the July 13 correction to the July 8 benchmark presentation. The old recall
denominator mixed comparable and non-comparable work. The correction itself says
that exact original report bytes were unavailable; its numeric examples are
historical assertions, not independently recomputed measurements. Do not repeat
those values as a current comparison or use post-hoc intersections as a ranking.

Retain the July 19 correction withdrawing current comparative authority from the
June 20 and June 27 reports. Fixture-derived results and dated closeout claims do
not establish present superiority. Preserve original dated reports; link this
disposition when interpreting them. References in those old corrections to a v2
experimental contract do not make that contract authoritative today.

## Bounded repair queue

| Priority | Owner | Candidate and acceptance evidence |
| --- | --- | --- |
| P1 | MCP transport | Bound response accumulation. Cover declared and chunked oversized bodies. Select a supported limit; the old 1 MiB constant is a proposal. |
| P1 | MCP transport | Prevent raw upstream error bodies from entering model context. Preserve useful typed error codes and correlation IDs; test text, HTML, malformed JSON, nested JSON, and chunk failures. |
| P1 | Context Pack | Reject empty or schema-only source identities without requiring every assertion to be a verbatim quote. Preserve supported reference variants with focused tests. |
| P1 | Service/API | Trace lifecycle state through search, document readback, and Context Pack. Check correction, deletion, scope, and restart behavior against the current contract before porting old tests. |
| P2 | Local harness | Review child-process reaping from `4840feac`; prove cleanup without changing production lifecycle behavior. |

These are retained candidates, not completed fixes or confirmed exploitable
vulnerabilities. Old test files depend on an incompatible model-delivery contract;
port their independent scenarios, not their output schema or route removals.

## Roadmap replacement

The July R0-R9 plan preserves useful provenance, correction, privacy, and cost
principles. Its broad model-ladder, graph, knowledge-workspace, and dreaming
expansion sequence is not the current execution queue. Use the September value
review to design a task-benefit pilot and one cross-agent correction workflow.
That review remains exploratory and does not itself authorize a new product API.

The old PR also contains valid path and metadata repairs. The radar renderer and
its checked-in report now reference the existing directory entrypoint. Other
historical documentation changes require current path checks; old verdicts must
not be presented as fresh validation.
