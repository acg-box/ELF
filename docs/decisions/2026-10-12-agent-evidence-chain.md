---
type: Decision
title: Keep claim evidence dependencies explicit and request-local
description: Preserve source bridges without duplicating citation authority or adding a semantic oracle.
status: accepted
authority: normative
owner: elf-service
last_verified: 2026-10-12
---
# Keep claim evidence dependencies explicit and request-local

Two prior Cobalt answers cited a real event source but omitted the original that
connected its person to Cobalt. That identity source was already in context.
Retrieving more text alone does not correct this output-composition defect.

Add optional backward `depends_on` indices to native claims. The service expands
the direct citations of each required premise once and returns their originating
claim indices. It checks current source access and propagates failed bindings.
Requests without dependencies preserve the previous serialized contract. The
same original can support more than one claim without caller-side quote copying.

This is a bounded topological dependency list: at most twelve claims with eight
direct citations each, hence at most 96 expanded slots per claim. Backward indices
make cycles impossible; a fixed-size reachability array prevents diamond paths
from duplicating invalid slots exponentially. Existing Rust collections and the
native citation resolver are sufficient. A graph library or database would add
ownership and persistence without an obligation. Reconsider this choice only if
the claim limit or supported dependency direction changes.

The agent declares the chain. ELF does not infer missing identity, certify
entailment, or silently turn extracted graph aliases into proof. An unknown or
conflicting premise must remain qualified in the answer. Original bytes and
stored memory remain unchanged. No migration or model call is required.

The maintained comparison is the source-backed recall and temporal separation
already documented in [the prior decision](2026-10-12-recall-time-graph.md).
This change addresses composition after retrieval. It does not introduce another
retriever, reranker, entity-merger, or semantic judge.

`config/agent/evidence-reader.md` owns the agent instructions. MCP publishes the
file verbatim; HTTP integration documentation directs callers to the same file.
The benchmark loads that exact file and receives only questions and sources.
The agent remains responsible for semantic reasoning and must render checked
expanded citations. The server cannot enforce how a third-party UI renders them.

The existing Python benchmark owner is explicit in
`docs/reference/module_ownership.md` and `makefiles/benchmark-live.toml`.
The new workload mode remains inside that established owner. It freezes eight
new cases before implementation, separately retains two prior regressions,
provides all case sources including distractors, and records one final response
per case. This tests source reading and citation composition, not search ranking
or independent blinded generalization. The budget gateway owns paid-call limits;
its reservations and old unsettled charges are not bypassed.

Acceptance requires native tests for transitive and diamond dependencies,
failed or inaccessible premises, deletion, malformed indices, legacy response
shape, and shared MCP instructions. Retain invalid and incorrect model responses.
A small fixed sample can reveal regressions; it does not prove general reliability.
