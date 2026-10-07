---
type: Evidence
title: Repository memory repair pilot on 2026-10-07
description: Paired real-source repairs, native index readiness correction, format recovery, and complete API accounting.
status: historical
authority: informative
owner: benchmark
last_verified: 2026-10-07
tags: [benchmark, repository, memory, cost]
source_refs:
  - config/benchmark/evidence/2026-10-07-repository-replay/accounting.json
  - config/benchmark/evidence/2026-10-07-repository-replay/post-drain/results.json
  - config/benchmark/evidence/2026-10-07-repository-replay/usage.jsonl
code_refs:
  - scripts/benchmark_replay/agent.py
  - scripts/benchmark_replay/checker.py
  - apps/elf-eval/src/bin/real_world_live_adapter/service_runtime.rs
related:
  - docs/runbook/benchmarking/repository_memory_replay.md
  - docs/evidence/benchmarking/2026-10-07-bounded-calibration.md
---
# Repository memory repair pilot

This pilot tests actual edits to frozen repository files. It also found two
measurement problems: incomplete native indexing and immediate termination on
invalid model JSON. Both are corrected. The first 24 trials remain diagnostic
evidence. All four conditions were then rerun under one revised protocol; no
individual failures were selectively replaced.

## Scope

Three historical repairs cover chained receipt provenance, interrupted
subprocess cleanup, and a floating stable Rust container tag. Each condition has
two independent repetitions. The old versions fail the evaluator, and the known
historical repairs pass. The evaluator accepts both equivalent stable Docker tag
spellings and verifies bounded graceful subprocess exit. These checks were
frozen before the first repair trial.

The prior exploration packet contains selected source files, not a real user
conversation. Each condition receives the same task, target path, source tools,
six-turn cap, and maximum 12,000 recalled characters. The writable target file
and explicit request make these small tasks easier than open-ended repository
work. The reference patch is outside the model's source-tool allowlist.

The model is `deepseek/deepseek-v4.1-flash`, low reasoning, routed to DeepSeek
without fallback. The output cap is 8,192 tokens, including reasoning. Native
embeddings use `qwen/qwen3-embedding-8b`, 1,536 dimensions, routed to DeepInfra.
The no-memory condition still has source read/search tools. Git memory means
model-written Markdown committed to a Git repository, not the full Agent Memory
Repo product. Notes are generated independently for the two repetitions and
reused unchanged in the second protocol. There is no learning between repair
trials.

## Measurement corrections

The old native adapter invoked the worker exactly eight times after ingestion.
Each worker pass handles at most one item per queue. Each source packet becomes
37 notes through this adapter, so eight passes cannot establish readiness.
Initial cold retrieval returned context for only 1 of 6 episodes; warm retrieval
returned context for 2 of 6. These are adapter observations, not evidence that
ELF cannot retrieve indexed source.

The adapter now waits for the dedicated benchmark worker queues to reach `DONE`.
A failed job or a 180-second timeout produces an explicit adapter error. It does
not score a partly indexed corpus as settled retrieval. Production worker code
and search ranking are unchanged.

Direct PostgreSQL readback confirmed 222 of 222 note-index jobs in `DONE`, with
zero failed jobs. The corrected cold and warm phases each returned five contexts
for all six episodes. Nonempty retrieval is a readiness observation, not proof
that every returned chunk is useful. The final repair tests measure task success.
The run used base source `e4a49e08bc6f6f81174563c3f2681168d1b93721` plus the
recorded worker-drain patch. Its image digest is
`sha256:be03d81d10e480efa730630466f7b3730f98f3eff91d608efff1126891f920da`.
Initial image and runner fingerprints remain in the initial protocol artifact.

The first agent protocol ended model dialogue on invalid JSON in five trials.
Four of those failed the final repair check; one had already made a valid repair. The revised protocol records the raw response and billed usage, gives
format feedback, and consumes one of the existing six turns. It does not grant
extra turns or silently retry provider calls. A transport failure still ends the
trial. One initial no-memory case also exhausted its turn limit without a repair.

Initial diagnostic outcomes were no-memory 4/6, file search 5/6, Git memory 4/6,
and ELF 6/6. The old ELF condition had empty recall in four cases. Do not use
these outcomes as a memory-product ranking. The original artifacts and their
runner source hashes are retained beside the corrected run.

## Corrected paired results

| Condition | Passed | Total turns | Repair seconds | Repair chat USD | Invalid responses |
| --- | ---: | ---: | ---: | ---: | ---: |
| No memory | 5/6 | 32 | 109.307 | 0.011493624 | 1 |
| File search | 6/6 | 25 | 88.205 | 0.007959090 | 0 |
| Git memory | 6/6 | 28 | 83.017 | 0.007931652 | 3 |
| ELF note retrieval | 6/6 | 25 | 76.521 | 0.007423434 | 0 |

