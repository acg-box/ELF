---
type: Runbook
title: Full memory product comparison
description: Completion criteria, fixed coverage, and cost controls for the full comparison.
status: active
authority: informative
owner: benchmark
last_verified: 2026-10-07
tags: [benchmark, memory, comparison]
source_refs:
  - config/benchmark/benchmark-v3.json
code_refs:
  - scripts/benchmark_runner/cli.py
related:
  - docs/runbook/benchmarking/repository_memory_replay.md
---
# Full memory product comparison

The 2026-10-07 repair pilot is not a full product comparison. Its 48 trials
include an initial protocol and a corrected protocol. They cover three repair
tasks. Keep that evidence separate from this comparison.

## Required coverage

Complete each lane below. A failed adapter is an execution gap, not evidence
that the product lacks the capability. A documented unsupported operation is a
capability limit. Never count an unstarted unit as measured coverage.

| Lane | Fixed scope | Completion evidence |
| --- | --- | --- |
| Existing regression | All 48 cases in the four versioned suites; cold and warm phases | Per-case retrieval, answer, mutation, failure, and cleanup records |
| Native workflows | Extraction, indexing, retrieval, and maintenance for each applicable product | Native commands, version, configuration, index readiness, and returned context |
| Corpus scale | 100 and 1,000 documents; eight answerable questions and two absent answers at each size | Recall, answer correctness, ingest cost, total time, and query latency |
| Cross-session use | Six decisions written in session A and queried by a new process in session B | Native write/read receipts and exact retained state |
| Conflicting authority | Six pairs with explicit source priority; six pairs with a later correction | Correct source selection and stale answer rate |
| Isolation | Two native namespaces with distinct canary facts in a shared store; six queries per namespace | Actual namespace configuration and observed foreign canary reads |
| Restart and mutation | Update and delete six facts, complete native maintenance, restart, then query | Before/after/restart readback; logical deletion distinguished from physical erasure |
| Agent task outcomes | The three frozen repair tasks, two repetitions per eligible memory condition | Task checks, source and context hashes, steps, tokens, and cost |

The scale lane uses one shared corpus per size, not a separate index for each
question. This measures index reuse and avoids redundant paid ingestion. A
warm query uses existing state. A restart test must create a new process.
Restarting a client does not establish server crash recovery. Namespace filtering
does not establish authentication or authorization security. ELF uses project
scopes, Hindsight uses banks, Mem0 uses users, and GBrain uses sources. A driver
with separate databases cannot claim shared-store isolation.

QMD's deep driver uses named collections in one database and passes the native
collection filter to each query. Its core suite retains separate job databases.
The host mode uses a prepared checkout and model files; it does not install a
runtime. Record the host platform and model hashes separately from Docker CPU
measurements. `--native-only` omits shared-reader calls and is not an answer-quality
result. The shared reader must run before answer-quality acceptance.

Context presence has different meanings by lane. Foreign namespace canaries
and deleted values are isolation or deletion signals. A retrieved source can
correctly mention a rejected draft, an obsolete value, or a development option.
Their presence alone does not make the final answer wrong. Score the selected
answer separately, and keep the native context for inspection.

The core `forbidden_evidence_hits` field includes superseded and off-topic
sources. Its strict `elf_seeded_invariants_passed` aggregate must not be reported
as an access-control verdict. Core text labels such as "private" do not configure
native permissions. Use the explicit shared-store namespace lane for isolation
observations, and actual mutation readback for deletion observations.

The deterministic deep workload contains 62 scored questions. The product
receives actions and source text; the answer oracle remains on the host. Each
action uses a new client process. Preserve the initial ingestion and all native
mutation receipts. Each ingest action has a 5,400-second limit; other actions
have a 1,200-second limit. The native invocation has a 7,200-second default total
limit. The bundle records these limits. A timeout is incomplete execution, not
proof of an unsupported capability. Use `cargo make benchmark-deep --help` to
inspect the CLI.

