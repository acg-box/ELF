---
type: Evidence
title: Matched Hindsight and RAGFlow system comparison
description: Compare native system answers and retrieval using common document and memory inputs.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-10
source_refs:
  - config/benchmark/fixtures/complex-documents-v1/oracle-source.json
  - config/benchmark/fixtures/parser-stress-v1/oracle-source.json
code_refs:
  - scripts/benchmark-system-comparison.py
  - scripts/benchmark_deep/memory_comparison.py
related:
  - docs/evidence/benchmarking/2026-10-10-native-memory-comparison.md
  - docs/evidence/benchmarking/2026-10-10-parser-stress.md
---
# Matched Hindsight and RAGFlow system comparison

**Final result: Hindsight 100/100; RAGFlow 100/100.** Both native systems
answered all 50 document questions and all 16 memory test questions correctly
under the declared semantic rubric. All 280 planned outputs completed and were
reviewed, with zero final gaps. The four development questions per condition
are excluded from the score. The fixture reached its accuracy ceiling; this
result does not establish a general product winner.

RAGFlow used fewer model calls and had lower confirmed successful-query API
costs on this workload. Hindsight exercised its native consolidation and
reflection tools, including correction of a mixed internal observation. Its
extra work did not improve the final requested-value accuracy on this small
corpus. One unpriced transport failure remains conservatively reserved, so the
confirmed-cost comparison is not a fully settled billing comparison.

## Scope and score

The comparison unit is the complete native system answer. Hindsight uses retain,
consolidation, native retrieval tools, and reflect with `budget=high`. RAGFlow
uses native ingestion, Infinity hybrid retrieval, a local cross-encoder reranker,
and native retrieval-chat. No ELF product behavior is measured.

The primary score is fixed before calls:

`100 * (0.5 * document_correct / 50 + 0.5 * memory_correct / 16)`

Documents and cross-session memory receive equal weight. This prevents the
larger document fixture from dominating the result. Four memory development
questions are checked but excluded from all primary scores. A secondary
retrieval comparison sends native Hindsight source chunks or RAGFlow retrieval
chunks to the same reader with a 4,096 `cl100k_base` context limit. Its score is
reported separately and does not add duplicate credit to the native score.
Costs, observed times, failures, and source fidelity are separate measures;
no arbitrary cost or speed penalty is mixed into accuracy.

There are 50 document questions: all 20 valid questions from the earlier complex
PDF fixture and all 30 parser-stress questions. The four ambiguous empty-cell
cases from the original fixture remain excluded for both systems. The memory
fixture has 20 dated records, 16 test questions, and four development questions.
It covers updated decisions, historical state, cross-session recovery, and
abstention. In total, each of four conditions answers 70 questions, for 280
outputs. These are 66 primary questions, not 264 independent test items.

## Matched inputs and model configuration

Both systems receive exactly the same retained Mistral OCR annotation text from
14 PDFs. The source PDF hashes are checked before input construction. The
annotations are reused without another OCR call. The original PDF-to-text
boundary remains inspectable in the previous reports. Both receive the same
memory record text; Hindsight additionally receives the dates as native
supported timestamps. No answer key or expected-value correction is ingested.

This evaluates RAGFlow with Mistral OCR preprocessing against Hindsight with the
same preprocessing. It does not handicap Hindsight with the free OCR errors,
and it does not claim that Hindsight provides a native PDF parser. Raw PDF
bounding boxes and automatic OCR routing are not scored here. The result is a
system comparison conditional on this input boundary.

Release API checks confirm Hindsight 0.10.3 and RAGFlow 1.0.0-rc1 as the current
latest releases for this run. Both run in Docker on the same ARM host. RAGFlow
uses AMD64 emulation; Hindsight uses ARM64. Observed times are not a matched
production-hardware speed ranking. The shared answer model is
DeepSeek V4.1 Flash with maximum reasoning. The catalog lists a 1,048,576-token
context and 943,718-token model-level maximum completion. A later endpoint
check reports a 393,216-token limit for the selected DeepSeek route; the
benchmark still requests 943,718 and does not impose a smaller local limit.
The model-level catalog maximum is not proof of the endpoint output capacity. The gateway applies that output
maximum to internal and final LLM calls; it does not silently retain native
4,096- or 8,192-token generation limits. Context and native retrieval budgets
remain explicit, distinct from generated output limits. Provider usage records
the actual model, output limit, reasoning setting, tokens, and charge.

