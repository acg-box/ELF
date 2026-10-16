---
type: Evidence
title: "Agent final citation gate regression"
description: "Block invalid final citations, retain rejected drafts, and verify one bounded correction against the native source store."
status: completed
authority: informative
owner: product
last_verified: 2026-10-16
source_refs:
  - config/benchmark/evidence/2026-10-16-agent-citation-gate/summary.json
  - config/benchmark/evidence/2026-10-16-agent-citation-gate/protocol.json
  - config/benchmark/evidence/2026-10-16-agent-citation-gate/manifest.json
code_refs:
  - scripts/benchmark_agent/answer.py
  - scripts/benchmark_pilot/tools.py
  - scripts/benchmark_pilot/runner.py
  - config/agent/evidence-reader.md
related:
  - docs/evidence/benchmarking/2026-10-15-elf-native-kb-memory.md
  - docs/runbook/agent-evidence.md
  - docs/reference/product-direction.md
---
# Agent final citation gate regression

Purpose: Verify that an invalid citation cannot pass the final Agent host boundary.
Read this when: Integrating final answers or reviewing the retained Cobalt quote failure.
Not this document: A new competitive score or a fresh ingestion and retrieval benchmark.

## Problem and change

The native checker rejected a quotation with an inserted ellipsis in the
[ELF comparison](2026-10-15-elf-native-kb-memory.md). The shared reader had already
received the complete original. Detection alone did not block the saved answer.
Source review also found that the reference tool-calling host could mark failed
bindings as completed on its last turn, and direct JSON paths did not enforce
the returned verdicts.

The existing answer module now owns one `finalize_answer` function. It copies
the final draft, sends its complete claims to `POST /v2/evidence/check`, requires
one ordered verdict per claim, and returns an answer only when every binding
passes. Rejection preserves the native verdicts. The tool-calling host can
request a correction within its existing turn and call budgets. A failed last
turn, incomplete verdict set, or unavailable checker never becomes a completed
answer. There is no silent quote edit, citation removal, or automatic conversion
to an unknown claim.

The reference host's `submit_answer`, direct JSON path, and other native-claim
reader entry points use the same helper. The shared MCP/HTTP reader contract and
integration runbook describe the final gate. No new service, database, model,
retrieval algorithm, or API endpoint is added. This is maintenance of the existing
Python host and its in-process regression tests; no language boundary is moved.

The helper is executable reference integration. MCP instructions alone cannot
intercept the final text of Codex, Claude, or another external client. Such a
client must connect the same check to its output hook. Source binding remains
distinct from semantic correctness.

## Same-case validation

Restore the prior isolated PostgreSQL backup and keep the exact source IDs,
hashes, and source text. Replay the thirteen saved answer drafts and their
already-delivered contexts through the new finalizer and the real ELF checker.
Do not run extraction, retrieval, or embedding again. The retained vectors are
Qwen3-Embedding-8B at 4096 dimensions. Separate source readback checks cover all
fourteen original objects before and after the replay.

The frozen protocol permits one correction call for the run. The rejected
draft receives its failed verdicts and the same original context. The correction
uses `openai/gpt-6-luna`, OpenAI routing, medium reasoning, and the same full
128000 output-token allowance. No expected answer or oracle enters that request.

| Check | Result |
| --- | ---: |
| Original drafts accepted without another model call | 12/13 |
| Invalid original draft blocked before delivery | 1/1 |
| Model correction calls | 1 |
| Final drafts accepted after the bounded correction | 13/13 |
| Original source objects unchanged | 14/14 |
| New extraction, retrieval, or embedding requests | 0 |

The Cobalt answer text is exactly unchanged. The model replaces the invalid
stitched quote with two separate contiguous quotes. All three resulting quotes
pass the native check. The original rejected draft and the correction request,
response, and verdicts are preserved. No historical answer is overwritten.

This proves the delivery gate and this one correction, not a new 13/13 competitive
score. The original comparison remains 13/13 semantic completeness and 12/13
semantic completeness with valid quotes. Fresh model variance and incremental
memory value over direct files are outside this regression.

## Cost and cleanup

The correction costs **USD 0.000842050**. The campaign settled total is
**USD 2.016143006**; conservative exposure is **USD 2.088323706**, below the
existing USD 10 ceiling. The one provider request reports 5009 input tokens and
432 output tokens. These figures exclude Codex usage and local compute.

The budget gateway is stopped. The restored API and worker are stopped, and
the two test containers and two volumes are removed. Fresh ownership queries
return none. The original backup, provider receipt, and public-safe evidence
remain available. Shared images and unrelated services are retained.

The repository runner-contract task passes 222 tests. Regression coverage includes
the recorded invalid quote, final-turn rejection, a recheck within the existing
turn budget, incomplete verdicts, checker unavailability, and unchanged accepted
answer snapshots. Full repository and PR checks are recorded with delivery.
