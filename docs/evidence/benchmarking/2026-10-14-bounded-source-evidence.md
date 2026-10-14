---
type: Evidence
title: Bounded original reads and decision coverage
description: Measure budget-aware original access and explicit decision qualifiers on the unchanged four-arm project replay.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-14
code_refs:
  - packages/elf-service/src/docs/service/excerpt_get.rs
  - scripts/benchmark_pilot/tools.py
  - config/agent/evidence-reader.md
  - config/benchmark/evidence/2026-10-14-bounded-source-evidence/verify.py
related:
  - docs/decisions/2026-10-14-bounded-source-evidence.md
  - docs/runbook/agent-evidence.md
  - docs/evidence/benchmarking/2026-10-14-agent-evidence-use.md
---
# Bounded original reads and decision coverage

The native excerpt route now accepts a positive byte cap and returns an exact,
verified original window within that cap. Full ELF lost evidence budget in four
of sixteen answers, down from eight, and its measured answer cost fell about
15%. Its required coverage changed from 45/64 to 46/64, while complete acceptance
fell from 5/16 to 3/16. This trial does not establish a reliable improvement in
subject, time, or condition coverage. Full ELF did not exceed ordinary file
access in this run.

## Frozen results

All 64 formal and eight calibration cells completed. No provider, transport,
harness, final JSON-envelope, or citation-binding failure occurred. All final
references were inspected. No answer was replaced or retried to improve a score.
MMR remained enabled and the note limit remained 240 characters.

Each answer has four composite obligations. All required parts must be present.
Complete acceptance also requires supported material claims and usable output.
Coverage is not factual accuracy. Reviews are source-based assistant judgments,
not independent or blinded evaluations. The same strict rubric and semantic
equivalence rules were retained, including its requirements for exact identifiers,
conjunctions, and current manifest checks.

Arrows compare the preceding default-configuration trial with this run. Median
time and mean cost describe the new run only; they exclude reused preparation.

| Condition | Required coverage, prior → current | Complete acceptance, prior → current | Median answer time | Mean answer cost | Cells with budget loss, prior → current |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary files | 38 → 49/64 | 4 → 5/16 | 38.2 s | $0.002590 | 9 → 9/16 |
| Source retrieval | 38 → 44/64 | 4 → 5/16 | 50.3 s | $0.002735 | 8 → 2/16 |
| Full ELF | 45 → 46/64 | 5 → 3/16 | 40.7 s | $0.003064 | 8 → 4/16 |
| Supplied originals (diagnostic) | 52 → 52/64 | 5 → 6/16 | 11.1 s | $0.000884 | 0 → 0/16 |

Full ELF won two, tied ten, and lost four paired cells against files, for three
fewer obligations overall. Its median answer time was 40.7 seconds versus 38.2
for files, and its mean answer cost was about 18% higher. Source retrieval gained
six obligations, but its median time rose from 40.5 to 50.3 seconds. These small,
retrospective samples do not establish a general speed or quality ranking.

All arms use the same native citation checker. The file arm has no memory/index
opening but can read the same immutable originals. Native arms also retain file
fallback tools. Thus the comparison measures the incremental value of discovery
and memory, not the entire value of ELF provenance. Supplied originals are a
diagnostic with preselected source bytes, no oracle or composed answer, and no
measured source-selection cost; this is not a deployable arm or an absolute
model ceiling.

Each entry below shows two repetition scores, each out of four. A four can still
fail acceptance if another material claim or configuration example is invalid.

