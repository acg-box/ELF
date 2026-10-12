"""Reproduce retained evidence integrity and scoring without model or database access."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / '2026-10-12-grounded-evidence'


def read(name):
    return json.loads((ROOT / name).read_text())


def lines(name):
    return [json.loads(row) for row in gzip.decompress((ROOT / name).read_bytes()).splitlines()]


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = read('manifest.json')
    assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    for name, expected in manifest.items():
        assert digest((ROOT / name).read_bytes()) == expected, name
    protocol = read('protocol.json')
    assert digest((BASE / 'workload.json').read_bytes()) == protocol['workload_sha256']
    assert digest((BASE / 'manifest.json').read_bytes()) == protocol['baseline_manifest_sha256']
    assert protocol['dimensions'] == 4096
    assert protocol['max_output_tokens'] == 393216 and protocol['reasoning'] == 'max'
    assert protocol['reader_mode'] == 'one_pass_evidence_pack'
    work = read('workload.json')
    assert work == json.loads((BASE / 'workload.json').read_text())
    initial = {r['case_id']: r['value'] for r in [json.loads(row) for row in gzip.decompress((BASE / 'initial.jsonl.gz').read_bytes()).splitlines()]}
    docs = {r['doc_id']: r for r in json.loads((BASE / 'source-documents.json').read_text())}
    notes = {r['note_id']: r for r in json.loads((BASE / 'native-notes.json').read_text())}
    inputs = {r['case_id']: r['value'] for r in lines('inputs.jsonl.gz')}
    cases = {r['query']['case_id']: r for r in lines('cases.jsonl.gz')}
    responses = {r['case_id']: r['value'] for r in lines('responses.jsonl.gz')}
    receipts = {r['response']['id']: r for r in lines('provider-receipts.jsonl.gz')}
    queries = {q['case_id']: q for q in work['queries']}
    assert inputs.keys() == cases.keys() == responses.keys() == queries.keys()
    assert len(cases) == 36
    reviews = {r['case_id']: r for r in read('answer-reviews.json')}
    assert reviews.keys() == cases.keys()
    mechanics = {}
    for key, source in inputs.items():
        assert source['query'] == queries[key]
        assert source['initial_note_ids'] == [n['note_id'] for n in initial[key]['notes']]
        pack = source['pack']
        assert pack['source_bytes'] == sum(len(s['text'].encode()) for s in pack['sources']) <= 32768
        available = {s['reference']: s for s in pack['sources']}
        assert len(available) == len(pack['sources'])
        for ref, row in available.items():
            doc = docs[row['doc_id']]
            assert ref == f"elf-source-v1/{row['doc_id']}/{row['content_hash']}/{row['start']}/{row['end']}"
            assert row['content_hash'] == doc['content_hash']
            assert row['text'].encode() == doc['content'].encode()[row['start']:row['end']]
            assert row['source_timestamp'] == doc['source_ref'].get('ts')
        for note in pack['notes']:
            assert note['note_id'] in source['initial_note_ids']
            assert note['text'] == notes[note['note_id']]['text']
            assert set(note['source_references']) <= available.keys()
            origins = {e['source']['document']['ref']['doc_id'] for e in notes[note['note_id']]['source_ref']['evidence']}
            assert all(available[ref]['doc_id'] in origins for ref in note['source_references'])
        response = responses[key]
        request = response['request']
        assert request['messages'] == [{'role': 'system', 'content': protocol['prompt']}, {'role': 'user', 'content': json.dumps({'question': queries[key]['question'], 'evidence_pack': pack}, ensure_ascii=False)}]
        assert request['model'] == protocol['model'] and request['max_tokens'] == 393216
        assert request['reasoning'] == {'effort': 'max'} and 'tools' not in request
        assert response['response'] == receipts[response['response']['id']]['response']
        paid_request = receipts[response['response']['id']]['request']
        assert paid_request['provider']['only'] == ['deepseek']
        case = cases[key]
        assert case['query'] == queries[key] and case['expected'] == work['oracle'][key]
        if case['status'] == 'completed':
            raw = json.loads(response['response']['choices'][0]['message']['content'])
            for field in ('text', 'claims', 'citations', 'supported'):
                assert case[field] == raw[field]
        review = reviews[key]
        assert review['answer_sha256'] == digest(case['text'].encode())
        assert review['claims_sha256'] == digest(json.dumps(case.get('claims'), sort_keys=True, ensure_ascii=False).encode())
        if case['status'] != 'completed':
            mechanics[key] = False
            continue
        bindings = case.get('claim_bindings', {})
        assert bindings.get('semantic_support') == 'not_evaluated'
        assert len(bindings['claims']) == len(case['claims'])
        seen = set()
        passed = bool(case.get('format_compliant')) and bool(case['claims']) and case['status'] == 'completed'
        for claim, binding in zip(case['claims'], bindings['claims']):
            assert len(claim['citations']) == len(binding['citation_verified']) == len(binding['resolved_citations'])
            for citation, valid, resolved in zip(claim['citations'], binding['citation_verified'], binding['resolved_citations']):
                ref = citation.get('reference')
                seen.add(ref)
                passed &= ref in available and valid
                if valid:
                    assert resolved['kind'] == 'source'
                    doc = docs[resolved['doc_id']]
                    assert resolved['content_hash'] == doc['content_hash'] and resolved['quote'] in doc['content']
                    if ref in available:
                        row = available[ref]
                        assert resolved['doc_id'] == row['doc_id'] and resolved['content_hash'] == row['content_hash'] and resolved['quote'] == row['text']
            enough = claim['state'] == 'unknown' or len(claim['citations']) >= (2 if claim['state'] == 'conflict' else 1)
            assert binding['binding_verified'] == (enough and all(binding['citation_verified']))
            passed &= binding['binding_verified']
        passed &= seen == set(case['citations'])
        mechanics[key] = passed
    canonical = {row['case_id']: row['answer'] for row in read('canonical-answers.json')}
    assert canonical.keys() == cases.keys()
    native = {row['case_id']: row['value'] for row in lines('native-audits.jsonl.gz')}
    assert native.keys() == cases.keys()
    native_pass = {}
    for key, value in native.items():
        raw = json.loads(responses[key]['response']['choices'][0]['message']['content'])
        assert value['raw_text'] == raw['text'] and value['raw_claims'] == raw['claims']
        answer = canonical[key]
        assert answer['text'] == raw['text'] and answer['claims'] == raw['claims'] and answer['supported'] == raw['supported']
        derived = list(dict.fromkeys(c['reference'] for claim in raw['claims'] for c in claim['citations']))
        assert answer['citations'] == derived
        original = raw.get('citations')
        legacy_valid = isinstance(original, list) and all(isinstance(x, str) for x in original) and set(original) == set(derived)
        assert answer['legacy_envelope_valid'] == legacy_valid
        available = {s['reference']: s for s in inputs[key]['pack']['sources']}
        bindings = value.get('result', {}).get('claims', [])
        passed = value['accepted'] and bool(raw['claims']) and len(bindings) == len(raw['claims'])
        if value['accepted']:
            assert value['result']['semantic_support'] == 'not_evaluated'
        for claim, binding in zip(raw['claims'], bindings):
            passed &= binding['binding_verified']
            assert len(claim['citations']) == len(binding['citation_verified']) == len(binding['resolved_citations'])
            for citation, verified, resolved in zip(claim['citations'], binding['citation_verified'], binding['resolved_citations']):
                ref = citation.get('reference')
                passed &= ref in available and verified
                if verified:
                    row = available[ref]
                    assert resolved == {'kind': 'source', 'doc_id': row['doc_id'], 'content_hash': row['content_hash'], 'quote': row['text']}
        native_pass[key] = passed
    for row in read('quality-summary.json'):
        keys = [key for key, query in queries.items() if ('contrast' if key.startswith('contrast-') else 'original') + '_' + query['split'] == row['cohort']]
        assert row['cases'] == len(keys)
        assert row['factual'] == sum(reviews[k]['correct'] for k in keys)
        assert row['semantic'] == sum(reviews[k]['semantic_grounding'] for k in keys)
        assert row['mechanical'] == sum(mechanics[k] for k in keys)
        assert row['joint'] == sum(reviews[k]['correct'] and reviews[k]['semantic_grounding'] and mechanics[k] for k in keys)
        assert row['native_mechanical'] == sum(native_pass[k] for k in keys)
        assert row['native_semantic'] == sum(reviews[k].get('native_semantic_grounding', reviews[k]['semantic_grounding']) for k in keys)
        assert row['native_joint'] == sum(reviews[k]['correct'] and reviews[k].get('native_semantic_grounding', reviews[k]['semantic_grounding']) and native_pass[k] for k in keys)
    logs = {row['path']: row['text'] for row in lines('validation-logs.jsonl.gz')}
    for check in read('validation.json')['checks']:
        assert check['status'] == 'passed'
        assert digest(logs[check['path']].encode()) == check['sha256']
    legacy = read('legacy-parser-compatibility.json')['cases']
    assert len(legacy) == 132 and sum(row['accepted'] for row in legacy) == 131
    assert all(row['claims_and_text_unchanged'] for row in legacy if row['accepted'])
    cleanup = read('cleanup.json')
    assert set(cleanup['preserved_unrelated_containers']) <= set(cleanup['remaining_containers'])
    assert not ({row['id'] for row in cleanup['removed_containers']} & set(cleanup['remaining_containers']))
    assert read('restored-fingerprints.json') == read('final-fingerprints.json')
    assert read('restored-fingerprints.json') == json.loads((BASE / 'backup-receipt.json').read_text())['tables']
    usage, account = lines('usage.jsonl.gz'), read('accounting.json')
    assert not any(x['status'] == 'in_flight' for x in usage)
    paid = sum((x.get('usage') or {}).get('cost', 0) or 0 for x in usage)
    assert abs(paid - account['new_paid_usd']) < 1e-9
    assert abs(account['prior_paid_usd'] + paid - account['cumulative_paid_usd']) < 1e-9
    assert account['conservative_exposure_usd'] <= 10
    print(json.dumps({'cases': len(cases), 'new_paid_usd': paid, 'cumulative_paid_usd': account['cumulative_paid_usd'], 'scope': 'Integrity and scored-label reproduction. Semantic labels require review; this verifier is not an entailment judge.'}))


if __name__ == '__main__':
    main()
