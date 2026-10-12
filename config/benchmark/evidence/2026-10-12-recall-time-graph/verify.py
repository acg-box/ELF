"""Verify frozen questions, native source bindings, reviews, and spend offline."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = ROOT.parent / '2026-10-12-grounded-evidence'
PREVIOUS = ROOT.parent / '2026-10-12-evidence-context'
sys.path.insert(0, str(REPO / 'scripts'))
from benchmark_agent.answer import decode_answer, parse_claim_answer


def read(name):
    return json.loads((ROOT / name).read_text())


def rows(name):
    return [json.loads(line) for line in gzip.decompress((ROOT / name).read_bytes()).splitlines()]


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = read('manifest.json')
    assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    for name, digest in manifest.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    protocol, work = read('protocol.json'), read('workload.json')
    assert work == json.loads((BASE / 'workload.json').read_text())
    assert protocol['workload_sha256'] == sha((BASE / 'workload.json').read_bytes())
    assert protocol['baseline_manifest_sha256'] == sha((BASE / 'manifest.json').read_bytes())
    assert protocol['dimensions'] == 4096 and protocol['supplemental_recall']
    assert protocol['max_output_tokens'] == 393216 and protocol['reasoning'] == 'max'
    questions = {q['case_id']: q for q in work['queries']}
    inputs = {r['case_id']: r['value'] for r in rows('inputs.jsonl.gz')}
    cases = {r['query']['case_id']: r for r in rows('cases.jsonl.gz')}
    responses = {r['case_id']: r['value'] for r in rows('responses.jsonl.gz')}
    receipts = {r['response']['id']: r for r in rows('provider-receipts.jsonl.gz')}
    reviews = {r['case_id']: r for r in read('answer-reviews.json')}
    assert inputs.keys() == cases.keys() == responses.keys() == reviews.keys() == questions.keys()
    assert len(cases) == 36
    planner = read('planner-response.json')
    planned_input = json.loads(planner['request']['messages'][1]['content'])
    assert planned_input == {'record_years': sorted({i['timestamp'][:4] for i in work['items']}),
                             'queries': [{'case_id': q['case_id'], 'question': q['question']} for q in work['queries']]}
    raw_plans, _ = decode_answer(planner['response']['choices'][0]['message']['content'])
    plans = read('recall-plans.json')
    assert len(raw_plans['plans']) == len(plans) == len(questions)
    for plan in raw_plans['plans']:
        key = plan['case_id']
        accepted = [s for s in plan['subjects'] if s.casefold() in questions[key]['question'].casefold()]
        assert plans[key] == {'subjects': accepted, 'as_of': plan['as_of'],
                              'rejected_subjects': [s for s in plan['subjects'] if s not in accepted]}
        assert accepted
    docs = {d['doc_id']: d for d in json.loads((BASE / 'source-documents.json').read_text())}
    initial = {r['case_id']: r['value'] for r in [json.loads(line) for line in gzip.decompress((BASE / 'initial.jsonl.gz').read_bytes()).splitlines()]}
    bindings = {}
    for key, data in inputs.items():
        assert data['query'] == questions[key]
        assert data['initial_note_ids'] == [n['note_id'] for n in initial[key]['notes']]
        assert data['supplemental_recall']['as_of'] == plans[key]['as_of']
        available = {}
        for pack in (data['pack'], data['supplemental_recall']['pack']):
            assert pack['source_bytes'] == sum(len(s['text'].encode()) for s in pack['sources']) <= 32768
            for source in pack['sources']:
                doc = docs[source['doc_id']]
                ref = f"elf-source-v1/{source['doc_id']}/{source['content_hash']}/{source['start']}/{source['end']}"
                assert source['reference'] == ref and source['content_hash'] == doc['content_hash']
                assert source['text'].encode() == doc['content'].encode()[source['start']:source['end']]
                available[ref] = source
        response = responses[key]
        assert response['request']['messages'] == [
            {'role': 'system', 'content': protocol['prompt']},
            {'role': 'user', 'content': json.dumps({'question': questions[key]['question'], 'evidence_pack': data['pack'], 'supplemental_recall': data['supplemental_recall']}, ensure_ascii=False)}]
        assert response['request']['max_tokens'] == 393216
        assert response['request']['reasoning'] == {'effort': 'max'}
        assert response['response'] == receipts[response['response']['id']]['response']
        assert receipts[response['response']['id']]['request']['provider']['only'] == ['deepseek']
        case, review = cases[key], reviews[key]
        assert case['query'] == questions[key] and case['expected'] == work['oracle'][key]
        parsed = parse_claim_answer(response['response']['choices'][0]['message']['content'])
        for field in ('text', 'claims', 'citations', 'supported'):
            assert case[field] == parsed[field]
        assert review['answer_sha256'] == sha(case['text'].encode())
        assert review['claims_sha256'] == sha(json.dumps(case['claims'], sort_keys=True, ensure_ascii=False).encode())
        checked = case['claim_bindings']
        assert checked['semantic_support'] == 'not_evaluated'
        assert len(checked['claims']) == len(case['claims'])
        passed = bool(case['claims']) and case['status'] == 'completed' and case['format_compliant']
        for claim, binding in zip(case['claims'], checked['claims']):
            enough = claim['state'] == 'unknown' or len(claim['citations']) >= (2 if claim['state'] == 'conflict' else 1)
            assert binding['binding_verified'] == (enough and all(binding['citation_verified']))
            passed &= binding['binding_verified']
            assert len(claim['citations']) == len(binding['resolved_citations']) == len(binding['citation_verified'])
            for citation, resolved, valid in zip(claim['citations'], binding['resolved_citations'], binding['citation_verified']):
                ref = citation['reference']
                passed &= ref in available and valid
                if valid:
                    source = available[ref]
                    assert resolved == {'kind': 'source', 'doc_id': source['doc_id'], 'content_hash': source['content_hash'], 'quote': source['text']}
        bindings[key] = passed
    for cohort in read('quality-summary.json'):
        keys = [k for k, q in questions.items() if ('contrast' if k.startswith('contrast-') else 'original') + '_' + q['split'] == cohort['cohort']]
        assert cohort['cases'] == len(keys)
        assert cohort['factual'] == sum(reviews[k]['correct'] for k in keys)
        assert cohort['semantic'] == sum(reviews[k]['semantic_grounding'] for k in keys)
        assert cohort['binding'] == sum(bindings[k] for k in keys)
        assert cohort['joint'] == sum(reviews[k]['correct'] and reviews[k]['semantic_grounding'] and bindings[k] for k in keys)
    assert read('restored-fingerprints.json') == read('final-fingerprints.json') == json.loads((PREVIOUS / 'final-fingerprints.json').read_text())
    account = read('accounting.json')
    usage = rows('usage.jsonl.gz')
    assert len(usage) == 37 and all(r['status'] == 'completed' and r['kind'] == 'chat' for r in usage)
    paid = sum(r['usage']['cost'] for r in usage)
    assert abs(paid - account['new_paid_usd']) < 1e-9
    assert abs(account['prior_paid_usd'] + paid - account['cumulative_paid_usd']) < 1e-9
    assert account['conservative_exposure_usd'] <= 10
    assert planner['response'] == receipts[planner['response']['id']]['response']
    print(json.dumps({'questions': len(cases), 'paid_requests': len(usage), 'new_paid_usd': paid,
                      'scope': 'Integrity and scored-label reproduction; assistant semantic labels are not an independent entailment judge.'}))


if __name__ == '__main__':
    main()
