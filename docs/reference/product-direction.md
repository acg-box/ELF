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

The October 14 frozen replay covered eight tasks with two repetitions per arm.
Required coverage was 49/64 for ordinary files, 44/64 for source retrieval,
46/64 for full ELF, and 52/64 for supplied originals. Complete acceptance was
5/16, 5/16, 3/16, and 6/16 respectively. Full ELF reduced its own answer cost
and budget-loss events relative to the preceding run, but did not establish a
quality gain. These are composite obligations, not accuracy percentages.

All arms used the native citation checker. The trial therefore measures the
incremental memory/discovery path, not the whole value of ELF provenance. It is
retrospective and small; supplied originals remove selection work and are a
diagnostic, not a production alternative or an absolute model ceiling. See the
[full evidence and limits](../evidence/benchmarking/2026-10-14-bounded-source-evidence.md).

## Next coherent slice

Trace the stale-current and wrong-owner failures through the existing extraction,
storage, recall, evidence-pack, and host paths. Establish where subject, effective
time, conditions, and correction links disappear or are misused before changing
their representation. Existing entity views, graph validity, lifecycle, and source
version mechanisms must be inspected before adding another state model.

Use the same reader and bounded source access to distinguish these failures:

| Evidence state | Next action |
| --- | --- |
| Required detail is absent from derived records | Check extraction and admission against the original. Keep a source-access path. |
| Detail exists but is absent from delivered context | Repair selection or serialization in the owning path. |
| Correct context reaches the reader but the answer is wrong | Check evidence presentation, tool use, and reader capability; do not blame the index by default. |
| A claim concerns current external state | Inspect an authorized current source when required; a past successful run is not a current-state check. |

Preserve the existing cases as regression evidence. Freeze a small fresh set before
formal execution, including an explicit supersession, a later correction about an
earlier time, two similar subjects with different authority, and a conditional
procedure. A task that asks what was known then must use only evidence available
then. A retrospective question about an earlier effective date can use a later
correction when the question permits it.

The first implementation should repair a demonstrated break in this path and
validate it end to end. It should not expand graph coverage or rewrite the reader
prompt merely because those changes might help.

## Decisions under review

| Choice or hypothesis | Current disposition | Reconsider when |
| --- | --- | --- |
| PostgreSQL authority plus Qdrant retrieval | Retain the supported deployment. Qwen3-Embedding-8B uses the full 4096-dimensional profile in the current experiment. | Representative quality, load, recovery, or operating-cost evidence supports a simpler or better design. A vendor speed claim is insufficient. |
| MMR and the 240-character note limit | Hold fixed for the next causal comparison. | Admission/recall evidence isolates them as the cause and a controlled test improves task outcomes. |
| Mandatory memory opening in the reference host | Retain for reproduction; test task-appropriate routing separately. | A frozen comparison can show when memory-first, source-first, or direct current-file access is useful. This review does not change the shipped reader contract. |
| Compact facts as the main derived representation | Keep the existing contract; investigate lost conditions and reusable procedures. | Observed workflows require a different representation and existing source/procedure references cannot meet the obligation. |
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
