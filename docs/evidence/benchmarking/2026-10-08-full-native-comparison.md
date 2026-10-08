---
type: Evidence
title: Full native memory benchmark on 2026-10-08
description: Full registered competitor execution with retained failures, deep lifecycle evidence, bounded repair trials, and cumulative API accounting.
status: historical
authority: informative
owner: benchmark
last_verified: 2026-10-08
tags: [benchmark, memory, cost, retrieval, lifecycle]
source_refs:
  - config/benchmark/evidence/2026-10-08-full-native/campaign.json
  - config/benchmark/evidence/2026-10-08-full-native/provenance.json
code_refs:
  - scripts/benchmark_deep/drivers.py
  - scripts/benchmark_contract/metrics.py
  - scripts/benchmark_budget.py
related:
  - docs/runbook/benchmarking/full_comparison.md
  - docs/evidence/benchmarking/2026-10-07-bounded-calibration.md
---
# Full native memory benchmark

This campaign evaluates native execution, retrieval, isolated answers, lifecycle operations, and bounded agent repair. It does not establish a universal product ranking. Scale failures and the repair ceiling effect limit the conclusions. All registered execution queues have ended. Some planned queries remain unmeasured because native preparation failed; the tables retain those gaps.

## Scope and method

The core matrix has 14 products and two baselines across four suites: 24 common questions, eight lifecycle questions, eight knowledge-structure questions, and eight repository-knowledge questions per target. This gives 64 conditions and 768 planned warm-phase answers. Cold and warm native execution are counted separately.

Eight representative deep conditions cover 100 and 1,000 documents, cross-session recall, source authority, temporal changes, native scope, updates, and deletes. Each full condition plans 62 queries. Separate behavior, scale, setup-fix, and recovery conditions retain their own denominators. The repair evaluation has 17 common-agent conditions of six trials each and a separate six-trial native Letta condition.

The shared reader uses DeepSeek V4.1 Flash with low reasoning and a fixed DeepSeek route. The main embedding route is Qwen3 Embedding 8B through DeepInfra at 1,536 dimensions. QMD host execution and native product preparation retain their distinct configurations. Earlier calibration routes and historical repair images are disclosed separately; they are not evidence of identical execution conditions.

Isolated reader calls use one case per request, a 4,096-token output limit, and a bounded context. Native context exports can contain text outside the reader budget. Revision-five deterministic core scores remain unchanged; the separate manual review identifies literal-matcher limitations without rewriting the scores. A correct answer does not prove that an update or deletion occurred.

## Original selected core conditions

The following table keeps the original whole-condition selection. Later recovery successes are not substituted into it. Correct answers are a subset of answered cases. An execution failure or missing answer is not an observed wrong answer.

| Target | Planned | Cold native | Warm native | Answered | Strict correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| elf | 48 | 48 | 48 | 48 | 46 |
| mem0 | 48 | 48 | 48 | 48 | 42 |
| qmd | 48 | 48 | 48 | 48 | 43 |
| lightrag | 48 | 44 | 43 | 43 | 43 |
| openviking | 48 | 48 | 48 | 48 | 46 |
| graphrag | 48 | 32 | 32 | 32 | 24 |
| graphiti | 48 | 48 | 48 | 48 | 21 |
| pageindex | 48 | 48 | 48 | 48 | 48 |
| openkb | 48 | 48 | 48 | 48 | 45 |
| honcho | 48 | 48 | 48 | 48 | 41 |
| gbrain | 48 | 48 | 48 | 48 | 45 |
| hindsight | 48 | 48 | 48 | 48 | 44 |
| sag-engine | 48 | 40 | 40 | 40 | 38 |
| memos | 48 | 48 | 48 | 48 | 43 |
| files-search | 48 | 48 | 48 | 48 | 47 |
| no-memory | 48 | 48 | 48 | 48 | 6 |

## Deep execution and recovery

The table includes original selected full conditions and separately registered supplements. Retained terminal evidence can contain blocked or unexecuted cases; terminal does not mean successful.

| Target | Condition group | Planned | Native completed | Answered | Correct |
| --- | --- | ---: | ---: | ---: | ---: |
| qmd | all | 62 | 62 | 62 | 57 |
| files-search | all | 62 | 62 | 62 | 53 |
| no-memory | all | 62 | 62 | 62 | 10 |
| elf | all | 62 | 10 | 10 | 10 |
| gbrain | all | 62 | 62 | 62 | 55 |
| hindsight | all | 62 | 52 | 52 | 52 |
| mem0 | all | 62 | 52 | 52 | 43 |
| sag-engine | all | 62 | 10 | 9 | 8 |
| elf | behavior | 42 | 42 | 42 | 41 |
| elf | scale-1000 | 10 | 0 | 0 | 0 |
| sag-engine | behavior | 42 | 42 | 42 | 42 |

Registered recoveries remain separate:

| Recovery condition | Queue finished | State | Answered | Correct |
| --- | --- | --- | ---: | ---: |
| graphrag-memory-lifecycle-v2-provider-recovery | True | failed | 4 | 4 |
| elf-deep-scale-1000-extended-v2-provider-recovery | True | terminal | 0 | 0 |
| gbrain-deep-mutations-v1-supported-embed-source | True | terminal | 12 | 12 |
| hindsight-deep-scale-1000-v1-provider-recovery | True | terminal | 0 | 0 |
| mem0-deep-scale-1000-v1-transport-recovery | True | terminal | 0 | 0 |

