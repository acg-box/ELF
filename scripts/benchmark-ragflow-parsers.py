#!/usr/bin/env python3
"""Compare frozen free-parser and Mistral OCR text in the same native RAGFlow."""
import argparse
import hashlib
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from benchmark_deep.complex_documents import workload
from benchmark_deep import parser_stress

spec = importlib.util.spec_from_file_location('native_comparison', Path(__file__).with_name('benchmark-native-comparison.py'))
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def inputs(items, root, condition):
    result = []
    for item in items:
        if condition == 'deepdoc':
            result.append({k: v for k, v in item.items() if k != 'text'})
            continue
        text = item['text'] if condition == 'free' else (root / 'ocr' / (item['evidence_id'] + '.txt')).read_text()
        if not text.strip():
            raise ValueError('Empty parser output')
        result.append({'evidence_id': item['evidence_id'], 'text': text})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--fixture-root', type=Path, help='Use the new parser stress fixture and all three parsers')
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    source, oracle = (parser_stress.workload(args.fixture_root, root / 'free')
                      if args.fixture_root else workload())
    scorer = parser_stress.score if args.fixture_root else common.score
    queries = [q for q in source['actions'][1:] if q['case_id'] not in common.EXCLUDED]
    source_items = source['actions'][0]['items']
    names = ('free', 'mistral-ocr', 'deepdoc') if args.fixture_root else ('free', 'mistral-ocr')
    conditions = {name: inputs(source_items, root, name) for name in names}
    protocol = {
        'scope': 'Parser intervention only; RAGFlow 1.0.0-rc1 with unchanged native retrieval and answer settings.',
        'historical_baseline': ('None; all three conditions use a fresh matched fixture.' if args.fixture_root else
                                '2026-10-10-native-memory-comparison: original DeepDOC PDF ingestion; not rerun here.'),
        'boundary': 'Both new conditions upload text/plain .txt sources. Includes representation and downstream text chunking changes; not a native DeepDOC model-weight upgrade.',
        'selection': ('All 30 frozen new diagnostic questions; no exclusions or answer-driven tuning.' if args.fixture_root else
                      'All 20 previous diagnostic questions, selected before answer calls; not a held-out test.'),
        'ocr_source': 'OpenRouter file annotations only, no generated assistant rewriting or answer-oracle enrichment.',
        'ocr_version': 'mistral-ocr engine; underlying model version not exposed in receipts.',
        'chat': common.CHAT, 'embedding': common.EMB, 'embedding_dimensions': 1536,
        'context_tokens': 4096, 'tokenizer': 'cl100k_base', 'reader_max_tokens': 8192,
        'rag_page_size': 64, 'rag_threshold': 0.0, 'rag_vector_weight': 0.3,
        'top_k': 1024, 'native_top_n': 20, 'native_max_tokens': 8192,
        'execution': (f'{len(names)} concurrent parser lanes; per-case cost windows overlap; no isolated latency comparison.' if args.fixture_root else
                      'Two concurrent parser lanes; per-case cost windows overlap; no isolated latency comparison.'),
        'reranker': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        'queries': queries, 'oracle': oracle,
        'source_hashes': {name: {x['evidence_id']: hashlib.sha256((x.get('text') or x['file_base64']).encode()).hexdigest() for x in items}
                          for name, items in conditions.items()},
    }
    if args.fixture_root:
        protocol['scoring'] = 'NFKC/casefold/whitespace normalization; numeric digit boundaries; citations removed; exact unknown for absent facts.'
    common.freeze(root / 'protocol.json', protocol)
    auth_file = root / 'private-auth.json'
    auth = json.loads(auth_file.read_text())['authorization'] if auth_file.exists() else common.register(root)
    common.api(common.SIDE, '/tokens', {'text': 'readiness'})
    if not (root / 'vllm-preflight.json').exists():
        common.api(common.RF, '/providers', {'provider_name': 'VLLM'}, method='PUT', token=auth)
        common.api(common.RF, '/providers/VLLM/instances', {
            'instance_name': 'native_cpu', 'api_key': 'local-benchmark-only',
            'base_url': 'http://host.docker.internal:19889/v1',
            'model_info': [{'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2', 'model_type': ['rerank'], 'max_tokens': 512}]}, token=auth)
        common.save(root / 'vllm-preflight.json', {'configured': True})
    rerank = 'cross-encoder/ms-marco-MiniLM-L-6-v2@native_cpu@VLLM'
    states = {name: common.ingest_rag(root, auth, name, items) for name, items in conditions.items()}
    def run_lane(name, state):
        common.save(root / (name + '-parsed.json'), common.wait_rag(state, auth))
        chunks = {}
        for identity, native_id in state['documents'].items():
            chunks[identity], _ = common.api(common.RF, f'/datasets/{state["dataset_id"]}/documents/{native_id}/chunks?page_size=100', token=auth)
        common.save(root / (name + '-chunks.json'), chunks)
        chat_path = root / (name + '-chat.json')
        if chat_path.exists():
            chat = json.loads(chat_path.read_text())
        else:
            chat, _ = common.api(common.RF, '/chats', {
                'name': 'parser-' + name, 'dataset_ids': [state['dataset_id']],
                'llm_id': common.CHAT + '@native_benchmark@OpenAI-API-Compatible',
                'llm_setting': {'temperature': 0.1, 'max_tokens': 8192},
                'similarity_threshold': 0.0, 'vector_similarity_weight': 0.3,
                'top_n': 20, 'top_k': 1024, 'rerank_id': rerank,
                'prompt_config': {'system': common.INSTRUCTION + '\nEvidence:\n{knowledge}',
                                  'empty_response': 'unknown', 'quote': True, 'refine_multiturn': False,
                                  'parameters': [{'key': 'knowledge', 'optional': False}]}}, token=auth)
            common.save(chat_path, chat)
        inverse = {v: k for k, v in state['documents'].items()}
        for q in queries:
            def retrieve():
                native, _ = common.api(common.RF, '/retrieval', {
                    'question': q['question'], 'dataset_ids': [state['dataset_id']],
                    'page': 1, 'page_size': 64, 'similarity_threshold': 0.0,
                    'vector_similarity_weight': 0.3, 'top_k': 1024, 'rerank_id': rerank}, token=auth)
                rows = [{'evidence_id': inverse.get(c['document_id']), 'text': c['content']} for c in native['chunks']]
                return common.shared_answer(q, rows, native)

            def native_answer():
                native, _ = common.api(common.RF, '/chat/completions', {
                    'chat_id': chat['id'], 'messages': [{'role': 'user', 'content': q['question']}],
                    'stream': False, 'max_tokens': 8192, 'store_history_messages': False}, token=auth, timeout=600)
                text = native.get('answer') or native.get('content')
                if not text or '**ERROR**' in text:
                    raise common.AnswerContractError('Native chat returned no usable answer', {'native': native})
                return {'text': text, 'native': native}

            common.run_case(root, name + '-retrieval', q, oracle[q['case_id']], retrieve, scorer)
            common.run_case(root, name + '-native-chat', q, oracle[q['case_id']], native_answer, scorer)
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        futures = [pool.submit(run_lane, name, state) for name, state in states.items()]
        for future in futures:
            future.result()
    rows = [json.loads(p.read_text()) for p in (root / 'cases').glob('*/*.json')]
    common.save(root / 'results.json', rows)
    return 0 if len(rows) == len(queries) * len(names) * 2 and all(r['status'] == 'completed' for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
