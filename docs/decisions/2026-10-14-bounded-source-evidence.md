---
type: Decision
title: Fit original reads to the Agent budget and retain decision conditions
description: Expose native byte bounds and remove repeated client payloads without changing memory ranking or admission.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-14
---
# Fit original reads to the Agent budget and retain decision conditions

The previous frozen trial lost evidence budget in eight of sixteen full-ELF
answers. A source reader found the relevant file but repeated smaller position
selectors still returned an L1-sized window. Cached search expansion repeated
already inspected candidates. Even supplied accurate originals left requested
conditions out of answers. These observations call for a read-boundary and
reader-contract change before another storage, ranking, or extraction change.

## Ownership and mechanism

Rust owns source access, UTF-8 window selection, and exact citation references.
Add optional positive `max_bytes` to the existing excerpt request, HTTP body,
and MCP schema. Clamp it to the selected level and any existing internal bound.
Requests that omit it retain the prior behavior. The cap counts original UTF-8
bytes, not serialized metadata. A window smaller than a UTF-8 character can be
empty; it then has no verified reference. Never modify source records.

The finite reference host uses that bound before returning an original. It
projects only the fields needed to read and cite the source. If JSON escaping
makes the result too large, one conservative native reread accounts for the
worst-case six-byte escape. This is a local read, not a model retry; record it
in the tool result and measured elapsed time. Do not clip a body while retaining
a reference to unseen bytes. File reads return complete lines that fit, with
the existing continuation line. Count all model-visible result bytes.

Conversation-local state suppresses exact repeated original bodies and cached
candidates only after they reached the reader. Keep their handles or note IDs.
Items dropped by output trimming remain eligible on the next expansion. The
native permission check still runs on reads and final claims. This adds no
cross-user cache, database, summarizer, or persistent authority. Existing Python
benchmark ownership follows the explicit exception in the project-memory-trial
decision. Rust retains product state and source invariants.

The shared Agent contract requires an answer for each requested part, with its
subject, applicable time, prerequisites, conjunctions, and exclusions. An update
announcement does not restate every retained rule; inspect the relevant current
original when needed. A host-owned final submission already checks bindings, so
a separate intermediate check is needed only for an uncertain binding. Binding
still does not establish semantic support. No automatic semantic judge or
question-specific answer hint is added.

## Frozen validation

Keep MMR enabled and the 240-character admission limit unchanged. Reuse the same
settled extraction proposals and exact-input Qwen3-Embedding-8B 4096-dimensional
embeddings. Add prior trial receipts to the reusable input cache. New reader and
embedding calls use the same cumulative $10 gateway and retain failed outputs.

Run the same four arms, eight formal tasks, two repetitions, and two calibration
tasks. Preserve questions, rubric, chronological checkpoints, exact-source
selections, and original hashes. Keep the model, provider, reasoning, full output
allowance, and workflow budgets unchanged. Freeze the reader implementation and
protocol before new paid calls. Do not rerun a recorded answer to improve scores.
Report paired coverage, complete acceptance, unsupported claims, evidence-budget
loss, elapsed time, and costs. Separate this retrospective project replay from
customer acceptance and extraction quality. No MMR or note-length comparison is
part of this follow-up.
