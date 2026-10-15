---
type: Decision
title: Preserve qualifiers through the existing memory evidence path
description: Keep subject, time, and condition clauses with compact memories without adding another state model.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-15
code_refs:
  - packages/elf-service/src/ingestion_profiles/profile.rs
  - packages/elf-service/src/evidence/pack.rs
  - packages/elf-service/tests/acceptance/text_boundary/evidence.rs
related:
  - docs/spec/agent_memory_knowledge_system_v1.md
  - docs/runbook/agent-evidence.md
  - docs/evidence/benchmarking/2026-10-14-bounded-source-evidence.md
---
# Preserve qualifiers through the existing memory evidence path

## Problem and outcome

An agent must retain the subject, applicable time, and conditions of a reusable
decision. A short summary and a valid citation do not establish those properties.
The October 14 replay contained both missing-context failures and failures after
the correct original reached the reader.

An audit found no populated structured fields in the 79 extraction proposals or
45 admitted notes. A recovery summary omitted a required positive identifier
check, while its returned source window omitted the helper that defined that
check. In a different case, the reader saw the complete retirement announcement
but still treated an older procedure as current. Those failures need different
explanations; a new index cannot be assumed to fix both.

The native evidence pack already loaded each complete note and source metadata,
but discarded the note kind, ownership, stored facts, and source origin before
returning the response. The existing storage and validation path can preserve
these fields without a new schema or model call at read time.

## Decision

Return existing note kind, owning project, visibility scope, and stored facts in
the native evidence pack. Return the stored source origin with each original
window. Also return the note's already admitted evidence quotes, but only when
they occur in its linked, readable windows that fit the pack budget. Deduplicate
quotes after merging windows of the same immutable version.

The note remains a retrieval summary. The quotations make its existing supporting
clauses visible beside that summary. They do not certify semantic completeness,
current authority, or applicability to another subject. The reader must still
inspect and cite the original window. Storage ownership is not an inferred claim
subject, and a source timestamp is not a fact's effective date.

This is read-time materialization of existing records. It preserves the original
extractor profile, source hashes, offsets, note limit, MMR, and shared reader
contract. Existing memories can use the change without rewriting or re-extracting
them. Source access checks continue to run for each read.

## Rejected extraction expansion

A measured intermediate candidate asked extraction profile v7 to duplicate
qualifiers in `structured.facts`. It produced 77 proposals, including nine
structured-binding rejections, and admitted 38 notes instead of the frozen
baseline's 45. Only six admitted notes retained facts. The profile change was
reverted before delivery; its complete results and cost remain in the evidence.
The binding validator remains strict.

The stored evidence quotes already carry source clauses selected by the existing
extractor. Materializing them avoids another model transcription, extra field
embeddings, and a new write-time failure path. It cannot recover a predicate that
the extractor never selected. Follow the relevant original or helper definition
when a required condition is absent.

## Limits

Quotes add response bytes and remain subject to the common result budget. A
complete pack means that its requested pointers resolved, not that every premise
for a question was found. A valid original reference proves access and integrity,
not entailment. No new temporal state, inferred supersession, or subject merge is
introduced.

## Verification boundary

Use the unchanged original replay plus four new, frozen questions on the same
historical corpus. Run the new questions on the previous native build before the
candidate. Keep all four arms, source availability, reader, output allowance,
tool budgets, embedding dimensions, note limit, and MMR fixed. Preserve every
answer and failure. The new questions are targeted variants, not independent
customer evidence.

The intermediate extraction candidate uses fresh, budgeted extraction calls.
The final read-only candidate reuses the original frozen proposals and exact
4096-dimensional embeddings. Reuse completed non-memory controls only because
their code paths, source inputs, and reader contract are unchanged. Count preparation and failures in
the existing cumulative budget, and do not label reused preparation as a cold
start. Compare the old and new cohorts separately. Keep the intermediate extraction trial separate from the final read-only
comparison.

The native integration check carries a subject, date, and conditional limit from
an admitted event through storage and evidence materialization, with unchanged
source bytes and current access checks. The provider-reuse check verifies that
new extraction instructions cannot silently replay an old extraction response.
