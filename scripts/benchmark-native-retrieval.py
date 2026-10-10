#!/usr/bin/env python3
"""Run raw-chunk recall or recover RAGFlow retrieval on the frozen cases."""
import argparse
import importlib.util
import json
from pathlib import Path
from benchmark_targets.hindsight import chunk_contexts_from_native

spec=importlib.util.spec_from_file_location('native_comparison',Path(__file__).with_name('benchmark-native-comparison.py'))
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact-root',type=Path,required=True);parser.add_argument('--target',choices=('hindsight','ragflow'),required=True);args=parser.parse_args()
    root=args.artifact_root.resolve();suites=json.loads((root/'frozen-workloads.json').read_text())
    common.freeze(root/'chunk-protocol.json',{'condition':'hindsight-recall-chunks','scope':'All frozen questions; no answer selection or source enrichment.',
        'boundary':'Added after native API/trace inspection and initial answer inspection. Exploratory capability correction, not an independently preregistered comparison.',
        'budget':'high','max_tokens':4096,'include':{'chunks':{'max_tokens':8192},'source_facts':{'max_tokens':8192}},
        'reader_context_tokens':4096,'reader_max_tokens':8192,'tokenizer':'cl100k_base',
        'presentation':'Native raw chunks only, ordered by first occurrence in returned native facts; remaining returned chunks retain native order. No corpus or oracle lookup.'})
    condition='hindsight-recall-chunks' if args.target=='hindsight' else 'ragflow-retrieval-rerank'
    if args.target=='ragflow':
        common.freeze(root/'rag-retrieval-recovery.json',{'page_size':64,'reason':'The native rerank candidate limit is 64; page_size=100 fails validation before retrieval. No completed answer is replaced. All other retrieval/reader settings are unchanged.'})
        auth=json.loads((root/'private-auth.json').read_text())['authorization']
    for scope in ('memory','pdf'):
        suite=suites[scope];bank='/v1/default/banks/native-'+scope
        if args.target=='ragflow':
            state=json.loads((root/(scope+'-rag-state.json')).read_text());inverse={v:k for k,v in state['documents'].items()}
        for q in sorted(suite['queries'],key=lambda q:q.get('split')!='dev'):
            def answer():
                if args.target=='ragflow':
                    raw,_=common.api(common.RF,'/retrieval',{'question':q['question'],'dataset_ids':[state['dataset_id']],'page':1,'page_size':64,'similarity_threshold':0.0,'vector_similarity_weight':0.3,'top_k':1024,'rerank_id':'cross-encoder/ms-marco-MiniLM-L-6-v2@native_cpu@VLLM'},token=auth)
                    rows=[{'evidence_id':inverse.get(c['document_id']),'text':c['content']} for c in raw['chunks']]
                    return common.shared_answer(q,rows,raw)
                raw,_=common.api(common.HS,bank+'/memories/recall',{'query':q['question'],'budget':'high','max_tokens':4096,
                    'include':{'chunks':{'max_tokens':8192},'source_facts':{'max_tokens':8192}},'trace':True})
                return common.shared_answer(q,chunk_contexts_from_native(raw),raw)
            common.run_case(root,condition,q,suite['oracle'][q['case_id']],answer)
    rows=[json.loads(p.read_text()) for p in (root/'cases'/condition).glob('*.json')]
    return 0 if len(rows)==40 and all(r['status']=='completed' for r in rows) else 1

if __name__=='__main__':raise SystemExit(main())