Both systems use Qwen3 Embedding 8B at 1,536 dimensions and the local
`cross-encoder/ms-marco-MiniLM-L-6-v2` reranker. RAGFlow uses native top 20 for
chat, page size 64 for retrieval, threshold 0, vector weight 0.3, and top-k
1,024. Hindsight recall uses `budget=high` with original chunks, without the
old five-hit cut. Reflect uses its native tools and `budget=high`.

All calls pass through the same cumulative USD 20 ledger. The maximum-output
profile serializes provider requests so worst-case reservations fit within the
remaining budget. Product operations are serial. Native ingestion completes
before scored queries. Gateway transport timeout is 3,600 seconds and the
answer consumer timeout is 3,660 seconds. The legacy 1,800-second ingestion polling deadline was extended to 7,200
seconds while native consolidation was still running. A controller handoff
kept the same gateway, containers, banks, and pending operations; it did not
resubmit documents. The receipt records the handoff. One later RAGFlow request hit its native HTTP response-header timeout; the
upstream gateway then recorded a transport-uncertain request. Its full USD
1.1390796 reservation remained in the ledger. Subsequent chat admissions were
blocked by the conservative USD 20 ceiling. A gateway restart tightened both
the enforced route price caps and reservation rates to the current DeepSeek
weekend prices (USD 0.15/M input, USD 0.60/M output), instead of the earlier
USD 0.30/M and USD 1.20/M caps. The model, route, reasoning, and requested
output limit stayed fixed. Hindsight restarted with the same data volume to
receive the new gateway credential. RAGFlow kept its existing data. All 221
completed answers were retained, and only failed or missing answers resumed.
No uncertain charge was released. Completed answers are never
replaced by a better retry. Failed attempts and their costs remain visible.

## Scoring and interpretation

Automatic scores are preserved. Semantic review requires all requested values,
checks literal copyable identifiers, and accepts a supported statement that
requested information is absent. A response can mention a superseded value
only when it clearly identifies that value as historical. Wrong or incomplete
answers do not receive full credit. The Codex agent reviews the outputs; this
is not an independent blinded human assessment.

This closes the matched comparison of the existing fixtures. The corpus is
small, synthetic, and already inspected. Some native retrieval responses can
include most or all source records. Results do not establish large-corpus
retrieval quality, resistance to malicious documents, production latency,
long-term memory quality over months, or a universal product ranking. A tied
ceiling score means this fixture cannot distinguish the products further.
Earlier parser and product evidence remains unchanged.

## Results and failure analysis

| Condition | Documents | Memory test | Weighted score / 100 |
| --- | ---: | ---: | ---: |
| Hindsight native reflect | 50/50 | 16/16 | 100 |
| RAGFlow native chat | 50/50 | 16/16 | 100 |
| Hindsight retrieval + shared reader (secondary) | 50/50 | 16/16 | 100 |
| RAGFlow retrieval + shared reader (secondary) | 50/50 | 16/16 | 100 |

Each native system scored 4/4 on each memory category: updates, cross-session
recovery, historical state, and abstention. Each condition also passed all four
development questions, which do not affect the table.

| Preserved automatic match count | Documents | Memory test |
| --- | ---: | ---: |
| Hindsight native | 21/50 | 4/16 |
| RAGFlow native | 47/50 | 7/16 |

The automatic matcher rejects any forbidden old identifier even when the answer
clearly labels it as historical. It also expects a narrow `unknown` string for
absence questions. The declared review rubric accepts a clearly superseded
identifier and explicit supported absence. All overrides retain the original
automatic result, an explanation, and the answer SHA-256. This is why the raw
match counts differ from the semantic scores; no stored answer was edited.

Hindsight native traces contain 149 `search_observations`, 217 `recall`, and 22
`expand` calls. Both native banks finished consolidation: 14 document records
produced 79 world facts and 52 observations; 20 memory records produced 67
world facts and 32 observations. Final native stats show no pending or failed
operations or consolidation. Thus the run did exercise native Hindsight memory.

The source audit checked 3,254 returned source references with no unknown source
identity. Every returned Hindsight source chunk checked was a literal substring
of its original ingested text. The 4,096-token shared-reader context limit
shortened 50 Hindsight and 32 RAGFlow test contexts; this is a retrieval-context
limit, not an output-generation cap. The native scores do not use this wrapper.

