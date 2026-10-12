---
type: Evidence
title: ELF source-context and native citation trial
description: Frozen-question results, raw output failures, deterministic claim consumption, and graph diagnosis.
status: completed
authority: informative
owner: elf-service
last_verified: 2026-10-12
code_refs:
  - packages/elf-service/src/evidence/pack.rs
  - packages/elf-service/src/evidence/reference.rs
  - scripts/benchmark_agent/answer.py
  - config/benchmark/evidence/2026-10-12-evidence-context/verify.py
related:
  - docs/decisions/2026-10-12-evidence-context.md
  - docs/evidence/benchmarking/2026-10-12-grounded-evidence.md
---
# ELF source-context and native citation trial

Source context and native citation references reduce attribution and copying
errors in this fixture. They do not supply sources that initial retrieval missed
or solve all temporal interpretation. The raw reader also exposed a redundant
answer-envelope contract: 24/36 outputs used citation objects where the old
answer-level list required strings. Those raw failures remain in the evidence.

## Delivered behavior

`elf_evidence_pack` resolves up to twelve selected notes into separate derived
notes and deduplicated original windows, with a total byte budget. Original text
retains subjects, dates, qualifications, and explicit negatives. Source-record
time and capture time have separate labels; neither is inferred fact validity.

The claim checker resolves returned source references under current permissions,
content hashes, and byte bounds. It returns exact `resolved_citations` and keeps
`semantic_support: not_evaluated`. No new database, embedding, model judge, or
source rewrite is required. The [design decision](../../decisions/2026-10-12-evidence-context.md)
records pinned Hindsight, Graphiti, RAGFlow, LightRAG, and LlamaIndex mechanisms
and the choices not adopted.

The consumer now treats atomic claims as the single citation authority. It
constructs the answer-level reference list deterministically from those claims.
It does not change claim text, answer text, quotes, or identifiers. Native
validation still checks each binding. The legacy and native readers share the
existing single-JSON-block decoding policy; arbitrary prose is not repaired.

## What was actually run

All thirty-six original questions and sources were frozen, including sixteen
original test questions, four development questions, and sixteen contrast
questions. The v5 extraction, original twelve retrieved note IDs per question,
and 624 full-4096-dimensional Qwen3-Embedding-8B vectors were restored unchanged.
There was no fresh extraction, embedding, reranking, or graph repair.

Each question received one native evidence-pack prefetch and one DeepSeek V4.1
Flash response through the official DeepSeek route, with maximum reasoning and
the unchanged 393216-token output allowance. The first four questions calibrated
cost and remain part of the same run. No completed answer was regenerated.
The largest source-text payload was 2596 bytes; all 36 packs resolved their
selected pointers completely. This does not imply complete answer coverage.

This is one new read-path condition, not a rerun of all five prior ablation arms.
Prefetch supplies source context before generation; the prior source-enabled
agent expanded sources iteratively. Prompt and evidence delivery changed
together, and the synthetic fixture is small. Do not infer an isolated causal
improvement, a database-speed result, or superiority over other products.

The paid generator and native runtime were frozen at `0e43e463`. The paid prompt
still requested the redundant top-level citation list. After observing the
format failures, the consumer was refactored to derive that list from claims.
All 36 retained raw outputs were replayed through that deterministic consumer,
without another model call. The final prompt also stops requesting the duplicate
list; no new generation under that shorter prompt is claimed. The next table
therefore separates raw strict-envelope results from native-consumer replay.

## Results

A joint pass requires correct requested facts, semantically appropriate
citations, and exact visible source binding. Justified unknown answers can be
well grounded but incomplete. Reviews are hash-bound assistant judgments, not
blinded expert labels or a paid judge.

| Cohort | Factual answers | Native semantic support | Native exact binding | Native joint pass | Raw strict-envelope joint pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original test | 16/16 | 16/16 | 16/16 | 16/16 | 4/16 |
| New contrast test | 14/16 | 15/16 | 16/16 | 14/16 | 7/16 |
| Development | 2/4 | 4/4 | 4/4 | 2/4 | 1/4 |

