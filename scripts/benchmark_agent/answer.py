"""Consume native claims with one citation authority; retain legacy-envelope diagnostics."""
import json
import re
from copy import deepcopy


class AnswerRejected(ValueError):
    """Retain failed native checks without exposing a renderable answer."""

    def __init__(self, bindings):
        super().__init__('The final answer has invalid citation bindings. Repair it before submission.')
        self.bindings = bindings


def finalize_answer(answer, api):
    """Return the exact draft only after every native claim binding passes."""
    if (not isinstance(answer, dict) or not isinstance(answer.get('text'), str)
            or not isinstance(answer.get('supported'), bool)
            or not isinstance(answer.get('claims'), list) or not answer['claims']):
        raise ValueError('Expected text, supported, and nonempty claims')
    final = deepcopy({key: answer[key] for key in ('text', 'supported', 'claims')})
    bindings = api('/v2/evidence/check', {'claims': final['claims']})
    checks = bindings.get('claims')
    if (not isinstance(checks, list) or len(checks) != len(final['claims'])
            or any(not isinstance(check, dict) or check.get('claim_index') != index
                   for index, check in enumerate(checks))):
        raise ValueError('The native checker did not return every claim verdict in order')
    if any(check.get('binding_verified') is not True for check in checks):
        raise AnswerRejected(bindings)
    return {'answer': final, 'claim_bindings': bindings}


def decode_answer(content):
    """Preserve the established single-JSON-block wrapper rule without prose repair."""
    content = content.strip()
    try:
        return json.loads(content), True
    except json.JSONDecodeError:
        blocks = re.findall(r'```(?:json)?\s*\n(.*?)```', content, re.DOTALL)
        if len(blocks) != 1:
            raise ValueError('Expected one unambiguous answer object')
        return json.loads(blocks[0]), False


def parse_claim_answer(content):
    """Keep claims and text unchanged; derive the redundant answer-level citation list."""
    value, format_compliant = decode_answer(content)
    if not isinstance(value, dict) or not isinstance(value.get('text'), str) or not isinstance(value.get('supported'), bool):
        raise ValueError('Expected a JSON answer with text and supported fields')
    claims = value.get('claims')
    if not isinstance(claims, list) or not claims:
        raise ValueError('Expected native claims')
    citations = []
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get('citations'), list):
            raise ValueError('Expected claim citations')
        for citation in claim['citations']:
            if not isinstance(citation, dict):
                raise ValueError('Expected a native citation object')
            field = {'reference': 'reference', 'note': 'note_id', 'source': 'doc_id'}.get(citation.get('kind'))
            identifier = citation.get(field) if field else None
            if not isinstance(identifier, str) or not identifier:
                raise ValueError('Expected a native citation identifier')
            if identifier not in citations:
                citations.append(identifier)
    legacy = value.get('citations')
    legacy_valid = isinstance(legacy, list) and all(isinstance(x, str) for x in legacy) and set(legacy) == set(citations)
    return {'text': value['text'], 'supported': value['supported'], 'claims': claims,
            'citations': citations, 'format_compliant': format_compliant, 'legacy_envelope_valid': legacy_valid}
