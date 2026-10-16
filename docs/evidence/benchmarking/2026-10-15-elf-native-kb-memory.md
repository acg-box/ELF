---
type: Evidence
title: "ELF addition to the native knowledge and memory comparison"
description: "Add unchanged ELF to the frozen OpenViking and RAGFlow cases, with separate answer, citation, source, and cost results."
status: completed
authority: informative
owner: product
last_verified: 2026-10-15
source_refs:
  - config/benchmark/evidence/2026-10-15-elf-native-kb-memory/results-summary.json
  - config/benchmark/evidence/2026-10-15-elf-native-kb-memory/protocol.json
  - config/benchmark/evidence/2026-10-15-elf-native-kb-memory/manifest.json
  - config/benchmark/evidence/2026-10-15-native-kb-memory/inputs.json
code_refs:
  - scripts/benchmark_pilot/runtime.py
  - scripts/benchmark_budget.py
  - packages/elf-service/src/add_event/service/decision.rs
  - packages/elf-service/src/evidence/pack.rs
  - packages/elf-service/src/evidence/claims.rs
related:
  - docs/evidence/benchmarking/2026-10-15-native-kb-memory.md
  - docs/evidence/external_memory/2026-10-15-reuse-assessment.md
  - docs/reference/product-direction.md
---
# ELF addition to the native knowledge and memory comparison

Purpose: Compare the current ELF implementation with the two completed native
system runs under the same small workload and reader conditions.
Read this when: Deciding which ELF behavior to retain and which mechanisms to reuse.
Not this document: A general product ranking, a graph or OCR comparison, or proof
that memory beats capable file access.

## Judgment

ELF gives **13/13 semantically complete answers** in this run. OpenViking and
RAGFlow each give **11/13**. When a complete answer must also have valid exact
quotes, ELF has **12/13**, and both other products have **11/13**. ELF's failed
quote remains in the evidence; no answer was repaired or repeated.

Retain the working ELF path. This run does not support replacing it to improve
answer quality. Its source links recover a current decision omitted from the
selected memory text, and its citation checker detects the reader's invalid
quote. These are useful concrete behaviors to retain across any future engine
change. The small margin is not evidence of general superiority or customer
readiness. It also does not justify expanding every ELF subsystem.

## Conditions and execution

- ELF source: `9940af3ca8b71e68f217c25c4061a8349f80b87e`. No product code,
  extraction prompt, ranking default, or model setting was changed for this run.
  The repository task `cargo make build-harness` built the tested binaries.
- The [existing inputs and oracle](../../../config/benchmark/evidence/2026-10-15-native-kb-memory/protocol.json)
  are unchanged. OpenViking 0.5.0 and RAGFlow 1.0.0-rc1 results are reused without
  another paid run. ELF has separate calibration data and a fresh formal store.
- Each product receives the same six knowledge texts and eight user records.
  Four initial records also appear in the knowledge corpus. Four later records
  enter through native memory. Two questions precede the updates, and eleven
  follow the updates and application restart or recovery.
- Every extractor and reader uses `openai/gpt-6-luna`, OpenAI routing, medium
  reasoning, and the full 128000 output-token allowance. ELF uses the unchanged
  shared reader prompt and a new independent reader request for each answer.
- Embeddings use `qwen/qwen3-embedding-8b`, Nebius, at **4096 dimensions**. ELF
  reuses 36 exact embedding requests from the earlier receipts. It makes no chat
  response substitutions. All 36 newly returned vectors have 4096 dimensions.
  PostgreSQL embedding rows and both persisted Qdrant collections confirm 4096.
- Native knowledge and memory each return at most six hits. The common context
  limit is 32768 serialized bytes, with whole-entry exclusion when necessary.
  No ELF entry was excluded. Native candidate generation, ranking, and content
  granularity remain product-specific.
- ELF uses `docs_search_l0` with `doc_type=knowledge`, and `planned_search` plus
  `evidence_pack` for memory. The filter prevents later chat originals from
  entering the knowledge-search branch. Original parents are read only through
  selected native memory links. Full-store source checks occur after answers.
- Both named projects share the same ELF project and agent namespace, as they
  share the native user or bank in the other products. No subject filter, golden
  source selection, or answer-specific date filter is added by the test client.
