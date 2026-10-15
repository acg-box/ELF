---
type: Evidence
title: Native Agent capture and recall work without a measured handoff advantage
description: Verify source admission and the real MCP-to-HTTP memory chain, then compare frozen handoffs from the current repair.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-15
related:
  - docs/decisions/2026-10-15-agent-memory-loop.md
  - docs/reference/product-direction.md
  - docs/runbook/agent-evidence.md
code_refs:
  - packages/elf-domain/src/writegate/secrets.rs
  - scripts/benchmark_pilot/runner.py
  - scripts/benchmark_pilot/evidence.py
---
# Native Agent capture and recall work without a measured handoff advantage

The observed source rejection is fixed. Native MCP accepted the complete original
provider gateway file and all five other selected records. Exact-byte readback
passed; a literal credential was still rejected before a provider call. The
shared MCP instructions matched the HTTP reader contract byte for byte.

The capture-to-answer chain was exercised. The full-ELF calibration reader read
three notes and two linked originals, then cited both originals with valid native
bindings. All four formal full-ELF readers read memory; three cited an original
delivered through memory in their final answers. The fourth used a current-source
fallback after memory returned an older state. Do not force an irrelevant memory
citation merely to increase this measure.

Full ELF did not outperform indexed originals on the frozen handoff obligations.
It had the same coverage and complete-answer count, with higher reader cost.
The paid trial is closed. No saved answer, prompt, task, or oracle was replaced.

## Scope and controls

This is a narrow fresh-session comparison over the actual current repair. Six
records contain the previous assistant closure, the exact current user request,
the real provider gateway blob, an explicitly authored assistant work receipt,
and two checked-in integration documents. The host selected these records. It
did not automatically collect an external client's complete conversation.

The work receipt records the local-repair checkpoint before native acceptance.
Questions ask about that checkpoint, not the later state of this completed trial.
The old and new records remain distinct. Original message timestamps were not
available; the capture metadata says when capture time is used. This is not an
effective-time benchmark.

One calibration question and two formal handoff questions were frozen before
paid execution. Each formal question ran twice in each of three conditions.
Every reader started in a separate process and conversation. The same original
bytes, handoff record, model, workflow limits, and common citation checker were
available across conditions. File access includes the authored handoff; it is a
capable file-memory baseline, not a memory-free agent. The primary incremental
memory contrast is full ELF against indexed originals.

Capture used the shipped MCP server over Streamable HTTP. Fresh readers used the
existing HTTP reference host and shared contract v5. This verifies those native
paths; it does not install capture into Codex or Claude. The setup runbook now
uses HTTP registration instead of the incorrect stdio recipe, and distinguishes
the finite smoke loop from persistent interactive services.

The reader and extractor used `openai/gpt-6-luna` through the standard OpenAI
OpenRouter route, medium reasoning, and the full 128000 output-token allowance.
The [route metadata](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints)
was checked before execution. Embeddings used Qwen3-Embedding-8B through Nebius
at 4096 dimensions. Each reader had eight rounds, sixteen tool calls, 32768
serialized evidence bytes, and a 12000-byte per-result bound. MMR and the
240-character note limit stayed fixed.

## Formal results

Each question has six frozen obligations. Review includes the answer and its
checked claim chain. A complete answer must state every obligation and contain
no unsupported added claim. The rubric distinguishes explicit retained credential
rejection, original-to-event hash/span binding, the semantic limits of a valid
citation, and the recorded budget amounts. Regex coverage is not semantic review.

| Condition | Supported obligations | Complete answers | Mean reader time | Total reader cost, four cells |
| --- | ---: | ---: | ---: | ---: |
| Files plus the same handoff records | 19/24 | 0/4 | 29.23 s | $0.008447435 |
| Indexed originals | 21/24 | 1/4 | 57.75 s | $0.008620310 |
| Full ELF | 21/24 | 1/4 | 52.97 s | $0.011160790 |

All twelve formal answers passed native binding and returned-reference checks.
No formal answer treated the pending native acceptance or customer acceptance as
completed. Incomplete answers omitted a required detail; these counts do not mean
that all of their handoff judgments were wrong. They are not general product
scores. Against indexed originals, full ELF won one complete-answer pair, lost
one, and tied two. It did not meet the predeclared incremental-benefit threshold.

