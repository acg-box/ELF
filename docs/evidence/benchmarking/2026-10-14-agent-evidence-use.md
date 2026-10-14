---
type: Evidence
title: Agent evidence use and retrieval controls
description: Compare complete citation handling, cached expansion, MMR, note admission, and supplied original context on frozen project tasks.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-14
code_refs:
  - packages/elf-service/src/evidence/pack/windows.rs
  - packages/elf-service/src/progressive_search/service/sessionized.rs
  - config/agent/evidence-reader.md
  - scripts/benchmark_pilot/evidence.py
  - config/benchmark/evidence/2026-10-14-agent-evidence-use/verify.py
related:
  - docs/decisions/2026-10-14-agent-evidence-use.md
  - docs/runbook/agent-evidence.md
  - docs/evidence/benchmarking/2026-10-13-memory-contract-followup.md
---
# Agent evidence use and retrieval controls

The reference client now returns a complete, checked citation chain for every
formal answer in this trial. Full ELF met seven more required obligations than
ordinary file access, but only one more answer met every obligation. Disabling
MMR or accepting notes up to 512 characters gave no aggregate quality gain.
Keep the existing 240-character and MMR defaults. This is evidence from one small
project replay, not proof of general customer readiness or a competitor ranking.

## Results

The study completed 96 formal cells and 12 calibration cells. No formal answer
was replaced. There were no transport, harness, format, or final binding failures.
The primary run compared four arms on eight tasks with two repetitions. Two
later controls each ran the same 16 full-ELF cells. They changed MMR first, then
the admission limit while MMR remained disabled.

| Condition | Required obligations met | Complete acceptance | Median answer time | Mean answer cost |
| --- | ---: | ---: | ---: | ---: |
| Ordinary files | 38/64 (59.38%) | 4/16 | 32.5 s | $0.002946 |
| Source retrieval | 38/64 (59.38%) | 4/16 | 40.5 s | $0.003480 |
| ELF, 240 characters, MMR on | 45/64 (70.31%) | 5/16 | 42.3 s | $0.003623 |
| Supplied originals (diagnostic) | 52/64 (81.25%) | 5/16 | 18.6 s | $0.001252 |
| ELF, 240 characters, MMR off | 45/64 (70.31%) | 5/16 | 42.4 s | $0.003457 |
| ELF, 512 characters, MMR off | 45/64 (70.31%) | 5/16 | 42.7 s | $0.003611 |

Each formal answer has four composite obligations. All required parts must be
present; a correct broad conclusion can still miss a qualifier or identifier.
Complete acceptance also requires valid bindings and no unsupported material
claim. Coverage is not a factual-accuracy probability. These are source-based
assistant reviews, not independent or blinded judgments.

The supplied-original arm receives selected, accurate source excerpts and native
references, without the rubric or a composed answer. It has no discovery tools.
Its source selection was done in advance and has no measured serving cost. It
is a diagnostic of this reader and workflow, not a deployable product arm or an
absolute model ceiling. All arms use the same native citation checker, including
ordinary files. The comparison measures incremental retrieval and memory value.

Full ELF won six, tied six, and lost four paired cells against files, for a net
seven additional obligations. Its gains were concentrated in capacity and
validation questions; its release-evidence answers were worse. Answer time and
cost were higher than files. The sample is too small for a broad superiority
claim.

Each entry below gives the two repetition scores, each out of four. A score of
four is not sufficient for acceptance if another material claim is unsupported.

| Task category | Files | Sources | ELF 240 / MMR on | Supplied originals | ELF 240 / MMR off | ELF 512 / MMR off |
| --- | --- | --- | --- | --- | --- | --- |
| Capacity handoff | 2, 1 | 0, 0 | 3, 4 | 4, 4 | 4, 4 | 4, 4 |
| Interrupted recovery | 4, 4 | 4, 4 | 4, 4 | 4, 3 | 3, 4 | 4, 3 |
| Acceptance boundaries | 0, 3 | 3, 3 | 3, 2 | 3, 3 | 3, 3 | 3, 3 |
| Rollback handoff | 4, 4 | 4, 4 | 4, 4 | 4, 4 | 4, 4 | 4, 4 |
| Validation and cache policy | 0, 1 | 1, 2 | 3, 2 | 3, 2 | 2, 2 | 1, 2 |
| Release evidence | 3, 2 | 3, 2 | 1, 1 | 3, 3 | 1, 1 | 3, 3 |
| Retired ownership | 3, 3 | 3, 3 | 3, 3 | 3, 3 | 3, 3 | 2, 3 |
| Retired product boundaries | 3, 1 | 1, 1 | 2, 2 | 3, 3 | 2, 2 | 1, 1 |

