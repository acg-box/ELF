---
type: Decision
title: Verify capture and memory use before a continuity comparison
description: Admit runtime source expressions and close the existing Agent evidence loop without a new framework.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-15
---
# Verify capture and memory use before a continuity comparison

The previous optional-tool trial never used native memory. It also rejected the
real provider gateway source because the credential heuristic treated runtime
token generation and keyword argument references as stored credentials. Fix
these two boundaries before another comparison.

## Source admission

Keep the existing `regex` owner and conservative default. Recognize complete
Python `secrets.token_hex`, `token_urlsafe`, and `token_bytes` calls with optional
numeric sizes. Recognize an identifier value in a keyword argument bounded by
an opening parenthesis or comma and a closing parenthesis or comma. A bare
identifier assignment remains ambiguous and stays rejected. Inspect every
credential assignment independently, including multiple assignments on one line.
Literal credentials, string arguments, unknown calls, fallbacks, and appended
expressions remain subject to rejection. Global private-key and API-key patterns
still apply to the complete input. Source bytes never change.

This is a lexical heuristic, not a language parser or a secret-free certificate.
The standard library has no multi-language source parser. A new Python or
tree-sitter parser would add grammar and dependency ownership without resolving
configuration literals or arbitrary embedded prose. A growing list of application
helper names would also be brittle. The bounded standard-library call and
keyword-reference forms address the observed file without either expansion.
The writegate owner must revisit this choice if another language or expression
needs an exception, or if a literal can cross this boundary. Remove an exception
when its input form is retired. Positive full-file and adversarial literal tests,
plus native byte-preservation readback, verify the accepted scope.

## Capture and read ownership

The host saves authorized, selected original messages and receipts. It does not
ask the model to recreate them. Existing document capture owns immutable bytes;
existing event ingestion owns extraction and admission; existing search, evidence
pack, and evidence check own recall and source binding. Preserve source kind,
role, timestamps, and session identity. A work record is an assistant observation,
not a new user grant. Work Journal retains its source-adjacent authority boundary.

The shared MCP/HTTP contract now describes the capture hook. The existing Python
reference host accepts real source metadata and records which memory-linked
originals reached the reader and its final citations. Formal comparison requires
this chain in each full-ELF calibration cell. It must also have valid native
bindings. Empty search, tool availability, or a stored note alone is insufficient.
This is an integration gate, not a semantic or product-value score.

The existing finite Python trial exception continues to apply. No new agent
framework, storage service, background collector, or installed-client hook is
introduced. The host must explicitly wire capture and the shared opening.

## Bounded evidence

Use this actual repair's selected user request, investigation, source, and work
receipts for fresh-session handoffs. Freeze questions and acceptance obligations
before reader execution. Preserve stages, source hashes, failures, and exact
answer traces. Compare ordinary files, indexed originals, and full ELF with the
same source bytes, model, output allowance, and workflow budgets. Keep calibration
separate. Do not re-run recorded conversations or add tasks to improve a score.

Keep the cumulative $10 gateway ledger, including old unresolved reservations.
Use the established daily model and full Qwen3-Embedding-8B 4096-dimensional
vectors. Stop if the next full request reservation does not fit. Report capture,
extraction, query, and answer costs, not only reader costs. A bounded handoff
comparison does not establish natural multi-week use, coding completion, or
customer readiness. Preserve that limit even when all bindings pass.
