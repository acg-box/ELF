---
type: HowTo
title: Run the real-project memory pilot
description: Compare ordinary source access, source retrieval, and native ELF memory on frozen project history.
status: active
authority: normative
owner: benchmark
last_verified: 2026-10-13
---
# Run the real-project memory pilot

This trial measures project handoff and decision updates. It uses real private Git
records and new retrospective questions. It is not a replay of natural user
sessions or a substitute for a multi-week customer pilot.

## Frozen experiment

The run directory’s private `fixture/` contains fourteen complete original records,
four chronological checkpoints, two calibration tasks, and eight formal tasks.
The formal tasks have two repetitions in each of three conditions: 48 cells.
The selected source corpus is bounded; it is not the entire repository. The
tasks require read-only handoff decisions, not code patches or live deployment.
The host retains `oracle.json`. The reader receives only its question, checkpoint,
source catalog, declared tool schemas, and tool responses. No previous answer
becomes a new memory. Every reader is a separate process and conversation.

| Condition | Available evidence |
| --- | --- |
| `no_elf` | Original Git records through bounded file read and grep tools |
| `source_only` | The same file tools plus native ELF document retrieval |
| `full_elf` | The same sources plus native extracted notes, evidence packs, and graph navigation |

All conditions receive identical source bytes. The primary memory comparison is
`full_elf` versus `source_only`. Condition order rotates. Sources enter the store
only at their checkpoint. Calibration uses only checkpoint zero, so it cannot
introduce future evidence before formal execution.

Sources are saved unchanged. Extraction uses contiguous line windows of at most
6000 bytes, with no answer-specific selection or hand-written summaries. Native
event ingestion receives a document ID, full content hash, and exact byte span.
Every stage verifies stored originals against the archive, waits for all native
indexing jobs to reach `DONE`, and checks that every vector has 4096 dimensions.
The API and worker stop between calibration and formal execution, while the
native stores persist. This proves restart continuity within the test scope.

Use the shipped API and worker, PostgreSQL, Qdrant, Qwen3-Embedding-8B at 4096
dimensions, and the standard OpenAI GPT-6 Luna route with medium reasoning.
Both retrieval arms use
the same built-in `local-token-overlap` reranker. This inexpensive reranker is a
declared limitation; the trial does not establish the best achievable neural
reranking result. The native memory and ranking defaults remain unchanged.

Each cell permits eight model rounds, sixteen tool calls, and 32768 serialized
tool-response bytes. One response may contain at most 12000 bytes. Truncation
removes complete tail records and is recorded. The output token limit is the
provider maximum of 128000; the host does not reduce it to save money. The shared
Agent evidence contract applies to all conditions. The host checks final claims
with the native checker and separately verifies that references were actually
returned to that reader.

## Execution

Build with `cargo make build-harness` and run
`cargo make test-benchmark-runner-contract`. Place the previously verified GPT-2
`tokenizer.json` in the run directory. Its required SHA-256 is
`8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6`.
The runtime requires existing Docker images `pgvector/pgvector:pg18` and
`qdrant/qdrant:v1.18.0`. It uses loopback ports, task-owned labels, and private
configuration. No secret belongs in the fixture or result bundle.

Start secret discovery in Personal Infisical. Inject the chosen key only into
`cargo make benchmark-budget`. Select Nebius, 4096 dimensions, maximum output,
medium reasoning, one simultaneous provider request, a $10 total ceiling, and
a $1 calibration tranche. Obtain fresh endpoint prices before this operation.
The gateway's enforced price bounds must cover the execution time window.
Set `--chat-model openai/gpt-6-luna --chat-provider openai`,
`--chat-max-tokens 128000 --force-chat-max-tokens --reasoning-effort medium`,
`--omit-chat-temperature --chat-prompt-price 0.1 --chat-completion-price 0.5`,
and `--request-max-bytes 196608`. These are the recorded short-context standard
prices, not a standing price guarantee. The byte bound also keeps these text
requests below the model's 272000-token long-context pricing threshold.

The gateway consumer is:

```sh
cargo make benchmark-project-pilot --root RUN_DIRECTORY --phase calibration
```

Inspect all six calibration cells and all preparation receipts. If the protocol
works, admit the formal phase under the same ledger and $10 ceiling:

```sh
cargo make benchmark-project-pilot --root RUN_DIRECTORY --phase formal
cargo make benchmark-project-pilot --root RUN_DIRECTORY --phase report
```

Never repeat an existing cell or unresolved extraction attempt. The native
extractor can make up to three JSON parse attempts; all are recorded and charged.
Preserve invalid
answers, provider failures, and their costs. A budget stop yields partial results,
not a product ranking. Recorded stage markers permit continuation at the next
unrun stage without reading future records at an earlier checkpoint.

## Evaluation and cleanup

The report separates frozen text-pattern coverage, native citation binding, and
explicit source-based semantic review. Pattern matches are not correctness. The
review must inspect every required obligation and additional claim, including
stale advice, wrong scope, and unsupported deployment or deletion assertions.
Assistant review is not an independent or blinded judge.

Report cell latency, calls, prompt/completion tokens, and provider-settled cost.
Include source indexing and memory preparation, with amortized costs at 1, 5,
and 20 tasks. Cached usage is already included in settled cost; do not subtract
a second discount. Paid preparation and failed calls count toward the new budget.
The previous experiment ledger remains intact and is outside this trial.
The interrupted maximum-reasoning preparation in this trial is exploratory cost.
Keep it in the shared ledger and report it separately from the daily comparison.

Before cleanup, preserve the raw corpus, provider receipts, traces, semantic
reviews, native state, and a database backup. Prove restore and source equality.
Then remove only this trial's stopped processes, containers, volumes, and managed
worktree after delivery. Do not prune unrelated Docker or Git resources.

Private originals, task questions, oracles, traces, and provider receipts stay in the local run directory. A public pull request contains only the reusable harness, de-identified measurements, and content hashes. Do not commit or push the private fixture archive.