- The existing local token-overlap reranker is used. MMR and the native aggregate
  admission limits remain unchanged. This is a native retrieval and shared-reader
  comparison, not a full external Agent client acceptance.

ELF runs as ARM64 API and worker processes with PostgreSQL and Qdrant in Docker.
The initial formal startup failed while Qdrant collection readiness returned an
internal error. No provider call or scored answer occurred in that attempt.
Starting the same binaries against the initialized stores succeeded. The later
application restart completed in 2.118 seconds with no reingestion. Preserve this
setup incident as operating evidence; its root cause was not isolated by a code
intervention. No product speed ranking follows from this run: the earlier runs
used different execution platforms and host conditions, and ELF reused vectors.

## Answer results

Category rows measure semantic completeness. Quote validity is separate.

| Requirement | ELF | OpenViking | RAGFlow |
| --- | ---: | ---: | ---: |
| Knowledge policy and table | 2/2 | 2/2 | 2/2 |
| Current delivery and retry decisions | 2/2 | 1/2 | 1/2 |
| Cross-session recovery and causal link | 2/2 | 1/2 | 2/2 |
| Historical decision, before and after updates | 4/4 | 4/4 | 4/4 |
| Unappointed owner: do not invent a person | 2/2 | 2/2 | 2/2 |
| Combined knowledge and updated memory | 1/1 | 1/1 | 0/1 |
| **Semantically complete answers** | **13/13** | **11/13** | **11/13** |
| Answers with every quote valid | 12/13 | 13/13 | 13/13 |
| **Complete answers with valid quotes** | **12/13** | **11/13** | **11/13** |
| Individual quote bindings | 24/25 | 30/30 | 26/26 |

The thirteen attempts share underlying facts and include repeated historical
questions. They are not thirteen independent projects. One sample per answer
does not establish a statistically stable ranking. Both competitors' earlier
semantic reviews are unchanged, including OpenViking's incomplete causal answer.

## What produced the ELF result

**Linked originals recover omitted information.** For `post/memory-0-0`, the six
selected memory texts include STREAM-0-286 but omit RETRY-0-907. The native parent
of the August 22 memory contains RETRY-0-907 and the named Larch subject. The
reader receives that parent and gives the correct current answer. The new retry
decision was not copied into the knowledge corpus. This traces an observed
benefit to source hydration. It does not replace a paid note-only ablation.

**Extraction and ranking still lose useful qualifiers.** Some notes say only
"For the next outage" or "The retry policy is now" without naming the project.
Larch retrieval also returns Cobalt memories. The linked originals preserve the
missing subject and date, and the reader avoids the wrong-project values in
this sample. Correct answers do not prove that extraction or ranking is solved.

**Current decisions are interpreted from dated evidence.** ELF adds 22 notes.
All remain active, all stored keys are null, and all ten initial notes retain
their text and source references after updates. The native extraction path
stores a model-generated key as metadata but passes `key: None` to update
resolution and persistence. It does not use an inferred key to overwrite another
record. This is consistent with the absence of cross-project replacement here;
it does not prove complete tenant or subject isolation. This run exercises the
reader's decision interpretation, not native keyed correction or consolidation.

**Graph traversal does not explain this result.** The store has zero graph
entities and zero graph facts, and the client makes no graph request. There is
no basis to credit the score to the graph or to expand that subsystem from it.

**One failure is in the reader's quotation.** For `post/memory-1-0`, the complete
Cobalt sources and correct decisions reach the reader. The answer is correct,
but a citation joins two source sentences with an inserted `...`. The original
does not contain that string. Both the shared substring check and ELF's native
`evidence_check` reject the quote. The one-call protocol gives no repair turn to
any product. The saved failed output is not changed. This is an Agent output
contract failure, not source mutation, failed extraction, or missed retrieval.

All 25 ELF citation handles point to original source windows. The native checker
returns the same 24/25 binding result. Hash and quote checks establish source
binding; semantic support was reviewed separately. See the
[case review](../../../config/benchmark/evidence/2026-10-15-elf-native-kb-memory/review-elf.json)
and [mechanism analysis](../../../config/benchmark/evidence/2026-10-15-elf-native-kb-memory/failure-and-mechanism-analysis.json).

