---
type: Decision
title: Complete Agent evidence use before adding retrieval machinery
description: Preserve cached candidates, complete binding verdicts, and immutable citations with a bounded controlled trial.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-14
---
# Complete Agent evidence use before adding retrieval machinery

The previous trial lost required evidence at the client boundary. Three relevant
updates moved from relevance rank four to MMR rank five, outside the opening
window. Cached candidates were never expanded. A correct answer copied a hash
incorrectly after checking it, and generic output trimming removed claim verdicts.
At least nine required details were already present in inspected originals but
were omitted from answers. No storage migration follows from this evidence.

Keep native source locators and access checks authoritative. Search responses add
the cached candidate count and whether more remain. Evidence packs merge only
overlapping or adjacent verified windows of the same document and content hash.
Their union contains exact original bytes and maps every note to its new window.
Original source records and existing notes remain unchanged.

The shared reader contract tells clients to expand cached results for missing
premises and read promising originals before more discovery. A host can map
short conversation-local handles to exact native locators. Unknown or unreturned
handles fail before a native check. The host submits and renders the same final
answer object; a second model response cannot corrupt its references. Compact
intermediate checks retain all verdicts and dependency indices while omitting
repeated source bodies. This is client integration, not semantic certification.
MCP continues to publish the same shared contract and forward native APIs; the
finite Python trial provides the HTTP reference host. It does not install these
hooks into arbitrary external Agent hosts.

The existing Python benchmark exception in the project-memory-trial decision
owns this finite replay. Rust retains product behavior and persistent state.
The interval union is a bounded sort-and-merge over at most the existing pack
limits, using standard-library strings and collections. An interval-tree library
would add dependency and update cost without a query or mutation requirement.
The evidence owner must revisit this choice if arbitrary edits or unbounded
interval sets become part of the contract. UTF-8 overlap and citation remapping
are checked directly, with native source/hash validation kept separate.

## Frozen verification

Keep the prior corpus, questions, rubric, answers, and costs immutable. The new
trial uses the same eight questions, two repetitions, model, provider, 4096-vector
dimensions, and shared workflow budgets. First run four arms: ordinary file
access, source retrieval, full ELF with 240 characters and MMR, and an explicitly
diagnostic arm supplied with accurate original excerpts. The diagnostic receives
source bytes and locators, not the rubric or a composed answer; it cannot search.

Next run full ELF with 240 characters and MMR disabled, then 512 characters with
MMR disabled. These are predeclared sequential one-factor comparisons, not a
complete factorial or randomized causal estimate. They total 96 formal cells
plus 12 calibration cells. Do not change defaults based only on admission rate.

Replay the same settled extraction proposals for the admission comparison, and
reuse exact-input, same-model 4096-dimensional embeddings when available. This
isolates the admission threshold; it does not measure how a fresh extractor
would change its proposals with a 512-character prompt. Unknown extraction
inputs fail closed. New embedding inputs and reader calls pass through the
existing cumulative $10 gateway. Reused calls are logged separately and never
charged again or presented as fresh model runs.

Freeze exact-source selections before any new model call. Apply each checkpoint's
visibility boundary. Retain failed answers and all costs. Review answer coverage,
binding, entailment, latency, preparation, and cached-provider reuse separately.
The private corpus, answers, and provider fixtures stay outside public exports.
