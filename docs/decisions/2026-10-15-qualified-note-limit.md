---
type: Decision
title: Admit complete qualified notes up to 512 characters
description: Replace the early 240-character default while retaining source identity and bounded admission.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-15
---
# Admit complete qualified notes up to 512 characters

The native Agent trial rejected a 266-character repair update before indexing.
The previous "not yet fixed" note remained discoverable. Seven of 26 candidates
were rejected for length; they had 247 to 321 characters. Original documents
remained intact. This is an admission failure, not a failed vector lookup.

The initial specification selected 240 for short English sentences without a
recorded empirical justification. The earlier 512-character replay admitted more
notes and improved two release-evidence answers, but did not improve aggregate
quality. That result does not justify discarding complete state updates.

Set the supplied configurations to 512 Unicode scalar values per note. Keep the
existing configurable admission check, source storage, evidence binding, retrieval
budgets, MMR, PostgreSQL, and Qdrant. A note expresses a concise, complete fact or
decision; it can have multiple sentences. Preserve its explicit subject,
applicable time, conditions, and exceptions. Do not truncate text to fit. This
bound is a provisional operating choice, not a product invariant or an optimum.

Publish the explicit qualification guidance as built-in ingestion profile 7.
Preserve existing stored profile versions and pins. Existing deployments must
update their configured limit and deliberately select the new profile when
needed. No service upgrade rewrites original documents or old notes. Previously
rejected candidates need an explicit replay; a configuration change alone does
not recover them.

First inspect the seven original rejections without model calls. Then replay the
same extraction proposals through native ingestion with unchanged sources,
chronology, reader, and MMR. Reuse only exact-input full 4096-dimensional
Qwen3-Embedding-8B vectors. Verify admission, indexed text, original hashes,
retrieval, and final citation separately. Run the original two handoff questions
twice and one separate fresh-extraction diagnostic. Retain all failed answers;
do not tune the frozen workload or repeat conversations to obtain a passing score.

The existing finite Python trial owner remains sufficient. Count all new calls,
including indexing and failures, in the existing cumulative $10 ledger. The
follow-up has a $0.50 admission tranche. Report reader omissions even if the
length defect is fixed. This slice does not establish general memory value or
customer readiness. Revisit the bound if complete, relevant claims still fail
admission or larger notes measurably harm retrieval and use.
