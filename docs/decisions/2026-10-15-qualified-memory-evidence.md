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

1. Keep the short note text as the retrieval summary. Built-in extraction profile
   version 7 asks for a few necessary qualifier clauses in `structured.facts`,
   copied from the selected evidence. Keep a condition with its rule. Narrow or
   omit a note if its summary and bound clauses cannot preserve the distinction
   between a past state, a proposal, and a current decision.
2. Return existing note kind, owning project, visibility scope, and stored facts
   in the evidence pack. Return the stored source origin with each original
   window. Reuse the existing fetch and permission checks.
3. Keep originals, hashes, byte offsets, note limits, MMR, storage, and the shared
   reader contract unchanged. Do not infer supersession from a timestamp or
   transfer authority between subjects from a similar name.

The existing fact validator permits a verbatim substring of the note or its
evidence quotes. This is a text binding, not a semantic verdict. Stored facts
remain derived records, and the reader must inspect original evidence. The
owning project and visibility scope do not identify the subject of every claim.
The source origin is a locator, not permission or current authority.

## Alternatives and limits

Longer summaries and different MMR settings would change admission and selection
at the same time. A new temporal or ontology layer would duplicate existing
source versions, lifecycle, entity, and graph mechanisms before their need was
proved. A stronger reader would confound the measured product change. Defer
those choices until a specific remaining failure requires them.

Additional qualifier text can increase evidence size and preparation cost. The
common response budget still applies. This change does not guarantee that the
extractor selects every necessary clause or that a reader applies it correctly.
Existing stored notes do not gain missing fields automatically. Profile pins
and custom profiles remain unchanged; activation is explicit in the runbook.

## Verification boundary

Use the unchanged original replay plus four new, frozen questions on the same
historical corpus. Run the new questions on the previous native build before the
candidate. Keep all four arms, source availability, reader, output allowance,
tool budgets, embedding dimensions, note limit, and MMR fixed. Preserve every
answer and failure. The new questions are targeted variants, not independent
customer evidence.

Changed extraction instructions must make fresh, budgeted extraction calls.
Reuse only exact 4096-dimensional embedding responses in the candidate. Preserve
the old extraction responses for the baseline. Count preparation and failures in
the existing cumulative budget, and do not label reused preparation as a cold
start. Compare the old and new cohorts separately. The combined change does not
isolate extraction from evidence presentation.

The native integration check carries a subject, date, and conditional limit from
an admitted event through storage and evidence materialization, with unchanged
source bytes and current access checks. The provider-reuse check verifies that
new extraction instructions cannot silently replay an old extraction response.
