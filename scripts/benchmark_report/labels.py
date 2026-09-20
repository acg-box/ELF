"""Names and display policies for measured benchmark metrics."""

SUITE_NAMES = {
    "common-core-v1": "Common Core (24 jobs)",
    "memory-lifecycle-v1": "Memory Lifecycle (8 jobs)",
    "knowledge-structure-v1": "Knowledge Structure (8 jobs)",
    "repository-knowledge-v1": "Repository Knowledge (8 jobs)",
}

METRIC_NAMES = {
    "mean_recall_at_5": "Recall@5",
    "mean_ndcg_at_5": "nDCG@5",
    "forbidden_or_stale_evidence_hit_rate": "Forbidden or stale evidence hit rate",
    "source_or_citation_trace_rate": "Source or citation trace rate",
    "programmatic_answer_correctness": "Programmatic answer correctness",
    "native_correction_and_update_success": "Native update success",
    "native_deletion_or_forgetting_success": "Native deletion success",
    "privacy_scope_violation_rate": "Privacy-scope violation rate",
    "unsupported_answer_rate": "Unsupported-answer rate",
    "mean_query_latency_ms": "Warm query latency (ms)",
}

LOWER_IS_BETTER = {
    "forbidden_or_stale_evidence_hit_rate",
    "privacy_scope_violation_rate",
    "unsupported_answer_rate",
    "mean_query_latency_ms",
}

SHARED_ANSWER_METRICS = {
    "programmatic_answer_correctness",
    "unsupported_answer_rate",
}

BASE_TABLE_METRICS = (
    "mean_recall_at_5",
    "mean_ndcg_at_5",
    "forbidden_or_stale_evidence_hit_rate",
    "source_or_citation_trace_rate",
    "programmatic_answer_correctness",
    "unsupported_answer_rate",
)

SUITE_TABLE_METRICS = {
    "common-core-v1": BASE_TABLE_METRICS,
    "knowledge-structure-v1": BASE_TABLE_METRICS,
    "memory-lifecycle-v1": BASE_TABLE_METRICS
    + (
        "native_correction_and_update_success",
        "native_deletion_or_forgetting_success",
        "privacy_scope_violation_rate",
    ),
    "repository-knowledge-v1": BASE_TABLE_METRICS
    + (
        "native_correction_and_update_success",
        "native_deletion_or_forgetting_success",
        "privacy_scope_violation_rate",
    ),
}

TABLE_LABELS = {
    "mean_recall_at_5": "Recall@5",
    "mean_ndcg_at_5": "nDCG@5",
    "forbidden_or_stale_evidence_hit_rate": "Stale hit rate (lower is better)",
    "source_or_citation_trace_rate": "Source trace",
    "programmatic_answer_correctness": "Answer correct",
    "unsupported_answer_rate": "Unsupported answer (lower is better)",
    "native_correction_and_update_success": "Update",
    "native_deletion_or_forgetting_success": "Delete",
    "privacy_scope_violation_rate": "Privacy violation (lower is better)",
}