Each action runs in its own process group. On an action timeout, the runner
terminates that group, retains captured output, and marks later queries in a
failed ingestion scope as blocked. This prevents a native child process from
continuing provider calls after its Python client has stopped.

Use `--workload-group` to run a fixed group in fresh native state. The groups
are `scale-100`, `scale-1000`, `session`, `conflicts`, `isolation`, and
`mutations`; `behavior` combines the four non-scale groups. The default `all`
retains the original 62-question workload. Group selection preserves question
IDs, source text, the oracle, and operation order. Isolation always includes
both namespaces in the same store. Reanswer preserves the recorded group.

Separate groups when a timed-out scale import leaves index work that delays
later capability tests. Retain the original combined attempt and its costs.
Report the fresh-group condition separately; do not claim it measured behavior
under the earlier backlog. All groups together must still cover all 62 questions.
An incomplete scale group remains an explicit coverage gap even if the other
42 questions complete.

For a separate extended-readiness experiment, set `--ingest-seconds` and
`--max-seconds` explicitly. The ingestion deadline includes native indexing;
it also sets ELF's worker drain deadline. The bundle records both limits.
Keep the default-deadline failure and all of its costs. An extended run can
measure eventual query quality, but it cannot turn the earlier timeout into
a successful default-budget result. Do not combine its latency with ordinary
deadline runs as if the conditions were identical.

Host CPU work can overlap image builds. Treat measured wall time as observed
execution time, not a controlled CPU performance ranking.

## Products and modes

All fourteen products receive all 48 core cases. Together with two baselines,
this is 64 product/suite units. Product category labels do not remove cases.
Record an unavailable native operation separately from an adapter gap.

The retained matrix includes ELF, Mem0, QMD, LightRAG, OpenViking, GraphRAG,
Graphiti, PageIndex, OpenKB, and Honcho. Add GBrain, Hindsight, and MemOS through
their supported local interfaces. Record the current SAG and Letta Code
interfaces before deciding which lanes apply. Do not substitute the retired
SAG v1 or Letta Python server for their current products.

Keep no-memory, file search, and Git-backed memory as separate baselines.
Git-backed memory evaluates the Agent Memory Repo pattern; it does not measure
the hosted Devin product. Do not present the two as equivalent.

Use native extraction for the main Mem0 condition. Keep raw `infer=False`
storage as a named diagnostic mode. Separate QMD lexical search from its native
hybrid and reranking mode. Separate GBrain immediate mutation readback from
readback after its native embedding refresh. A hierarchy-only PageIndex run
cannot receive a ranked-retrieval score.

Freeze each product's source commit or resolved package version before its
first measured run. Retain image digests and upstream release evidence. A
version migration requires a new result identity. Historical measurements
must retain their original version and configuration.

## Shared controls

Use DeepSeek V4.1 Flash with low reasoning through the DeepSeek OpenRouter
route. Use Qwen3 Embedding 8B with 1,536 dimensions through DeepInfra where
the product accepts an external embedder. Record required native deviations,
including local models. Shared answer context is limited to 12,000 characters.
Do not send answer keys, relevance labels, or evaluator-only metadata to a
product or model. Do not tune a product on the scored questions.

The manifest records each native profile and deviation. Important distinctions:

- ELF uses `ElfService.add_note`, native worker indexing, and `search_raw` in
  this comparison. The adapter splits sources into 220-character note chunks
  to fit the measured configuration's 240-character note limit. Count logical
  sources and stored notes separately. This condition does not measure the
  separate document-ingestion API or establish its bulk-import performance.
  Deep runs set `ELF_REAL_WORLD_INDEX_TIMEOUT_SECONDS=5400` for the native worker
  drain. Other invocations retain the 180-second default. Record a drain timeout
  as incomplete indexing, never as a retrieval-quality result.
