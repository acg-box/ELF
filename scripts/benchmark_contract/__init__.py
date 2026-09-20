"""Public contract for the isolated competitor benchmark."""

from .answers import NativeContextError, answer_cases
from .evaluation import evaluate_unit
from .fixtures import (
    FAILURE_CLASSES, FORBIDDEN_PRODUCT_KEYS, PRODUCT_IDS, SUITE_IDS,
    assert_product_payload_is_blind, canonical_json, load_json,
    materialize_product_fixtures, opaque_evidence_id, opaque_identifier,
    opaque_job_id, product_job, sha256_json, validate_manifest, validate_suite,
)