ELF and Hindsight scale-1000 recoveries stopped on upstream embedding HTTP 429 before retrieval could be measured. The GBrain mutation recovery completed six updates, six deletes, and all 12 answers after use of the supported CLI flag. Its original failed updates remain recorded. SAG passed the separate 42-query behavior condition; its earlier scale timeout remains unresolved. The final Mem0 scale recovery also stopped on embedding HTTP 429 after 599 ingestion receipts and 79.3 minutes; all ten queries were blocked. This is distinct from its earlier transport disconnect, whose endpoint remains unconfirmed.

## Repair outcomes and limits

All 102 common-agent trials have terminal records: 89 passed validation, 11 were blocked during native preparation, and two executed without passing validation. Execution completion and validation success differ: a turn-limit run can still pass the task checks. The separate native Letta workflow passed six of six.

File search and many memory systems passed six of six; the historical no-memory condition passed five. With three tasks repeated twice, this set has little power to distinguish the successful products. It does not prove that a memory product improves general coding ability. Historical image differences also prevent a clean latency ranking.

## Cost and cache accounting

The closed campaign ledger reports $8.742426971 paid and $0.284895900 reserved for requests with unknown final costs. Conservative exposure is $9.027322871, within the latest $20 user authorization. No paid gateway remained active at export. The unknown costs remain reserved, not treated as free.

Costs include pilots, invalid attempts, provider failures, and retained recoveries. They exclude host compute, CI, and Codex orchestration. Receipt costs already include cache pricing. Observed completion rates include both $0.60 and $1.20 per million tokens for the fixed model/provider; no unverified cause is assigned. Raw costs must therefore not be presented as intrinsic product price rankings.

## Product conclusions

ELF shows useful lifecycle behavior in the measured cases. Its independent behavior condition scored 41 of 42; the one failure returned unknown despite the required fact appearing in the first supplied context. That is evidence of a reader failure after successful retrieval, not a reason to claim the evidence was missing.

Prioritize observable ingestion readiness and recovery from upstream interruptions. Keep source authority and superseded facts explicit: correct shared-reader answers can hide conflicting retrieval context. Preserve separate evidence for native operations, post-restart retrieval, and final answers. Zero foreign canary hits do not establish authorization security.

This campaign does not measure live business-system integration, external ontology construction, production tenant isolation, long-term drift, or representative user task distribution. It cannot establish those capabilities from synthetic cases. Later benchmark changes should use new frozen tasks and include a strong file baseline; they must not overwrite this campaign.

## Separate core repeats

LightRAG's full common-core repeat completed all 24 cases and answers; its knowledge repeat answered seven of eight, with one native indexing failure. SAG's knowledge repeat completed eight of eight. GraphRAG's repository repeat completed five cold and three warm native queries, with three correct answers. Its lifecycle recovery completed four native queries per phase and four correct warm answers. Graph extraction and upstream failures remain separate from wrong answers. These complete attempts do not replace the original table.

## Accounting detail

The ledger contains 33,552 requests. Recorded chat input totals 33,473,316 tokens,
of which 25,301,470 were cached (75.59%). Chat output totals 9,120,610 tokens,
including 7,018,025 reasoning tokens. Embedding input totals 1,548,149 tokens.
There are 189 missing-cost receipts; their $0.284895900 reservation remains in
conservative exposure. Earlier pilot costs and $0.002103636 recorded before the
ledger are included. Missing usage is not assigned zero tokens.

## Evidence and reproduction

The [campaign manifest](../../../config/benchmark/evidence/2026-10-08-full-native/campaign.json)
records artifact hashes and coverage. Its sibling folders contain compressed
JSONL case, native-operation, repair-trial, and usage records. The
[provenance](../../../config/benchmark/evidence/2026-10-08-full-native/provenance.json)
retains source revisions and available image fields; missing image values stay
unknown. The [selection](../../../config/benchmark/evidence/2026-10-08-full-native/execution-selection.json)
and [recoveries](../../../config/benchmark/evidence/2026-10-08-full-native/recoveries.json)
retain attempt boundaries. Private paths in the selection use explicit
placeholders. Raw provider reasoning, credentials, and service state are not
published. Full private attempts remain retained separately.

Use the [full comparison runbook](../../runbook/benchmarking/full_comparison.md)
for repository-owned execution commands and fixed groups. The checked-in
[manual answer review](../../../config/benchmark/evidence/2026-10-08-full-native/answer-review.json)
does not alter strict scores. The
[native operation audit](../../../config/benchmark/evidence/2026-10-08-full-native/native-mutations.json)
separates the original GBrain update failures from the successful independent
recovery. Host QMD runs and preflight-blocked conditions can lack per-unit
container cleanup records; null is not promoted to a passing cleanup result.
The terminal deep conditions passed cleanup, and no campaign `elfdeep-` or
`elfb-` containers remained at export.

Historical calibration and repository-repair evidence remain unchanged. Results
from this campaign apply to the recorded inputs, native modes, source versions,
and provider conditions, not every feature of each product.
