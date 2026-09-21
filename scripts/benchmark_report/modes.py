"""Render v2 mode evidence without claiming a complete measured competitor run."""
from __future__ import annotations


def publish_modes(bundle):
    lines = ["# Benchmark result", "", f"Mode: {bundle['mode']}",
             f"Execution passed: {bundle['acceptance']['passed']}",
             "", "Execution success does not establish product quality or superiority.",
             "Quick mode does not execute ELF, external products, or model answers.", "",
             "| Suite | Target | Status | Reused | Seconds |", "| --- | --- | --- | --- | --- |"]
    for name, suite in sorted(bundle["suite_results"].items()):
        for row in suite["results"]:
            lines.append(f"| {name} | {row['target']} | {row['evaluation']['classification']} | "
                         f"{row.get('reuse', {}).get('reused', False)} | {row.get('duration_seconds', 0)} |")
    lines += ["", "## Warm retrieval metrics", "",
              "| Suite | Target | Recall@5 | nDCG@5 | Answer correctness |", "| --- | --- | --- | --- | --- |"]
    for name, suite in sorted(bundle["suite_results"].items()):
        for row in suite["results"]:
            metrics = row["evaluation"].get("phases", {}).get("warm", {}).get("metrics") or {}
            def value(key):
                measured = metrics.get(key)
                return "not measured" if measured is None else str(measured)
            lines.append(f"| {name} | {row['target']} | {value('mean_recall_at_5')} | "
                         f"{value('mean_ndcg_at_5')} | {value('programmatic_answer_correctness')} |")
    lines += ["", "## Findings", ""] + [f"- {f}" for f in bundle["acceptance"]["findings"]]
    lines += ["", "## Seeded invariant findings", ""]
    for finding in bundle.get("quality", {}).get("seeded_violations", []):
        lines.append(f"- {finding['target']}/{finding['job']}: {finding['reason']}")
    missing = [key for key, present in bundle.get("provider_configuration", {}).items() if not present]
    if missing:
        lines += ["", "Missing provider configuration: " + ", ".join(missing)]
    lines += ["", "## Selected scenarios", ""]
    for suite, jobs in sorted(bundle["coverage"].items()):
        lines.append(f"- {suite}: " + ", ".join(jobs))
    lines += ["", "## Coverage limits", "", "Unmeasured: native host memory, end-to-end agent actions, Chinese inputs, "
              "ACL enforcement, restart recovery, and large-corpus behavior. Use the repository integration/E2E gates "
              "for their existing guarantees. File search is a lexical baseline, not a simulated competitor.", "",
              "All raw unit results and evaluator metrics are in bundle.json. Reused timings are historical samples."]
    return "\n".join(lines) + "\n"

