---
type: Decision
title: Preserve complete memories within request budgets
description: Remove character admission and silent candidate truncation without changing storage ownership.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-15
---
# Preserve complete memories within request budgets

Purpose: Keep qualified, source-backed memory complete while bounding work.
Read this when: Changing ingestion, search previews, or evidence transport.
Not this document: A promise that extraction finds every fact or memory improves
all agent tasks.

The 240-to-512 change admitted seven old rejections, but a new 520-character
candidate still failed. Its last clause limited what citation bindings prove.
Increasing the number again would retain the same failure mechanism. This
supersedes the admission choice in the
[qualified-note decision](2026-10-15-qualified-note-limit.md); preserve its dated
results and failed candidate.

Remove the note and structured-text character gates and the silent
three-candidate tail discard. A note
contains a complete reusable claim with its subject, time, conditions, and
exceptions. Independent claims remain separate. Original documents remain
immutable. Derived text, indexing chunks, and display previews have separate
roles; the existing PostgreSQL records, outbox, and Qdrant child chunks suffice.
No new table, store, semantic splitter, automatic retry worker, or ontology is
needed.

Use `memory.ingest_max_bytes` for the aggregate serialized extraction input and
complete candidates in one event. Direct note writes count complete candidates;
updates count their request. The supplied value is 32768 bytes. Reject oversized
extraction input before a provider call. Return every generated candidate and an
explicit `DEFERRED_INGEST_BUDGET` outcome for one that cannot fit. Defer the whole
candidate; do not persist or index part of it. The caller keeps the receipt and
source identity for an explicit later attempt. This is not a hidden queue.
`processing_complete` describes budget processing, not semantic completeness.

`preview_max_chars = 512` applies only to search display. Label previews and
return complete stored text through full reads. Pack and recall `max_bytes`
bound the complete serialized response, including derived content, originals,
and metadata. Remove whole entries and report gaps; do not cut off conditions or
retain a wider reference for clipped bytes. The host retains its total evidence,
call, and provider-spending budgets.

Profile 8 selects contiguous original fragments with an optional inclusive
`end_span_id`. Fragment size is navigation granularity, not a maximum supporting
quote. The server joins exact bytes and keeps their original positions. Binding
checks establish byte identity and access, not entailment. Existing profile
versions and pins remain immutable. Use the
[configuration and profile migration](../runbook/agent-evidence.md#activate-the-extraction-profile)
for existing installations.

## Verification boundary

First verify all 26 old proposals and the three later proposals, including the
520-character candidate, against their unchanged original windows. Then replay
native ingestion, indexing, recall, and citation binding in frozen stage order.
Keep the original two questions and two repetitions. Add a separate contract
boundary question and a frozen multilingual fixture with four independent rules,
late conditions, dates, and amounts. Include native low-budget, Unicode,
contiguous-range, and preview/full-read cases.

Retain every failed answer. Do not tune MMR, prompts, source windows, or repeated
formal conversations after execution starts. The new contract is a sequential
regression against historical readers; it is not a randomized product comparison.
Reuse only exact-input extraction receipts and full 4096-dimensional vectors.
Fresh extraction is a separate diagnostic. The existing finite Python trial
owner is sufficient.

All new provider work, preparation, and failed requests use the existing
cumulative $10 ledger and a $0.50 follow-up tranche. Input bytes are a bounded-work
proxy, not exact model tokens or a monetary guarantee. The provider gateway
retains full output reservations and stops work when the budget cannot admit it.
