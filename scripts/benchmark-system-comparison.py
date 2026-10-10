#!/usr/bin/env python3
"""Matched Hindsight/RAGFlow system comparison with a shared OCR input boundary."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

from benchmark_deep import complex_documents, memory_comparison, parser_stress
from benchmark_targets.hindsight import chunk_contexts_from_native

spec = importlib.util.spec_from_file_location('native_comparison', Path(__file__).with_name('benchmark-native-comparison.py'))
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
MAX_OUTPUT = 943718
MODEL_CONTEXT = 1048576
HS_NAME = 'elf-final-system-hindsight'


def suites():
    """Use previously frozen original OCR annotations; never ingest answer keys."""
    pdf, oracle = complex_documents.workload()
    result = {'documents': {'items': [], 'queries': [q for q in pdf['actions'][1:] if q['case_id'] not in common.EXCLUDED],
                            'oracle': {k: v for k, v in oracle.items() if k not in common.EXCLUDED}}}
    manifests = [('2026-10-10-ragflow-ocr', 'complex-documents-v1'),
                 ('2026-10-10-parser-stress', 'parser-stress-v1')]
    for evidence, fixture in manifests:
        docs = json.loads((common.REPO / 'config/benchmark/fixtures' / fixture / 'oracle-source.json').read_text())
        source_digests = {d['evidence_id']: d['sha256'] for d in docs}
        with gzip.open(common.REPO / 'config/benchmark/evidence' / evidence / 'parser-outputs.jsonl.gz', 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                if row.get('parser', row.get('condition')) != 'mistral-ocr':
                    continue
                identity = row.get('source', row.get('evidence_id'))
                if row.get('source_sha256', row.get('pdf_sha256')) != source_digests[identity]:
                    raise ValueError('OCR receipt does not match frozen PDF')
                result['documents']['items'].append({'evidence_id': identity, 'text': row['text']})
        if fixture == 'parser-stress-v1':
            index = 0
            for doc in docs:
                for q in doc['questions']:
                    key = f'stress-{index:03d}'; index += 1
                    result['documents']['queries'].append({'case_id': key, 'question': q['question'], 'lane': q['lane']})
                    result['documents']['oracle'][key] = {**{k: q[k] for k in ('facts', 'forbidden', 'lane')},
                        'supported': bool(q['facts']), 'evidence': [doc['evidence_id']] if q['facts'] else []}
    mem, mo = memory_comparison.workload()
    result['memory'] = {**mem, 'oracle': mo}
    return result


def start_hindsight(root):
    existing = subprocess.run(['docker', 'inspect', HS_NAME], capture_output=True, text=True)
    if existing.returncode == 0:
        obj = json.loads(existing.stdout)[0]
        if obj['Config']['Labels'].get('elf.benchmark') != 'final-system' or obj['Config']['Image'] != common.HS_IMAGE:
            raise ValueError('Existing container is not owned by this comparison')
        # A new gateway requires new injected credentials. Restart only the owned container;
        # its named volume retains native banks and in-flight operation state.
        subprocess.run(['docker', 'stop', HS_NAME], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['docker', 'rm', HS_NAME], check=True, stdout=subprocess.DEVNULL)
    base = os.environ['LITELLM_BASE_URL'].replace('127.0.0.1', 'host.docker.internal')
    settings = {'LLM_PROVIDER': 'openai', 'LLM_API_KEY': os.environ['LITELLM_API_KEY'],
        'LLM_BASE_URL': base, 'LLM_MODEL': common.CHAT, 'LLM_REASONING_EFFORT': 'max',
        'LLM_MAX_CONCURRENT': '1', 'LLM_MAX_RETRIES': '0', 'LLM_TIMEOUT': '3600',
        'RETAIN_MAX_CONCURRENT': '1', 'EMBEDDINGS_PROVIDER': 'openai',
        'EMBEDDINGS_OPENAI_API_KEY': os.environ['EMBEDDING_API_KEY'], 'EMBEDDINGS_OPENAI_BASE_URL': base,
        'EMBEDDINGS_OPENAI_MODEL': common.EMB, 'EMBEDDINGS_OPENAI_DIMENSIONS': '1536',
        'EMBEDDINGS_MAX_CONCURRENT_REQUESTS': '1', 'RERANKER_LOCAL_FORCE_CPU': 'true'}
    env = {**os.environ, **{'HINDSIGHT_API_' + k: v for k, v in settings.items()}}
    cmd = ['docker', 'run', '-d', '--name', HS_NAME, '--label', 'elf.benchmark=final-system',
        '--add-host', 'host.docker.internal:host-gateway', '-p', '127.0.0.1:19888:8888', '-p', '127.0.0.1:19889:8899',
        '-v', 'elf-final-system-hindsight-data:/home/hindsight/.pg0',
        '-v', str(common.REPO / 'scripts/benchmark_deep/native_sidecar.py') + ':/native-sidecar.py:ro',
        '-v', str(root) + ':/experiment']
    for key in settings:
        cmd += ['-e', 'HINDSIGHT_API_' + key]
    with (root / 'hindsight-start.log').open('a') as stream:
        subprocess.run(cmd + [common.HS_IMAGE], env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    common.ready(common.HS + '/health', seconds=900)
    subprocess.run(['docker', 'exec', '-d', HS_NAME, 'sh', '-c',
                    'python /native-sidecar.py > /experiment/sidecar.log 2>&1'], check=True)
    for _ in range(180):
        try:
            common.api(common.SIDE, '/tokens', {'text': 'ready'}); return
        except Exception:
            time.sleep(2)
    raise TimeoutError('Shared tokenizer/reranker readiness')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifact-root', type=Path, required=True)
    args = ap.parse_args(); root = args.artifact_root.resolve(); root.mkdir(parents=True, exist_ok=True)
    data = suites()
    common.freeze(root / 'frozen-workloads.json', data)
    common.freeze(root / 'protocol.json', {
        'products': {'hindsight': '0.10.3', 'ragflow': '1.0.0-rc1'},
        'chat': common.CHAT, 'reasoning_effort': 'max', 'provider_max_output_tokens': MAX_OUTPUT,
        'gateway': 'Force the same provider output maximum for internal and final LLM calls; cumulative USD 20 ceiling.',
        'input': 'Both products receive identical retained Mistral OCR annotations for 14 PDFs and identical 20 dated memory records.',
        'primary': 'Native Hindsight reflect budget high versus RAGFlow native retrieval-chat with reranker.',
        'primary_score': '50% document accuracy (50 questions) + 50% memory test accuracy (16 questions). Four development cases excluded.',
        'secondary': 'Native source-chunk recall versus hybrid retrieval; same shared reader and 4096 cl100k_base context tokens.',
        'scoring': 'Frozen normalized matching plus disclosed semantic review: requested values complete; literal identifiers; explicit supported absence accepted; historical values allowed only when clearly identified as historical.',
        'execution': 'Serial product operations and cases; ingestion completes before queries; no completed-answer retries.',
        'limitations': 'Known small synthetic suites; no held-out or general production ranking. Native reflect and chat have different internal algorithms.',
        'embedding': common.EMB, 'dimensions': 1536, 'reranker': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        'excluded_cases': sorted(common.EXCLUDED),
        'source_hashes': {scope: {x['evidence_id']: hashlib.sha256(x['text'].encode()).hexdigest() for x in suite['items']} for scope, suite in data.items()}})
    start_hindsight(root)
    auth_file = root / 'private-auth.json'
    if auth_file.exists():
        auth = json.loads(auth_file.read_text())['authorization']
        common.configure_rag_provider(auth, update=True, context_tokens=MODEL_CONTEXT)
    else:
        auth = common.register(root, context_tokens=MODEL_CONTEXT)
    if not (root / 'reranker-configured.json').exists():
        common.api(common.RF, '/providers', {'provider_name': 'VLLM'}, method='PUT', token=auth)
        common.api(common.RF, '/providers/VLLM/instances', {'instance_name': 'native_cpu',
            'api_key': 'local-benchmark-only', 'base_url': 'http://host.docker.internal:19889/v1',
            'model_info': [{'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2', 'model_type': ['rerank'], 'max_tokens': 512}]}, token=auth)
        common.save(root / 'reranker-configured.json', {'configured': True})
    ledger = root.parent / 'cost-calibration/budget-ledger.json'
    def metered_phase(name, call):
        first = len(json.loads(ledger.read_text())['requests']) + 1
        started = time.monotonic(); value = call()
        common.save(root / (name + '-phase.json'), {'first_ordinal': first, 'last_ordinal': len(json.loads(ledger.read_text())['requests']), 'seconds': time.monotonic() - started})
        return value
    states = {}; banks = {}
    for scope, suite in data.items():
        def ingest_rag():
            state = common.ingest_rag(root, auth, 'final-' + scope, suite['items'])
            common.save(root / (scope + '-parsed.json'), common.wait_rag(state, auth))
            return state
        states[scope] = metered_phase('ragflow-' + scope + '-ingest', ingest_rag)
        banks[scope] = metered_phase('hindsight-' + scope + '-ingest',
            lambda: common.ingest_hindsight(root, 'final-' + scope, suite['items']))
    rerank = 'cross-encoder/ms-marco-MiniLM-L-6-v2@native_cpu@VLLM'
    for scope, suite in data.items():
        state = states[scope]; bank = banks[scope]
        inverse = {v: k for k, v in state['documents'].items()}
        chat_file = root / (scope + '-chat.json')
        if chat_file.exists():
            chat = json.loads(chat_file.read_text())
        else:
            chat, _ = common.api(common.RF, '/chats', {'name': 'final-' + scope, 'dataset_ids': [state['dataset_id']],
                'llm_id': common.CHAT + '@native_benchmark@OpenAI-API-Compatible',
                'llm_setting': {'temperature': 0.1, 'max_tokens': MAX_OUTPUT},
                'similarity_threshold': 0.0, 'vector_similarity_weight': 0.3, 'top_n': 20, 'top_k': 1024, 'rerank_id': rerank,
                'prompt_config': {'system': common.INSTRUCTION + '\nEvidence:\n{knowledge}', 'empty_response': 'unknown',
                    'quote': True, 'refine_multiturn': False, 'parameters': [{'key': 'knowledge', 'optional': False}]}}, token=auth)
            common.save(chat_file, chat)
        for q in sorted(suite['queries'], key=lambda x: x.get('split') != 'dev'):
            expected = suite['oracle'][q['case_id']]
            def reflect():
                raw, _ = common.api(common.HS, bank + '/reflect', {'query': q['question'] + '\n' + common.INSTRUCTION,
                    'budget': 'high', 'max_tokens': MAX_OUTPUT, 'include': {'facts': {}, 'tool_calls': {}}}, timeout=3660)
                if not raw.get('text'): raise common.AnswerContractError('Empty native reflect answer', {'native': raw})
                return {'text': raw['text'], 'native': raw}
            def rag_chat():
                raw, _ = common.api(common.RF, '/chat/completions', {'chat_id': chat['id'],
                    'messages': [{'role': 'user', 'content': q['question']}], 'stream': False,
                    'max_tokens': MAX_OUTPUT, 'store_history_messages': False}, token=auth, timeout=3660)
                text = raw.get('answer') or raw.get('content')
                if not text or '**ERROR**' in text: raise common.AnswerContractError('Native chat error', {'native': raw})
                return {'text': text, 'native': raw}
            def hs_recall():
                raw, _ = common.api(common.HS, bank + '/memories/recall', {'query': q['question'], 'budget': 'high',
                    'max_tokens': 4096, 'include': {'chunks': {'max_tokens': 8192}, 'source_facts': {'max_tokens': 8192}}, 'trace': True}, timeout=3660)
                return common.shared_answer(q, chunk_contexts_from_native(raw), raw, MAX_OUTPUT, 'max', 3660)
            def rag_recall():
                raw, _ = common.api(common.RF, '/retrieval', {'question': q['question'], 'dataset_ids': [state['dataset_id']],
                    'page': 1, 'page_size': 64, 'similarity_threshold': 0.0, 'vector_similarity_weight': 0.3,
                    'top_k': 1024, 'rerank_id': rerank}, token=auth)
                rows = [{'evidence_id': inverse.get(c['document_id']), 'text': c['content']} for c in raw['chunks']]
                return common.shared_answer(q, rows, raw, MAX_OUTPUT, 'max', 3660)
            scorer = parser_stress.score if q['case_id'].startswith('stress-') else common.score
            for condition, call in [('hindsight-native', reflect), ('ragflow-native', rag_chat),
                                    ('hindsight-retrieval', hs_recall), ('ragflow-retrieval', rag_recall)]:
                common.run_case(root, condition, q, expected, call, scorer)
    rows = [json.loads(p.read_text()) for p in (root / 'cases').glob('*/*.json')]
    common.save(root / 'results.json', rows)
    return 0 if len(rows) == 280 and all(r['status'] == 'completed' for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
