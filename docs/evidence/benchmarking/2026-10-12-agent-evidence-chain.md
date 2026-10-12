---
type: Evidence
title: Native claim chains and frozen source-reading validation
description: Evaluate explicit citation dependencies through the shared production agent contract.
status: accepted
authority: informative
owner: elf-service
last_verified: 2026-10-12
---
# Native claim chains and frozen source-reading validation

## Result and remaining gap

Both prior Cobalt citation failures pass the final source-by-source review. All
eight frozen new cases also have correct factual answers and sufficient source
chains. Three new cases still use `supported` for conclusions that describe
conflict, unknown information, or explicit absence. Their text is correct, but
consumers that route on the structured state cannot treat this as full success.

| Cohort | Factual | Source-chain support | Native binding | State-contract observation | All four |
| --- | ---: | ---: | ---: | ---: | ---: |
| Prior Cobalt regressions | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| Frozen new cases | 8/8 | 8/8 | 8/8 | 5/8 | 5/8 |

The first three columns reproduce the frozen factual/citation rubric. The
state-contract observation is an additional integration finding, not a change
to that rubric after results arrived. The all-four column makes the limitation
visible. It is not a replacement for the earlier 32-question score. This run did
not repeat that full suite or any competitor benchmark.

The remaining cases are `conflict-6`, `unknown-7`, and `absence-8`. The model
reports the intended uncertainty, conflict, or vacancy in prose but tags the
conclusion `supported`. ELF intentionally does not infer or rewrite the model's
semantic state. Do not branch on that field as if this sample had proven reliable
classification. No extra generation was used to improve these results.

## Product change

Native claims accept optional backward `depends_on` indices. A conclusion can
refer to an earlier, cited subject or temporal premise. The server returns its
direct citations plus the transitive premise sources, with
`citation_claim_indices` to retain the origin of each expanded slot. A missing,
unreadable, deleted, or hash-invalid premise fails the dependent binding too.

The Cobalt failures previously placed the project/person bridge elsewhere in the
answer. The final responses explicitly connect premises to the conclusion, so
the returned conclusion citations include both the bridge and event originals.
The native checker does not infer undeclared links or certify entailment.
`semantic_support` remains `not_evaluated`.

This mechanism is request-local. It adds no database, schema migration, model
call, graph repair, or source mutation. A backward dependency order and a fixed
12-element reachability array bound expansion to 96 direct citation slots. It
avoids repeated expansion of diamond paths, including invalid citations. Legacy
requests without dependencies keep their previous serialized binding shape.

MCP initialize now publishes the exact
[shared contract](../../../config/agent/evidence-reader.md). The
[HTTP and MCP integration runbook](../../runbook/agent-evidence.md) describes
retrieval, temporal interpretation, chain checking, and rendering from returned
`resolved_citations`. The same file supplies the benchmark instructions. A live
MCP initialization response was checked against the file bytes, not only a unit
test. Third-party clients must still honor that contract and render the full
returned chain; this test does not certify every agent host or UI.

## Frozen validation boundary

Commit `775217cb` froze the eight new questions and source rubric before the
implementation commit `13e6ef38`. The cases cover:

- A project-to-lane bridge with a same-name distractor.
- A three-source project, custodian, and authorization-time chain.
- Two people with the same first name in different service scopes.
- A later record that explicitly corrects an earlier effective state.
- A future approval revoked before it takes effect.
- Conflicting decisions with no precedence or adjudication.
- Chinese unknown-role information that does not establish vacancy.
- Chinese explicit vacancy that requires a project-to-account bridge.

The eight cases use 26 immutable originals stored through the native document
API. Native recall returns each known source window. The reader receives every
case source, including distractors; this isolates source reading and citation
composition. It does not measure search ranking, large-corpus recall, or graph
benefit. The two regressions reuse their exact prior evidence inputs. Existing
notes and full Qwen3-Embedding-8B 4096-dimensional vectors are retained; no new
embedding or extraction request was made.

The same assistant authored the fixture and reviewed results. This is not a
blinded independent evaluation. The fixture was frozen before implementation,
but two new cases were exposed during the protocol pilot described below.
Source-chain composition and instruction changes were evaluated together. This
is not a causal ablation or a repeated-seed reliability estimate.

## Protocol pilot and final trial

The first pilot emitted four paid responses. Three contained plain-text DSML
invocations of `elf_evidence_check`, even though the text-only reader request had
no callable tools. They are invalid outputs, not successful tool execution. One
new case returned a valid answer. All four responses, provider receipts, and
statuses remain in the bundle.

The consumer was paused while the fourth request settled. Its completed provider
receipt was recovered offline after the consumer stopped; no replacement call
was made for that pilot result. The shared production contract was then clarified:
a tool exists only when the host declares its callable schema. A text-only host
requires direct structured output and performs the native check before rendering.
Simulated XML or DSML calls are not accepted.

The final trial uses the clarified contract on all ten inputs, including the
pilot's successful case. Inputs are identical across phases. It records one
response per case, with no answer-driven resampling or silent repair. All ten
return valid JSON. The three state-label limitations remain in the final report.
This is an explicit protocol-repair trial, not ten first-attempt successes.

Both phases use `deepseek/deepseek-v4.1-flash` through the official DeepSeek route,
max reasoning, and the full 393216-token output ceiling. Requests are sequential.
The budget gateway reserves the full possible cost before each call; it does not
reduce the output ceiling to fit more requests.

## Cost

| Boundary | USD |
| --- | ---: |
| Prior settled | 8.503227 |
| Four-response protocol pilot | 0.017190 |
| Ten-response final trial | 0.034685 |
| This task total | 0.051875 |
| Cumulative settled | 8.555102 |
| Previous unsettled reserves | 1.083800 |
| Conservative cumulative exposure | 9.638903 |
| Authorized ceiling | 10.000000 |

All fourteen requests settled. Old failed-provider reserves remain charged
against the ceiling. Native replay, compilation, and tests use no paid model.

## Verification and cleanup

463 Rust unit tests, 106 integration tests, 184 Python contracts, the focused
claim-chain acceptance test, Clippy, vstyle, formatting, and docs checks passed.
The new fixture initially omitted required source metadata; the complete
integration suite passed after that fixture repair. The native API, rebuilt from
the implementation revision, reproduced all ten final claim-binding responses.
The two prior evidence bundles still verify offline with unchanged scores.

All eleven fingerprints of original database columns match the previous fixture
when the 26 new documents and their chunks are excluded. This includes unchanged
original source bytes, notes, vector tables, and graph data. New documents were
added; no previous original was rewritten. No production deployment was run.

The owned API and MCP processes, two Docker containers, and anonymous database
volume are removed after verification. Shared images and unrelated containers are
preserved. Raw responses and the database backup remain outside the worktree.

From a full repository checkout, reproduce the source lineage, recorded labels,
response dependencies, and cost totals with:

```sh
python3 config/benchmark/evidence/2026-10-12-agent-evidence-chain/verify.py
```

This verifier reproduces recorded review labels. It is not an independent
semantic judge. The next quality improvement should address structured state
classification and broader independently reviewed samples, with a new budget
decision if the remaining conservative headroom cannot reserve a full request.