| Task category | Files | Sources | Full ELF | Supplied originals |
| --- | --- | --- | --- | --- |
| Capacity handoff | 3, 4 | 4, 0 | 4, 4 | 4, 4 |
| Interrupted recovery | 4, 4 | 4, 3 | 3, 3 | 4, 3 |
| Acceptance boundaries | 4, 3 | 4, 3 | 3, 3 | 3, 3 |
| Rollback handoff | 4, 3 | 4, 4 | 4, 4 | 4, 4 |
| Validation and cache policy | 2, 2 | 3, 2 | 2, 2 | 3, 1 |
| Release evidence | 3, 2 | 3, 3 | 1, 2 | 3, 3 |
| Retired ownership | 3, 3 | 3, 2 | 3, 3 | 3, 3 |
| Retired product boundaries | 3, 2 | 1, 1 | 3, 2 | 3, 4 |

## What changed and what was proved

HTTP and MCP expose the existing native window bound as optional `max_bytes`.
It counts original UTF-8 bytes and is clamped to the selected L0/L1/L2 limit.
Omitting it retains the prior level behavior. A narrow position selector alone
still does not define a small window. Returned offsets, hashes, and references
identify the actual window. Empty windows below a complete UTF-8 character have
no verified reference. Source records remain unchanged.

The reference HTTP host requests a window within its remaining budget and keeps
full native read receipts outside the model view. It does not clip a body while
retaining a wider reference. Discovery results omit repeated pointer metadata.
Cached expansion returns new candidates plus already delivered IDs. Exact
original bodies already delivered in that conversation are suppressed, while
their handles remain usable. Dropped, unseen items are not suppressed. Native
access checks still run; there is no cross-user cache or new persistent state.

The trace audit checked 931 delivered original bodies and 40 native bounded
reads across calibration and formal cells. Every body matched its unchanged
original bytes, and every native read respected its requested cap. The host
suppressed 265 repeated bodies, including 235 in the formal file arm. Full ELF
had no exact repeated body in its formal cells; overlapping windows can still
repeat bytes under different references. The full-ELF cost change therefore does
not establish a gain from exact-body suppression. No native read needed the conservative second
read for JSON-escape expansion, which has a separate contract test.

No formal `elf_docs_excerpts_get` call failed for exceeding the common result
budget. The remaining budget-loss events came from broad file-search and
file-read fallback after the shared budget was nearly spent. Some retries still
tried to read when even one complete line could not fit. Budget loss counts use
the prior definition: a budget error or an empty truncated result. A nonempty,
partially trimmed result is not included in that count.

Full ELF's mean charged evidence bytes fell from 24292 to 20875 per answer.
Its answer cost fell from $0.057961295 to $0.049025205 for sixteen cells. Mean
original payload size, answer cost, and latency have different causes; these
numbers do not isolate the effect of each bundled change.

The final submission already performs the native binding check. The shared
contract now uses a separate intermediate check only for an uncertain binding.
Full ELF used one such check, down from seven cells; supplied originals used
none, down from sixteen. The shared contract also asks the reader to retain each
subject, applicable time, prerequisite, conjunction, and exclusion. Its measured
semantic effect remains unproved. MCP publishes that contract and the byte-cap
schema; other Agent hosts must implement the documented client lifecycle.

## Remaining failure boundaries

| Boundary | Observed failure | Implication |
| --- | --- | --- |
| Original selection | One source-only repeat read recovery material but did not establish the requested capacity rules. Four full-ELF cells still lost budget in file fallback. | A narrower, explicit source/version selection is the next useful control before more broad searches. |
| Conditions after reading | Answers omitted a positive runner-ID predicate, a sampling cadence, cache ownership, or the unchanged-running-image qualification. | A valid citation and a broad correct conclusion do not establish complete coverage. More prompt wording alone did not solve this. |
| Effective time | Two full-ELF answers presented a retired recovery workflow as a current workflow after the hosted cutover. | Access to authentic historical text is insufficient for current-state reasoning. Preserve history and require a current-source connection. |
| Subject and authority | File/source and supplied-original answers sometimes applied the old project's Staging or delivery requirements to a separate replacement. | Do not transfer procedures across owners without evidence that they apply. |
| Output fidelity | One full-ELF answer met the semantic obligations but corrupted a copyable label-array example with a control character and extra brackets. | Valid final JSON and citation bindings do not establish that embedded configuration is usable. This cell failed complete acceptance. |
| Inspection completeness | Every retirement-ownership answer omitted some part of the current Cargo/Makefile removal check. Complete manifests were available, including in the supplied-original arm. | This was an unperformed check, not an unavailable-source or missing-test excuse. |

