---
type: Evidence
title: ELF source integrity and bounded agent retrieval
description: Matched regression evidence for source identity, verified originals, graph uncertainty, and bounded completion.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-12
source_refs:
  - config/benchmark/evidence/2026-10-12-evidence-integrity/manifest.json
  - config/benchmark/evidence/2026-10-12-evidence-integrity/quality-summary.json
related:
  - docs/evidence/benchmarking/2026-10-11-agent-evidence.md
  - docs/decisions/2026-10-12-evidence-integrity.md
  - docs/runbook/elf-agent-evidence-benchmark.md
code_refs:
  - packages/elf-service/src/update_resolution.rs
  - packages/elf-service/src/docs/event_sources.rs
  - packages/elf-service/src/graph_ingestion.rs
  - scripts/benchmark_agent/runner.py
---
# ELF source integrity and bounded agent retrieval

ELF now preserves distinct source occurrences and verified original-document
links. The bounded agent completes this memory fixture more reliably. Source
access recovers omitted information. These results do not establish complete
citation correctness, useful graph connectivity, or superiority to another
product.

## Changes and upgrade boundary

PostgreSQL remains the owner of original records, notes, graph assertions, and
canonical vectors. Qdrant remains the retrieval index. No new backend or service
is introduced. An unkeyed note can deduplicate only the same stable source
occurrence and prose. An explicit caller key remains replacement authority.
Transactions serialize each candidate identity through its write.

An event can carry an existing Source Library document, hash, and byte span.
The service validates access, scope, hash, and original bytes before it persists
the pointer. The extractor does not receive the caller-supplied pointer and
cannot invent one. The operation does not edit the original document.

Unknown graph validity remains unknown. Observation time is separate. Exact
canonical names and source-backed aliases can resolve an existing entity;
conflicting resolved identities fail instead of merging by approximate names.
Entity kind is an annotation. Pending predicates remain pending. Existing facts
retain their timestamps; this change does not guess old business-effective dates.
The repeatable table upgrade requires coordination with clients that previously
required a non-null validity start. Assess index rebuild locks separately before
production use.

The new extraction guidance is published as built-in profile `default` version
4. Existing version 3 records and pinned defaults remain unchanged. Existing
deployments must explicitly select version 4. This task does not deploy it.

The benchmark binary is frozen at
`5df4500ca70be177b631f49baa2d31fd6898a98b`.
A later source correction publishes the same guidance under version 4 instead
of overwriting or colliding with version 3. Between that binary and
`d532f98f8ce484e3111522ba2a3eca61769cb392`, the only runtime source change
is the built-in version constant. Prompt, schema, and extraction message-builder
hashes match. The retained benchmark profile references still say version 3;
they are not rewritten. Version 4 publication and preservation of version 3
pins pass the native integration suite. The exact boundary is recorded in
`profile-version-compatibility.json`.

## Matched protocol

The trial uses the same twenty original records, twenty questions, sixteen test
cases, and four development cases as the previous agent benchmark. Each question
runs with notes, notes plus source tools, notes plus graph tools, and both tool
sets. Twenty additional controls receive only the same initial twelve notes and
structured fields. The initial projection removes source provenance in every
condition. Source-enabled note reads later add quotes and pointers as well as
document tools, so their effect is not attributable to document reads alone.

All reader calls use DeepSeek V4.1 Flash on the official DeepSeek route with
maximum reasoning and an output allowance of 393,216 tokens. No smaller output
limit is imposed. Qwen3-Embedding-8B uses all 4,096 dimensions. Exact embedding
inputs reuse prior provider receipts. Native extraction is fresh, because the
changed extraction guidance and identity contract must be exercised. The trial
retains one model extraction per original, including validation failures that
were replayed after fixes without a new model sample.

The agent has the original twelve-response and twenty-four-tool ceilings.
Cached search expansion is now available in every primary condition. Compact
search responses keep diagnostic plans outside model context. The last response
has no tools and must answer from evidence already read. It is inside the
original budget, not a separate favorable finalization. Completed wrong answers
are retained. A provider connection loss on one development case resumed from
two complete tool batches; its partial third response and the rejected incomplete
resume are archived. Its full wall timer is unavailable and excluded.

