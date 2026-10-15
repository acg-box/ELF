---
type: Evidence
title: Complete memories under aggregate budgets
description: Replay all old proposals, retain the 520-character claim, and verify multilingual qualifications without per-note truncation.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-15
code_refs:
  - packages/elf-service/src/ingest_budget.rs
  - packages/elf-service/src/add_event/extraction.rs
  - packages/elf-service/src/evidence/pack/budget.rs
  - packages/elf-service/tests/acceptance/text_boundary/budget.rs
  - config/benchmark/evidence/2026-10-15-complete-memory/verify.py
related:
  - docs/decisions/2026-10-15-complete-memory-budgets.md
  - docs/evidence/benchmarking/2026-10-15-note-limit-512.md
  - docs/reference/product-direction.md
---
# Complete memories under aggregate budgets

The complete 520-character candidate now passes admission, keeps its final
qualification, and ranks first in a targeted query. There is no note or
structured-text character gate and no silent three-candidate tail discard.
Original documents, stored note text, indexed child chunks, and source bindings
passed native checks. Aggregate write/read budgets report gaps explicitly.

## Frozen replay and reader results

The main replay kept six original records, all 26 old extraction proposals, the
two original questions, six obligations per question, and two repetitions. A
separate replay kept the three later proposals, including the old 520-character
failure. All 29 proposal objects were unchanged. The result was 27 added notes
and the same two importance/confidence policy ignores, with no length rejection
or budget deferral. The repair and comparison-condition probes each ranked first.

| Original four reader cells | Previous 512-character run | Complete-memory run |
| --- | ---: | ---: |
| Obligations met | 21/24 | 22/24 |
| Complete answers | 1/4 | 2/4 |
| Mean reader time | 53.23 s | 51.32 s |
| Paid reader cost | $0.012236165 | $0.009964180 |
| Actual memory read | 4/4 | 4/4 |
| Exact memory-delivered source span cited | 2/4 | 1/4 |

All four current answers preserved the repair state, remaining credential
rejections, and pending native acceptance and memory benefit at the historical
checkpoint. Two omissions remained: one capture hash/span detail and one pair
of historical settled/exposure amounts. Both were already in original context
returned to the reader. These are answer omissions, not evidence for changing
admission, MMR, or storage again. Three answers cited wider source windows instead
of the exact spans delivered with memory; all final bindings were valid.

The reader uses the shipped v6 contract and native total response budgets. MMR,
source windows, questions, and scoring criteria stayed fixed. This is a small
sequential regression, with uncontrolled model variation, caching, and provider
latency. The score and cost change do not establish repeatable memory benefit
against indexed originals or file tools. Those baselines were not rerun here.

## Separate boundary cases

| Case | Result | Qualification |
| --- | --- | --- |
| Old 520-character candidate | Added unchanged; targeted rank 1; complete indexed text and valid binding | A 1024-byte pack omitted the whole note and returned its ID with `complete=false`. |
| Capture/calibration boundary question | 5/6 obligations | Kept Work Journal, ingestion, actual-use, pending-state, and binding limitations. Omitted the frozen capture-metadata checklist. |
| Fresh Chinese source, profile 8 | 5/5 candidates added | Kept four project rules separate and retained dates, amounts, approvals, and exclusions. One range joined contiguous original spans. |
| Chinese multi-project question | 4/4 obligations | Retained both budget amounts, the October 20 approver change, restore plus authorization, and both-tests plus owner-confirmation conditions. |

The 5/6 checklist includes role/time/session capture metadata that the selected
work receipt does not explicitly enumerate. Keep the failed frozen criterion,
but do not call it a demonstrated extraction defect. No question, oracle, or
original text was revised to improve an answer. Calibration coverage was 3/4,
6/6, and 2/2 respectively; all three passed the separate native read-and-cite
gate. The 3/4 calibration omitted the simple-architecture/PR-merge instruction.
No scored conversation was repeated.

Reviews inspected complete answers and claim chains against their originals.
They are assistant reviews, not independent or blinded assessments. Valid hashes
and bindings establish identity and access, not semantic truth. The synthetic
case is a regression fixture, not customer-workflow acceptance.

## Cost, execution, and recovery

The reader and fresh extractor used `openai/gpt-6-luna`, medium reasoning, and the
full 128000-token output allowance. Embeddings remained Qwen3-Embedding-8B with
4096 dimensions. Exact-input settled extraction and embedding receipts were
reused; fresh preparation, queries, planning, answers, and cache charges were
included in the same ledger.

- New provider requests: 70. New settled cost: **$0.020628590**.
- Cumulative settled cost: **$1.965424136**.
- Prior unresolved reserve retained: **$0.071338400**; no new unresolved charge.
- Conservative cumulative exposure: **$2.036762536 / $10**.
- The finite follow-up stayed below its $0.50 tranche. Provider work is closed.

Two setup failures occurred before model work for the affected operation. The
benchmark authentication overlay depended on TOML column alignment; it now uses
key-based matching. The synthetic capture envelope omitted required source
metadata; the corrected envelope added its kind, URI, and unverified trust label
before extraction. Its frozen text, questions, oracle, and extraction input did
not change. Both failures and their recovery receipts remain in private evidence.

Local validation passed 479 Rust tests, 216 benchmark contract tests, four tooling
tests, and 111 external-service integration tests. The latter cover complete long
notes, more than three candidates, explicit deferred outcomes without indexing,
input admission before model use, UTF-8 range selection, and preview/full reads.
Original/source access checks remain in place.

All three native stores passed PostgreSQL restore comparison and restored Qdrant
queries with full 4096-dimensional vectors. Task-owned containers and volumes
were removed after restoration and lossless archive verification. Private raw
receipts, original text, answers, and restore archives remain outside Git. The
compact public bundle contains metrics, hashes, cost receipts, and a verifier;
it does not independently reproduce private semantic review.

Run `python3 config/benchmark/evidence/2026-10-15-complete-memory/verify.py` to
check public artifact integrity, cost arithmetic, cell counts, and native receipts.
