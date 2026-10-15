---
type: Reference
title: "Current ELF product direction"
description: "Separate the active memory-value hypothesis from stable intent and historical delivery plans."
status: active
authority: informative
owner: product
last_verified: 2026-10-15
related:
  - docs/spec/agent_memory_knowledge_system_v1.md
  - docs/evidence/external_memory/2026-10-15-product-alignment.md
  - docs/evidence/benchmarking/2026-10-15-qualified-memory-evidence.md
  - docs/evidence/benchmarking/2026-10-14-bounded-source-evidence.md
  - docs/decisions/2026-10-13-project-memory-trial.md
---
# Current ELF product direction

Purpose: Identify the next useful product question and its evidence boundary.
Read this when: Planning, implementing, or reviewing an ELF change.
Not this document: A second product contract, a task queue, or permission to run a
paid experiment. The [product contract](../spec/agent_memory_knowledge_system_v1.md#product-contract)
owns the goal and stable principles.

## Current judgment

ELF should prove that source-backed project memory improves continuity and
decision updates across real agent sessions. Its incremental value over capable
source access is still a hypothesis. Provenance, correction history, and scoped
access are useful foundations, but their existence alone is not unique market
value or customer acceptance.

The October 15 read-only evidence change raised full ELF's original-task
coverage from 46/64 to 49/64 and complete acceptance from 3/16 to 6/16. On four
new frozen variants, coverage changed from 27/32 to 26/32 and acceptance from
3/8 to 2/8. This is mixed evidence, not a stable task-quality gain. An attempted
extractor expansion caused nine structured-binding rejections and was reverted.
The delivered path preserves existing note context and already bound quotations
without a new extraction pass.

The source-only control reached 47/64 on original tasks and 26/32 on new tasks;
full ELF cost more per original answer. File-control coverage varied substantially
without a tool change. All arms use the native citation checker. This is a small
retrospective archive replay, not a current-checkout shell agent or a natural
customer workflow. Supplied originals are a selection diagnostic, not a model
ceiling. One ambiguous promotion-receipt item has a symmetric sensitivity
exclusion; raw frozen scores remain available. See the
[complete evidence and limits](../evidence/benchmarking/2026-10-15-qualified-memory-evidence.md).

## Next coherent slice

The next work is a bounded maintenance trial, not another memory feature patch.
The previous archive questions remain regression evidence. Two real gaps in the
benchmark tooling provide executable deliverables: preserve opening settlement
cost in public reports, and verify partial evidence without pretending a stopped
trial completed its plan.

Compare ordinary current-checkout tools and file handoffs, indexed originals,
and full ELF in two fresh sessions per task. The second session gets a frozen
requirement update. Every arm can edit, test, and keep its own handoff. Measure
accepted patches, critical scope/integrity errors, repeated inspection, elapsed
time, and total provider cost including preparation. These are controlled
maintenance episodes; scripted updates are not natural human corrections.

Freeze both small batches and their stop rule before execution. If neither batch
shows the predeclared useful effect, stop this optimization line for that
workflow and use ordinary files or source access by default. Do not add another
repair batch to rescue these tasks. The
[workflow trial decision](../decisions/2026-10-15-workflow-pilot.md) owns the
protocol and thresholds. It does not establish customer readiness or justify
removing memory from unrelated workflows.

Original selection and subject/time misuse remain known failure boundaries.
Address them only when a real workflow or an isolated regression establishes a
specific cause. A newer capture timestamp, valid citation, or similar subject
name must not become authority. Resolve ambiguous expected outcomes before a
new quality claim.

## Decisions under review

| Choice or hypothesis | Current disposition | Reconsider when |
| --- | --- | --- |
| PostgreSQL authority plus Qdrant retrieval | Retain the supported deployment. Qwen3-Embedding-8B uses the full 4096-dimensional profile in the current experiment. | Representative quality, load, recovery, or operating-cost evidence supports a simpler or better design. A vendor speed claim is insufficient. |
| MMR and the 240-character note limit | Hold fixed for the next causal comparison. | Admission/recall evidence isolates them as the cause and a controlled test improves task outcomes. |
| Mandatory memory opening in the reference host | Retain for reproduction; test task-appropriate routing separately. | A frozen comparison can show when memory-first, source-first, or direct current-file access is useful. This review does not change the shipped reader contract. |
| Compact facts as the main derived representation | Keep short notes with read-time bound source quotes. The extra model transcription into structured facts was rejected. | Observed workflows require a different representation and existing source/procedure references cannot meet the obligation. |
| Stronger reader or extraction model | Evaluate roles separately when justified. Model size and coding scores do not grant authority. | A bounded diagnostic separates generation, retrieval, and use failures and reports total cost. |
| Live verification of reusable lessons | Candidate for a narrow read-only probe through the application. | Current-state failures persist and an authorized source can resolve the uncertainty. Do not add broad background crawling. |
| More databases, a universal ontology, or a new agent harness | Defer. | A measured obligation cannot be met within the current owners at acceptable cost. |

## Evidence needed for a customer pilot

Use a real workflow with new sessions and decision changes. Compare ordinary
source access, indexed originals, and full ELF with the same available evidence,
model, permissions, and budget. Include maintained native/file memory or a strong
long-context control when that is the user's actual alternative. Do not require
every baseline on every regression run.

Freeze the task outcome, minimum useful effect, critical errors, repetition plan,
and budget before execution. Track task completion, user corrections, stale or
wrong-scope actions, repeated discovery, elapsed time, and total cost. Include
capture, extraction, indexing, maintenance, failures, and infrastructure; separate
cold setup from reused preparation. No held-out task or answer may enter memory
before its turn.

A limited pilot needs repeatable benefit on the selected workflow and no failures
in its critical provenance, scope, correction, and deletion cases. Passing those
cases does not prove universal reliability. If derived memory adds no useful
benefit after a bounded test, narrow its use and simplify the path instead of
expanding the architecture to defend it.

## Keeping this record current

Update this reference when accepted evidence changes a disposition or next step.
Link the dated report or decision and reconcile affected current specs in the same
PR. Do not mark unrelated claims as freshly verified merely by changing a date.

Review is warranted when a relevant model/tool change challenges an assumption,
a requirement changes, or a regression or pilot contradicts the expected result.
The shared review method and any recurring coordination belong to
[Agentry issue 25](https://github.com/acg-box/agentry/issues/25), currently pending.
ELF's [existing weekly radar](../runbook/external_memory_pattern_radar.md) is a
metadata signal source; it does not perform this judgment. No additional ELF
review automation is established by these documents.
