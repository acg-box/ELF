"""Paired reader ablation over frozen native candidates; no re-extraction."""
import importlib.util
import json
import os
import time
import tiktoken
from benchmark_runner.answers import request_answers
from .common import REPO, digest, labeled, read, save

spec = importlib.util.spec_from_file_location('lab_native', REPO / 'scripts/benchmark-native-comparison.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def context(rows, encoding, budget=4096):
    text = labeled(rows)
    tokens = encoding.encode(text)
    return {'text': encoding.decode(tokens[:budget]), 'tokens': min(len(tokens), budget), 'untruncated_tokens': len(tokens)}


def ablation(root):
    encoding = tiktoken.get_encoding('cl100k_base')
    pools = {x['case_id']: x for x in read(root / 'ablation-pools.json')}
    suite = read(root / 'frozen-workloads.json')['memory']
    env = {'BENCHMARK_CHAT_API_BASE': os.environ['LITELLM_BASE_URL'].replace('127.0.0.1', 'host.docker.internal'),
           'BENCHMARK_CHAT_API_KEY': os.environ['LITELLM_API_KEY'],
           'BENCHMARK_CHAT_MODEL': legacy.CHAT, 'BENCHMARK_CHAT_REASONING_EFFORT': 'max'}
    matches = 0
    for q in suite['queries']:
        old = pools[q['case_id']]
        assert context(old['rows'], encoding)['text'] == old['prior_context']['text'], q['case_id']
        matches += 1
    save(root / 'context-controls.json', {'prior_combined_contexts_reproduced': matches, 'total': len(pools), 'tokenizer': 'cl100k_base', 'budget': 4096, 'candidate_order': 'Frozen native retrieval order; filter by source type without reranking', 'conditions': ['source', 'memory', 'combined'], 'reader_function': 'Unmodified benchmark_runner.answers.request_answers', 'order': 'Rotate three conditions by query ordinal', 'source_revision': read(root / 'input-protocol.json')['source_commit'] if (root / 'input-protocol.json').exists() else '6cf7bc03a23579cb9415541b04906f2e87485c79'})
    for index, q in enumerate(suite['queries']):
        conditions = ['source', 'memory', 'combined']
        conditions = conditions[index % 3:] + conditions[:index % 3]
        for condition in conditions:
            path = root / 'ablation' / condition / (q['case_id'] + '.json')
            if path.exists():
                assert read(path)['status'] == 'completed', 'Retain failed attempts before an explicit retry'
                continue
            rows = [r for r in pools[q['case_id']]['rows'] if condition == 'combined' or r['kind'] == condition]
            ctx = context(rows, encoding)
            start = time.monotonic()
            try:
                response = request_answers([{'case_id': q['case_id'], 'question': q['question'], 'context': ctx['text']}], env, max_tokens=943718, timeout=3600)
                answer = legacy.decode_answer(response, q['case_id'])
                result = {**answer, 'status': 'completed', 'strict_correct': legacy.score(suite['oracle'][q['case_id']], answer['text']), 'reader': response}
            except Exception as error:
                result = {'status': 'failed', 'error': type(error).__name__ + ': ' + str(error).replace(env['BENCHMARK_CHAT_API_KEY'], '[redacted]')}
            result.update(condition=condition, query=q, expected=suite['oracle'][q['case_id']], context=ctx, context_sha256=digest(ctx['text']), source_ids=[r['evidence_id'] for r in rows], seconds=time.monotonic() - start)
            save(path, result)
            print(json.dumps({'event': 'ablation', 'condition': condition, 'case_id': q['case_id'], 'status': result['status'], 'strict_correct': result.get('strict_correct'), 'seconds': result['seconds']}), flush=True)
            if result['status'] != 'completed':
                raise RuntimeError('Ablation stopped after failed request; receipt retained')
