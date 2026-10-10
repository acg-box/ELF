---
type: Decision
title: "Keep source evidence immutable and make memory language-neutral"
description: "Separate original evidence, derived memory, and text-format validation."
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-10
code_refs:
  - packages/elf-domain/src/text_validation.rs
  - packages/elf-storage/src/docs/documents.rs
  - packages/elf-service/src/structured_fields/relation_time.rs
  - packages/elf-service/src/ingestion_profiles/profile.rs
---
# Keep source evidence immutable and make memory language-neutral

## Decision

Source Library owns original evidence. Notes and graph facts own derived memory.
The shared domain text contract checks storage format. It does not classify
language, translate text, or normalize Unicode. Extraction profiles can prefer
English summaries, but original names and evidence quotes retain their language.
This removes the need for every agent caller to translate text before use.

Source Library stores the exact accepted UTF-8 content. Content-addressed record
IDs distinguish source versions. A changed source gets a new ID; existing record
content, ownership, chunk text, hashes, and citation offsets cannot be replaced
through storage upserts. Document lifecycle and capture metadata remain managed
metadata, separate from immutable content. Existing ACL and deletion rules still
apply; immutability does not mean that deleted evidence remains readable.

A source write policy that changes content now fails explicitly. The caller can
submit a permitted derivative as a separate record with its own provenance.
Secret checks still apply. Do not put secrets in an original capture to bypass
these checks. A hash of discarded content is not a stored original.

Events remain an extraction interface, not an automatic transcript archive.
Callers that need the complete original must also capture it in Source Library
or retain an external source. Event quotes are checked against extraction input;
each stored quote carries the caller message ID and timestamp, the BLAKE3 hash
of the original message, the hash of the extraction input, and its write-policy
audit. The two hashes differ when a policy changes the input. Caller message IDs
are locators, not access grants or proof of an external source's authenticity.
The hashes permit verification against the retained source. Derived memory is
allowed to change without changing its original source record.

## Extraction contract ownership

Generate the built-in JSON Schema from the Rust extraction types. Field descriptions
state the evidence-binding rules. Do not maintain a second illustrative object that
can drift from the decoder. Unknown extraction fields fail explicitly instead of
silently dropping an incorrectly wrapped subject. Facts and relation surfaces remain
verbatim-bound to note text or evidence; this change does not weaken that rule to
increase benchmark scores. Profiles can omit optional graph details when the source
does not support them.

## Relation time contract

The relation decoder and built-in extraction instructions share one format:
RFC 3339 with a timezone, or an ISO date `YYYY-MM-DD`. An ISO date denotes the
start of that UTC day for graph validity. This is a boundary convention, not a
claim that the event occurred at midnight. Source text and evidence keep the
original date and precision. Other timestamp APIs still require RFC 3339.
Ambiguous dates, invalid calendar dates, and timezone-free datetimes fail.
Extraction errors report the failed schema constraint instead of claiming that
an existing `notes` array is missing.

## Upgrade

1. Remove `security.reject_non_english` from configuration. Unknown security
   fields fail validation. Replace client handling of `NON_ENGLISH_INPUT` and
   `REJECT_NON_ENGLISH` with `INVALID_TEXT` and `REJECT_INVALID_TEXT`.
2. The built-in extraction profile is `default`, version `2`. A new tenant uses
   this version. Existing saved defaults and explicit version pins remain intact;
   the service does not overwrite custom profiles or historical versions.
3. For an existing tenant, read its default profile with the admin API, inspect
   any customization, then select `default` version `2` with the existing default
   setter. A request can also select `{"id":"default","version":2}` explicitly.
   Language-neutral API validation and the relation decoder apply to all profiles.
4. Source writers that used inline redaction or exclusion must submit a separate
   permitted derivative. Existing stored records are not rewritten on upgrade.

## Validation and limits

Regression tests cover multilingual events, notes and queries, original Chinese
quotes, date-only graph boundaries, immutable source versions and chunk offsets,
and continued rejection of invalid controls and secrets. The matched benchmark
uses the same frozen inputs, provider settings, and reader as the earlier ELF run.
Old measurement artifacts remain unchanged.

Multilingual API support does not guarantee equal ranking quality for every
language. Embedding, lexical retrieval, and reranking remain independently
configurable. No translation service or new storage system is required.
