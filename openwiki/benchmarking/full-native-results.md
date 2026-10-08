---
type: Evidence
title: Full native benchmark results and limits
description: Closed October 8 execution, retained coverage gaps, cumulative costs, and evidence-backed ELF priorities.
tags: [benchmark, memory, evidence, cost]
verified:
  - by: openwiki/0.7.1
    at: 2026-10-08T21:07:20.478Z
sources:
  - id: openwiki-source-41de5f94ac6ea55c66eee31a
    resource: repo://config/benchmark/evidence/2026-10-08-full-native/accounting/summary.json
  - id: openwiki-source-6219396479a72b88e3fa502e
    resource: repo://config/benchmark/evidence/2026-10-08-full-native/campaign.json
  - id: openwiki-source-1e5bdaedc43adf2b53403bc6
    resource: repo://config/benchmark/evidence/2026-10-08-full-native/native-mutations.json
  - id: openwiki-source-c661aed2c2b67ce97977fb6e
    resource: repo://docs/evidence/benchmarking/2026-10-08-full-native-comparison.md
generated: { by: "codex", at: "2026-10-08T21:07:20.478Z" }
---
# Full native benchmark results and limits

The October 8 campaign finished all registered execution queues. It did not
measure every planned query: native preparation failures and deadlines left
explicit gaps. Use the [dated report](../../docs/evidence/benchmarking/2026-10-08-full-native-comparison.md)
for the full tables. Do not interpret completed execution as universal product
coverage or a product ranking.

## What was measured

The original core selection covers fourteen products and two baselines, four
suites, and 768 planned answers. It retains 740 completed cold native queries,
739 completed warm native queries, and 739 isolated answers. Whole-condition
repeats and five recovery conditions remain separate. Successful cases from
different attempts are not combined into a replacement score.

Eight representative deep conditions add scale, cross-session recall, competing
authority, temporal changes, scope, updates, and deletes. Independent ELF and SAG
behavior conditions scored 41/42 and 42/42. The original GBrain full condition
scored 55/62 but six update refresh operations failed on an unsupported CLI
argument. The corrected independent mutation condition completed six updates,
six deletes, and 12/12 answers; it does not replace the original failures.

ELF, Hindsight, and Mem0 scale-1000 recoveries stopped on upstream embedding
HTTP 429 before retrieval could be measured. Mem0 retained 599 ingestion receipts
in 79.3 minutes before that failure. Its earlier transport disconnect remains a
different, unconfirmed cause. SAG's earlier scale timeout also remains in the
record. These outcomes measure execution reliability under the recorded route;
they do not establish scale retrieval accuracy.

The common repair workflow has 102 terminal trials: 89 passed validation, 11
were blocked during native preparation, and two executed without passing.
The separate native Letta workflow passed 6/6. File search and many products
also passed 6/6, while historical no-memory passed 5/6. Three tasks repeated twice
provide limited discrimination; these results do not prove a general coding
advantage from memory.

## Cost and traceability

Cumulative reported API cost is **$8.742426971**. Unknown-cost reservations add
**$0.284895900**, for conservative exposure of **$9.027322871**, below the latest
$20 authorization. The 33,552-request ledger includes pilots, invalid attempts,
and recoveries. Host compute, CI, and Codex orchestration are excluded. Costs
already reflect provider caching; recorded chat-input cache hits were 75.59%.
Unknown usage is not assigned zero cost or zero tokens.

The [campaign manifest](../../config/benchmark/evidence/2026-10-08-full-native/campaign.json)
records data hashes. The [provenance](../../config/benchmark/evidence/2026-10-08-full-native/provenance.json)
retains source revisions and available image fields. Compressed JSONL files in
that evidence directory preserve cases, operations, repair trials, and usage.
Null image or cleanup fields remain unknown. Raw credentials, service state,
and provider reasoning are excluded from publication.

## What to improve next

The ELF behavior miss returned `unknown` although the first supplied context
contained the required checkpoint. Keep reader and retrieval failures separate.
Prioritize observable ingestion readiness and recovery from upstream failures.
Keep source authority and superseded facts explicit instead of relying solely
on a capable reader to resolve conflicting retrieved context.

Do not infer tenant authorization from synthetic canaries or external ontology
support from this campaign. Future benchmark changes need new frozen tasks and
a strong file baseline; preserve this campaign's measured outcomes.

Use [calibration and comparison](calibration-and-comparison.md) for protocol and
historical pilot boundaries, and [quickstart](../quickstart.md) for commands.
