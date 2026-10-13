---
type: Evidence
title: Memory contract and Agent follow-up trial
description: Measure exact evidence extraction, actual memory reads, and a source hydration control at daily model cost.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-13
code_refs:
  - packages/elf-service/src/add_event/extraction.rs
  - packages/elf-service/src/evidence/pack.rs
  - scripts/benchmark_pilot/tools.py
  - config/benchmark/evidence/2026-10-13-memory-contract-followup/verify.py
  - config/benchmark/evidence/2026-10-13-source-hydration-control/verify.py
related:
  - docs/decisions/2026-10-13-daily-memory-contract.md
  - docs/runbook/agent-evidence.md
  - docs/evidence/benchmarking/2026-10-13-daily-project-trial.md
---
# Memory contract and Agent follow-up trial

The extraction and evidence-access defects are repaired. All 16 full-ELF formal
readers used derived memory and its original evidence. This trial still does not
show a reliable incremental benefit from memory over ordinary source access.
It does not establish customer readiness or a competitor ranking.

## Results and interpretation

The primary trial has 48 formal cells: eight frozen tasks, two repetitions, and
three conditions. Four tasks are regressions and four are new handoff questions.
It returned 45 structurally valid answers and three invalid answers. There were
no transport or harness failures. Invalid answers remain in the same 64-obligation
denominator per arm; no scored answer was replaced.

| Condition | Valid answer format | Required obligations met | Complete acceptance | Median elapsed | Mean answer cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary file access | 16/16 | 40/64 (62.5%) | 4/16 | 45.4 s | $0.004141 |
| Source retrieval | 14/16 | 32/64 (50.0%) | 3/16 | 58.5 s | $0.004948 |
| Sources and memory | 15/16 | 41/64 (64.1%) | 3/16 | 52.6 s | $0.004922 |
| Source hydration control | 16/16 | 35/64 (54.7%) | 4/16 | 47.6 s | $0.004574 |

The last row is a separate, later control, not a fourth randomized arm. The
primary source-only reader could repeat searches before reading an original,
while full ELF read a memory evidence pack after discovery. Two source-only
release-evidence cells spent their budget before any successful original read.
Protocol v4 therefore selects one native excerpt after nonempty source discovery,
then returns control to the model. It uses the same questions, sources, model,
and budgets, and does not extract unused memories. It also retains native API
error bodies so the client can interpret a failed request. The primary records
remain unchanged. Provider latency and cache state were not controlled between runs.

Complete acceptance requires all four obligations and no invalid or unsupported
material claim. Coverage measures required details, not a factual-accuracy score.
Each obligation can contain several necessary parts. For example, naming a
signature without its required verification method does not meet the whole
release obligation. Semantic review was performed by the assistant against the
private originals. It was not independent or blinded. Native binding proves
source identity and access, not that a claim follows from that source.

| Condition | Four regression tasks, two repetitions | Four new tasks, two repetitions |
| --- | ---: | ---: |
| Ordinary file access | 17/32 | 23/32 |
| Source retrieval | 15/32 | 17/32 |
| Sources and memory | 18/32 | 23/32 |
| Source hydration control | 12/32 | 23/32 |

Each pair below is the required-detail score for the two repetitions. It does
not imply complete acceptance; separate citation and format failures can reject
a response with four requirements met. The bundle records those flags per cell.

