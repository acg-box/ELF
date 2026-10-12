"""Reproduce frozen case lineage, source bindings, recorded reviews, and spend."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
from benchmark_agent.answer import parse_claim_answer


def read(name):
    return json.loads((ROOT / name).read_text())


def rows(name):
    return [json.loads(line) for line in gzip.decompress((ROOT / name).read_bytes()).splitlines()]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest = read('manifest.json')
    assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    for name, digest in manifest.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    work, protocol = read('workload.json'), read('protocol.json')
    assert sha((ROOT / 'workload.json').read_bytes()) == protocol['workload_sha256'] == read('freeze.json')['workload_sha256']
    assert sha(protocol['contract'].encode()) == protocol['contract_sha256']
    assert protocol['dimensions'] == 4096 and protocol['max_output_tokens'] == 393216
    cases = {r['case_id']: r for r in rows('cases.jsonl.gz')}
    inputs = {r['case_id']: r['value'] for r in rows('inputs.jsonl.gz')}
    responses = {r['case_id']: r['value'] for r in rows('responses.jsonl.gz')}
    reviews = {r['case_id']: r for r in read('answer-reviews.json')}
    receipts = {r['response']['id']: r for r in rows('provider-receipts.jsonl.gz')}
    expected_keys = set(work['regression_cases']) | {c['case_id'] for c in work['cases']}
    assert set(inputs) == expected_keys and set(cases) == set(responses) == set(reviews)
    assert set(cases) <= expected_keys
    new = {c['case_id']: c for c in work['cases']}
    source_receipts = rows('source-receipts.jsonl.gz')
    originals = {}
    for receipt in source_receipts:
        value = receipt['value']
        doc = value['document']
        originals[doc['doc_id']] = (value['request']['content'], doc['content_hash'])
    base = ROOT.parent / '2026-10-12-grounded-evidence'
    for doc in json.loads((base / 'source-documents.json').read_text()):
        originals[doc['doc_id']] = (doc['content'], doc['content_hash'])
    for key, data in inputs.items():
        sources = data['pack']['sources'] + (data.get('supplemental_recall') or {}).get('pack', {}).get('sources', [])
        if key in new:
            assert data['query']['question'] == new[key]['question']
            assert data['supplemental_recall']['as_of'] == new[key]['as_of']
            assert {s['text'] for s in sources} == {s['text'] for s in new[key]['sources']}
        available = {}
        for source in sources:
            content, digest = originals[source['doc_id']]
            assert source['content_hash'] == digest
            assert source['text'].encode() == content.encode()[source['start']:source['end']]
            assert source['reference'] == f"elf-source-v1/{source['doc_id']}/{digest}/{source['start']}/{source['end']}"
            available[source['reference']] = {'kind': 'source', 'doc_id': source['doc_id'], 'content_hash': digest, 'quote': source['text']}
        if key not in cases:
            continue
        response, case, review = responses[key], cases[key], reviews[key]
        request = response['request']
        payload = {'question': data['query']['question'], 'evidence_pack': data['pack'], 'supplemental_recall': data['supplemental_recall']}
        if data['supplemental_recall']['as_of'] is not None:
            payload['requested_as_of'] = data['supplemental_recall']['as_of']
        assert {k: v for k, v in request.items() if k != 'messages'} == {
            'model': protocol['model'], 'max_tokens': 393216, 'reasoning': {'effort': 'max'}}
        assert len(request['messages']) == 2
        assert request['messages'][0] == {'role': 'system', 'content': protocol['contract']}
        assert request['messages'][1]['role'] == 'user'
        assert json.loads(request['messages'][1]['content']) == payload
        receipt = receipts[response['response']['id']]
        assert receipt['response'] == response['response']
        assert receipt['request']['messages'] == request['messages']
        assert receipt['request']['max_tokens'] == request['max_tokens']
        assert receipt['request']['reasoning'] == request['reasoning']
        assert receipt['request']['provider']['only'] == ['deepseek']
        assert review['answer_sha256'] == sha(case.get('text', '').encode())
        assert review['claims_sha256'] == sha(json.dumps(case.get('claims', []), sort_keys=True, ensure_ascii=False).encode())
        parsed = parse_claim_answer(response['response']['choices'][0]['message']['content'])
        for field in ('text', 'claims', 'citations', 'supported'):
            assert case[field] == parsed[field]
        if case['status'] != 'completed':
            assert not review['binding']
            continue
        bindings = case['claim_bindings']['claims']
        assert case['claim_bindings']['semantic_support'] == 'not_evaluated'
        assert len(bindings) == len(case['claims'])
        all_bound = True
        for index, claim in enumerate(case['claims']):
            resolved = [available[c['reference']] for c in claim['citations']]
            origin = [index] * len(resolved)
            needed = set(claim.get('depends_on', []))
            assert all(0 <= dep < index for dep in needed)
            for dep in range(index - 1, -1, -1):
                if dep in needed:
                    needed.update(case['claims'][dep].get('depends_on', []))
            for dep in sorted(needed):
                for citation in case['claims'][dep]['citations']:
                    source = available[citation['reference']]
                    if source not in resolved:
                        resolved.append(source)
                        origin.append(dep)
            checked = bindings[index]
            assert checked['resolved_citations'] == resolved
            assert checked['citation_verified'] == [True] * len(resolved)
            if claim.get('depends_on'):
                assert checked['citation_claim_indices'] == origin
            else:
                assert 'citation_claim_indices' not in checked
            enough = claim['state'] == 'unknown' or len(resolved) >= (2 if claim['state'] == 'conflict' else 1)
            bound = enough and all(bindings[d]['binding_verified'] for d in claim.get('depends_on', []))
            assert checked['binding_verified'] == bound
            all_bound &= bound
        assert review['binding'] == all_bound
    account = read('accounting.json')
    usage = rows('usage.jsonl.gz')
    pilot = rows('pilot.jsonl.gz')
    assert len(pilot) == 4
    assert len(receipts) == len(usage) == len(responses) + len(pilot)
    pilot_protocol = read('pilot-protocol.json')
    for row in pilot:
        assert row['response']['request']['messages'][0]['content'] == pilot_protocol['contract']
        assert row['response']['request']['messages'][1:] == responses[row['case_id']]['request']['messages'][1:]
        response = row['response']['response']
        assert response == receipts[response['id']]['response']
        try:
            parsed = parse_claim_answer(response['choices'][0]['message']['content'])
        except ValueError:
            assert row['case']['status'] == 'invalid'
        else:
            assert row['case']['status'] == 'completed'
            assert parsed['claims'] == row['case']['claims']
    assert sum(r['case']['status'] == 'invalid' for r in pilot) == 3
    assert all(r['status'] == 'completed' for r in usage)
    paid = sum(r['usage']['cost'] for r in usage)
    assert abs(paid - sum(r['response']['usage']['cost'] for r in receipts.values())) < 1e-9
    assert abs(paid - account['new_paid_usd']) < 1e-9
    assert abs(account['prior_paid_usd'] + paid - account['cumulative_paid_usd']) < 1e-9
    assert abs(account['cumulative_paid_usd'] + account['unsettled_reserved_usd'] - account['conservative_exposure_usd']) < 1e-9
    assert account['conservative_exposure_usd'] <= 10
    for row in read('quality-summary.json'):
        keys = [key for key in cases if ('regression' if key in work['regression_cases'] else 'new') == row['cohort']]
        assert row['cases'] == len(keys)
        for field in ('factual', 'semantic', 'binding'):
            assert row[field] == sum(reviews[key][field] for key in keys)
        assert row['joint'] == sum(all(reviews[key][field] for field in ('factual', 'semantic', 'binding')) for key in keys)
    replay = {row['case_id']: row['value'] for row in rows('native-replay.jsonl.gz')}
    def clean(value):
        return {k: v for k, v in value.items() if k != 'request_id'}
    assert replay.keys() == cases.keys()
    for key in replay:
        assert clean(replay[key]) == clean(cases[key]['claim_bindings'])
    implementation = read('implementation.json')
    for path, digest in implementation['file_sha256'].items():
        assert sha(subprocess.check_output(['git', 'show', implementation['commit'] + ':' + path], cwd=REPO)) == digest, path
    integrity = read('source-integrity.json')
    assert integrity['originals_unchanged']
    assert integrity['baseline_original_columns'] == integrity['final_original_columns_excluding_new_fixture_documents']
    assert integrity['new_fixture_documents'] == 26
    mcp = read('mcp-contract.json')
    assert mcp['live_initialize_verified'] and mcp['response']['result']['instructions'] == protocol['contract']
    assert mcp['contract_sha256'] == protocol['contract_sha256']
    cleanup = read('cleanup.json')
    assert len(cleanup['removed_containers']) == 2 and cleanup['shared_images_preserved']
    assert not cleanup['global_prune']
    assert set(cleanup['preserved_unrelated_containers']) <= set(cleanup['remaining_containers'])
    assert not {r['id'] for r in cleanup['removed_containers']} & set(cleanup['remaining_containers'])
    assert sum(not r['state_contract_correct'] for r in reviews.values()) == 3
    logs = {r['path']: r['text'] for r in rows('validation-logs.jsonl.gz')}
    for row in read('validation.json')['logs']:
        assert sha(logs[row['path']].encode()) == row['sha256']
    print(json.dumps({'completed': len(cases), 'expected': len(expected_keys), 'new_paid_usd': paid,
                      'scope': 'Recorded review reproduction and source binding, not independent semantic judgment.'}))


if __name__ == '__main__':
    main()
