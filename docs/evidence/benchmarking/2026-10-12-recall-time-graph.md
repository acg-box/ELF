---
type: Evidence
title: Source recall and historical-state trial
description: Frozen 36-question evaluation of supplemental recall and alias authority.
status: accepted
authority: informative
owner: elf-service
last_verified: 2026-10-12
---
# Source recall and historical-state trial

## Result

The final reader answers all 32 test-partition questions correctly. Two answers
still omit a source needed to establish the subject of an atomic claim. The
strict test score is 30/32, unchanged from the previous condition. This is a
factual improvement, not a demonstrated improvement in overall citation quality.

| Cohort | Previous factual | Final factual | Previous native joint | Final native joint |
| --- | --- | --- | --- | --- |
| Original test | 16/16 | 16/16 | 16/16 | 14/16 |
| Contrast test | 14/16 | 16/16 | 14/16 | 16/16 |
| Development, separate | 2/4 | 4/4 | 2/4 | 4/4 |

Native joint requires factual correctness, semantic support for each claim, and
valid native source bindings. All 36 final responses pass native binding checks.
A valid hash and byte range do not prove that a quotation supports a claim.
Previous scores use the previous report's `native_joint` contract, not its older
raw answer-format score. Development cases are not added to the test denominator.
These partitions were reused during development; they are not unseen test data.
Semantic reviews were performed by the assistant, not a blinded independent judge.

## What changed

The new supplemental endpoint combines original-text matches, derived-text
matches, and graph incidence. It keeps distinct entity IDs separate and prefers
source diversity. The Cedar August 15 source had no derived note; searching notes
alone could not recover it. Original-text discovery recovered that evidence
without extraction or embedding calls.

Historical graph results now classify temporal status at the requested `as_of`,
not at wall clock time. Current permissions and deletion rules still apply. The
benchmark reader receives that target explicitly and distinguishes a continuing
in-use mode, formal authorization, a new approval event, and a later decision.
The reader contract is a benchmark/agent integration change; it is not a new
server-side entailment judge.

The trial also exposed one generic Atlas entity with aliases for both North and
South. Unqualified extracted aliases leaked opposite-branch incident candidates
into recall. A new alias-authority column lets only caller-declared aliases act
as identity selectors. Existing aliases remain present with `unknown` authority.
Alias-only lookups may therefore require a caller to reassert a reviewed alias
or use the canonical name or ID. Extraction cannot downgrade caller authority.

The design combines complementary recall from Hindsight and validity/record-time
separation from Graphiti with ELF's existing source contract. See the
[decision and primary references](../../decisions/2026-10-12-recall-time-graph.md).
No database replacement, fuzzy entity merge, or inferred causal edge was added.

## Failure analysis and graph limit

- `memory-1-1`: the Cobalt no-change assertion cites an Ivo/BATCH August 8 source,
  but omits the source that connects Ivo to Cobalt.
- `memory-1-2`: the historical-state answer is correct and has adequate evidence.
  An auxiliary Cobalt no-change claim again lacks its subject bridge citation.

The first trial also substituted a later North STREAM approval for the immediate
August 8 state. The final temporal contract resolves this case and qualifies
in-use state when formal approval is not explicit. Both trial outputs remain in
the bundle. Incorrect factual answers were not silently resampled.

Supplemental recall adds sources for 15 of 36 questions. Direct original discovery
contributes eight question-level source additions across two unique documents.
The first trial's eight graph-only additions were opposite-branch incident noise.
The final alias rule removes all eight; it produces no remaining graph-only
addition in this fixture. This does not establish independent graph score uplift.
Source-backed navigation bypasses fragmented entities and missing semantic edges;
it does not repair the graph into a complete ontology. Exact canonical-name
collisions and unsupported extracted relations remain separate design concerns.

The explicit lexical recovery path can scan the visible corpus. Result limits
bound returned material, not database scan cost. Large-corpus throughput and
production query plans were not measured. Index this arm before making it a
high-volume default if measured query cost requires it.

## Reproduction and trial lineage

The trial preserves the previous 36 questions, source corpus, notes, initial
12-note candidates, and Qwen3-Embedding-8B 4096-dimensional vectors. PG and Qdrant
remain in use. No extraction, embedding, reranking, competitor, or old 132-case
matrix was rerun. One planner call receives questions and corpus years only.
Two invented subject additions are rejected because they do not occur literally
in their questions; the raw planner response remains available.

The first trial has 36 new reader responses and scores 35/36 factual and 33/36
joint, including development. The final condition has 30 new responses and six
reused responses. Reuse requires identical model, prompt, question, and evidence,
excluding only the two root transport `request_id` fields. Reuse includes the
known failed `memory-1-1` citation; it is not selected by outcome. The final score
uses one retained response per case. Prompt and context changes are combined, so
this is not a causal ablation of each mechanism. There are no repeated-seed
confidence estimates.

All calls use `deepseek/deepseek-v4.1-flash`, the official DeepSeek provider, max
reasoning, and the full 393216-token output ceiling. This preserves the existing
reader profile. Final retained-response median latency is 43.4 seconds for the
original test and 51.8 seconds for the contrast test. Local prefetch medians are
about 0.052 seconds on this small restored fixture. Latency is descriptive, not a
backend performance comparison.

The final compiled API freely replays all 36 initial packs, supplemental recalls,
and native claim checks. Results match the paid trial after removal of root
transport request IDs. All eleven original-column database fingerprints match;
the new alias column separately has 103 `unknown` rows. Original source bytes,
notes, embeddings, entity IDs, facts, and evidence relations remain unchanged.

Run the offline integrity and score reproduction check from the repository root:

```sh
python3 config/benchmark/evidence/2026-10-12-recall-time-graph/verify.py
```

The checked-in bundle includes both trial responses, inputs, reviews, 67 unique
provider receipts, request lineage, usage, final native replay, schema receipt,
validation logs, and hashes. The verifier reproduces recorded labels and source
bindings; it does not independently adjudicate entailment.

## Cost and validation

| Cost boundary | USD |
| --- | ---: |
| Prior settled total | 8.099249 |
| Initial planner and 36 answers | 0.199929 |
| Final 30 changed requests | 0.204050 |
| This task total | 0.403979 |
| Cumulative settled | 8.503227 |
| Previous unsettled reservations | 1.083800 |
| Conservative cumulative exposure | 9.587028 |
| Authorized ceiling | 10.000000 |

No embedding cost was added. The two old failed-provider reservations remain
charged against the ceiling; they are not treated as free. Final requests use
the verified official-provider price ceiling of $0.15/M input and $0.60/M output.
Actual provider usage, including cache effects, determines settled cost.

Validation passed: 462 Rust unit tests, 105 Rust integration tests, 183 Python
contracts, four focused acceptance tests, formatting, docs, Clippy, and vstyle.
One existing payload-shape integration test reported a leaky pipe; its focused
rerun passed without that warning and no test API process remained. Complete
logs are retained. Fresh schema, pre-column upgrade, replayed schema application,
authority preservation, access isolation, historical deletion, and source-only
recall have regression coverage.

The owned native API, two Docker containers, and one anonymous volume were
removed after verification. Ten unrelated containers and shared images remain.
The verified database backup and raw results remain outside the worktree. No
production deployment or shared database migration was performed.

Next work should target source-bridge citation assembly and independently scored
unseen cases. More graph infrastructure is not justified by this fixture alone.