| Task category | Ordinary files | Source retrieval | Sources and memory | Source hydration control |
| --- | --- | --- | --- | --- |
| Capacity handoff | 4/4, 3/4 | 0/4, 0/4 | 1/4, 3/4 | 0/4, 0/4 |
| Interrupted recovery | 4/4, 4/4 | 4/4, 3/4 | 3/4, 4/4 | 4/4, 4/4 |
| Acceptance boundaries | 3/4, 1/4 | 3/4, 3/4 | 4/4, 3/4 | 3/4, 3/4 |
| Rollback handoff | 4/4, 3/4 | 4/4, 4/4 | 4/4, 4/4 | 4/4, 4/4 |
| Validation and cache policy | 1/4, 1/4 | 1/4, 2/4 | 2/4, 1/4 | 1/4, 0/4 |
| Release evidence | 2/4, 1/4 | 0/4, 0/4 | 3/4, 1/4 | 3/4, 2/4 |
| Retired ownership | 1/4, 3/4 | 3/4, 3/4 | 1/4, 3/4 | 3/4, 2/4 |
| Retired product boundaries | 2/4, 3/4 | 1/4, 1/4 | 2/4, 2/4 | 1/4, 1/4 |

## What changed and what remains weak

The model now selects numbered, exact input spans. The server resolves those
selectors before the existing source checks. All 140 returned evidence quotes
matched their selected original windows. None exceeded the byte limit or failed
source identity. This does not prove that each quote supports its proposed note.
The 32 extraction windows proposed 79 notes: 45 were admitted, 33 exceeded the
unchanged 240-character note limit, and one exceeded the quote-count limit.
The previous trial admitted 23 of 74 proposals. Different proposal sets prevent
a controlled claim about the admission-rate change.

