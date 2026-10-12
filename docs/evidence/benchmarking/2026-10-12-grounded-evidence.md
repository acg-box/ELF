---
type: Evidence
title: ELF grounded source and graph evidence trial
description: Matched agent retrieval with separate factual, citation, and subject attribution checks.
status: completed
authority: informative
owner: elf-service
last_verified: 2026-10-12
code_refs:
  - config/benchmark/evidence/2026-10-12-grounded-evidence/verify.py
  - packages/elf-service/src/evidence.rs
  - scripts/benchmark_agent/runner.py
related:
  - docs/decisions/2026-10-12-grounded-evidence.md
  - docs/evidence/benchmarking/2026-10-12-evidence-integrity.md
---
# ELF grounded source and graph evidence trial

This trial tests whether an agent can bind each claim to the correct subject,
time, and source. A correct answer does not establish that its citations are
reliable. Byte verification does not establish semantic support.

## Product changes

ELF keeps PostgreSQL as the source of truth and Qdrant as the derived index.
The new note-evidence API expands a selected memory into its existing original
source, with current access checks, byte offsets, and content hashes. Large
source spans use exact quote anchors within the declared span. Original records
are not rewritten or copied into a new authority.

A separate claim-check API verifies exact quote bindings. Its result explicitly
sets `semantic_support` to `not_evaluated`. The caller must assess subject, time,
causality, explicit absence, uncertainty, and conflict. The benchmark runs this
check after the answer in every condition, including the initial-memory
control, with no feedback or answer repair. It does not measure a
closed-loop agent that uses the checker to revise an answer.

Automatic extraction cannot merge different canonical entities from a shared
alias. Callers can supply an existing project-scoped entity ID when they have
identity authority. Extracted graph relations carry verbatim evidence quotes.
These changes prevent specific new identity and provenance errors; they do not
split historical merged entities or solve all same-name ambiguity.

The [design decision](../../decisions/2026-10-12-grounded-evidence.md) records
adaptations from Hindsight context expansion, RAGFlow parent-child retrieval,
Anthropic contextual retrieval, and Zep entity resolution. No new database or
model judge was added. The extractor changes are profile `default` version 5;
existing deployments must explicitly select it. No production rollout occurred.

## Frozen experiment

The original twenty questions and sources remain unchanged: sixteen test cases
and four development cases. Sixteen new cases add North/South projects with a
shared name, different budget appointments, Chinese roles, unresolved conflicts,
and unapproved future proposals. The expanded corpus has thirty-six originals.
All arms use this same corpus, model, and initial retrieval. This is not a
corpus-identical A/B comparison with the previous twenty-source run.

The original questions use five conditions:

- `initial`: the initial twelve memory records, with no additional tool calls.
- `notes`: memory search, pagination, and note reads.
- `source`: memory tools plus original-source expansion and retrieval.
- `graph`: memory tools plus graph traversal.
- `both`: memory, original-source, and graph tools together.

Every initial context uses the same derived-note projection. The `initial`,
`notes`, and `graph` views omit `source_ref`, including its original quotes and
source timestamps. Source-enabled note reads expose that provenance and the
resolved original context. This ablation measures the source-access bundle,
not the isolated value of parent-text expansion. The production note API itself
still returns provenance; these restricted views are benchmark controls.

The contrast cases compare `both` and `initial`. The selected matrix has 132
cases. It was narrowed from the planned 180 for cost before any contrast reader
answer. The fixture and rubric remained frozen. The execution amendment and
selection receipts are in the bundle. There is no five-arm contrast ablation.

Qwen3-Embedding-8B uses all 4,096 dimensions. Exact matching vectors are reused.
DeepSeek V4.1 Flash uses the official DeepSeek route, maximum reasoning, and the
393,216-token output allowance. Each primary case has at most twelve responses
and twenty-four tool calls. Two independent primary cases can run concurrently;
controls run serially. After one HTTP 520 failure, provider calls were serialized
while the two-case scheduler remained unchanged. Two provider requests were
later restored after a controlled drain when measured remaining costs allowed
both full reservations. The failed request had no model
answer. Its four complete prior turns and eighteen tool results were preserved
and the next response was resumed within the original per-case limits. The
unsettled cost reservation remains charged against the ceiling. A later provider
completion returned `finish_reason: error`, partial reasoning, and no answer,
with an explicit zero-cost receipt. Its two complete prior turns were retained;
the unfinished response was retried and the failed fragment was archived.
A control response later failed in the same way, with only partial reasoning
and an explicit zero-cost receipt. Its failed fragment was archived before
retrying the unanswered control from the same frozen inputs.
Logical response and tool limits were unchanged. The shared
ledger reserves the full possible request cost
before dispatch. Latencies are not directly comparable with prior serial runs.

