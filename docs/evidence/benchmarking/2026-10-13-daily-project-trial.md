---
type: Evidence
title: Daily-cost project memory trial
description: Real private project replay, matched content assessment, complete cost exposure, and native recall diagnosis.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-13
code_refs:
  - scripts/benchmark_pilot/runner.py
  - scripts/benchmark_pilot/report.py
  - config/benchmark/evidence/2026-10-13-daily-project-trial/verify.py
related:
  - docs/runbook/benchmarking/real_project_memory_trial.md
  - docs/decisions/2026-10-13-project-memory-trial.md
---
# Daily-cost project memory trial

The current reader workflow did not demonstrate an incremental benefit from
derived memory. Source retrieval had the best observed requirement coverage,
time, and answer cost. This is a small retrospective trial, not evidence of
statistical superiority or customer readiness. A separate native probe found
useful memories that the scored reader had not used.

## Results

The trial attempted 48 formal cells: eight tasks, two repetitions, and three
conditions. There were 47 returned answers and one upstream `IncompleteRead`.
That failed cell and its cost reservation remain in the record. Its matching
cell is excluded from content comparison in all three conditions, leaving the
same 15 comparisons and 60 required obligations per condition. No answer was
replaced or retried for a better score.

| Condition | Returned answers | Required obligations met, matched set | Complete task acceptance, matched set | Median elapsed, matched set | Mean answer cost, matched set |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary file access | 15/16 | 37/60 (61.7%) | 2/15 | 31.1 s | $0.002929 |
| ELF source retrieval | 16/16 | 49/60 (81.7%) | 6/15 | 23.5 s | $0.002525 |
| ELF sources and memory | 16/16 | 47/60 (78.3%) | 5/15 | 28.8 s | $0.002845 |

Complete acceptance requires every frozen obligation and no invalid or unbound
claim. Requirement coverage is not a factual-accuracy percentage: most failures
were missing detail, incomplete source access, or citation handling. One answer
put a timeout origin after the request instead of at the start of polling.
Semantic review was performed by the assistant against the private originals;
it is not an independent or blinded judge. Native reference binding verifies
source identity and access, not entailment.

The two repetitions below show requirements met out of four. An asterisk marks
an additional invalid-reference failure. The transport failure has no content
score.

| Task category | Ordinary files | Source retrieval | Sources and memory |
| --- | --- | --- | --- |
| Capacity handoff | 0/4, 0/4 | 3/4, 3/4 | 2/4, 4/4 |
| Recovery acceptance | 3/4, 3/4 | 4/4, 3/4 | 3/4, 3/4 |
| Revision and history rules | 4/4, 4/4 | 4/4, 4/4 | 4/4, 4/4 |
| Local versus integrated acceptance | 3/4, 3/4 | 3/4, 3/4 | 3/4, 3/4 |
| Superseded configuration | 3/4, 3/4 | 3/4 *, 3/4 | 3/4 *, 3/4 |
| Validation and cache policy | 1/4, 2/4 | 1/4, 3/4 | 3/4, 1/4 |
| Subsystem ownership retirement | 2/4, transport failure | 4/4, 4/4 | 3/4, 3/4 |
| Secret-contract retirement | 3/4, 3/4 | 4/4, 4/4 | 4/4, 4/4 |

## What the reader actually used

All conditions could read the same originals through bounded file tools.
Source-only added native document search; full ELF also offered note search,
evidence packs, recall, and graph traversal. The agent chose its tools.

- Source-only used native source search in 4/16 cells. Full ELF used it in 4/16.
- Full ELF attempted memory search in 1/16 cells. The one attempt was blocked by the already exhausted evidence-byte budget. No scored cell completed a memory or graph call.
- Evidence-budget loss affected 9/16 ordinary-file cells, 9/16 source-only cells, and 8/16 full-ELF cells.
- Some native document queries returned an empty, explicitly truncated result after earlier reads spent the budget. These are not proof that the backend recalled nothing.

The result therefore measures this Agent integration. It does not measure the
maximum quality of ELF memory retrieval. The file adapter also exposes native
search positions as byte offsets while its common read tool accepts line
numbers. That adds a navigation step. The common claim checker runs after the
final answer; this workflow does not provide a citation-repair turn.

## Native memory diagnosis

The shipped API and worker processed all 32 extraction windows. Of 74
proposed notes, 23 were added and 51 were rejected.
Original text was not rewritten or removed to make admission succeed.

| First failing check | Candidates |
| --- | ---: |
| Evidence quote exceeds 320 UTF-8 bytes | 29 |
| Note exceeds 240 characters | 14 |
| Evidence does not match the selected message | 7 |
| Evidence quote count exceeds the allowed range | 1 |

The public error code `REJECT_EVIDENCE_MISMATCH` covers quote length and count as
well as actual source mismatch. It must not be interpreted as 37 notes with fabricated
evidence. The prompt stated the note length and quote count, but did not state
the quote byte limit. The validator uses bytes for that quote limit, despite the
configuration name ending in `chars`. See
[the evidence validator](../../../packages/elf-service/src/add_event/validation/evidence.rs)
and [the extraction profile](../../../packages/elf-service/src/ingestion_profiles/profile.rs).
This diagnosis records the first failed check; another check can also fail.