Runtime limits now enter every extraction profile. Quote bytes, quote count, and
source mismatch have separate rejection reasons. Built-in profile version 6
uses selectors; old profile pins remain intact. See the
[activation instructions](../../runbook/agent-evidence.md#activate-the-extraction-profile).

Evidence packs allocate the requested source budget before fetching windows.
Verified excerpts return references that the Agent can copy into claims. The
shared MCP/HTTP contract and reference host activate discovery and evidence
reading early and expose the existing claim checker. These changes use the
existing service boundaries; PostgreSQL, Qdrant, and immutable originals remain.
No new persistence layer or Agent framework was added.

| Condition | Bound answer with inspected references | Actual memory and original read | Agent citation-check use | Cells with evidence-budget loss |
| --- | ---: | ---: | ---: | ---: |
| Ordinary file access | 12/16 | 0/16 | 12/16 | 11/16 |
| Source retrieval | 10/16 | 0/16 | 8/16 | 11/16 |
| Sources and memory | 14/16 | 16/16 | 9/16 | 10/16 |
| Source hydration control | 15/16 | 0/16 | 6/16 | 10/16 |

An unknown answer with no references does not count as a bound, evidenced answer;
it is not necessarily a native-checker failure. The final host check runs for
every parseable answer, separately from the Agent's voluntary repair calls.
Some mechanically bound claims still cited an unrelated nearby span. Other
answers omitted exact identities, changed ownership, or acceptance conditions.
One full-ELF answer produced malformed JSON. No formal full-ELF reader used graph
traversal, so this trial establishes no graph benefit.

The remaining work is about complete evidence and concise memory content:
retrieve the right original section, retain each decision's subject and time,
and verify that each claim is supported by its bound span. The results do not
justify changing databases or adding another retrieval layer. A natural project
pilot and a clear acceptance threshold are still needed before customer claims.

## Cost and timing

The existing reset budget remains $10. All exploration, preparation, failed
attempts, cache charges, and answers count. The older pre-reset benchmark ledger
was not changed.

| Budget component | Settled USD |
| --- | ---: |
| Earlier reset-budget work, including interrupted maximum reasoning | $0.427739401 |
| Follow-up exploratory calibrations | $0.040030955 |
| Primary preparation, six calibration answers, and 48 formal attempts | $0.260507150 |
| Control preparation, two calibration answers, and 16 formal attempts | $0.077102070 |
| This follow-up work, including its exploration | $0.377640175 |
| Cumulative settled | $0.805379576 |
| Conservative cumulative exposure | $0.875864376 |

The follow-up subtotal overlaps the three follow-up rows above; do not add it
again. The old unresolved request retains its full $0.0704848 reservation.
No uncertain charge was removed or treated as a refund. Every paid call reserved
its full configured output allowance before execution.

Primary source indexing took 125.2 seconds and cost
$0.000332760. Memory preparation took
439.6 seconds and cost $0.023091305.
The control rebuilt the same document index in
103.9 seconds for $0.000332760; it made no memory writes.
Preparation is excluded from answer latency and included in the amortized costs below.
Exploration is excluded from these recurring per-task estimates.

| Condition | One task | Five tasks | Twenty tasks |
| --- | ---: | ---: | ---: |
| Ordinary file access | $0.004141 | $0.004141 | $0.004141 |
| Source retrieval | $0.005281 | $0.005015 | $0.004965 |
| Sources and memory | $0.028346 | $0.009607 | $0.006093 |
| Source hydration control | $0.004906 | $0.004640 | $0.004590 |

Token totals include repeated request prefixes. Cached reads and writes are
already charged in settled cost; do not subtract another discount. Reasoning
tokens are part of completion tokens.

| Condition | Prompt tokens | Cached reads | Cache writes | Completion tokens | Of which reasoning |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary file access | 1,143,326 | 864,922 | 275,995 | 45,719 | 17,489 |
| Source retrieval | 1,350,762 | 970,289 | 376,676 | 44,247 | 17,953 |
| Sources and memory | 1,128,290 | 759,360 | 363,444 | 50,519 | 21,822 |
| Source hydration control | 1,176,757 | 797,237 | 373,977 | 35,981 | 15,430 |

## Reproducibility and limits

- The source corpus contains 14 unchanged private Git records, 137723 bytes, and four chronological checkpoints. These are retrospective read-only handoffs, not natural multi-day sessions, code edits, or deployed acceptance.
- Each reader runs in a fresh process and conversation. Stores persist across the calibration/formal restart. Later originals are unavailable at earlier checkpoints.
- The route is OpenRouter `openai/gpt-6-luna`, OpenAI standard provider, medium reasoning, with the full 128000 output-token allowance. Embeddings are Qwen3-Embedding-8B through Nebius at 4096 dimensions. Both native retrieval arms use the same local-token-overlap reranker.
- Each cell has eight model rounds, sixteen tool calls, 32768 serialized response bytes, and a 12000-byte per-result limit. These are common workflow limits, not model context limits.
- Primary execution used commit `c1dc5f3e`; the control used `5e5a3fef`. Executable files and the shared reader contract remained unchanged during each scored run. Later documentation edits were not reader input.
- Exploratory calibrations remain recorded separately: the initial quote-copy draft completed four reader cells before its stop marker took effect; the selector calibration completed six. They are not formal scores.
- Original hashes and all stored vector dimensions passed verification at every checkpoint. PostgreSQL and Qdrant snapshots were restored in isolated containers. All originals matched. Nonempty 4096-dimensional collections passed stored-vector similarity queries; the control's memory collection remained empty. Compressed snapshots were checked losslessly before cleanup.
- Local validation passed 471 Rust tests, 196 benchmark contract tests, four tooling tests, and the repository format/docs/workflow/lint checks. The default local gate skipped 106 integration-environment tests. A separate Docker run passed all 106; the later bounded-pack adjustment passed all 11 focused source/evidence integration tests.

The [primary evidence bundle](../../../config/benchmark/evidence/2026-10-13-memory-contract-followup/manifest.json)
and [source control bundle](../../../config/benchmark/evidence/2026-10-13-source-hydration-control/manifest.json)
contain anonymized cells, protocol, runtime hashes, sanitized request ledgers,
admission audits, and restoration summaries. Raw sources, questions, answers,
traces, and provider receipts remain private. The verifiers check integrity,
arithmetic, budget accounting, chronology, and recorded restoration. They cannot
independently reproduce private semantic judgments.

```sh
python3 config/benchmark/evidence/2026-10-13-memory-contract-followup/verify.py
python3 config/benchmark/evidence/2026-10-13-source-hydration-control/verify.py
```
