---
type: Decision
title: Measure native memory against the same project originals
description: Keep project replay, source integrity, and cost evidence separate from a product superiority claim.
status: accepted
authority: normative
owner: benchmark
last_verified: 2026-10-13
---
# Measure native memory against the same project originals

## Decision

Use chronological project records to compare ordinary file access, indexed
originals, and indexed originals plus native extracted memory. Every condition
can read the same original bytes. The full-memory versus source-only comparison
isolates the incremental value of derived memory. A fresh process starts each
reader; only the declared store persists between sessions.

Keep the implementation in the existing Python benchmark owner. The runner
coordinates the shipped Rust API and worker. PostgreSQL owns source and memory
records; Qdrant owns the existing 4096-dimensional retrieval index. No additional
database, scheduler, general agent framework, or product answering endpoint is
required. Standard-library subprocess, JSON, HTTP, gzip, and hashing operations
are sufficient for this finite local trial.

The corpus and answer oracle stay private when the source repository is private.
Published evidence contains de-identified measurements and hashes. A public
evidence bundle does not grant access to the underlying source records. Do not
commit private source blobs, questions, answers, or provider request receipts.

## Source admission

The first native import found that the credential heuristic rejected source-code
environment references and a dependency name containing `token`. Those are not
credential values. Do not rewrite the original, remove the source from the trial,
or disable credential checks to make ingestion succeed.

Match credential assignment names at a word or underscore boundary. Exempt only
complete, recognized environment-reference expressions. Continue to reject
literal assignments, literal fallbacks, appended statements, API key patterns,
private-key headers, and seed-phrase text. Synthetic regression tests cover both
directions, and the native trial must preserve every admitted original byte.
This remains a heuristic, not proof that arbitrary source text contains no secret.

The maintained `regex` crate already owns matching. An additional language parser
would add runtime and grammar maintenance for this small set of references. The
explicit expression matcher is limited to the supported forms and fails closed
for other assignments. Revisit that choice if more language-specific forms become
necessary; do not grow it into a general parser.

The [2026-10-15 follow-up](2026-10-15-agent-memory-loop.md) extends the accepted
forms to bounded runtime token generation and keyword-variable references after
the actual gateway file was rejected. That decision owns the extension; the
original trial and its dated evidence remain unchanged.

## Evidence boundary

Freeze questions, source hashes, chronological membership, and required outcomes
before paid execution. Keep all invalid responses and failures. A mechanical
source binding only proves identity and accessible bytes. Review subject, time,
scope, and entailment separately. Report pattern checks, native bindings, and
semantic review as distinct measurements.

Use the provider's full output allowance and a daily economical reasoning profile.
The frozen trial uses GPT-6 Luna with medium reasoning and a 128000-token output
allowance. An interrupted maximum-reasoning preparation probe remains separate
from comparative measurements; its charges still count toward the same ceiling.
Reserve the
worst-case call cost before dispatch. Charge indexing, extraction, query planning,
answers, and failures to the same new $10 ledger. The initial calibration tranche
is $1. The extractor retains its native maximum of three JSON parse attempts;
each attempt is charged. The host does not repeat recorded cells. A prior
experiment's ledger is preserved and is not reset or refunded.

Two repetitions of eight retrospective tasks can reveal specific workflow
failures and cost differences. They cannot establish general superiority,
multi-week memory reliability, customer readiness, or an expected time saving
for all projects. A natural longitudinal pilot remains a separate acceptance
boundary.
