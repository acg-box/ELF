"""Apply an explicit scoring revision without changing native product input."""

import copy


def review_suite(suite, contract):
    if contract is None:
        return copy.deepcopy(suite)
    if contract.get("schema") != "elf.benchmark_answer_contract/v1":
        raise ValueError("unknown answer contract schema")
    reviewed = copy.deepcopy(suite)
    for job in reviewed["jobs"]:
        correction = contract["corrections"].get(job["job_id"])
        if correction is None:
            continue
        if job["query"] != correction["query"]:
            raise ValueError("answer contract question differs from the frozen suite")
        job["qrels"].update(correction["qrels"])
    reviewed["answer_contract_revision"] = contract["revision"]
    if contract.get("source_trace_measurement"):
        reviewed["source_trace_measurement"] = contract["source_trace_measurement"]
    if contract.get("calendar_date_normalization"):
        if contract['calendar_date_normalization'] != 'unambiguous_english_month_names':
            raise ValueError('unknown calendar date normalization')
        reviewed['calendar_date_normalization'] = contract['calendar_date_normalization']
    return reviewed
