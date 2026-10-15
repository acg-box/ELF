---
type: Evidence
title: "Recheck ELF intent against current agent-memory research"
description: "Review primary sources, identify product-contract drift, and bound the next memory-value experiment."
status: completed
authority: informative
owner: product
last_verified: 2026-10-15
code_refs:
  - packages/elf-domain/src/text_validation.rs
  - packages/elf-service/src/entity_memory/types.rs
  - packages/elf-service/src/entity_memory/service.rs
  - packages/elf-service/src/graph_query.rs
  - packages/elf-service/src/update_resolution.rs
  - packages/elf-service/src/docs/source_capture.rs
  - scripts/benchmark_pilot/tools.py
  - config/agent/evidence-reader.md
  - .github/workflows/external-memory-pattern-radar.yml
related:
  - docs/spec/agent_memory_knowledge_system_v1.md
  - docs/reference/product-direction.md
  - docs/decisions/2026-10-10-language-neutral-source-memory.md
  - docs/evidence/benchmarking/2026-10-14-bounded-source-evidence.md
---
# Recheck ELF intent against current agent-memory research

Purpose: Record the evidence behind the October product-alignment update.
Read this when: Reviewing the next memory-value experiment or the rationale for
separating stable goals from replaceable mechanisms.
Not this document: A new benchmark, competitor ranking, market-demand study, or
authorization to adopt a dependency or run paid experiments.

## Conclusion

Keep source-backed project continuity as the goal. Treat better memory quality,
lower total cost, and reduced user correction as hypotheses to prove in real
work. Recent sources support targeted evidence retrieval, explicit time/scope,
and separate evaluation of memory creation and use. They also challenge any
assumption that a dedicated memory architecture must beat files or long context.

The previous proposal to repair subject/time propagation is a reasonable next
diagnostic, not a proved complete solution. Correct originals can still produce
wrong answers. The next test should distinguish missing extraction, missing
delivery, evidence presentation, and reader behavior. Current-state verification
may help where historical text cannot establish a live fact.

## Review scope and source quality

Reviewed on October 15, 2026: current ELF source at baseline
`c1963dffbf40db1f27d39de66443c972647bb797`, its product/experiment contracts,
official project documentation, selected public source, and the papers below.
Paper dates are publication dates; the review date does not make their models or
implementations current. Vendor claims and preprints are hypotheses or bounded
author results, not independently reproduced ELF measurements. No provider model
call, new paid benchmark, runtime installation, or competitor deployment occurred.