- Mem0 extracts memories with `infer=True`; raw insertion is not the main condition.
- QMD uses local embedding, query expansion, and reranking. Its host Metal and
  Docker CPU measurements are different runtime conditions.
- OpenViking generates native L0/L1 summaries and uses thinking search. The old
  fast, content-only profile does not establish the hierarchy's capability.
- LightRAG and Graphiti execute native graph construction. Their retrieved
  context feeds the shared reader.
- GraphRAG uses JSON-object transport for typed outputs, with the original
  schema supplied to the model and native GraphRAG validation retained. The
  fixed DeepSeek route advertises JSON mode but not strict structured outputs.
  Preserve the initial JSON-schema transport failure as a diagnostic.
- Honcho supplies native hybrid message search. This does not measure peer chat
  or dreaming. Its available session deletion can remove unrelated retained
  messages; report that loss separately from a successful deletion request.
- MemOS deletes the exact memory IDs returned by native source-filtered readback,
  then checks the same source again. The pinned API treats `user_id` as a filter
  delete mode, so the ID delete request must omit it. Keep failed filter-delete
  attempts separate from this condition. Its embedding timeout is 90 seconds
  to match the bounded provider gateway; the native five-second default timed
  out before otherwise successful provider responses arrived.
- PageIndex uses generated PDFs and its local tool-using agent. Retain the native
  answer, but build shared-reader context from observed tool results.
- A missing source mapping reduces measured traceability. Keep the returned
  text, including foreign or obsolete content; never replace it with fixture text.

Dependency overrides, audit receipt hashes, and the measured input boundaries
are recorded in
`config/benchmark/evidence/full-comparison-dependencies.json`. An override is
part of the measured configuration. It is not an upstream product release.

The cumulative API limit is USD 10, including prior pilot spend. Reconcile
completed requests with explicit provider costs. Keep conservative reservations
for unknown costs and in-flight requests. Allow only one active budget gateway;
use at most USD 0.50 of new exposure for an eight-case core suite or repair
phase, USD 1.50 for the 24-case common-core suite, and USD 1 for a full
1,000-document deep invocation. The larger common-core tranche follows its
threefold case count; it does not change model output limits or remove earlier
failures. The cumulative USD 10 limit
applies to all invocations. A cost stop remains
incomplete coverage. It does not justify silently shrinking the matrix.

## Results and acceptance

Publish coverage before aggregate scores. Show planned, attempted, completed,
unsupported, and blocked counts separately. Keep all failed attempts and their
costs. After a protocol repair, rerun the affected comparison conditions; do
not replace individual unfavorable results.

Report retrieval quality, task success, stale/conflicting answers, isolation,
mutation durability, time, and total API cost separately. Native inference and
shared-reader costs must be distinguishable. Local compute time is not free
API cost. Small samples support directional findings, not universal rankings.

The work is complete only after every applicable lane has usable evidence or
a specific verified external blocker, coverage gaps are explicit, OpenWiki
matches the final results, the delivery PR is merged, and task-owned resources
are cleaned up. A green regression command alone does not meet this condition.

## Cost gateway

Run paid work through `cargo make benchmark-budget`. Inject the authorized
OpenRouter key into this gateway process as `OPENROUTER_API_KEY`. The child
receives a temporary local token. The gateway fixes both provider routes,
rejects multiple completions, limits request size and output, and records
provider usage. It keeps reservations for failed or unknown-cost requests.
The cumulative ledger includes earlier runs; do not start a new empty ledger
to bypass the agreed limit. A lock permits one gateway per ledger.

The gateway can frame a complete native response as buffered SSE for clients
that require streaming. This preserves response and tool-call content, but it
does not measure time to first token. The upstream call remains non-streaming
so its usage receipt is available before the response is forwarded.

```sh
cargo make benchmark-budget --ledger tmp/benchmark-costs.json --ceiling 10 --tranche 0.5 -- cargo make benchmark-competitors --mode compare
```

## Explicit embedding recovery