The paid reader runtime is commit `a0bb04d3`. The final long-source correction is
commit `0b41ef27`. All eighty-four frozen-corpus note-evidence responses matched
between the two runtime images after removal of request and trace IDs. This
comparison made no paid calls. The long-source branch has a separate native
integration test with distant Chinese and English quotes and an invalid span.
The paid answers were not rerun after that correction.

## Scoring

The final table separates three obligations:

1. Whole-answer factual correctness, including additional explanations.
2. Semantic citation support: each citation fits its claim's subject, time, and
   causal assertion. A redundant unrelated citation fails citation precision.
3. Mechanical binding: the exact quote was visible to the agent and belongs to
   the cited readable note or hash-guarded original.

The factual column requires the requested oracle facts as well as correct
additional statements. A justified unknown response when the initial context
lacks an answer is incomplete for that column, not automatically a hallucination.
A joint pass requires all three. Invalid structured answers remain failures;
there is no resampling for a better answer. The original lexical score is also
retained, but it can reject a correct answer that explicitly contrasts an old
value with a new one. The table uses full-answer review instead. Reviews are
hash-bound to retained answers and claims and were made by the coding assistant;
they are not blinded expert labels or an independent paid judge.

## Original test questions (16 per condition)

| Condition | Factual | Semantic citations | Exact binding | Joint pass |
| --- | ---: | ---: | ---: | ---: |
| Memory tools | 16/16 (100.0%) | 7/16 (43.8%) | 16/16 (100.0%) | 7/16 (43.8%) |
| Memory + original sources | 16/16 (100.0%) | 16/16 (100.0%) | 15/16 (93.8%) | 15/16 (93.8%) |
| Memory + graph | 15/16 (93.8%) | 6/16 (37.5%) | 16/16 (100.0%) | 6/16 (37.5%) |
| Memory + original sources + graph | 16/16 (100.0%) | 16/16 (100.0%) | 14/16 (87.5%) | 14/16 (87.5%) |
| Initial memory only | 14/16 (87.5%) | 4/16 (25.0%) | 16/16 (100.0%) | 3/16 (18.8%) |

## New contrast questions (16 per selected condition)

| Condition | Factual | Semantic citations | Exact binding | Joint pass |
| --- | ---: | ---: | ---: | ---: |
| Memory + original sources + graph | 14/16 (87.5%) | 13/16 (81.2%) | 12/16 (75.0%) | 10/16 (62.5%) |
| Initial memory only | 10/16 (62.5%) | 6/16 (37.5%) | 16/16 (100.0%) | 4/16 (25.0%) |

## Original development questions (4 per condition)

| Condition | Factual | Semantic citations | Exact binding | Joint pass |
| --- | ---: | ---: | ---: | ---: |
| Memory tools | 3/4 (75.0%) | 2/4 (50.0%) | 4/4 (100.0%) | 1/4 (25.0%) |
| Memory + original sources | 3/4 (75.0%) | 3/4 (75.0%) | 4/4 (100.0%) | 3/4 (75.0%) |
| Memory + graph | 3/4 (75.0%) | 2/4 (50.0%) | 4/4 (100.0%) | 1/4 (25.0%) |
| Memory + original sources + graph | 4/4 (100.0%) | 4/4 (100.0%) | 3/4 (75.0%) | 3/4 (75.0%) |
| Initial memory only | 2/4 (50.0%) | 2/4 (50.0%) | 4/4 (100.0%) | 1/4 (25.0%) |

## Calls and latency for original test questions

| Condition | Tool calls | Cases at 24-tool limit | Median seconds | Maximum recorded seconds | Answer chat cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Memory tools | 341 | 9/16 | 163.8 | 288.9 | 0.50616 |
| Memory + original sources | 234 | 1/16 | 115.8 | 234.7 | 0.48797 |
| Memory + graph | 367 | 12/16 | 134.4 | 226.1 | 0.49004 |
| Memory + original sources + graph | 263 | 1/16 | 108.0 | 193.1 | 0.46685 |
| Initial memory only | 0 | 0/16 | 21.0 | 155.0 | 0.07214 |

The resumed answer has no comparable total latency and is excluded from the
median. Costs include all successful chat turns in each retained trajectory.
Preparation, other cohorts, query embeddings, and unresolved reservations are
reported separately in the cumulative ledger. Serial and concurrent provider
periods are both present; the medians are descriptive, not isolated speed tests.
They include model and embedding-provider time and do not benchmark PostgreSQL
or Qdrant query latency in isolation.

## Findings

