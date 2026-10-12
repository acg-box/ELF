---
type: Runbook
title: ELF agent source and graph benchmark
description: Measure iterative recall, source provenance, and graph traversal over frozen memory extraction.
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
  - docs/runbook/retrieval-laboratory.md
---
# ELF agent source and graph benchmark

## Scope

Use this experiment to separate answer quality from tool availability. The four
primary conditions use the same initial twelve derived notes, including their
structured fields. All conditions can search and read notes. `source` adds
original-document search and verified excerpts. `graph` adds outgoing graph
queries and evidence-note traversal. `both` adds both sets of tools. Initial
notes do not include provenance quotes. A source-enabled agent must read a note
to obtain its provenance.

The later `initial` control receives the same prompt and initial notes with no
tools. It helps distinguish richer initial context from iterative retrieval.
Keep this control separate from the rotated four-condition experiment. The
shared prompt still asks for verification when tools exist. Record invented
textual tool calls or invalid JSON as failed control outputs; do not resample
them. This prompt interaction limits attribution to retrieval alone.

The workload has twenty memory questions. Sixteen belong to the test split;
four belong to the development split. This is a small diagnostic fixture, not
a product ranking or a document-parser benchmark. Do not combine its score with
older competitor runs as if all systems were tested under identical conditions.

## Preparation

Use the repository's ELF runtime Docker target and record its source revision
and image digest. Run one matched ELF fixture at a time. The shared runtime
helper owns the `elf-matched` container namespace and checks its ownership label.
Do not start this runner against another active experiment's containers.

```sh
docker build --target elf-service-runtime --build-arg ELF_SOURCE_COMMIT="$(git rev-parse HEAD)" -t elf-agent-evidence:current -f docker/benchmark/Dockerfile .
```

Set `ROOT` to a new absolute artifact directory. Run the commands below as the
consumer of `cargo make benchmark-budget`. Inject the provider credential only
into that gateway, and use the existing cumulative ledger and authorized cap.
The gateway supplies ephemeral `LITELLM_BASE_URL` and `LITELLM_API_KEY` values.
Do not put a provider key in the runner, Docker configuration, or command line.

```sh
cargo make benchmark-elf-agent --root "$ROOT" --image elf-agent-evidence:current --phase prepare --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --image elf-agent-evidence:current --phase run --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --image elf-agent-evidence:current --phase paged --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --phase finalize --output-maximum 393216
cargo make benchmark-elf-agent --root "$ROOT" --phase control --output-maximum 393216
```

The recorded DeepSeek route supports a maximum completion of 393,216 tokens.
This differs from the model-directory maximum. Before a new trial, verify the
selected endpoint's output allowance and prices. Keep all conditions on the
same provider and settings. Preserve route failures and their outstanding cost
reservations. A missing usage receipt is not proof of zero charge.

Use `--request-max-bytes 1048576` on the budget gateway for this agent profile.
The legacy 256 KiB limit can reject a multi-turn history before provider dispatch.
This changes the transport envelope, not the provider output allowance or the
cumulative dollar cap. Each request still reserves its full input and maximum
output cost. Do not truncate evidence to fit the old envelope.

Preparation creates source documents and ingests the corresponding events
through native ELF APIs. The extraction proxy returns exact prior successful
responses only when the extraction messages match. It reuses exact cached
Qwen3-Embedding-8B inputs at all 4,096 dimensions. New search-query embeddings
can use the budget gateway. This tests retrieval over frozen extraction, not
the quality of a new extraction model. New native identifiers and ingestion
timestamps are expected; derived note bodies must match the recorded fixture.

The runtime helper uses a pinned local reranker image. That image's packaging
does not constitute a competitor benchmark.

## Collection and interpretation

Each agent has at most twelve model rounds and twenty-four tool calls. The
provider output allowance remains unchanged. Retain tool or round exhaustion as
an unsuccessful outcome; do not resample it until it produces an answer. These
limits measure a bounded workflow, not unlimited-search capability.

The separate `finalize` phase makes one final model call for each exhausted
primary or paged trace. It supplies only the evidence already read, marks pending tool calls as
unexecuted, and permits no further retrieval. Keep these answers separate from
the primary outcomes. This distinguishes failure to stop searching from failure
to obtain the requested facts. Persist the raw finalization response before
parsing it; a restart must not purchase a replacement factual answer.

The runner records every provider response and completed tool call before the
next step. Tool failures remain visible to the agent. Wrong factual answers are
retained. A single fenced final JSON object can be read without a new model
call, but record its formatting noncompliance. Archive transport or ambiguous
format failures before an explicit retry. A completed-case restart skips prior
answers and exhausted cases.

For an archived transport rejection after a complete tool batch, explicitly
pass `--resume-case CONDITION/CASE_ID` to the `run` phase. It restores the saved
responses and tool outputs and retains both round and tool-call counts. It
refuses to resume a recorded final answer or an incomplete tool batch. Keep
the original failure and trace. Report total wall-clock latency as unavailable
when the original timer was lost.

Graph tools use `/v2/graph/query`. The primary agent does not use the separate
graph-report, Context Pack, knowledge-page, or entity-memory interfaces. Record
additional read-only diagnostics separately. Do not describe this experiment as
coverage of every ELF interface.

The primary wrapper fixes note-search output at twelve items. ELF itself also
supports `elf_searches_get` with a larger `top_k` over the existing cached
session. The separate `paged` diagnostic exposes that capability, supplies the
native initial `search_id`, and recommends expansion before another query. It
selects the four questions with missing identifiers in the initial context,
recorded in `initial-fact-coverage.json`. This is a targeted follow-up selected
after inspection, not an unbiased extension of the primary score. It adds no
source or graph tools. Report the wrapper omission rather than describing
cached expansion as a missing ELF product feature.

Run offline analysis without provider credentials or Docker:

```sh
cargo make benchmark-elf-agent --root "$ROOT" --phase analyze
```

Report strict scores and semantic review separately. Bind each review to the
answer's SHA-256 hash. A current-state answer can correctly mention an explicitly
superseded value; a raw forbidden-substring check cannot judge that distinction.
Known absence of an appointed owner also differs from missing information.
Keep unsupported claims and genuinely wrong current states as failures.

The analyzer records actual document reads, verified provenance follows,
object-entity traversal attempts, graph evidence-note reads, tool errors, and
unseen citation identifiers. A graph traversal can reach a dead end. Identifier
presence in tool output does not prove that its subject binding is correct.
Inspect the traces before attributing an improvement to a graph or source tool.

Keep canonical source bytes, extraction receipts, graph snapshots, initial
contexts, raw answers, reviews, and cost receipts. Use explicit source lineage
for reused evidence. Exclude private runtime configuration and authentication
files from public bundles. After delivery, remove only this experiment's owned
containers, volumes, network, and unused task-created images.
