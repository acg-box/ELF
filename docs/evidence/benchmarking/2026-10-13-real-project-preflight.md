---
type: Evidence
title: Real-project memory pilot stopped at budget admission
description: Freeze real ELF handoff sources and record why no paid trial could start.
status: blocked
authority: informative
owner: benchmark
last_verified: 2026-10-13
---
# Real-project memory pilot stopped at budget admission

This is the preserved preflight result for the original cumulative budget and
seven-file workload. The later
[private-project trial](../../runbook/benchmarking/real_project_memory_trial.md)
uses a separately authorized budget and a different frozen corpus. It does not
replace this no-execution receipt or clear the older unresolved reservations.

The actual three-condition experiment did not run. The cumulative budget cannot
reserve even one full-output request at the verified current official-provider
price. No model or embedding call was sent, no native memory was ingested, and
no quality, latency, or memory-value result is claimed.

## Prepared scope

The pilot uses this repository's real merged project records at three immutable
checkpoints: PR 409 (`08772142`), PR 410 (`5e724589`), and PR 411 (`ff1147c8`).
Seven complete source files are captured byte-for-byte with Git blob IDs, commit
IDs, hashes, and canonical GitHub links. Four newly written handoff requests ask
about actual source-context work, updated recall decisions, Agent integration,
and the latest remaining limitations. These are retrospective task prompts,
not a replay of private user conversations.

Each of the four tasks has three planned conditions: no ELF with ordinary
repository/history access; persistent original-source retrieval; and full ELF
with the same sources plus native extracted memories. All groups have access to
the same source facts. The planned memory-value contrast is full ELF versus
source-only. Inputs from later checkpoints are forbidden at earlier checkpoints.

The frozen workload is `config/benchmark/real-project-pilot/workload.json`.
The [execution protocol](../../runbook/benchmarking/real_project_memory_pilot.md)
requires fresh reader processes, native extraction and 4096-dimensional vectors,
index readiness, complete failures, and preparation-inclusive costs. It is
prepared for subsequent execution; it has not passed native runtime acceptance.

## Budget stop

The official DeepSeek endpoint quote captured on 2026-10-13 has active prices
of $0.30/M input and $1.20/M output in the captured UTC time window. The selected
endpoint output maximum remains 393216 tokens. With the existing gateway's
8192-token input safety allowance and an otherwise empty request, the smallest
full-output reservation is:

`(8192 * 0.30 + 393216 * 1.20) / 1000000 = $0.4743168`

Real requests have input bytes and require more. This is a worst-case admission
reservation, not an estimate that each actual answer costs $0.474.

| Boundary | USD |
| --- | ---: |
| Previously settled | 8.555102170 |
| Previous unresolved reservations | 1.083800400 |
| Opening conservative exposure | 9.638902570 |
| Authorized cumulative ceiling | 10.000000000 |
| Remaining headroom | 0.361097430 |
| Minimum full-output request reservation | 0.474316800 |
| New settled spend | 0.000000000 |

The input ledger hash before and after preflight is identical. The two older
unsettled reservations remain present. Pricing has scheduled time-window
changes, so a later run must obtain a fresh quote. No scheduled run, provider
switch, smaller output cap, or automatic retry was created.

## Actual results

| Item | Result |
| --- | --- |
| Frozen sources | 7 |
| Handoff tasks | 4 |
| Conditions | 3 |
| Planned task-condition cells | 12 |
| Executed cells | 0 |
| Quality, latency, and memory benefit | Not measured |
| New model/embedding requests | 0 |

Offline verification checks source bytes against Git objects, source chronology,
condition parity, workload hashes, captured price selection, reserve arithmetic,
and the explicit no-result state. It does not test retrieval or cross-session
behavior. No Docker or service resources were created for this preflight.

```sh
python3 config/benchmark/evidence/2026-10-13-real-project-preflight/verify.py
```

The user instruction was to stop if the cumulative $10 allowance was insufficient.
That stop applies here. Resume only after a fresh price and ledger admit the
required requests under the authorized constraints. Until then, the memory
layer's real-project value remains an open question.