The fixture is a known, small regression set. Candidate expansion can cover all
59 notes. One trajectory per condition, fresh extraction, prompt changes, and
agent changes do not isolate individual causal effects. No competitor is rerun.
The pinned Hindsight container supplies a local reranker only.

## Results

| Condition | Prior test facts | Current test facts | Current dev facts | Test cases with citation defects | Test unsupported absence assertions |
| --- | --- | --- | --- | --- | --- |
| Initial context only | 11/16 | 11/16 | 3/4 | 15/16 | 2 |
| Notes | 13/16 | 15/16 | 3/4 | 15/16 | 2 |
| Notes plus source | 15/16 | 16/16 | 4/4 | 12/16 | 0 |
| Notes plus graph | 11/16 | 15/16 | 4/4 | 16/16 | 2 |
| Notes, source, and graph | 13/16 | 16/16 | 4/4 | 11/16 | 0 |

The four primary conditions complete 80/80 cases, compared with 62/80 before.
There are no exhausted primary outcomes and no separate finalizations. All
20 no-tool controls also return valid final answers. The prior no-tool prompt
still asked for tool verification; the current final-response instruction
removes that ambiguity, so control-format gains are not a pure memory gain.

Factual scores use complete-answer review, not the unchanged literal substring
rule, which rejects correctly qualified historical values. Two primary test
answers fail: the notes answer for Larch recovery incorrectly excludes Larch
from the August 8 no-change records; the graph answer for Sable current state
adds an unsupported later reaffirmation of the August 22 decisions. One notes
development answer moves Cedar's original delivery choice to after the August
8 outage. Required identifiers alone would hide these failures.

The initial control lacks four required concrete identifiers in test and one
in development. It marks those details unknown. A further test answer inserts
a Sable incident into Reed's historical meeting context. Thus 11/16 test and
3/4 development controls pass complete-answer review. No completed factual
answer was replaced or resampled.

The same truth score can still conceal unsupported absence claims. The current
joint diagnostic requires factual correctness, no recorded citation defect,
and no unsupported absence assertion. It passes only 1/16 notes, 4/16 source,
0/16 graph, and 5/16 combined test answers. This deliberately conservative
current-only diagnostic is not a general product score or a comparison with
the old run. The per-answer evidence and review reasons remain inspectable.

| Condition | Test tool calls | Cases reading documents | Verified provenance follow | Graph object follow | Graph evidence-note follow | Median seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Notes | 236 | 0 | 0 | 0 | 0 | 58.3 |
| Notes plus source | 194 | 16 | 12 | 0 | 0 | 52.2 |
| Notes plus graph | 242 | 0 | 0 | 14 | 11 | 49.3 |
| Notes, source, and graph | 235 | 16 | 14 | 7 | 7 | 49.9 |

A provenance follow requires a prior note read, matching source identity and
hash, and a verified original excerpt containing the quote. A graph object
follow can reach an empty node; it does not prove useful multi-hop reasoning.
All structured citation identifiers and inline UUIDs were returned in evidence.
Their existence does not establish correct attribution.

## Integrity and remaining limitations

Twenty original documents retain exact bytes, hashes, and chunk offsets. All
59 notes retain verified source pointers: 75 pointers in total. Equal prose from
distinct records now remains distinct: one recovery directive has four separate
source occurrences, and one historical-state sentence has three. Canonical
vectors before and after the reader trial match: 59 note, 59 note-chunk, 256
field, and 20 document-chunk vectors, all at 4,096 dimensions.

The graph contains 60 facts, including 48 with unknown effective start. It no
longer converts omitted validity into ingestion time. Forty-two objects are
entity references and eighteen are literals. Exact alias handling reduces the
number of project topics split across multiple entities from four of five in
the prior fixture to two of five here. This is an observation across fresh
extractions, not an isolated alias-algorithm effect.

No topic has an outgoing project-to-recovery path within four edges, even when
all stored candidate facts and unknown-validity facts are included. More graph
facts therefore do not establish a useful relation chain. Source reads and note
search still carry the useful evidence in this trial.

