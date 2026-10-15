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
  - docs/evidence/benchmarking/2026-10-15-bounded-workflow-trial.md
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

The latest bounded maintenance trial did not establish memory value. Its first
batch was affected by prototype tool-budget defects. In the second batch, the
full-ELF availability arm passed two functional checks, but no formal agent in
any arm used a native retrieval or memory tool. No second-batch handoff was
completed, and one source-arm session stopped at a local request-size limit.
Functional passes therefore do not establish complete workflow acceptance or a
memory ranking. The optional-tool prototype also differs from the shipped
memory-first reader. See the
[trial evidence and limitations](../evidence/benchmarking/2026-10-15-bounded-workflow-trial.md).

The preceding read-only evidence change raised original-task coverage from 46/64
to 49/64, while frozen new variants changed from 27/32 to 26/32. Those archive
results remain mixed evidence. Keep their
[original scoring and boundaries](../evidence/benchmarking/2026-10-15-qualified-memory-evidence.md)
separate from the maintenance trial; these are different tasks and integrations.

## Next coherent slice

Stop the synthetic maintenance optimization line. Do not add another adapter,
repair batch, representation, or store to obtain a favorable score. The finite
workflow adapter has been retired; its code and all results remain in the
experiment record. Reporting defects found during the trial were fixed outside
the scored comparison, without replacing any saved answer.

For short repository maintenance with an available current checkout, use normal
file tools and an explicit handoff as the working approach. This is a scoped
choice while incremental memory benefit is unproved. It does not remove memory
from other workflows or change the shipped memory-first reader contract.

The next value test must come from an actual work item with a demonstrated
continuity need. Use the intended Agent integration. Verify capture, current
source access, and actual use of the declared memory treatment in calibration.
If the agent never uses that treatment, stop the comparison before a formal run;
an API smoke check alone is insufficient. A capable baseline needs realistic
context and file access, and may retain its own notes. Keep functional checks,
handoff completion, human corrections, and product benefit separate.

A specific admission defect is now grounded: dynamic token-generation and
variable-reference expressions in real source code were rejected as credentials.
It needs a bounded correctness decision that preserves literal-secret rejection
and immutable originals. Do not silently skip rejected records, rewrite their
bytes, or treat index availability as complete. This defect is separate from
whether derived memory improves the task.

Current-original selection and subject/time misuse remain known boundaries.
Reopen them only for an isolated regression or a real workflow, with a specific
cause and an acceptance test. Future paid work still requires a frozen scope and
admission under the existing cumulative ledger; unused budget is not a reason to
continue experiments.

## Decisions under review

| Choice or hypothesis | Current disposition | Reconsider when |
| --- | --- | --- |
| PostgreSQL authority plus Qdrant retrieval | Retain the supported deployment. Qwen3-Embedding-8B uses the full 4096-dimensional profile in the current experiment. | Representative quality, load, recovery, or operating-cost evidence supports a simpler or better design. A vendor speed claim is insufficient. |
| MMR and the 240-character note limit | Hold fixed for the next causal comparison. | Admission/recall evidence isolates them as the cause and a controlled test improves task outcomes. |
| Mandatory memory opening in the reference host | Retain the shipped contract. The optional-tool maintenance trial did not exercise it. | A frozen comparison can show when memory-first, source-first, or direct current-file access is useful. This review does not change the shipped reader contract. |
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