Both native systems answered all 50 document questions correctly: 20 legacy
complex-document questions, 10 mixed-scan questions, 10 Chinese questions, and
10 complex-table questions. Both secondary retrieval conditions also answered
all 50 correctly. This is an answer result after matched Mistral preprocessing;
it is not a new standalone parser score.


In `stress-002`, Hindsight retained correct source facts for both dispatchers,
but a consolidated observation combined Nolan Wu and Clara Lin without a clear
document boundary. Native reflect identified the conflict, checked the source
records, and correctly answered Clara Lin for Harbor mixed A. This is a
recovered internal consolidation error, not a failed final answer. The saved
native trace contains the observation and source facts. It shows both the risk
of merging similar records and the value of source-backed native reflection.
The primary score checks requested values; it does not certify every extra
sentence in an explanation.


## Usage, validation, and cleanup

| Measure | Hindsight | RAGFlow |
| --- | ---: | ---: |
| Confirmed ingestion API cost | USD 0.341872 | USD 0.000067 |
| Confirmed native-query API cost (70 answers) | USD 0.429838 | USD 0.052547 |
| Confirmed ingestion + native-query cost | USD 0.771710 | USD 0.052614 |
| Native-query chat requests | 268 | 70 |
| Native-query output tokens, including reasoning | 281,294 | 17,695 |
| Median successful test-query time | 35.9 s | 5.4 s |
| Median test-answer length | 843.5 characters | 63 characters |

Query costs include the four development answers. They exclude the secondary
reader conditions, shared setup calls, failed attempts, and the reused OCR
preprocessing charge. The secondary Hindsight and RAGFlow readers cost USD
0.055229 and USD 0.043410, respectively.
All recorded token costs already include provider cache pricing. Hindsight
native queries report 1,770,496 cached input tokens; RAGFlow reports 52,736.
No extra cache discount is subtracted from the recorded charges.

Hindsight document and memory ingestion took 2,121.8 and 1,119.1 seconds.
RAGFlow took 87.6 and 108.4 seconds. Hindsight performed extraction and
consolidation; RAGFlow ingested the already parsed annotations and memory text.
These are measured run times under serial gateway execution and different
container architectures, not a universal production latency ratio. Longer
answers and more internal reasoning do not receive extra accuracy credit.

There were 34 archived failed answer attempts: one native RAGFlow response-
header timeout and 33 subsequent local-budget admission failures propagated
through the native APIs or shared reader. All were retried successfully; no
completed answer was retried. A separate ingestion embedding HTTP 504 also
appears in the provider ledger; native ingestion ultimately completed. These
failures are operational evidence, not silently counted as incorrect answers.

The run added **USD 0.923024 in confirmed charges**. Cumulative
confirmed charges are **USD 16.939535**. Including all older
and current unknown-cost reservations, cumulative exposure is **USD 19.067354**
against the USD 20 ceiling. The current transport-uncertain chat retains USD
1.1390796, and the embedding 504 retains USD 0.0008592. These are upper-bound
reservations, not confirmed charges. They are not released merely because the
answer retry succeeded. In particular, the RAGFlow timeout prevents a claim
about its fully settled total bill. The confirmed successful-call costs above
are still directly observable.

Validation: 153 benchmark contract tests passed. The final documentation check,
TOML format check, whitespace check, and offline evidence verifier passed.
The verifier checks file hashes, case uniqueness, completion, review bindings,
score arithmetic, request ordinals, confirmed charges, and the USD 20 ceiling.
It does not substitute for semantic review.

Cleanup verified removal of all eight owned containers, seven data volumes,
one network, and eight newly pulled images. No global prune was used. Local
benchmark credentials were deleted after the public evidence privacy scan.
The before/after snapshot also detected unrelated service changes during the
long run; those resources were outside the removal list and were not modified
by this cleanup. No claim is made that the entire host stayed unchanged.

Public evidence: [manifest](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/manifest.json),
[evaluation](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/evaluation.json),
[accounting](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/accounting.json),
[review](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/review.json),
[source audit](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/source-audit.json),
and [offline verifier](../../../config/benchmark/evidence/2026-10-10-final-system-comparison/verify.py).
Run the verifier with `python3 config/benchmark/evidence/2026-10-10-final-system-comparison/verify.py`.
