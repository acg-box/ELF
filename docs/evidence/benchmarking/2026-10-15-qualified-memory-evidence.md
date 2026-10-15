---
type: Evidence
title: Qualified memory evidence and source-use failures
description: Compare a read-only quote projection with the frozen extractor and retain the rejected extraction experiment.
status: completed
authority: informative
owner: benchmark
last_verified: 2026-10-15
code_refs:
  - packages/elf-service/src/evidence/pack.rs
  - packages/elf-service/src/evidence/pack/windows.rs
  - scripts/benchmark_pilot/tools.py
related:
  - docs/decisions/2026-10-15-qualified-memory-evidence.md
  - docs/runbook/agent-evidence.md
  - docs/evidence/benchmarking/2026-10-14-bounded-source-evidence.md
---
# Qualified memory evidence and source-use failures

The delivered change preserves existing note context and bound source quotations
in the native evidence pack. It uses the original extractor and stored evidence;
it does not rewrite originals or ask a model to transcribe qualifiers again.
The trial separates extraction loss, selection of citable originals, and errors
after evidence reaches the reader. It does not establish customer readiness or
a general advantage over capable file tools.

The original frozen coverage changed from **46/64 to 49/64**, and complete
acceptance from **3/16 to 6/16**. The new variants changed from **27/32 to 26/32**
and **3/8 to 2/8**. The result is a local improvement on some obligations, with
no reliable improvement established on the new variants. Historical/current and
wrong-owner errors remain.

## Results and scoring boundary

The original eight tasks and four new frozen variants each have two repetitions
per arm. Each answer has four composite obligations. Every required part must be
present; semantic equivalents count. Complete acceptance also requires supported
material claims and usable output. These are source-based assistant judgments,
not independent or blinded evaluations, and coverage is not factual accuracy.

One original promotion-receipt obligation uses an ambiguous source label. The
first score column excludes that same obligation in both repetitions for every
arm, including the prior results. Frozen acceptance counts remain unchanged.
The new questions have no such scoring exclusion.

| Condition | Original coverage, prior → final | New coverage, baseline → final | Original frozen acceptance | New frozen acceptance |
| --- | ---: | ---: | ---: | ---: |
| Archived file search | 48 → 36/62 | 26 → 24/32 | 5 → 5/16 | 4 → 4/8 |
| Original-source retrieval | 42 → 45/62 | 28 → 26/32 | 5 → 5/16 | 6 → 5/8 |
| Full ELF | 46 → 49/62 | 27 → 26/32 | 3 → 6/16 | 3 → 2/8 |
| Supplied originals (diagnostic) | 50 → 49/62 | 31 → 30/32 | 6 → 6/16 | 7 → 7/8 |

For auditability, the original frozen coverage below retains the disputed item.
Time and cost describe the final original-task cohort and exclude preparation.

| Condition | Original frozen coverage | Median answer time | Mean answer cost |
| --- | ---: | ---: | ---: |
| Archived file search | 49 → 37/64 | 31.8 s | $0.002770 |
| Original-source retrieval | 44 → 47/64 | 42.7 s | $0.002369 |
| Full ELF | 46 → 49/64 | 37.2 s | $0.003074 |
| Supplied originals (diagnostic) | 52 → 51/64 | 14.9 s | $0.000816 |

Controls vary despite unchanged reader behavior. This small retrospective replay
does not isolate a stable product effect from reader and selection variance.
The file baseline searches a frozen archive of historical snapshots; it is not
a full current-checkout shell agent. Supplied originals have preselected source
bytes and do not include source-selection cost. All arms use the native citation
checker, so the comparison is not a test of the whole value of ELF provenance.

## Where information was lost or misused

| Boundary | Evidence | Disposition |
| --- | --- | --- |
| Extraction | The frozen 79 proposals and 45 admitted notes had no populated structured fields. A short summary omitted a positive assignment-ID predicate; another omitted the reason for a required data/image pair. | Preserve selected original clauses. Do not assume a short summary is a complete rule. |
| Evidence materialization | The pack loaded note kind, project, scope, structured facts and source origin but discarded them. It also omitted the stored supporting quotes as a compact note-linked view. | Return existing context and quotes without another write or model pass. |
| Candidate to citable original | A source-only search returned the entire short retirement record in its discovery snippet. The reader repeatedly searched and opened other sources, then left retirement unknown. A full-ELF pack delivered that record with a usable original reference. | This was not an index miss. The next useful boundary is selection and hydration of the relevant current original. |
| Missing source premise | One intermediate full-ELF answer recovered the exact success predicate through ordinary-file fallback even though its new summary still omitted it. | Credit the original read, not improved extraction. Follow a named helper or source when its conditions are missing. |
| Reader interpretation | Answers still applied old runner controls or a parent project's delivery gate to the wrong checkpoint or independent replacement. Some omitted qualifiers after reading the correct source. | Metadata and binding checks do not prove applicability or entailment. |
| Benchmark authority | A reader identified two different acceptance results described with a similar short label. The frozen obligation demanded an unqualified promotion claim. | Retain the raw scores and apply the symmetric sensitivity exclusion. Do not count justified uncertainty as a demonstrated model error. |