| Primary source | Finding and implication for ELF | Boundary |
| --- | --- | --- |
| [Cognition Agent Memory Repo](https://cognition.com/agent-memory-repo) | A short entry point routes to source-linked memory and reusable artifacts; maintenance updates the store. Use one compact development entry point and existing linked authority. | File history alone does not prove current authority, scoped access, or useful task improvement. Do not copy its autonomous write policy into ELF. |
| [Hindsight best practices](https://hindsight.vectorize.io/best-practices) | Extraction context, stable document identity, explicit time, strict filters, and optional source facts/chunks affect retrieval. Similar text can have different purposes that ranking alone cannot distinguish. | This is vendor guidance. A recalled fact, observation, and synthesized answer have different contracts; its default filters must not be assumed to match ELF ACLs. |
| [Graphiti source](https://github.com/getzep/graphiti/blob/aca369364226a666ca541b061ff2a1a54b80f2ff/graphiti_core/edges.py) | Edge records distinguish creation/expiry from validity and carry source episodes. Compare these semantics with ELF's existing time and evidence fields before adding state. | Separate timestamps do not prove correct extraction or automatic supersession. A graph database migration does not follow from this review. |
| [Letta memory evaluation, July 28](https://www.letta.com/blog/evaluating-memory-in-production-agents/) | Memory generation/repair, retrieval, and adherence are distinct evaluation dimensions. A capable task model can still fail at memory maintenance. | Private, production-derived synthetic scenarios and model judgments are not an independent public comparison. Do not use its ranking to choose ELF's model without a role-specific test. |
| [Letta Trajectory, July 23](https://www.letta.com/blog/trajectory/) | Cross-harness experience can have a compact common view. | Its agent-facing normalization is not a full-fidelity replay format. Keep immutable originals and stable references behind any compact view; portability alone is not unique to ELF. |
| [GBrain README](https://github.com/garrytan/gbrain/blob/44eb0493ff2776f04d6616b1a526657702f7544a/README.md) | Source-linked facts, corrections, withdrawal, cross-agent use, and a keyless starting path already exist as product claims. ELF must demonstrate useful outcomes and acceptable setup cost. | The README distinguishes remote grants from shared local-file/database trust. This review does not verify its scale, authorization, or quality claims. |
| [OpenViking architecture](https://blog.openviking.ai/post/openviking-context-database-architecture/) | A navigable context hierarchy is another way to organize resources, memory, and skills for progressive access. | A useful interaction pattern does not require adopting its storage/runtime. Compare with ELF's existing pointers and pack views first. |
| [RAGFlow repository](https://github.com/infiniflow/ragflow/tree/9f94f13cd4865dc99b3d8bc42ae7ee2a3ce6fd1a) | Document ingestion and retrieval remain adjacent capabilities worth learning from when document evidence is the bottleneck. | Document QA scores do not establish cross-session decision-update quality. Keep parser and whole-system comparisons separate. |
| [Anthropic context engineering, September 29, 2025](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Small useful context, clear tools, progressive retrieval, and a task-dependent mix of preparation and exploration are consistent with a bounded source-plus-memory interface. | This engineering guidance is older than the current model landscape. Recheck workarounds as models improve; do not encode an expanding list of benchmark-specific rules. |

## Research that changes the experiment design

| Paper | Useful result or method | What to carry into ELF |
| --- | --- | --- |
| [LongMemEval-V2, May 12](https://arxiv.org/html/2605.12493v1) | The work-in-progress benchmark separates static state, dynamic state, workflow knowledge, gotchas, and premise awareness. Its oracle study shows that evidence slices and notes can outperform whole answer-bearing trajectories. | Keep a supplied-source diagnostic, distinguish selection from reading, and test wrong premises. Supplying the right document does not isolate the reader from all presentation effects. Do not compare its percentages with ELF's composite obligations. |
| [EvoMemBench, June 15 revision](https://arxiv.org/html/2605.18421v2) | Strong long-context baselines remain competitive; revision is harder than retention, and benefits vary by memory type and task. The study counts task-agent and memory-module tokens. | Preserve strong controls and total-cost accounting. Evaluate decision changes and procedural reuse, not only whether an old fact can be retrieved. No universal winner is established. |
| [Filesystem-Based Memory, July 29](https://arxiv.org/html/2607.26637v1) | The study varies store organization, tools, and management/search models. Organization can lower search cost while failing to improve answer quality, and store health can decline as records accumulate. | Measure upkeep and growth as well as retrieval. Do not assume Markdown, a hierarchy, or a new memory manager is automatically simpler or more accurate. |
| [Grounding Agent Memory, September 10](https://arxiv.org/html/2609.11060v1) | Targeted read-only environment probes check candidate memories while leaving the task agent and write authority unchanged. The controlled study uses explicit drift and separates curator work. | A narrow source check is a candidate for stale-state failures. Preserve application authority and evaluation cutoffs. Reported task-agent savings exclude distillation/curation; count those costs before claiming a total saving. |
| [Agent Zero Memory, August 30](https://arxiv.org/html/2608.29606v1) | The paper proposes provenance-aware routing and skips retrieval for self-contained turns, with a more complex multi-search design. | Test whether retrieval is needed. Do not copy its parallel-agent architecture without evidence that a simpler route fails. Published scores are not ELF comparison results. |

## Activity check

GitHub API readback found all eight repositories below unarchived. Exact default
branch heads were recorded to distinguish source snapshots from moving websites.
Push recency is only a signal: a CLA or banner update is not algorithm progress,
and a vendor's current SDK may be maintained outside its older server repository.

| Repository | Observed head | Last push (UTC) |
| --- | --- | --- |
| vectorize-io/hindsight | `d5b1d4282f3325116c06f76ce3e79dce5ea4e22c` | 2026-10-14 16:03:42 |
| getzep/graphiti | `aca369364226a666ca541b061ff2a1a54b80f2ff` | 2026-10-15 00:19:20 |
| letta-ai/letta | `5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a` | 2026-09-10 17:59:08 |
| garrytan/gbrain | `44eb0493ff2776f04d6616b1a526657702f7544a` | 2026-10-15 05:55:46 |
| AgentMemoryRepo/agentmemoryrepo | `8798cb26c817d451a5ed6cba0ad8d9eca8d5ec3e` | 2026-10-06 23:52:20 |
| volcengine/OpenViking | `9baf83f04ce0245d1d543d4b7dfc637eb0f64ec3` | 2026-10-15 05:45:38 |
| infiniflow/ragflow | `9f94f13cd4865dc99b3d8bc42ae7ee2a3ce6fd1a` | 2026-10-15 06:02:08 |
| mem0ai/mem0 | `0724291bd864cf807e88ee8981c8226644e8fb42` | 2026-10-14 15:40:09 |

## ELF semantic drift audit

| Inspected authority or code | Finding | Disposition in this documentation change |
| --- | --- | --- |
| Product spec versus the October 10 language-neutral decision and domain/service contracts | The product spec still required an English gate after its accepted removal. | Remove the obsolete constraint and link the successor; retain historical evidence. |
| Product spec execution program and current experiment | The normative entry still led readers through the July P0-P5 program. | Label that program as historical and route current work to one current-direction reference. |
| `entity_memory` types/service, `graph_query`, and `update_resolution` | Subject identity, validity, lifecycle, and explicit update identity already exist. The entity view uses current time; historical graph queries have their own `as_of`. | Do not claim a uniform historical interface or propose a second state model without tracing the actual failing path. |
| `evidence-reader.md` and the reference benchmark host | The host forces a memory opening to verify use. A valid native binding does not evaluate semantic support. | Preserve reproduction and label task-dependent routing as a separate experiment, not a delivered behavior change. |
| October 14 report | Full ELF did not beat direct files. Supplied originals also left omissions and wrong-scope answers. | Keep the result unchanged; do not attribute every failure to extraction or ranking. |
| Existing radar workflow and runbook | The weekly job refreshes metadata and uploads artifacts. [October 14 run](https://github.com/acg-box/ELF/actions/runs/38543242417) succeeded. | Keep it as a signal producer. Success does not prove source research or decision updates occurred. |
| `AGENTS.md`, README, and PR entry | No compact route connected ordinary development to current intent and evidence. | Add links to the existing product authority and current direction; keep routine fixes proportionate. |

The public [Agentry issue 25](https://github.com/acg-box/agentry/issues/25) records
the shared alignment and central-review requirement. It does not mean the plugin
is installed, the mechanism has run, or an automation is active. No new recurring
task or per-repository scheduler was created. ELF retains its own intent and
decision evidence; Agentry owns the reusable method and coordination work.

## Verification boundary

This change updates documentation and development guidance only. Source inspection
supports the drift findings; the existing trial supports the measured scores.
`cargo make fmt`, `cargo make lint-fix`, and `cargo make check` passed. The check
ran 473 Rust tests, 209 benchmark-contract tests, and four tooling tests; 108
environment-dependent integration tests remained skipped. The documentation
link/task check and manual frontmatter/ownership review passed. No runtime file
changed, and no new Docker integration run was required for this documentation
scope. These checks do not prove future agent compliance or product benefit.
The next implementation and natural longitudinal pilot remain unperformed.
