"""Execute frozen source-reading cases with the production agent contract."""
import hashlib
import json
import os
import re
from pathlib import Path
import time
import urllib.error


def prepare(args, read, save, freeze, api, token):
    repo = Path(__file__).resolve().parents[2]
    fixture_path = repo / 'config/benchmark/agent-evidence-chain/workload.json'
    fixture = read(fixture_path)
    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == read(fixture_path.parent / 'freeze.json')['workload_sha256']
    freeze(args.root / 'workload.json', fixture)
    for case in fixture['cases']:
        target = args.root / 'inputs' / (case['case_id'] + '.json')
        if target.exists():
            continue
        sources, mapping = [], {}
        for source in case['sources']:
            receipt = args.root / 'source-receipts' / (case['case_id'] + '-' + source['key'] + '.json')
            if receipt.exists():
                saved = read(receipt)
            else:
                body = {'scope': 'agent_private', 'title': case['case_id'] + '-' + source['key'],
                        'source_ref': {'schema': 'doc_source_ref/v1', 'doc_type': 'knowledge', 'ts': re.search(r'2026-\d{2}-\d{2}', source['text']).group() + 'T00:00:00Z'}, 'content': source['text']}
                doc = api(args.api_base, token, '/v2/docs', body)
                # A literal prefix selects this known source without a model or oracle.
                subject = source['text']
                while len(subject.encode()) > 128:
                    subject = subject[:-1]
                recall = api(args.api_base, token, '/v2/evidence/recall', {'subjects': [subject]})
                saved = {'request': body, 'document': doc, 'recall': recall}
                save(receipt, saved)
            matches = [s for s in saved['recall']['pack']['sources'] if s['doc_id'] == saved['document']['doc_id']]
            assert len(matches) == 1 and matches[0]['text'] == source['text']
            sources.append(matches[0])
            mapping[source['key']] = matches[0]['doc_id']
        save(target, {'query': {'case_id': case['case_id'], 'question': case['question']},
                      'pack': {'schema': 'elf.evidence_pack/v1', 'notes': [], 'sources': sources,
                               'complete': True, 'source_bytes': sum(len(s['text'].encode()) for s in sources)},
                      'supplemental_recall': {'as_of': case['as_of']}, 'source_keys': mapping})
    prior = repo / 'config/benchmark/evidence/2026-10-12-recall-time-graph'
    import gzip
    initial = {r['case_id']: r['value'] for r in map(json.loads, gzip.decompress((prior / 'inputs.jsonl.gz').read_bytes()).splitlines())}
    for key in fixture['regression_cases']:
        freeze(args.root / 'inputs' / (key + '.json'), initial[key])
    contract = (repo / 'config/agent/evidence-reader.md').read_text()
    freeze(args.root / 'protocol.json', {'contract': contract, 'contract_sha256': hashlib.sha256(contract.encode()).hexdigest(),
           'workload_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(), 'model': 'deepseek/deepseek-v4.1-flash',
           'reasoning': 'max', 'max_output_tokens': 393216, 'dimensions': 4096,
           'boundary': 'Eight frozen new source-reading cases with all case originals and distractors, plus two frozen regression inputs. No retrieval ranking, fresh embedding, or independent-judge claim. One response per case; keep all failures.'})


def run(args, read, save, api, token, reader_request, parse_claim_answer):
    fixture = read(args.root / 'workload.json')
    keys = fixture['regression_cases'] + [c['case_id'] for c in fixture['cases']]
    contract = read(args.root / 'protocol.json')['contract']
    for key in keys:
        if (args.root / 'STOP').exists():
            print(json.dumps({'event': 'operator_stop', 'next_case': key}), flush=True)
            return
        target = args.root / 'cases' / (key + '.json')
        response_path = args.root / 'responses' / (key + '.json')
        if target.exists():
            continue
        frozen = read(args.root / 'inputs' / (key + '.json'))
        request = reader_request(frozen['query'], frozen, agent_contract=True)
        assert request['messages'][0]['content'] == contract
        if response_path.exists():
            raise RuntimeError('Recorded response needs offline recovery, not another paid call: ' + key)
        started = time.monotonic()
        try:
            response = api(os.environ['LITELLM_BASE_URL'], os.environ['LITELLM_API_KEY'], '/chat/completions', request)
        except urllib.error.HTTPError as error:
            save(args.root / 'stopped.json', {'case_id': key, 'http_status': error.code,
                                            'reason': error.read().decode(), 'policy': 'Stop; no paid retry.'})
            raise
        save(response_path, {'request': request, 'response': response})
        result = {'case_id': key, 'seconds': time.monotonic() - started, 'status': 'completed'}
        try:
            result.update(parse_claim_answer(response['choices'][0]['message']['content']))
            result['claim_bindings'] = api(args.api_base, token, '/v2/evidence/check', {'claims': result['claims']})
        except (ValueError, KeyError, urllib.error.HTTPError) as error:
            result.update(status='invalid', error=str(error))
        save(target, result)
        print(json.dumps({'case_id': key, 'status': result['status'], 'cost': response.get('usage', {}).get('cost')}), flush=True)