The original campaign uses zero gateway retries. For a separately recorded
recovery condition, `--embedding-429-retries 3` permits at most three additional
attempts for an embedding request that returns HTTP 429. The default remains
zero. The model, provider, request body, and scoring do not change.

Each attempt reserves budget and records its own outcome. Failed attempts retain
their unknown-cost reservation. Rows carry `request_ordinal`, `attempt`, and the
selected retry delay so one logical request can be audited across attempts.
Budget exhaustion stops before another provider call.

Backoff is 2, 4, then 8 seconds. A positive numeric `Retry-After` up to 30 seconds
replaces that delay. Longer or nonnumeric headers are returned to the consumer
without an automatic retry. Chat responses, HTTP statuses other than 429, and
uncertain transport failures are not replayed by this policy.

Use the same cumulative ledger and explicitly authorized ceiling. Retain the
original condition and its costs. A successful recovery does not replace the
original reliability result or prove that every failed query can be repaired.

## Scoring revisions

Revision 2 corrects three question/oracle mismatches. Revision 3 also measures
source traceability per returned native context row. Multiple chunks or
consolidated facts can share one source without losing provenance. Neither
revision changes the blinded product input. Preserve original bundles and use
`--rescore` to apply the same revision to every retained condition without paid
calls. Use `--reanswer` only when shared-reader responses need regeneration.

### Calendar date scoring (revision 4)

Revision 4 accepts valid English month-name dates as their ISO equivalents in
required and forbidden answer facts. It does not infer ambiguous numeric dates
or accept invalid dates. The Vega migration question does not require ISO
formatting. Preserve each original bundle and apply the revision uniformly with
`--rescore`. This offline step changes no native result, answer, or API cost.


### Requested facts (revision 5)

Revision 5 accepts the Cinder module name without its repository path prefix.
It rejects the retired module name with or without that prefix. The Lumen
question requires the retention periods and written Legal approval, but does
not request the additional case identifier. Preserve original and prior scores;
apply this review uniformly to all retained conditions with no provider calls.
Literal matching remains a bounded requested-fact check, not a semantic judge.


The legacy update metric accepts only the native operation types `update`,
`replace`, and `reindex_update`. It also requires exact replacement text in the
retrieved context. A `delete_then_insert` operation receives zero on this metric
even when the replacement is returned correctly. A native update can also return
a correct paraphrase and fail the exact text check. Report the operation method,
acknowledgement, final readback, and answer correctness separately. This metric
alone does not establish whether a logical correction worked or was atomic.

The final shared-reader protocol submits exactly one case per request. A batch
of separate cases still exposes every case's context to the model, so a correct
answer can use another case's evidence. Retain earlier batch results as protocol
diagnostics and reanswer their native readbacks before comparison. Deep scores
also separate a matching answer from a value that is present in that case's
supplied context. A matching but unsupported value is not a grounded success.

A failed unit can still have valid individual native results. Retain those
results and their shared-reader answers, but do not treat the unit as complete
or hide failed cases from coverage. Small keyword-based answer checks cannot
establish a general intelligence ranking.

## Native agent condition

`cargo make benchmark-letta --out PATH` runs Letta Code 0.34.4 with its local
backend on the same three historical repair tasks, twice each. A first process
records source knowledge through native persistent memory. A second process
and conversation performs the repair. Both have six turns and use the same
bounded model route. Skills, mods, and background reflection are disabled.
The native tool allowlist contains Read, Edit, Write, and Bash. Keep native
memory-file snapshots and verify a new conversation on the same agent. A
successful repair alone does not prove that memory was written or used.
Report this native-agent condition separately from the common JSON-action
agent, because their tool sets and system prompts differ.

The common repair agent can use any configured native retrieval product:
prepare a replay with `--target PRODUCT`, retrieve with the same target and
manifest, then run both repetitions with `--arm PRODUCT`. The reference patch
and checks remain outside product input.
