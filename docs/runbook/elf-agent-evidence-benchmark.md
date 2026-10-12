---
type: Runbook
title: ELF agent source and graph benchmark
description: Measure bounded evidence retrieval, source provenance, graph traversal, and final answers over fixed source workloads.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-12
code_refs:
  - scripts/benchmark-elf-agent.py
  - scripts/benchmark_agent/runner.py
  - scripts/benchmark_agent/tools.py
  - scripts/benchmark_agent/replay.py
related:
  - docs/evidence/benchmarking/2026-10-11-agent-evidence.md
  - docs/decisions/2026-10-12-evidence-integrity.md
---
# ELF agent source and graph benchmark

## Contract

The four primary conditions share the same twelve initial derived notes and
structured fields. All can search/read notes and expand cached search sessions.
`source` adds original-document search and verified excerpts. `graph` adds
outgoing graph queries and object/evidence-note traversal. `both` adds both.
Initial contexts omit `source_ref`; a source-enabled agent must read a note to
obtain provenance. Source-disabled conditions remove the complete provenance
envelope. This is an ablation, not the normal full ELF response.

Twenty fixed memory questions contain sixteen test and four development cases.
The later `initial` control receives the same initial notes without tools. Never
combine this fixture's score with a different competitor protocol as a product
ranking. Record factual correctness, citation attribution, source integrity,
actual tool usage, and cost separately.

## Prepare and run

Use the repository ELF runtime Docker target. Record the exact source revision
and image digest. The shared runtime owns the `elf-matched` namespace; do not
reuse another active experiment's containers.

```sh
docker build --target elf-service-runtime --build-arg ELF_SOURCE_COMMIT="$(git rev-parse HEAD)" -t elf-evidence-integrity:current -f docker/benchmark/Dockerfile .
```

Set `ROOT` to a new absolute artifact directory. Run the following commands as
consumers of `cargo make benchmark-budget`, with the authorized cumulative
ledger and dollar cap. Inject provider credentials only into that gateway. It
supplies ephemeral `LITELLM_BASE_URL` and `LITELLM_API_KEY` values to consumers.

```sh
cargo make benchmark-elf-agent --root "$ROOT" --image elf-evidence-integrity:current --phase prepare --live-extraction --reuse-receipts config/benchmark/evidence/2026-10-11-agent-evidence/provider-receipts.jsonl.gz --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --image elf-evidence-integrity:current --phase run --live-extraction --reuse-receipts config/benchmark/evidence/2026-10-11-agent-evidence/provider-receipts.jsonl.gz --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --phase control --output-maximum 393216
```

The recorded official DeepSeek route supports 393,216 output tokens. Verify
endpoint allowance and prices before a new run. Keep the provider, reasoning,
output allowance, and input workload fixed across conditions. Use gateway
`--request-max-bytes 1048576` for multi-turn histories. This permits a larger
transport envelope while retaining full input/output monetary reservations.
Never truncate evidence to fit a smaller envelope or clear unknown charges.

`--live-extraction` uses the current native schema and extraction guidance. It
archives original source documents, passes verified document/span pointers to
event ingestion, and retains each extraction receipt. The model cannot assign
the source pointer. This is necessary when evaluating changes to extraction.
Without the flag, the replay proxy requires an exact match with a prior
extraction request; it refuses to substitute an old output for changed messages
or prompts. Use a compatible runtime for historical frozen-extraction trials.

`--reuse-receipts` imports only exact Qwen3-Embedding-8B inputs at the full 4,096
dimensions. It does not import old reader answers or tool outputs. Changed note
text and new queries can request new embeddings through the gateway. Record
fresh extraction and changed derived state as experiment factors.

The pinned sidecar supplies a local reranker. Its image packaging is not a
competitor rerun. The raw artifact directory retains complete native initial
responses and tool traces; model-facing note-search results omit internal
ranking diagnostics while preserving returned evidence and search IDs.

## Bounded agent policy

Each agent has at most twelve model responses and twenty-four tool calls. The
`bounded-v2` policy reserves the final response inside that original allowance.
When tool capacity ends, it closes unexecuted tool calls with explicit errors
and requests a final answer using only prior evidence. It does not increase the
budget, provide oracle facts, or retry a wrong answer. Invalid output remains a
failed outcome.

The prompt tells the agent to expand an existing search before repeating a
query, follow a supplied source pointer, distinguish unknown validity from
current truth, and stop after the requested facts have sufficient evidence.
It explicitly states that unavailable tools cannot be invented. Record this
policy alongside native changes; a combined improvement is not causal evidence
for one individual patch.

The older evidence bundle used post-run `finalize` and selected `paged` phases.
Keep those historical results separate. The current primary conditions already
include cached expansion and bounded finalization. The legacy phase commands
remain diagnostic utilities, not required additions to the current score.

Every provider response and completed tool call is saved before the next step.
A restart skips completed cases. If a transport failure interrupts a complete
tool batch, archive the failure and explicitly use
`--resume-case CONDITION/CASE_ID`. Do not repurchase completed calls or overwrite
a recorded final answer. Lost wall timers remain unavailable. A single fenced
JSON answer can be recovered from its saved response, with formatting failure
recorded. A pending control response requires offline recovery before restart.

## Inspect and publish

Run analysis without credentials or Docker:

```sh
cargo make benchmark-elf-agent --root "$ROOT" --phase analyze
```

Review full answers against original sources and bind reviews to answer hashes.
Keep raw strict scores. Explicit historical comparisons and known absence must
not be mistaken for wrong current states. Conversely, required keywords alone
do not excuse a wrong subject or unsupported explanation. Audit citation
identity and claim support independently of factual-answer scores.

A graph follow can reach an empty node. A returned fact must have readable
supporting evidence; unknown temporal status is not established current truth.
The benchmark uses selected REST operations, not every MCP, Context Pack,
knowledge-page, or entity-memory interface.

Preserve original bytes, offsets/hashes, extraction receipts, graph snapshots,
initial contexts, answers, reviews, and usage. Exclude private runtime config
and credentials from public bundles. Verify the public evidence offline. After
collection, remove only this task's owned Docker resources and preserve raw
results needed for review or later matched trials.