## What the changes established

The service reports the number of candidates retained in an authorized search
session and whether more remain. The shared Agent contract directs the client
to expand that session before starting another broad query. Thirteen of sixteen
primary full-ELF cells used cached expansion; the previous trial used none.

Evidence packs merge overlapping or adjacent verified windows only when document
identity and content hash match. They retain exact original bytes and remap note
references to the merged windows. In the private trace audit, within-pack overlap
fell from 18568 of 87991 returned original bytes to zero. Mean serialized pack
size was 10291 bytes before and 6220 bytes in this run. Pack selection and call
counts differed, so these averages are descriptive, not an isolated speed test.

The reference host assigns conversation-local citation handles, rejects handles
that were not returned with original evidence, and keeps all native claim and
dependency verdicts. Final submission resolves the handles and checks the exact
object that it returns. The model does not copy native hashes after that final
check. MCP publishes the shared contract and forwards the service changes. The
Python HTTP host is a reference integration; third-party Agent hosts must wire
its final-submission lifecycle themselves.

| Condition | Bound answer with inspected refs | Cached expansion | Memory and original read | Evidence-budget loss | Review flagged a stale, unsupported, or incorrect-scope claim |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary files | 16/16 | 0/16 | 0/16 | 9/16 | 0/16 |
| Source retrieval | 16/16 | 0/16 | 0/16 | 8/16 | 0/16 |
| ELF, 240 characters, MMR on | 16/16 | 13/16 | 16/16 | 8/16 | 0/16 |
| Supplied originals (diagnostic) | 16/16 | 0/16 | 0/16 | 0/16 | 0/16 |
| ELF, 240 characters, MMR off | 16/16 | 12/16 | 16/16 | 6/16 | 2/16 |
| ELF, 512 characters, MMR off | 16/16 | 13/16 | 16/16 | 5/16 | 1/16 |

Binding proves source identity and access. It does not prove entailment. The
MMR-off control reused an obsolete runner-routing statement in one answer and
incorrectly allowed a fork run to qualify for a required gate in another. The
512-character control overstated health verification for a set of services in
one answer. These observations remain in the results; they do not establish that
one setting universally causes those errors. No formal cell used graph traversal.

## What MMR and the length control did

All three native stores received the same 79 proposed notes from the same 32
settled extraction windows. Their normalized proposal digest is
`1575bf6ce058343a0e3e9604cb7c0a6f814379abbb4ab130e6d2bbb09057e96a`.
All 140 evidence quotes matched their unchanged original windows.

| Setting | Admitted notes | Character-limit rejects | Quote-count rejects | Required obligations met |
| --- | ---: | ---: | ---: | ---: |
| 240 characters, MMR on | 45/79 | 33 | 1 | 45/64 |
| 240 characters, MMR off | 45/79 | 33 | 1 | 45/64 |
| 512 characters, MMR off | 78/79 | 0 | 1 | 45/64 |

The 512-character reader used previously rejected notes of 280 and 248 characters
in both release-evidence cells. Those cells improved from one to three
obligations each. Other details regressed, so the aggregate score and complete
acceptance did not improve. Higher admission is not itself evidence of better
memory. The MMR result also shows why an improved offline top-four rank is not
equivalent to a better final answer after cached expansion.

This comparison replays the same proposed notes. It isolates admission; it does
not test fresh extraction under a 512-character prompt. Full 4096-dimensional
Qwen3-Embedding-8B responses were reused only for matching recorded inputs. New
embedding inputs and all new reader requests passed through the budget gateway.

## Remaining failure boundaries

| Layer | Evidence from this study | Smallest useful next step |
| --- | --- | --- |
| Extraction | Some release rules were proposed but rejected at 240 characters. Cache ownership and the source-rebase/running-image distinction were not explicit proposed notes. | Check coverage of decision conditions and updates; avoid treating the derived notes as complete source coverage. |
| Retrieval and reading | Primary full ELF still lost evidence budget in 8/16 cells. Source readers could find the right file, then fail to obtain a usable window. | Expose the existing bounded original-read behavior to the client and return a verified window that fits its remaining budget. |
| Agent use | Even supplied accurate originals met only 52/64 obligations. Missing qualifiers and one unsupported service-health claim remained. | Validate subject, time, exclusions, and claim scope against the inspected originals in a small frozen follow-up. |
| Citations | All 96 formal answers retained valid, inspected native references. Semantic errors still passed binding. | Keep native binding and semantic review separate. |