Reviews flagged a material issue beyond omission in one file cell, one source
cell, three full-ELF cells, and two supplied-original cells. These are manual
review classifications, not independent model-error probabilities. The supplied
originals still met only 52/64 obligations, the same aggregate as before. Do not
attribute all missing details to extraction or retrieval.

Extraction was deliberately held fixed, so this run does not test a better
extractor. All 32 earlier extraction outputs produced the same 79 proposals and
140 verbatim evidence quotes. Admission remained 45 notes, with 33 character-limit
rejects and one quote-count reject. The normalized proposal digest remained
`1575bf6ce058343a0e3e9604cb7c0a6f814379abbb4ab130e6d2bbb09057e96a`.
There is no evidence here to change MMR, the note limit, PostgreSQL, or Qdrant.

## Cost and delivery evidence

The existing reset-budget ceiling remains $10. This run added **$0.157536450**:
$0.009176005 for calibration and $0.148360445 for formal answers and their query
embeddings. Replayed preparation added no provider charge; this is not a
cold-start preparation estimate. The ledger retains all earlier work and failed
or uncertain calls. Cached reads and writes are already included in settled cost.

| Budget component | USD |
| --- | ---: |
| Earlier reset-budget settled cost | $1.117343081 |
| New calibration and formal work | $0.157536450 |
| Cumulative settled cost | $1.274879531 |
| Conservative cumulative exposure | $1.345364331 |

The last two rows are totals, not additional charges. The historical uncertain
request retains its $0.0704848 reservation. The closed ledger has 2477 requests,
393 added in this run. No new request remained unsettled. The replay cache served
32 extraction and 75 embedding requests; 68 unmatched embedding requests went
through the budget gateway. Reused requests are not new provider invocations.

The corpus, questions, rubric, chronology, and exact-source selections have the
same hashes as the prior primary run. The 14 originals contain 137723 bytes and
span four checkpoints. The model remains OpenRouter `openai/gpt-6-luna`, standard
OpenAI provider, medium reasoning, with its full 128000 output-token allowance.
Provider metadata was checked before execution through the
[OpenRouter endpoint API](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints).
Embeddings remain Qwen3-Embedding-8B through Nebius at 4096 dimensions. The shared
budgets remain eight model rounds, sixteen tool calls, 32768 evidence bytes, and
12000 bytes per result. No ranking or prompt change followed formal start.

Reader and native changes were frozen at
`3fb405b830547786a403e13928d7049344b64d46` for calibration and formal execution.
Later changes affect reporting/export only. Validation passed `cargo make check`
(473 Rust tests, 209 benchmark contracts, and tooling checks), the harness build,
and 108 Docker integration tests. Exact-head delivery checks are recorded on the
pull request; these are not a customer or production acceptance claim.

An isolated PostgreSQL/Qdrant restoration preserved all 14 original hashes and
row counts. Stored-vector queries passed for 29 document points and 45 memory
points, both at 4096 dimensions. The 6199058-byte compressed snapshot passed
lossless hash verification. Private originals, prompts, answers, traces, and
provider receipts remain outside the public bundle.

The [evidence bundle](../../../config/benchmark/evidence/2026-10-14-bounded-source-evidence/manifest.json)
contains de-identified cells, protocol, native limits, read-audit counts, budget
records, code/binary hashes, and restoration metadata. Its verifier checks
integrity, chronology, dimensions, arithmetic, and recorded restoration. It
cannot independently reproduce the private semantic judgments.

```sh
python3 config/benchmark/evidence/2026-10-14-bounded-source-evidence/verify.py
```