## Original text and maintenance boundary

| Check | ELF | OpenViking | RAGFlow |
| --- | --- | --- | --- |
| Knowledge originals unchanged after updates and recovery | 6/6 | 6/6 | 6/6 |
| Original user messages unchanged | 8/8 | 8/8 | 8/8 |
| Derived source links inspected | 22/22 notes resolve to verified originals | Archive and memory-diff mapping; no direct archive URI in tested note files | 21/21 derived-to-raw parent IDs resolve |
| Runtime components in this test | API, worker, PostgreSQL, Qdrant | One application container and local workspace | Seven services |

The fourteen original objects include four texts stored in both knowledge and
memory. This verifies the tested update sequence, not enforced immutability,
arbitrary recovery, retention, or ACL security. Component count is not a monthly
maintenance bill. ELF retains responsibility for its API, extraction, retrieval,
worker, migrations, and integration code; it has not become a thin wrapper.

## Retain, reuse, and defer

| Area | Decision from current evidence |
| --- | --- |
| Source identity, immutable versions, bounded parent reads, and citation verification | Retain the behavior and current working implementation. Require equivalent readback before replacement. The current source path contributes a missing fact and detects a bad quote. |
| Subject and time handling | Retain the contract and failure cases. A future change should address demonstrated qualifier loss or stale decisions in real work. This run does not authorize a new ontology or authority engine. |
| Extraction and ranking | Keep the working path for now. Keep algorithms replaceable in principle; there is no evidence here that each custom mechanism is necessary. Do not build a generic backend framework merely to enable hypothetical reuse. |
| Models, embedding, and storage | Continue the existing reuse of model providers, Qwen 4096, PostgreSQL, and Qdrant. No store migration follows from answer scores. |
| Document parsing, OCR, connectors, and general knowledge UI | Prefer an existing component when a concrete input or workflow needs it. This text-only run does not select or rank such components. |
| Wiki, graph, and broad automatic organization | Defer expansion until a real workflow demonstrates the missing capability. None contributed to this result. |
| Full OpenViking or RAGFlow substitution | Keep them as candidates. No quality-led migration is justified now. Compare contract coverage and actual maintenance work before replacing a working path. |

The next narrow reliability concern is the final Agent quote contract: the
existing checker detects the error, but detection alone does not prevent an
invalid final answer in this fixed reader. No production fix was made here.
The earlier real-project source-only comparison remains valid; this small
competitor result does not establish incremental memory value over direct files.

## Cost, preservation, and checks

| Item | USD |
| --- | ---: |
| Campaign settled cost before this addition | 2.000364401 |
| ELF calibration | 0.000893255 |
| ELF formal ingestion, retrieval, and 13 answers | 0.014043300 |
| **New cost for this addition** | **0.014936555** |
| **Campaign settled total** | **2.015300956** |
| Conservative campaign exposure | 2.087481656 |
| Remaining conservative allowance within USD 10 | 7.912518344 |

There are 58 new provider requests, all settled: 24 chat and 34 embedding requests.
They report 86403 input tokens and 8596 output tokens. Usage cost includes provider
cache effects. The 36 exact embedding reuses are separately counted, not billed
as fresh calls. ELF's formal reader alone costs USD 0.010119525 and receives a
mean 11978 context bytes, compared with OpenViking's 9468 and RAGFlow's 4433.
The common allowance is equal; actual context size and operating work differ.
These figures exclude Codex usage, local compute, and human maintenance time.

Paid execution is stopped. Both PostgreSQL dumps and the private provider receipts
are preserved. All four task-owned Docker containers and four volumes were
removed; fresh label queries return none. Shared images and unrelated services
remain. No new worktree, product feature, commit, or pull request was created.

The public-safe evidence contains inputs by immutable reference, reviewed answers,
delivered contexts, native retrieval and source checks, storage snapshots without
vector arrays, model usage, and the cleanup receipt. The clients are retained as
historical `.py.txt` records, not as a new benchmark framework. Both the original
and added artifact manifests pass hash verification. `cargo make check-docs` and
`git diff --check` pass. The final checks also confirm the frozen client, inputs,
oracle, reader prompt, complete reader outputs, and stopped budget gateway.