Full ELF's reader cost was about 29% higher than indexed originals. Its mean time
was about 8% lower, but it was about 81% slower than file access. These small,
sequential samples do not control provider latency, cache state, or shared-host
load. They do not establish a repeatable latency advantage.

Preparation cost was $0.000089200 for source indexing and $0.008923490 for memory
extraction/indexing. Their measured work times were 102.15 s and 307.77 s,
respectively. Add these preparation costs to the relevant reader condition before
claiming savings. Preparation was reused across the formal questions; it was not
free. Local compute, service startup, and Codex session usage are not priced by
the provider ledger.

## Located failures

**Admission loses a current update before retrieval.** The extractor proposed 26
notes. Seventeen were added, seven exceeded 240 characters, and two were ignored
by the normal policy threshold. The current work receipt produced three
candidates, but only its capture-contract note was admitted. The note stating
that source admission was repaired had 266 characters; the updated comparison
constraint had 261. Both were rejected. The source remained complete and readable.

In one formal full-ELF handoff, the opening returned the old "not yet fixed" note.
Expanding cached results exposed the surviving capture-contract note, but the
agent then used original search and cited only the current work receipt. This is
evidence for an extraction/admission gap and a useful source fallback. It is not
evidence that Qdrant failed to retrieve a stored repair note: that note never
entered the index.

**The reader can omit a condition it has seen.** Full ELF omitted the explicit
retained literal-credential rejection in both handoff repetitions and one
decision-update repetition. File and source controls also omitted obligations,
including document hash/span binding, the semantic limit of binding, or numeric
budget details. Adding another graph or store does not follow from these errors.

**Calibration use is not semantic acceptance.** The full-ELF calibration answer
treated the old $1.9531 exposure total as an additional unresolved reserve. That
amount was not misstated in the retrieved note text; the error arose while
interpreting the linked original. The source-only calibration also mislabeled
this amount. Full ELF additionally nested a serialized answer inside its text.
These failures remain recorded. The predeclared gate checks actual memory read,
original citation, and native binding; it does not certify answer meaning. The
formal inputs already included the exact settled, exposure, and reserve amounts
in the newer work receipt. No prompt was changed to repair calibration scores.

## Decision and limits

Keep the source fix, shared capture contract, corrected HTTP setup, actual-use
measurements, and formal-admission gate. Keep the current stores and API shape.
For a small maintenance handoff with a good current work record, file access
remains the practical default. This comparison does not establish coding-task
completion, multi-week autonomous capture, or customer readiness.

The next justified extraction change is to make candidates satisfy the existing
declared note bound while preserving the source-linked update. Do not infer that
raising the bound, changing MMR, or migrating stores is the solution. Any such
repair needs a bounded admission regression and separate new evidence; this trial
must remain unchanged.

## Cost and integrity

There were 128 new paid provider requests, all settled. They cost
**$0.042698750**, including capture/indexing, extraction, calibration, formal
queries, answers, and cache charges. Cumulative settled cost is **$1.925263591**.
The historical unresolved reservation is **$0.070484800**, so total conservative
exposure is **$1.995748391** against the unchanged $10 ceiling. Exposure already
includes settled cost; it is not an additional charge.

A private MCP startup probe initially failed to parse an empty SSE priming event.
This occurred before any provider request. Its receipt was kept, and parsing was
repaired before capture. No recorded reader conversation was repeated. The native
service and frozen reader implementation did not change during the comparison.

All six originals and the PostgreSQL state passed isolated restore checks.
Qdrant restored both collections at 4096 dimensions and passed stored-vector
queries. A lossless compressed archive was verified before task-owned containers
and volumes were removed. Original records, traces, rejected candidates, and
receipts remain private.

The [compact evidence bundle](../../../config/benchmark/evidence/2026-10-15-agent-memory-loop/manifest.json)
contains all new provider charges, interval accounting, de-identified cell
measurements, review counts, and native integrity metadata. Its standalone
verifier checks hashes, arithmetic, paired counts, and recorded restore evidence.
It cannot independently reproduce the private semantic review.