A narrower requested position does not necessarily shrink an L1 excerpt: the
current public excerpt route expands it to the level window. In a failed source
cell, retrying smaller positions therefore still exceeded the remaining common
budget. This is an observed client/read-boundary limitation. PostgreSQL and
Qdrant remain the storage owners. The evidence supports focused improvements to
source access and decision coverage.

The frozen rubric includes fine details that can be absent from an otherwise
useful answer, such as a current manifest check after a retirement decision.
Future natural-session trials should state user-visible acceptance requirements
clearly and distinguish a missing detail from a harmful decision. Do not change
this study's rubric after seeing its scores.

## Cost and protocol

The existing reset budget remains $10. Preparation, calibration, failed historical
attempts, cached input charges, and answers remain accounted for. No scored
answer was rerun. New work cost **$0.311963505**.

| Budget component | Settled USD |
| --- | ---: |
| Earlier reset-budget work | $0.805379576 |
| Primary preparation, calibration and formal answers | $0.194157635 |
| 240-character MMR-off control | $0.057954020 |
| 512-character MMR-off control | $0.059851850 |
| Cumulative settled | $1.117343081 |
| Conservative cumulative exposure | $1.187827881 |

The two cumulative rows are totals, not additional charges. The historical
uncertain request retains its full $0.0704848 reservation. It was not deleted or
treated as refunded. Cached reads and writes are already included in settled
cost; no additional discount is applied.

Preparation in this study replayed paid fixtures. Its incremental cost is not a
cold-start estimate, so the bundles do not report amortized cold-start cost.
The results table reports measured answer cost only. The earlier trial's fresh
preparation measurements remain separate.

- The corpus has 14 unchanged private Git records, 137723 original bytes, and four chronological checkpoints. Four questions are earlier regressions and four are handoff questions frozen for the preceding trial. This is retrospective, not natural multi-day use.
- Each reader has a fresh process and conversation. Later sources are unavailable at earlier checkpoints. All stage checks preserved original hashes and full 4096-dimensional vectors.
- The reader route is OpenRouter `openai/gpt-6-luna`, standard OpenAI provider, medium reasoning, with the full 128000 output-token allowance. Embeddings use Qwen3-Embedding-8B through Nebius at 4096 dimensions. The native arms share the local-token-overlap reranker.
- The common workflow budget is eight model rounds, sixteen tool calls, 32768 serialized evidence bytes, and 12000 bytes per result. These are workflow limits, not the model's context capacity. Output allowance was not reduced.
- Formal execution used `c3cfc5bd7551e3b8541a4e9da80a86be5e17e66b`. Reader files stayed unchanged across all formal runs. Later edits affect reporting and export metadata only.
- The primary calibration used `2425078b`. One supplied-original calibration input omitted an import paragraph. That answer and its fixture remain intact. A recorded pre-formal amendment added the paragraph, and final submission became mandatory. No formal source selection, question, criterion, or original byte changed, and the calibration answer was not repeated.
- These are sequential one-factor controls, not a complete factorial or randomized causal estimate. The study did not test 512 characters with MMR on. Provider cache state, stochastic output, and latency were not controlled across runs.
- Three PostgreSQL/Qdrant snapshots passed isolated restoration. All 14 originals matched in each. The 4096-dimensional source and memory collections passed stored-vector queries; compressed backups passed lossless file-hash verification.
- Runtime validation passed `cargo make check`, the harness build, 472 Rust tests, 107 Docker integration tests, and 204 benchmark contract tests. Reporting changes passed the benchmark contract suite separately. Documentation and exact-head PR checks are delivery gates, recorded on the pull request.

## Evidence bundles

The [primary bundle](../../../config/benchmark/evidence/2026-10-14-agent-evidence-use/manifest.json),
[MMR-off bundle](../../../config/benchmark/evidence/2026-10-14-agent-evidence-mmr-off/manifest.json),
and [512-character bundle](../../../config/benchmark/evidence/2026-10-14-agent-evidence-limit-512/manifest.json)
contain de-identified cells, protocol, actual native settings, normalized proposal
hashes, reused-provider counts, runtime hashes, sanitized cumulative ledgers,
and restoration summaries. Original records, task text, answers, traces, and
provider fixtures remain private.

The verifiers check artifact integrity, chronology, dimensions, admission,
settings, costs, and recorded restoration. They cannot independently reproduce
the private semantic judgments.

```sh
python3 config/benchmark/evidence/2026-10-14-agent-evidence-use/verify.py
python3 config/benchmark/evidence/2026-10-14-agent-evidence-mmr-off/verify.py
python3 config/benchmark/evidence/2026-10-14-agent-evidence-limit-512/verify.py
```