Many answers contain citations from other synthetic topics. Generic extracted
sentences omit their subject, and broad retrieval exposes several such sentences.
The new identity rule preserves their provenance but cannot prove that the
reader selected the right source. All topics share one authorized ELF project;
this finding is not an access-control leak. Citation defects are recorded after
reading the answer to exclude legitimate, correctly attributed comparisons.
The counts are not a complete claim-level entailment score.

The absence questions expose another limit. Only Larch and Cobalt have a derived
negative budget-owner statement. Reed, Sable, and Cedar have that statement in
the original records, but extraction omits it. A reader can answer correctly by
copying another topic's negative. The fixture gives every topic the same negative
answer, so truth agreement can hide missing support. `absence-grounding.json`
checks whether the reader received a target-origin negative statement. It keeps
calibrated unknown separate from an unsupported claim that nobody was appointed.
This is a fixture-specific diagnostic, not a general natural-language validator.

The source adapter also rejected 41 calls that supplied both a chunk selector
and a byte-position selector. Its runtime contract requires exactly one, but
the model-facing schema exposes both optional fields without that constraint.
Agents recovered by choosing a selector, so all source-enabled cases eventually
read verified documents. This is avoidable tool friction, not a parser failure.
Four graph queries used undeclared surfaces and returned not found. These errors
remain in the traces and `tool-error-diagnostics.json`; the trial does not hide
them behind successful final answers. The next adapter iteration should make
selector alternatives explicit in its tool contract and repeat this protocol.

The next iteration should preserve subject and temporal anchors in compact
memory, bind each answer citation to its claim, and use source lookup when the
memory lacks decisive evidence. Evaluate graph utility with explicit evidence
on every required edge. Add an asymmetric held-out fixture with appointed and
unappointed owners, conflicting updates, and multilingual cases before tuning
these behaviors further. Do not substitute a storage change for these semantic
gaps.

## Cost, verification, and cleanup

This iteration adds **$1.778473** in confirmed provider charges. The unchanged
ledger totals **$4.067706**, including **$2.289233** before this iteration.
The older unsettled request reservation of **$0.569178** remains retained;
conservative cumulative exposure is **$4.636883**, below the **$10** ceiling.
No requests remain in flight.

The new ledger contains 474 chat attempts and 382 embedding requests. Chat
usage totals 10,027,106 input tokens, including 6,960,768 cached input tokens,
and 697,931 output tokens. The interrupted provider response reports zero billed
cost. Accounting uses actual `usage.cost`, not the provider's separate upstream
cost estimate. Cache hits and time-dependent prices confound causal dollar
comparisons. Local compute and CI are outside these API charges.

Local validation passes 457 Rust unit tests, 101 native integration tests,
171 benchmark Python tests, Clippy, Rust style, and TOML checks. The previous
benchmark's offline verifier also passes with the current analyzer. Final
bundle and documentation checks are recorded with the evidence.

A PostgreSQL custom-format backup was restored into a separate temporary
database. Eleven tables of originals, notes, canonical vectors, and graph data
matched before that restore database was removed. Raw results and the protected
24.5 MB dump remain outside the task worktree. Seven task-owned Docker containers, two volumes, one network, and four image
references were removed after this proof. Ten unrelated containers remain.
Exact IDs and image receipts are in `cleanup.json`.
Shared PostgreSQL/Qdrant base images and unrelated containers are preserved.
No global prune runs.

Recompute the frozen analysis without Docker, credentials, or model calls:

```sh
python3 config/benchmark/evidence/2026-10-12-evidence-integrity/verify.py
```

The verifier checks source workload identity, all primary and control cases,
provider-response identity and settings, extraction sample identity, tool bounds,
retained continuation, original slices, note pointers, canonical vectors,
hash-bound reviews, citation issues, absence support, and cumulative accounting.
The manifest covers the public evidence bundle. Semantic review was performed by
the Codex assistant and is not an independent blinded human judgment.

This is not an OCR, large-corpus, concurrency, authorization-isolation, or full
MCP-server acceptance test. Native API regressions and integration tests cover
separate contracts. End-to-end latency includes the model, tools, and shared
local compute; it is not a database benchmark. These results cannot rank ELF,
Hindsight, and RAGFlow under one comparable score.
