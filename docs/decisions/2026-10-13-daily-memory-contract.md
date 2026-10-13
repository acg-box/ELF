---
type: Decision
title: Align memory admission and Agent evidence access
description: Use runtime limits and existing evidence APIs to make daily memory use measurable.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-13
---
# Align memory admission and Agent evidence access

## Problem and decision

The first daily project trial admitted 23 of 74 proposed notes. The extraction
prompt omitted the quote byte limit. The reader never completed a memory read
before its evidence budget ran out. These are contract and integration failures;
they do not justify a storage migration or a new Agent framework.

Keep PostgreSQL, Qdrant, immutable Source Library records, and the existing native
search, evidence pack, excerpt, and claim-check APIs. The extraction prompt and
its generated schema use the same configuration as admission. Notes count Unicode
characters; evidence quotes count UTF-8 bytes. Do not silently shorten a note,
translate a quote, or repair a mismatched source with fuzzy matching.

The canonical setting is `security.evidence_max_quote_bytes`. The old
`evidence_max_quote_chars` setting remains a deserialize-only alias with its old
byte semantics. Supplying both is an error. Existing stored ingestion profiles
remain immutable. Built-in version 6 adds concise quote guidance; existing
explicit version pins remain in place. Runtime limits apply to every profile,
including custom templates that omit the limit placeholders.

A preliminary calibration still produced quotes with collapsed newlines. Version
6 therefore gives the extractor request-local `evidence_spans`, each bounded by
the configured byte limit. The model selects `message_index` and `span_id`; the
server copies that exact span before the existing provenance checks. The spans
cover every input byte and keep UTF-8 boundaries. Unknown or ambiguous selectors
fail before persistence. Legacy verbatim quote objects remain valid. Selecting a
span proves identity, not entailment; semantic review remains separate.

Count, byte-length, and verbatim-matching failures have distinct reason codes.
Count and length errors identify the rejected field and actual limit. The limits
remain 240 note characters and 320 quote bytes in the default configuration.
This phase tests a correct contract before changing those product defaults.

## Agent boundary

The shared Agent contract starts a handoff with a small memory search and the
originals behind selected notes. Missing memory triggers source discovery.
Source-only clients start with document discovery. Neither path scans every
file by default. The same contract is published by MCP and loaded by HTTP clients
and the benchmark. Tool availability remains controlled by each host.

Document excerpts return native references only for verified original bytes.
Search byte positions pass directly into the existing excerpt API. Agents copy
these references instead of reconstructing hashes or converting offsets to lines.
The reference grants no access; claim checks still apply current permissions.

The existing claim checker is callable before the final answer so the agent can
repair invalid citation bindings. This is mechanical verification, not proof that
the source entails the answer. No server-side answer generator or new persistence
layer is added. The existing Rust service owns source and validation behavior;
the established Python benchmark owner coordinates the finite experiment.

## Verification boundary

Keep the prior trial immutable. A new private freeze selects four regressions and
four new follow-up questions, two repetitions, and the same three conditions.
All conditions retain identical original records, chronological visibility,
GPT-6 Luna medium reasoning, full 128000 output allowance, and common budgets.
Embeddings remain Qwen3-Embedding-8B at 4096 dimensions. All requests count against
the existing cumulative $10 ledger, including unresolved prior reservations.

Report actual memory reads, admission, citation binding, semantic review, latency,
and amortized cost separately. The new source-only comparison isolates memory
availability within the improved workflow. Comparison to the old trial also
includes workflow changes and cannot isolate one patch's causal effect. These
retrospective tasks do not establish natural multi-day session or customer readiness.
