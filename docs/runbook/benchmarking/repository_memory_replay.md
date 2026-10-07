---
type: Runbook
title: Bounded repository memory replay
description: Run paired repair trials against historical ELF source with four memory conditions and isolated behavioral checks.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-07
code_refs:
  - scripts/benchmark_replay/cli.py
  - scripts/benchmark_replay/agent.py
  - scripts/benchmark_replay/memory.py
  - scripts/benchmark_replay/checker.py
related:
  - docs/runbook/benchmarking/benchmark_modes.md
---
# Bounded repository memory replay

Use this pilot to measure whether recalled source knowledge helps a bounded
agent repair actual repository files. It extends the existing Python benchmark
owner. It does not run the full development agent or rank complete memory products.

## Inputs and conditions

The runner freezes three historical defects: chained receipt provenance,
subprocess interruption cleanup, and the Rust container channel. Each condition
has two independent repetitions, for 24 trials. Each trial starts with the same
source snapshot and task text. The reference patch stays outside the agent's
source allowlist. Before paid trials, the evaluator must reject each old version
and accept each historical repair.

The prior exploration packet contains selected source files from the old
revision. It is a controlled source packet, not a recovered human conversation.
The conditions are:

- `no-memory`: no recalled context; source tools remain available.
- `files-search`: literal token overlap ranks the source packet and returns up to
  five items.
- `git-memory`: the shared model writes and commits a short `MEMORY.md` and method
  notes from the packet. Each repetition gets independent notes. This is a file
  memory baseline, not Cognition's complete Agent Memory Repo system.
- `elf`: the native adapter ingests the same packet and returns warm retrieval
  contexts. Automatic LLM memory extraction is not enabled.

Recall is capped at 12,000 characters in every condition. Each repair has six
model turns. The agent can read or search listed files, replace exact text in the
single target file, invoke tests, or finish. It cannot use a shell, install
packages, or access the evaluator's reference files through these tools. Test
code runs in a network-disabled, read-only Docker container without credentials.
The final test runs regardless of the model's completion claim.

The small tasks and explicit target path make this a sensitivity pilot. They do
not measure large-repository discovery, cross-session user preferences, ordered
updates, conflicting authority, longitudinal learning, or full agent autonomy.
Repeats are not six independent task families. Use paired case results before
aggregate percentages.

## Execution

Run from the repository root. Reuse the host's supported Python, Git, Docker,
and cargo-make. The historical commits must be available locally. The current
pilot uses `elf-benchmark-elf:replay-drain` by default. `BENCHMARK_ELF_IMAGE`
can select another built image for both native retrieval and isolated checks.
Build the repository's `docker/benchmark/Dockerfile`, target `elf-runtime`, from
the intended source before use. Record the image digest and source provenance.
Do not infer that a cached image matches current Rust source.

The native adapter waits for its dedicated benchmark worker queues to drain.
A failed job or a 180-second drain timeout aborts the adapter. The previous
fixed eight-pass loop was insufficient for source packets with more than eight
notes; its results must not be treated as settled retrieval.

```sh
cargo make benchmark-repository-memory prepare --out /absolute/run-directory
cargo make benchmark-repository-memory validate --out /absolute/run-directory
```

For paid phases, inject `LITELLM_BASE_URL` and `LITELLM_API_KEY` into the consumer
through an authorized provider or budget gateway. Native ELF embedding setup
uses the existing benchmark provider environment. Keep upstream credentials out
of logs, fixtures, and test containers.

```sh
cargo make benchmark-repository-memory learn --out /absolute/run-directory
cargo make benchmark-repository-memory retrieve --out /absolute/run-directory
cargo make benchmark-repository-memory run --out /absolute/run-directory --arm no-memory --repeat 1
cargo make benchmark-repository-memory report --out /absolute/run-directory
```

Run all four arms for repetition 1, then reverse their order for repetition 2.
The runner refuses to replace existing trial directories. It does not implement
phase recovery: retain a partial run and its costs if preparation or learning
fails. Do not silently overwrite measured trials or rerun failures until they
pass. A report requires 24 trial results.

The shared chat model is `deepseek/deepseek-v4.1-flash`, low reasoning, with an
8,192 output-token cap. Native embeddings use `qwen/qwen3-embedding-8b`, 1,536
dimensions. This command does not enforce an account-wide spend limit. The
2026-10-07 run used a separate local gateway with a $10 cumulative ceiling,
$0.50 admission allowance per invocation, and provider price ceilings. Use an
equivalent budget control before a paid run. Keep phases sequential when they
share a ledger without locking.

## Evidence and interpretation

Retain source revisions and hashes, image digest, protocol, prior source packets,
generated notes, retrieved contexts, per-turn actions and usage, final tests,
setup costs, failed requests, cleanup receipts, and the complete request ledger.
Separate learning and native ingestion costs from repair-chat costs. Include
cache hits and reasoning output in accounting. Local compute and CI are outside
provider API cost.

An invalid JSON action or truncated model response consumes a turn. The runner
records the response and usage, gives format feedback, and continues within the
same six-turn cap. Transport failures end a trial. None of these failures proves
a memory retrieval defect. A
patch that passes after the final turn is still a passing repair even if the
agent did not emit `finish`; preserve the separate termination classification.
Wall time includes model and local test time but excludes setup from each repair
row. Do not infer product latency from totals with different setup boundaries.