All 36 native claim payloads were accepted and their exact source bindings
passed. That does not make all 36 answers correct. The native-consumer replay
keeps the original claims; it is not a second factual answer or a silent repair
of wrong citations. The original strict-envelope failures are not relabeled.
The same consumer preserves text and claims for 131/132 prior raw responses;
the prior response with an unwrapped prose preface still fails. Separately,
all 131 prior accepted native claim payloads retain identical binding verdicts
on the new service. The earlier retrieval and model answers were not rerun.

For context, the previous source-enabled iterative condition passed 15/16
original test cases jointly, and its combined source/graph condition passed
10/16 contrast cases. These are reference results from a different delivery
policy, not a controlled estimate of the new pack's individual contribution.

## Remaining failures

- Cedar current-mode and causal-change questions lack the August 15 source in
  their initial candidate set. The pack cannot invent it. Both answers correctly
  retain uncertainty but fail factual completeness. Iterative source retrieval
  remains necessary when relevant records are missing.
- North's historical question is interpreted as a new approval event and gets
  an unknown response instead of the required retained BATCH mode. South's
  historical question selects the later August 15 STREAM approval. The frozen
  wording says “approved immediately after”; its ambiguity remains documented.
- The raw output-envelope errors are deterministic format/ownership failures,
  separate from source attribution. Consumers should use native claims and
  resolved citations, not trust a second independently generated reference list.

Chinese role distinctions, separate North/South budget appointments, explicit
absence versus unknown, and the unapproved future retry proposal are preserved
in this run. These observations cover the retained cases only.

## Graph diagnosis

The frozen graph has 119 facts, 68 predicate surfaces, and 33 scalar objects.
Ninety-seven facts have unknown start validity, and none has known end validity.
North Atlas and Delta each have three canonical variants. Trying each name
variant independently finds a recovery path in 0/9 groups with three directed
edges, and 2/9 with reverse edges allowed. Shared-source incidence finds
candidate evidence paths for 9/9 within four hops. Incidence is navigation, not
proof of identity, causality, or effective time.

The practical next step is to connect selected graph evidence-note IDs to the
same native evidence-pack read. Do not create causal edges from co-occurrence or
replace the database to fix missing relations. Better graph extraction or a
bounded application ontology needs its own evidence before adoption.

## Cost and latency

This trial adds **$0.19228509**. Cumulative paid cost is
**$8.09924852**, including the prior $7.906963426.
Conservative exposure is **$9.18304892**, below $10.
The old unsettled reservations (1577 and 4501, totaling $1.0838004) remain
included. Offline replay and native binding checks incur no model charge.

| Cohort | Median reader seconds | Maximum reader seconds | Median prefetch seconds | Answer chat cost (USD) |
| --- | ---: | ---: | ---: | ---: |
| Original test | 39.0 | 73.9 | 0.023 | 0.081385 |
| New contrast test | 32.3 | 103.3 | 0.023 | 0.076933 |
| Development | 72.8 | 117.8 | 0.022 | 0.033967 |

Reader time excludes initial retrieval and post-answer checking. Prefetch is
reported separately. Provider caching, concurrency, and billing time differ
from the previous run; these numbers do not establish a causal speedup.

## Validation and cleanup

460 Rust unit tests, 105 Docker integration tests, two focused source-reference
integration tests, 181 Python contract tests, Clippy, strict Rust style, format,
and documentation checks passed. The prior 132-case evidence verifier passed.
The final bundle verifies raw requests, source bytes, unchanged claims,
canonical citation projection, scored labels, and accounting without network.

All eleven original/source/note/vector/graph table fingerprints match the prior
verified backup before and after the trial. The owned native API process, two
Docker containers, and one volume were removed. Ten unrelated containers and
shared images were preserved. The prior verified backup and raw results remain
outside the worktree. No production deployment occurred.

```sh
python3 config/benchmark/evidence/2026-10-12-evidence-context/verify.py
python3 config/benchmark/evidence/2026-10-12-evidence-context/graph_diagnostics.py
```

The [evidence bundle](../../../config/benchmark/evidence/2026-10-12-evidence-context)
retains raw output failures and the separate native-consumer replay.
