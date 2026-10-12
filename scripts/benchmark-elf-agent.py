#!/usr/bin/env python3
"""Exercise ELF source and graph tools over frozen, receipt-backed memory extraction."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

from benchmark_agent.replay import Replay
from benchmark_agent.runner import run,finalize_recorded,parse_answer
from benchmark_agent.analysis import analyze
from benchmark_deep import elf_runtime

spec=importlib.util.spec_from_file_location('matched',Path(__file__).with_name('benchmark-elf-matched.py'))
matched=importlib.util.module_from_spec(spec);spec.loader.exec_module(matched)
common=matched.common
CONDITIONS=['notes','source','graph','both']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--image')
    parser.add_argument('--phase',choices=['prepare','run','control','finalize','analyze'],required=True);parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--output-maximum',type=int,default=943718)
    args=parser.parse_args();root=args.root.resolve();root.mkdir(parents=True,exist_ok=True)
    if args.phase=='analyze':
        print(json.dumps(analyze(root)['summary'],indent=2));return
    if args.phase=='finalize':
        protocol=json.loads((root/'protocol.json').read_text());assert protocol['max_output_tokens']==args.output_maximum
        common.freeze(root/'finalization-protocol.json',{'purpose':'Separate loop termination failure from missing evidence. One final model response from the original exhausted trace, with no additional retrieval. Primary exhausted cases remain unchanged.','max_output_tokens':args.output_maximum})
        for source in sorted((root/'cases').glob('*/*.json')):
            case=json.loads(source.read_text())
            if case['status'] not in ('tool_budget_exhausted','round_budget_exhausted'):continue
            path=root/'finalizations'/case['condition']/source.name
            if path.exists():continue
            initial=json.loads((root/'initial'/source.name).read_text())['notes']
            raw_path=root/'finalization-responses'/case['condition']/source.name
            if raw_path.exists():raw=json.loads(raw_path.read_text())
            else:
                raw=finalize_recorded(case,initial,os.environ['LITELLM_BASE_URL'],os.environ['LITELLM_API_KEY'],args.output_maximum);common.save(raw_path,raw)
            choice=raw['response']['choices'][0]
            if choice.get('finish_reason') in ('error','length'):raise RuntimeError('Failed finalization; preserve response')
            value=parse_answer(choice['message'].get('content') or '')
            value.update(condition=case['condition'],query=case['query'],expected=case['expected'],seconds=raw['seconds'],status='completed',original_status=case['status'])
            value['strict_correct']=common.score(value['expected'],value['text']);common.save(path,value)
            print(json.dumps({'finalized':case['condition'],'case_id':case['query']['case_id']}),flush=True)
        return
    if args.phase=='control':
        protocol=json.loads((root/'protocol.json').read_text())
        assert protocol['max_output_tokens']==args.output_maximum
        common.freeze(root/'control-protocol.json',{'condition':'initial','purpose':'Separate richer initial structured notes from iterative tool use. Same prompt, initial projection, model, and output allowance; no tools. Run after the four primary arms.','max_output_tokens':args.output_maximum})
        suite=json.loads((root/'workload.json').read_text())
        for q in suite['queries']:
            path=root/'cases'/'initial'/(q['case_id']+'.json')
            if path.exists():continue
            initial=json.loads((root/'initial'/(q['case_id']+'.json')).read_text())['notes']
            value=run(None,'initial',q['question'],initial,os.environ['LITELLM_BASE_URL'],os.environ['LITELLM_API_KEY'],max_rounds=1,max_calls=0,max_output_tokens=args.output_maximum,checkpoint=lambda trace:common.save(root/'progress'/'initial'/(q['case_id']+'.json'),trace))
            value.update(condition='initial',query=q,expected=suite['oracle'][q['case_id']])
            value['strict_correct']=value['status']=='completed' and common.score(value['expected'],value['text'])
            common.save(path,value);print(json.dumps({'condition':'initial','case_id':q['case_id'],'status':value['status']}),flush=True)
        return
    if not args.image:parser.error('--image is required for prepare/run')
    base=os.environ['LITELLM_BASE_URL'];token=os.environ['LITELLM_API_KEY']
    frozen=common.REPO/'config/benchmark/evidence/2026-10-11-memory-consistency-4096'
    replay=Replay(frozen/'provider-receipts.jsonl.gz',base,token,root/'replay.jsonl',root/'provider-receipts');local=replay.start()
    elf_runtime.IMAGE=args.image
    image=json.loads(elf_runtime.docker('image','inspect',args.image))[0]
    common.freeze(root/'protocol.json',{'runtime_revision':image['Config']['Labels']['org.opencontainers.image.revision'],'image_id':image['Id'],'conditions':CONDITIONS,'model':common.CHAT,'embedding':common.EMB,'dimensions':4096,'max_rounds':12,'max_tool_calls':24,'max_output_tokens':args.output_maximum,'reasoning':'max','scope':'20 frozen memory questions; 16 scored and 4 development; no competitor rerun','fixture':'Native ingestion with receipt-replayed extraction, not new extraction evaluation; exact cached embeddings reused. All conditions share initial notes. Fresh native identities and ingestion timestamps.','source_tools':'Public document search and verified excerpts only; no hidden message-id to document-id map.','graph_tools':'Public outgoing graph query by surface or returned entity id; follow object entities and evidence-note ids.','generation':'Wrong factual answers are retained. Transport/contract failures require explicit retained-attempt retry.'})
    suite=json.loads((frozen/'frozen-workloads.json').read_text())['memory'];common.freeze(root/'workload.json',suite)
    elf_runtime.prepare_tokenizer(root)
    os.environ['LITELLM_BASE_URL']=local
    try:auth=elf_runtime.start(root,common.REPO,common)
    finally:os.environ['LITELLM_BASE_URL']=base
    def api(path,body=None):return common.api(matched.BASE,path,body,token='Bearer '+auth['memory'],timeout=3600)[0]
    if args.phase=='prepare':
        for item in suite['items']:
            path=root/'ingest'/(item['evidence_id']+'.json');state=json.loads(path.read_text()) if path.exists() else {}
            if 'document' not in state:
                state['document']=api('/v2/docs',{'scope':'agent_private','title':item['evidence_id'],'source_ref':{'schema':'doc_source_ref/v1','doc_type':'knowledge','ts':item['timestamp'],'evidence_id':item['evidence_id']},'content':item['text']});common.save(path,state)
            if 'event' not in state:
                state['event']=api('/v2/events/ingest',{'scope':'agent_private','dry_run':False,'messages':[{'role':'user','content':item['text'],'ts':item['timestamp'],'msg_id':item['evidence_id']}]});common.save(path,state)
            print(json.dumps({'ingested':item['evidence_id']}),flush=True)
        elf_runtime.drain()
        notes=json.loads(elf_runtime.docker('exec','elf-matched-db','psql','-U','postgres','-d','elf','-At','-c',"SELECT json_agg(n) FROM (SELECT note_id,text,status,source_ref FROM memory_notes ORDER BY note_id) n"))
        prior=json.loads((frozen/'baseline-extraction-diagnostics.json').read_text())['notes']
        assert sorted(n['text'] for n in notes)==sorted(n['text'] for n in prior),'Frozen extraction changed note bodies'
        common.save(root/'notes.json',notes);persisted_note_count=len(notes)
        for table in ['graph_entities','graph_entity_aliases','graph_predicates','graph_facts','graph_fact_evidence','memory_note_fields']:
            value=json.loads(elf_runtime.docker('exec','elf-matched-db','psql','-U','postgres','-d','elf','-At','-c',f"SELECT COALESCE(json_agg(t),'[]'::json) FROM {table} t"));common.save(root/(table+'.json'),value)
        for q in suite['queries']:
            path=root/'initial'/(q['case_id']+'.json')
            if path.exists():continue
            result=api('/v2/searches',{'mode':'planned_search','query':q['question'],'top_k':12,'candidate_k':60})
            notes=[api('/v2/notes/'+x['note_id']) for x in result['items']]
            common.save(path,{'search':result,'notes':notes})
        elf_runtime.drain();common.save(root/'prepared.json',{'notes':persisted_note_count,'same_note_bodies':True})
    else:
        assert (root/'prepared.json').exists()
        completed=0
        for index,q in enumerate(suite['queries']):
            order=CONDITIONS[index%4:]+CONDITIONS[:index%4]
            initial=json.loads((root/'initial'/(q['case_id']+'.json')).read_text())['notes']
            for condition in order:
                path=root/'cases'/condition/(q['case_id']+'.json')
                if path.exists():
                    assert json.loads(path.read_text())['status'] in ('completed','tool_budget_exhausted','round_budget_exhausted'),'Archive failed attempt before retry';continue
                if args.limit and completed>=args.limit:return
                try:
                    value=run(api,condition,q['question'],initial,base,token,max_output_tokens=args.output_maximum,checkpoint=lambda trace:common.save(root/'progress'/condition/(q['case_id']+'.json'),trace))
                except Exception as error:
                    value={'status':'failed','error':str(error).replace(token,'[redacted]')}
                value.update(condition=condition,query=q,expected=suite['oracle'][q['case_id']])
                if value['status']=='completed':value['strict_correct']=common.score(value['expected'],value['text'])
                common.save(path,value);completed+=1
                print(json.dumps({'condition':condition,'case_id':q['case_id'],'status':value['status'],'strict_correct':value.get('strict_correct'),'tools':value.get('tool_calls')}),flush=True)
                if value['status']=='failed':raise RuntimeError('Agent run stopped; retain failure and progress before retry')
        elf_runtime.drain();common.save(root/'completed.json',{'cases':80,'note':'Exhausted agents are retained outcomes, not rerun answers.'})
    replay.server.shutdown()


if __name__=='__main__':main()
