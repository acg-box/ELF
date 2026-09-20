"""Benchmark report publish: derived only from measured bundle evidence."""

from __future__ import annotations

from typing import Any
import json

from .coverage import (
    common_ci,
    coverage_table,
    failure_table,
    native_contract_boundaries,
    provider_usage,
    result_table,
)
from .decisions import five_decisions, product_observations
from .labels import SUITE_NAMES
from .metrics import fmt, metric_leaders
from .roadmap import elf_job_summary, roadmap


def publish(bundle: dict[str, Any]) -> str:
    source = bundle.get("source") or {}
    routes = bundle.get("provider_routes") or {}
    preflight = bundle.get("provider_preflight") or {}
    acceptance = bundle.get("acceptance") or {}
    lines = [
        "# ELF Competitor Benchmark Report",
        "",
        "## Interpretation Boundaries",
        "",
        "This complete measured run is an internal ELF development decision tool. It is not a public leaderboard or superiority claim. Only comparable rows that used real self-hosted runtimes, real APIs, and ended as `completed` enter a quality denominator. Provider, product, adapter, harness, timeout, cleanup, and configuration failures keep their exact type and are not converted to zero scores.",
        "",
        f"- Run mode: `{bundle.get('mode')}`; acceptance passed: `{fmt(bool(acceptance.get('passed')))}`.",
        f"- Fixed source: `{source.get('head', 'unknown')}`; dirty=`{source.get('dirty')}`; content SHA-256=`{source.get('content_sha256', 'unknown')}`.",
        f"- Manifest SHA-256: `{bundle.get('manifest_sha256', 'unknown')}`; Docker Server: `{bundle.get('docker_server_version', 'unknown')}`.",
        f"- Chat: `{routes.get('chat_model')}` / reasoning `{routes.get('chat_reasoning_effort')}`; embedding: `{routes.get('embedding_model')}` / `{routes.get('embedding_dimensions')}` dimensions.",
        f"- Preflight: embedding `{(preflight.get('embedding') or {}).get('classification')}`; chat `{(preflight.get('chat') or {}).get('classification')}`.",
        "- Unsupported-answer rate, forbidden or stale evidence hit rate, and privacy-scope violation rate are lower-is-better. Other quality success rates are higher-is-better.",
        "- One target-blind Luna request produces the shared answers for each score-eligible unit. Answer correctness and unsupported-answer rate remain end-to-end observations. One sample and the query-to-qrel entailment boundary do not support native product attribution, so these fields do not declare product strengths, winners, ELF scenario strengths, or roadmap actions.",
        "",
        "## Decision Summary",
        "",
    ]
    for suite_id, suite in bundle.get("suite_results", {}).items():
        leaders = metric_leaders(
            suite["results"],
            (
                "mean_recall_at_5",
                "mean_ndcg_at_5",
                "source_or_citation_trace_rate",
                "programmatic_answer_correctness",
                "native_correction_and_update_success",
                "native_deletion_or_forgetting_success",
                "forbidden_or_stale_evidence_hit_rate",
                "privacy_scope_violation_rate",
            ),
        )
        if leaders:
            lines.append(f"- **{SUITE_NAMES.get(suite_id, suite_id)}**: " + "; ".join(leaders) + ".")
        else:
            lines.append(
                f"- **{SUITE_NAMES.get(suite_id, suite_id)}**: insufficient comparable completed rows; no leader is declared."
            )
    lines.extend(
        [
            "",
            "Conclusions are metric-specific. Conflicting metric leaders do not become one aggregate score or one global winner. Zero stale hits with zero recall do not prove stale suppression. Shared-answer metrics remain visible in tables and confidence intervals, but they do not support product attribution.",
            "",
            "## Five Product Decisions",
            "",
            *five_decisions(bundle),
        ]
    )
    for suite_id, suite in bundle.get("suite_results", {}).items():
        lines.extend(
            [
                "",
                f"## {SUITE_NAMES.get(suite_id, suite_id)}",
                "",
                "This numerical table contains only completed, score-eligible rows in the quality denominator. Coverage, failures, and native not-applicable boundaries remain in the dedicated tables below.",
                "",
                *result_table(suite["results"], suite_id),
            ]
        )
        if suite_id == "common-core-v1":
            lines.extend(
                [
                    "",
                    "### Job-level 95% confidence intervals",
                    "",
                    *common_ci(suite["results"]),
                ]
            )
    lines.extend(
        [
            "",
            "## Coverage and Failures",
            "",
            "Denominators are scheduled, completed, failed, directly proven not applicable, and actually scored. A capability-only native operation may complete, but `score_eligible=false` keeps it outside retrieval-quality denominators.",
            "",
            *coverage_table(bundle),
            "",
            "### Typed failures",
            "",
            *failure_table(bundle),
            "",
            "## Measured Product Observations",
            "",
            *product_observations(bundle),
            "",
            "## ELF Strongest and Weakest Scenarios",
            "",
            "The parenthesized value is the directional mean of metrics executed for one job. It locates ELF-internal strengths and weaknesses and is not a cross-product aggregate rank.",
            "",
            *elf_job_summary(bundle),
            "",
            "## ELF Development Order",
            "",
            *roadmap(bundle),
            "",
            "## Reproducibility and Limitations",
            "",
            "- Each `{suite,target}` uses an isolated Compose project. Scheduler capacity is two. Cleanup results are in the coverage table.",
            "- Shared answers must contain non-empty fact text or exact `unknown`. The raw chat response stays in the corresponding raw unit, then the central scorer applies deterministic fact checks.",
            "- Shared answers are sampled once. If a query does not entail every scorer-only answer fact, or the same native context can produce another answer, the value cannot prove a native product difference. The report keeps the observation but does not use it for a product winner, ELF scenario strength, or roadmap action.",
            f"- Image digests: `{json.dumps(bundle.get('target_image_digests') or {}, sort_keys=True)}`.",
            f"- Product pins: `{json.dumps(bundle.get('target_pins') or {}, sort_keys=True)}`.",
            "- Common Core uses job-level normal-approximation 95% confidence intervals. The frozen suite is internal descriptive evidence only.",
            "- The table below reproduces manifest not-applicable reasons and native deviations verbatim. Adapters do not disguise different native semantics as one CRUD contract.",
            "",
            "### Native-interface boundaries",
            "",
            *native_contract_boundaries(bundle),
        ]
    )
    usage = provider_usage(bundle)
    if usage:
        lines.append(
            f"- Provider-returned shared-answer usage total: `{json.dumps(dict(usage), sort_keys=True)}`."
        )
    else:
        lines.append("- The provider returned no aggregate token or request usage; cost is not inferred.")
    if acceptance.get("findings"):
        lines.append("- Unmet acceptance items: " + "; ".join(map(str, acceptance["findings"])) + ".")
    return "\n".join(lines) + "\n"