After scoring, two unscored native queries used the unchanged final-checkpoint
task text. Both retrieved the current retirement decision first, with original
source references. They also returned historical or unrelated candidates.

| Native probe | Candidates | Original sources returned | Notes with complete source evidence | Whole pack complete |
| --- | ---: | ---: | ---: | --- |
| Ownership retirement | 6 | 3 | 3/6 | No |
| Contract retirement | 6 | 5 | 5/6 | No |

The probes cost $0.000000900 in total. They were not
new reader answers and did not alter the formal scores. At the final checkpoint,
the graph contained 5 entities and 0 facts. No graph-reasoning gain is established.

## Cost and timing

The new budget started at zero and retained a $10 ceiling. The earlier benchmark
ledger was preserved unchanged. The interrupted maximum-reasoning preparation
is charged here as exploration, separate from the daily model comparison.

| Cost component | Known settled USD |
| --- | ---: |
| Interrupted maximum-reasoning preparation | $0.263160 |
| Daily source indexing | $0.000333 |
| Daily memory preparation | $0.023720 |
| Six calibration answers | $0.008484 |
| All formal answer attempts | $0.132042 |
| Two native recall probes | $0.000001 |
| Total settled | $0.427739 |
| Conservative exposure, including the unresolved request | $0.498224 |

One incomplete upstream response has no returned settlement receipt. Its full
$0.0704848 reservation is still counted. No reservation was deleted or treated as a refund.

Source preparation took 75.0 seconds and memory preparation
364.8 seconds. The following per-task estimates amortize those
preparation costs over the indicated number of tasks and use the matched set's
mean answer cost. They exclude exploration and unscored diagnosis.

| Condition | One task | Five tasks | Twenty tasks |
| --- | ---: | ---: | ---: |
| Ordinary file access | $0.002929 | $0.002929 | $0.002929 |
| ELF source retrieval | $0.002858 | $0.002592 | $0.002542 |
| ELF sources and memory | $0.026897 | $0.007655 | $0.004047 |

Provider token totals below include all formal calls, including repeated prompt
prefixes. Cached reads and cache writes are already reflected in settled cost.
Reasoning tokens are part of completion tokens, not an extra amount to add.

| Condition | Prompt tokens | Cached reads | Cache writes | Completion tokens | Of which reasoning |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary file access | 520,612 | 322,665 | 197,716 | 34,986 | 16,802 |
| ELF source retrieval | 482,736 | 318,917 | 163,498 | 34,807 | 15,684 |
| ELF sources and memory | 529,859 | 353,821 | 175,716 | 40,008 | 20,167 |

## Scope and verification

- Four chronological checkpoints contain 14 complete Git records and 137723 original bytes from a real private project. Tasks were newly authored retrospective questions, not natural user-session replays or code-editing tasks.
- The model was `openai/gpt-6-luna`, standard OpenAI route through OpenRouter, medium reasoning, and the full native 128000-token output allowance. Native extraction used the same route. No model/provider fallback was enabled.
- Both retrieval conditions used Qwen3-Embedding-8B at 4096 dimensions and the same local-token-overlap reranker. The API and worker were local debug builds with Docker PostgreSQL and Qdrant. This was not a database throughput comparison.
- Each reader had eight rounds, sixteen tool calls, and 32768 serialized tool-response bytes. This is a workflow limit, not the model's native context limit. Later sources were unavailable at earlier checkpoints.
- All original hashes and stored vector dimensions were verified at every checkpoint. Runtime file hashes remained unchanged during the scored run. Raw questions, originals, answers, traces, and provider receipts remain private.
- PostgreSQL and Qdrant backups were restored in separate temporary containers. All 14 current original records matched; restored 4096-dimensional document and memory vectors passed stored-vector similarity queries. The interrupted preparation snapshot was also restored separately.
- Local checks passed: 465 Rust tests, with 106 integration-environment tests skipped; 192 benchmark contract tests; four tooling tests; formatting, documentation, workflow lint, and Rust lint. Native trial execution is separate evidence from those local checks.

The [public evidence bundle](../../../config/benchmark/evidence/2026-10-13-daily-project-trial/manifest.json)
contains anonymized cells, the sanitized request ledger, protocol, runtime hashes,
write-gate audit, restore receipt summary, and a verifier. It checks artifact
integrity, costs, cohort arithmetic, chronology, and recorded restoration results.
It cannot independently reproduce private semantic judgments.

```sh
python3 config/benchmark/evidence/2026-10-13-daily-project-trial/verify.py
```

## Next work

1. Make the extraction contract and validator share the same explicit limits and units. Use precise rejection reasons and source-bound evidence selections; retain immutable originals and strict provenance.
2. Improve the Agent entrypoint before adding more storage: retrieve a small relevant source set, expose usable source positions, preserve read budget, and check citation handles before displaying the answer. Activate memory early enough to test its value.
3. Freeze new follow-up tasks for natural project handoffs and decision updates. Measure whether a memory-aware client beats the source-only baseline. This trial does not establish a customer-readiness threshold or a competitor ranking.
