#!/usr/bin/env python3
"""Test the formal ELF API against the frozen Hindsight/RAGFlow workloads."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.error

from benchmark_deep import elf_runtime
from benchmark_runner.answers import request_answers

spec = importlib.util.spec_from_file_location('system_comparison', Path(__file__).with_name('benchmark-system-comparison.py'))
system = importlib.util.module_from_spec(spec); spec.loader.exec_module(system)
common = system.common
BASE = 'http://127.0.0.1:19892'


def retrieve(api, question, scope, pack, inverse):
    notes = api('/v2/searches', {'mode':'planned_search','query':question,'top_k':12,'candidate_k':60}) if scope=='memory' else None
    if notes:
        elf_runtime.drain()
    if pack:
        body = {'task':question,'query':question,'docs_query':question,'include_dreaming':False,'limit':32}
        if notes: body['trace_id'] = notes['trace_id']
        result = api('/v2/context-packs', body)
        refs = [item['item_ref'] for item in result['items']]
    else:
        result = api('/v2/docs/search/l0', {'query':question,'top_k':12,'candidate_k':60,'explain':True})
        refs = result['items']
        if notes: refs = [*notes['items'], *refs]
    rows = []; hydrated = []; seen = set()
    for ref in refs:
        if 'doc_id' in ref and 'chunk_id' in ref:
            key = ('doc',ref['doc_id'],ref['chunk_id'])
            if key in seen: continue
            excerpt = api('/v2/docs/excerpts', {'doc_id':ref['doc_id'],'chunk_id':ref['chunk_id'],'level':'L2','explain':True})
            if not excerpt['verification']['verified']: raise ValueError('Unverified native excerpt')
            row = {'evidence_id':inverse[ref['doc_id']],'text':excerpt['excerpt']}
        elif 'note_id' in ref:
            key = ('note',ref['note_id'])
            if key in seen: continue
            excerpt = api('/v2/notes/'+ref['note_id'])
            row = {'evidence_id':'elf-note:'+ref['note_id'],'text':excerpt['text']}
        else:
            raise ValueError('Unsupported selected context reference: '+json.dumps(ref))
        seen.add(key); hydrated.append(excerpt); rows.append(row)
    return rows, {'selection':result,'note_search':notes,'hydrated':hydrated}


def answer(q, rows, native, pack):
    if not pack:
        return common.shared_answer(q,rows,native,max_tokens=system.MAX_OUTPUT,reasoning_effort='max',timeout=3600)
    context,_=common.api(common.SIDE,'/tokens',{'text':common.labeled(rows)})
    env={'BENCHMARK_CHAT_API_BASE':os.environ['LITELLM_BASE_URL'],
         'BENCHMARK_CHAT_API_KEY':os.environ['LITELLM_API_KEY'],
         'BENCHMARK_CHAT_MODEL':common.CHAT,'BENCHMARK_CHAT_REASONING_EFFORT':'max'}
    response=request_answers([{'case_id':q['case_id'],'question':q['question'],'context':context['text']}],
                             env,max_tokens=system.MAX_OUTPUT,timeout=3600)
    try: parsed=common.decode_answer(response,q['case_id'])
    except (ValueError,KeyError,TypeError,IndexError) as error:
        raise common.AnswerContractError(str(error),{'context':context,'native':native,'reader':response}) from error
    return {'text':parsed['text'],'supported':parsed['supported'],'context':context,'native':native,'reader':response}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact-root',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=0,help='Maximum new queries per condition; zero runs all')
    args=parser.parse_args();root=args.artifact_root.resolve();root.mkdir(parents=True,exist_ok=True)
    elf_runtime.prepare_tokenizer(root)
    data=system.suites();common.freeze(root/'frozen-workloads.json',data)
    common.freeze(root/'protocol.json',{
        'source_commit':'45663eb4c04e5bb3082b8f7463b0deb48404fe00',
        'image':elf_runtime.IMAGE,'chat':common.CHAT,'reasoning_effort':'max',
        'provider_output_maximum':system.MAX_OUTPUT,'embedding':common.EMB,'dimensions':1536,
        'reranker':'cross-encoder/ms-marco-MiniLM-L-6-v2','independent_ceiling_usd':10,
        'primary':'ELF Context Pack (limit 32), hydrate only selected references, same external reader without extra context truncation.',
        'secondary':'Formal native retrieval (12 hits, 60 candidates per source), same reader, 4096 cl100k_base context tokens.',
        'ingest':'Unchanged OCR annotations and dated memory records in Source Library; memory records also use native events ingestion.',
        'defaults':'elf.example.toml; real GPT-2 tokenizer at frozen revision; mandatory reject_non_english=true; memory and ranking defaults retained.',
        'tokenizer':json.loads((root/'tokenizer-receipt.json').read_text()),
        'boundary':'ELF has no native final-answer API. Neither condition claims native reflect equivalence. No manual knowledge pages or oracle-directed structures.',
        'execution':'Serial queries; preserve all completed answers; retry failures only; development cases excluded from score.',
        'limitations':'Known small synthetic suites; asynchronous comparison with saved competitor results; no general superiority claim.',
        'source_hashes':{s:{i['evidence_id']:hashlib.sha256(i['text'].encode()).hexdigest() for i in v['items']} for s,v in data.items()}})
    auth=elf_runtime.start(root,common.REPO,common)
    def client(scope):
        def call(path,body=None):
            try:
                return common.api(BASE,path,body,token='Bearer '+auth[scope],timeout=3600)[0]
            except urllib.error.HTTPError as error:
                detail=error.read().decode()
                raise ValueError(f'ELF HTTP {error.code}: {detail}') from error
        return call
    for scope,suite in data.items():
        api=client(scope)
        for item in suite['items']:
            path=root/'ingest'/scope/(item['evidence_id']+'.json')
            state=json.loads(path.read_text()) if path.exists() else {}
            if 'document' not in state and 'document_rejected' not in state:
                try:
                    state['document']=api('/v2/docs',{'scope':'agent_private','title':item['evidence_id'],
                        'source_ref':{'schema':'doc_source_ref/v1','doc_type':'knowledge',
                            'ts':item.get('timestamp','2026-10-10T00:00:00Z'),
                            'evidence_id':item['evidence_id']},'content':item['text']})
                except ValueError as error:
                    if 'NON_ENGLISH' not in str(error): raise
                    state['document_rejected']={'error':str(error)}
                common.save(path,state)
            if scope=='memory' and 'event' not in state and 'event_failed' not in state:
                try:
                    state['event']=api('/v2/events/ingest',{'scope':'agent_private','dry_run':False,
                        'messages':[{'role':'user','content':item['text'],'ts':item['timestamp'],'msg_id':item['evidence_id']}]})
                except ValueError as error:
                    state['event_failed']={'error':str(error)}
                common.save(path,state)
            print(json.dumps({'event':'ingested','scope':scope,'id':item['evidence_id']}),flush=True)
    elf_runtime.drain()
    common.save(root/'ingestion-completed.json',{'time':time.time()})
    for scope,suite in data.items():
        api=client(scope)
        inverse={json.loads(p.read_text())['document']['doc_id']:p.stem for p in (root/'ingest'/scope).glob('*.json') if 'document' in json.loads(p.read_text())}
        for pack in (True,False):
            condition='elf-'+scope+('-pack-reader' if pack else '-retrieval-reader');new=0
            for q in suite['queries']:
                path=root/'cases'/condition/(q['case_id']+'.json')
                if path.exists() and json.loads(path.read_text())['status']=='completed': continue
                if args.limit and new>=args.limit: break
                def call():
                    rows,native=retrieve(api,q['question'],scope,pack,inverse)
                    return answer(q,rows,native,pack)
                common.run_case(root,condition,q,suite['oracle'][q['case_id']],call)
                new+=1
    common.save(root/'run-completed.json',{'time':time.time(),'limited':bool(args.limit)})


if __name__=='__main__': main()