The source-access bundle improves subject and time attribution on the original
test cohort. Its benefit cannot be isolated to parent-text expansion alone.
Memory-only and graph-enabled answers can give the correct requested identifier
while citing an unrelated project or a generic note without a visible subject.
A real quote can therefore pass the byte checker and still fail the semantic
review. Source-enabled answers can also copy an original quote onto a note ID;
those errors fail the mechanical binding check.

The combined contrast arm gives factually correct text in 14/16 cases and a
joint pass in 10/16. Two historical-state answers select the later August 15
choice for an immediately-after-August-8 question. One answer has correct raw
facts but fails the required structured answer format. Chinese facts are correct
in all four combined cases, but one Chinese owner answer has a quote-binding
failure. Conflict, an unapproved future proposal, and unknown versus explicit
absence remain separate checks, not a single abstention score.

The Cedar development question exposes a concrete information-loss case:
The memory-only trajectory never receives STREAM-4-286 and correctly marks
it unknown; none of the stored note bodies contains that identifier. The
source-enabled trajectory recovers it from the original August 15 approval.
This is an incomplete-answer failure, not a fabricated value.

The initial-memory Cedar recovery control took 441.1 seconds and 85,080
output tokens (83,721 reasoning tokens), at a billed cost of $0.05108637.
It still marked the causal change gate unknown. This is a retained long-tail
case, not an estimate of database latency; maximum reasoning did not supply
the missing source evidence.

The combined arm does not establish a stable graph advantage over source
expansion alone. The fixture stores 99 entities, 119 facts, and 123 evidence
links, all with quotes; 97 facts have unknown `valid_from`. A separate offline
diagnostic finds no project-to-recovery path within three stored directed edges
for the nine project groups, even when each name variant is tried independently.
It does not merge fragments or supply oracle paths to the reader. This diagnoses
representation gaps; it does not prove that all graph queries are useless.

## Integrity, cost, and cleanup

Cumulative paid API cost is **$7.90696343**, including the earlier
$4.06770569. This trial adds **$3.83925773**.
Conservative exposure is **$8.99076383**, below the $10 ceiling.
Both unsettled reservations remain included: ordinal 1577 ($0.5691777) and
ordinal 4501 ($0.5146227). They are not assumed free. No paid semantic judge
or repeat of a completed factual answer was used.

All 36 originals, 105 source pointers, and 624 full-4,096-dimensional stored
vectors were checked before and after the run. PostgreSQL was backed up and
restored into a temporary database; eleven table fingerprints matched before
the temporary restore was removed. The raw dump and receipts remain local.
Only this task's eight containers, their volumes, its network, and its two image
tags were removed. Unrelated containers and shared images were preserved.

Local validation passed 459 Rust unit tests, 105 Docker integration tests,
176 Python contract tests, Clippy, strict Rust style, documentation checks,
and the previous two evidence verifiers. PR #408 records final exact-head CI.

Reproduce retained evidence without network or model calls:

```sh
python3 config/benchmark/evidence/2026-10-12-grounded-evidence/verify.py
python3 config/benchmark/evidence/2026-10-12-grounded-evidence/diagnose_representation.py
```

The [evidence bundle](../../../config/benchmark/evidence/2026-10-12-grounded-evidence)
contains the matrix, full trajectories, per-answer reviews, usage receipts,
source snapshots, compatibility checks, backup proof, and cleanup receipt.


## What this trial cannot establish

No Hindsight or RAGFlow run was repeated. These results cannot rank ELF against
those products or isolate the benefit of each code change. This is one synthetic
fixture, one extraction per source, and one answer per condition and question.
The North/South contrast questions say 'was approved immediately after', while
the originals say 'was still approved'. This leaves some ambiguity between an
approval event and the mode in force. Reviews accept an answer that explicitly
keeps the original mode while stating that no new approval occurred. The wording
difference prevents a clean attribution of temporal errors to architecture alone.
The graph diagnostics cover bounded directed paths, not every possible graph
query. Existing canonical fragments and unknown validity times remain visible.

The benchmark adapter flattens a note and its expanded source evidence for the
reader. Quote-to-identifier copying errors can therefore include agent and
adapter-integration effects; they are not automatically storage corruption.
The public APIs keep derived notes and original evidence structurally distinct.

## Next iteration

The next useful work is to preserve subject and time in an evidence package,
and to let agents cite stable evidence handles instead of copying identifiers,
hashes, and quotes independently. Graph work should demonstrate useful paths to
source evidence before adding more relations. The agent also needs a measurable
stopping rule: repeated equivalent verification consumes latency and tool calls
without necessarily improving attribution. These are measured follow-up
priorities, not features delivered by this change.