Result rows include final tests, each action, invalid responses, per-call usage,
recalled text, and the actual patch. A completion statement does not determine
success. Tests run in a read-only, network-disabled Docker container without
provider credentials. Final verification also runs when the agent exhausts its
turns.

The remaining no-memory failure is the second receipt-origin repetition. The
agent read more surrounding modules, produced one invalid response, invoked a
failing test, and exhausted six turns without an edit. All memory conditions
passed that case. Git memory recovered from three invalid responses across its
trials, without extra turns. These are observed execution differences, not a
statistically established memory advantage.

ELF and file search both passed 6/6 and used 25 total turns. The small elapsed-time
and repair-cost differences do not establish a reliable ranking. Git learning
added $0.009180660 for the six successful note writers, plus $0.001668750 for the
failed attempt. ELF native preparation added $0.000248200 and 428.820 seconds.
The table excludes those setup costs; the ledger includes them. A file baseline
has no provider-backed setup in this protocol. This pilot does not establish
that ELF delivers more repair value than simple source-file recall.

## Cost and timing

Total cumulative API spend is **$0.094396915**, about **9.44 US
cents**, against the authorized **$10** ceiling. This pilot added
**$0.077748104** to the earlier **$0.016648811** calibration.

| This pilot, both protocols and setup | Value |
| --- | ---: |
| Accounted provider requests | 955 |
| Chat requests | 217 |
| Chat input tokens, including cached input | 556,834 |
| Cached chat input tokens | 439,168 |
| Chat output tokens, including reasoning | 97,299 |
| Reasoning tokens within output | 70,675 |
| Embedding requests | 738 |
| Embedding input tokens | 40,130 |
| Unsettled request costs | 0 |
| Retained cumulative admission reservations, not billed spend | $4.460053336 |

Cached input is charged at the provider's returned cost, not at the uncached
input rate. About 79% of this pilot's chat input tokens were cache hits. The
ledger retains prompt, cached input, output/reasoning, and upstream cost details.
Across this pilot and the earlier calibration, 1,348 provider requests are
accounted for. No paid consumer or run-owned test container remains active.

Costs include the failed 2,048-token learning request, six successful note
writers, both native preparations, all 48 repair trials, cached input, and
reasoning output. The failed learner used its entire output budget for reasoning
and produced no content. Its subsequent invocation used the declared 8,192 cap.
No failed request was removed from accounting.

The gateway retained a conservative reservation before each request. It enforced
$0.50 of new reservations per invocation and a $10 cumulative ceiling. Retained
reservations are not the provider bill. The upstream key stayed in the gateway;
test containers received no credentials. This local control is not an
account-wide spending limit. Local compute, image downloads, Codex usage, and CI
are excluded from provider API cost.

Initial native preparation took 197.731 seconds and made 282 embedding calls.
Correct preparation took 428.820 seconds and made 456 embedding calls, costing
$0.0002482. The sum of gateway embedding-request durations was 392.721 seconds.
Remote request time dominates this small preparation. The increase includes the
previously omitted indexing work and provider latency variation; it is not a
search-ranking performance regression.

For fast iteration, run offline contracts first and reuse a frozen prepared run
when only the agent protocol changes. Remeasure native ingestion when its source,
configuration, or corpus changes. Batch or reuse identical embeddings in a future
adapter improvement, with a declared cache boundary. Do not recover speed by
scoring unfinished indexes.

The [accounting artifact](../../../config/benchmark/evidence/2026-10-07-repository-replay/accounting.json)
separates every phase. The [request ledger](../../../config/benchmark/evidence/2026-10-07-repository-replay/usage.jsonl)
contains this pilot's incremental calls. Add the prior calibration total only
once. The native cleanup receipts confirm removal of run-owned containers,
volumes, and networks.

## Limits and next decision

Three task families with two repeats cannot establish a stable product ranking.
The same frozen cases were visible in the diagnostic run before protocol repair;
the second run is a calibration, not an untouched held-out evaluation. Do not
report confidence intervals that treat six repeats as six independent task types.

File search returns whole source items. This ELF adapter normalizes whitespace,
splits notes at 220 characters, and retrieves five chunks. Both have the same
maximum context allowance, but the actual text and usable code structure differ.
This tests that native note-ingestion path, not all ELF document or knowledge
features. No LLM extraction, graph traversal, longitudinal memory maintenance,
or other competitor's full agent system was measured.

Use the harness as a fast repair regression and cost calibration. The next
product comparison needs tasks that require prior decisions or changed source
knowledge, larger competing corpora, and independent unseen task families.
Add native competitors only after their indexing-readiness boundary is explicit.
Do not add more memory architecture based on these small task scores.