The final pack returns `note_type`, storage `project_id`, visibility `scope`,
existing `facts`, and source `origin`. It copies `evidence_quotes` from the note's
already admitted evidence, then retains only quotes present in its linked,
readable returned windows. Duplicates are removed. If the host trims a window for
its result budget, it also removes quotations left without that window. These
fragments are not complete rules; cite the original window and preserve subject,
effective time, conjunctions and exclusions. A stored project is not an inferred
claim subject. No timestamp automatically establishes supersession.

## Rejected extraction candidate

The first candidate changed profile v7 to request additional `structured.facts`.
All 96 formal and eight calibration answers were retained. It produced 77 memory
proposals, admitted 38, rejected 30 for length, and rejected nine for structured
binding. Each of those nine offending fact strings was not verbatim in its input.
Six admitted notes stored 13 valid facts, but that did not justify the lost writes
or a second model transcription of already selected source clauses.

The profile change was reverted. The final implementation retains profile v6,
the same 79 frozen proposals, 45 admitted notes and 140 verbatim source quotes.
Its read-only projection works with existing notes. MMR stays enabled, the note
limit stays at 240 characters, and the shared reader stays at v4. This is not a
length-limit, storage, graph, or model comparison.

## Source ambiguity and reproducibility

One paragraph in the same original says that Main Release records Registry
acceptance with image digests in a signed tag. Another describes a separate
Registry Acceptance receipt after Runtime Release, which that release does not
wait for, sign, or embed. A read-only check of two workflow files at the exact
historical commit distinguished runtime proof included in Staging acceptance
from the separate owner receipt. Those files were not added to any reader input.
The captured README and rubric do not adequately distinguish the two objects.

All questions, source bytes, rubric and exact-source selections remained frozen.
No answer was regenerated or replaced. The new questions are targeted variants
on the same history, not an external holdout. The final 24-cell ELF-only run uses
the original frozen extraction and reuses the completed non-memory controls:
their paths, inputs and reader did not change. The intermediate 96-cell run is
published separately. One host amendment before formal execution removes the new quote
field when its original is trimmed; both recorded calibration packs were
untruncated, and no reader prompt or semantic answer was tuned.

Final native and host source is frozen at `8ef7e4c7`; the intermediate extraction
candidate is `7c5edcc7`. Runtime artifacts record binary and reader-file hashes.
The API/worker binaries used for final calibration and formal execution match.
The model is OpenRouter `openai/gpt-6-luna`, OpenAI provider, medium reasoning,
with the full 128000 output-token allowance. Embeddings use
Qwen3-Embedding-8B through Nebius at 4096 dimensions. Budgets remain eight model
rounds, sixteen tool calls, 32768 evidence bytes, and 12000 bytes per result.
The [endpoint metadata](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints)
was checked before execution; settled receipt costs include prompt-cache charges.

The final trace audit verified 238 original bodies
and 12 bounded native reads. All matched
the unchanged original bytes and respected the read cap. It checked
144 quote presentations against admitted
quotes and their returned original windows. The corpus remains 14 records and
137723 bytes. Isolated PostgreSQL/Qdrant restores preserved original hashes,
note/provenance and structured-field payloads, and full 4096-dimensional vectors.

## Cost and validation

The task added **$0.412301940** to the existing reset-budget ledger.
Cumulative settled cost is **$1.687181471**; conservative cumulative
exposure is **$1.757666271**, below the authorized $10 ceiling.
The historical unresolved request still reserves $0.0704848. These totals include
the rejected candidate, calibration, preparation and failed/uncertain calls.
Reused embeddings and extraction were settled in earlier runs; this is not a
cold-start cost estimate, and local compute is not priced here.

The final implementation passed formatting, Clippy and 108 Docker integration
checks, including literal quote retention, source-window budgets, current access
and unchanged originals. Runner contracts cover fresh-extraction cache bypass,
quote removal on host truncation, and privacy of public exports. Full repository
checks and exact-head delivery evidence are recorded with the pull request.

The [comparison data](../../../config/benchmark/evidence/2026-10-15-qualified-memory-evidence/comparison.json),
[new-question baseline](../../../config/benchmark/evidence/2026-10-15-qualified-memory-evidence/baseline-new/manifest.json),
[rejected extraction candidate](../../../config/benchmark/evidence/2026-10-15-qualified-memory-evidence/extraction-candidate/manifest.json),
and [final ELF run](../../../config/benchmark/evidence/2026-10-15-qualified-memory-evidence/pack-only/manifest.json)
contain de-identified measurements and standalone verifiers. Private source text,
questions, answers, traces, credentials and provider responses remain outside
the published bundles.
