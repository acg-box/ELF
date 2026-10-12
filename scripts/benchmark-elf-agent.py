#!/usr/bin/env python3
"""Exercise ELF source and graph tools over frozen, receipt-backed memory extraction."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

from benchmark_agent.replay import Replay
from benchmark_agent.schedule import run_jobs
from benchmark_agent.runner import run,finalize_recorded,parse_answer,PROMPT,GROUNDED_PROMPT
from benchmark_agent.analysis import analyze,initial_coverage
from benchmark_deep import elf_runtime

spec=importlib.util.spec_from_file_location('matched',Path(__file__).with_name('benchmark-elf-matched.py'))
matched=importlib.util.module_from_spec(spec);spec.loader.exec_module(matched)
common=matched.common
CONDITIONS=['notes','source','graph','both']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--image')
    parser.add_argument('--phase',choices=['prepare','run','paged','control','finalize','analyze'],required=True);parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--live-extraction',action='store_true',help='Use the current native extractor instead of frozen extraction; retain source workloads and receipts')
    parser.add_argument('--reuse-receipts',type=Path,action='append',default=[],help='Reuse only exact full-4096d embedding inputs from a prior gzipped receipt bundle')
    parser.add_argument('--output-maximum',type=int,default=393216)
    parser.add_argument('--resume-case',help='Explicit condition/case_id continuation from a retained complete tool batch after an archived transport failure')
    parser.add_argument('--grounded',action='store_true',help='Use native evidence expansion and per-claim citations; retain semantic failures')
    parser.add_argument('--workload',type=Path,help='Frozen compatible workload, including distinct comparison cases')
    parser.add_argument('--workers',type=int,choices=[1,2],default=1,help='Independent primary cases; controls remain serial. Never changes per-case budgets.')
    args=parser.parse_args();root=args.root.resolve();root.mkdir(parents=True,exist_ok=True)
    if args.phase=='analyze':
        print(json.dumps(analyze(root)['summary'],indent=2));return
    if args.phase=='finalize':
        protocol=json.loads((root/'protocol.json').read_text());assert protocol['max_output_tokens']==args.output_maximum
        common.freeze(root/'finalization-protocol.json',{'purpose':'Separate loop termination failure from missing evidence. One final model response from the original exhausted trace, with no additional retrieval. Primary exhausted cases remain unchanged.','max_output_tokens':args.output_maximum})
        for source in sorted((root/'cases').glob('*/*.json'))+sorted((root/'paged-cases').glob('*/*.json')):
            case=json.loads(source.read_text())
            if case['status'] not in ('tool_budget_exhausted','round_budget_exhausted'):continue
            path=root/'finalizations'/case['condition']/source.name
            if path.exists():continue
            saved=json.loads((root/'initial'/source.name).read_text());initial=saved['notes']
            raw_path=root/'finalization-responses'/case['condition']/source.name
            if raw_path.exists():raw=json.loads(raw_path.read_text())
            else:
                raw=finalize_recorded(case,initial,os.environ['LITELLM_BASE_URL'],os.environ['LITELLM_API_KEY'],args.output_maximum,initial_search_id=saved['search']['search_id'] if protocol.get('initial_search_id') or case['condition']=='paged' else None);common.save(raw_path,raw)
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
            progress=root/'progress'/'initial'/(q['case_id']+'.json')
            if progress.exists():
                raise RuntimeError('A recorded control response requires offline recovery before continuing: '+str(progress))
            value=run(None,'initial',q['question'],initial,os.environ['LITELLM_BASE_URL'],os.environ['LITELLM_API_KEY'],max_rounds=1,max_calls=0,max_output_tokens=args.output_maximum,checkpoint=lambda trace:common.save(progress,trace),grounded=args.grounded)
            value.update(condition='initial',query=q,expected=suite['oracle'][q['case_id']])
            value['strict_correct']=value['status']=='completed' and common.score(value['expected'],value['text'])
            common.save(path,value);print(json.dumps({'condition':'initial','case_id':q['case_id'],'status':value['status']}),flush=True)
        return
    if not args.image:parser.error('--image is required for prepare/run')
    base=os.environ['LITELLM_BASE_URL'];token=os.environ['LITELLM_API_KEY']
    frozen=common.REPO/'config/benchmark/evidence/2026-10-11-memory-consistency-4096'
    replay=Replay(frozen/'provider-receipts.jsonl.gz',base,token,root/'replay.jsonl',root/'provider-receipts',live_extraction=args.live_extraction,reuse_receipts=args.reuse_receipts);local=replay.start()
    elf_runtime.IMAGE=args.image
    image=json.loads(elf_runtime.docker('image','inspect',args.image))[0]
    common.freeze(root/'protocol.json',{'runtime_revision':image['Config']['Labels']['org.opencontainers.image.revision'],'image_id':image['Id'],'conditions':CONDITIONS,'model':common.CHAT,'embedding':common.EMB,'dimensions':4096,'max_rounds':12,'max_tool_calls':24,'max_output_tokens':args.output_maximum,'reasoning':'max','scope':'Original memory questions and separately scored frozen contrast cases; no competitor rerun' if args.workload else '20 frozen memory questions; 16 scored and 4 development; no competitor rerun','fixture':('Current native extraction from unchanged source documents; exact matching embeddings reused.' if args.live_extraction else 'Native ingestion with receipt-replayed extraction; exact cached embeddings reused.'),'live_extraction':args.live_extraction,'agent_policy':'grounded-v3' if args.grounded else 'bounded-v2','agent_prompt':GROUNDED_PROMPT if args.grounded else PROMPT,'initial_search_id':True,'reused_embedding_bundles':[str(p) for p in args.reuse_receipts],'source_tools':'Native note evidence expansion plus public document search and verified excerpts; no hidden source mapping.' if args.grounded else 'Public document search and verified excerpts only; no hidden message-id to document-id map.','graph_tools':'Public outgoing graph query by surface or returned entity id; follow object entities and evidence-note ids. Unknown validity is not current truth.','generation':'Wrong factual answers are retained. Transport/contract failures require explicit retained-attempt retry.'})
    suite=json.loads(args.workload.read_text()) if args.workload else json.loads((frozen/'frozen-workloads.json').read_text())['memory'];common.freeze(root/'workload.json',suite)
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
                message={'role':'user','content':item['text'],'ts':item['timestamp'],'msg_id':item['evidence_id']}
                if args.live_extraction:
                    message['source_document']={'doc_id':state['document']['doc_id'],'content_hash':state['document']['content_hash'],'position':{'start':0,'end':len(item['text'].encode())}}
                state['event']=api('/v2/events/ingest',{'scope':'agent_private','dry_run':False,'messages':[message]});common.save(path,state)
            print(json.dumps({'ingested':item['evidence_id']}),flush=True)
        elf_runtime.drain()
        notes=json.loads(elf_runtime.docker('exec','elf-matched-db','psql','-U','postgres','-d','elf','-At','-c',"SELECT json_agg(n) FROM (SELECT note_id,text,status,source_ref FROM memory_notes ORDER BY note_id) n"))
        prior=json.loads((frozen/'baseline-extraction-diagnostics.json').read_text())['notes']
        same_note_bodies=sorted(n['text'] for n in notes)==sorted(n['text'] for n in prior)
        if not args.live_extraction:assert same_note_bodies,'Frozen extraction changed note bodies'
        common.save(root/'notes.json',notes);persisted_note_count=len(notes)
        for table in ['graph_entities','graph_entity_aliases','graph_predicates','graph_facts','graph_fact_evidence','memory_note_fields']:
            value=json.loads(elf_runtime.docker('exec','elf-matched-db','psql','-U','postgres','-d','elf','-At','-c',f"SELECT COALESCE(json_agg(t),'[]'::json) FROM {table} t"));common.save(root/(table+'.json'),value)
        for q in suite['queries']:
            path=root/'initial'/(q['case_id']+'.json')
            if path.exists():continue
            result=api('/v2/searches',{'mode':'planned_search','query':q['question'],'top_k':12,'candidate_k':60})
            notes=[api('/v2/notes/'+x['note_id']) for x in result['items']]
            common.save(path,{'search':result,'notes':notes})
        elf_runtime.drain();common.save(root/'prepared.json',{'notes':persisted_note_count,'same_note_bodies':same_note_bodies,'live_extraction':args.live_extraction})
    else:
        assert (root/'prepared.json').exists()
        queries=suite['queries'];folder='cases'
        if args.phase=='paged':
            missing={r['case_id'] for r in initial_coverage(root,suite) if r['structured_missing']}
            queries=[q for q in queries if q['case_id'] in missing];folder='paged-cases'
            common.freeze(root/'paged-protocol.json',{'cases':sorted(missing),'selection':'Diagnostic subset selected after observing missing identifiers in the initial context; not a new unbiased suite.','tools':'Note search/read plus native cached search-session expansion. No source or graph tools.','initial':'Same twelve notes plus the native initial search_id. In bounded-v2 this capability is already available in primary conditions.','max_output_tokens':args.output_maximum})
        jobs=[]
        for index,q in enumerate(queries):
            order=['paged'] if args.phase=='paged' else CONDITIONS[index%4:]+CONDITIONS[:index%4]
            for condition in order:
                path=root/folder/condition/(q['case_id']+'.json')
                if path.exists():
                    assert json.loads(path.read_text())['status'] in ('completed','tool_budget_exhausted','round_budget_exhausted','invalid_answer'),'Archive failed attempt before retry';continue
                jobs.append((q,condition,path))
        planned=len(jobs)
        if args.limit:jobs=jobs[:args.limit]
        common.freeze(root/(args.phase+'-execution-policy.json'),{'workers':args.workers,'scope':'Independent cases only. Single-case prompts and tool budgets are unchanged. Concurrent wall latency is not directly comparable to serial latency.'})
        def execute_case(job):
            q,condition,path=job
            saved=json.loads((root/'initial'/(q['case_id']+'.json')).read_text());initial=saved['notes']
            prior=None
            if args.resume_case==condition+'/'+q['case_id']:
                prior=json.loads((root/'progress'/condition/(q['case_id']+'.json')).read_text())
            try:
                value=run(api,condition,q['question'],initial,base,token,max_output_tokens=args.output_maximum,checkpoint=lambda trace:common.save(root/'progress'/condition/(q['case_id']+'.json'),trace),initial_search_id=saved['search']['search_id'],prior_trace=prior,grounded=args.grounded)
            except Exception as error:
                value={'status':'failed','error':str(error).replace(token,'[redacted]')}
            value.update(condition=condition,query=q,expected=suite['oracle'][q['case_id']])
            if prior is not None:
                value['resume_seconds']=value.get('seconds');value['seconds']=None;value['resumed_recorded_turns']=len(prior)
            if value['status']=='completed':value['strict_correct']=common.score(value['expected'],value['text'])
            common.save(path,value)
            print(json.dumps({'condition':condition,'case_id':q['case_id'],'status':value['status'],'strict_correct':value.get('strict_correct'),'tools':value.get('tool_calls')}),flush=True)
            if value['status']=='failed':raise RuntimeError('Agent run stopped; retain failure and progress before retry')
        run_jobs(jobs,execute_case,args.workers)
        elf_runtime.drain()
        completion={'cases':len(jobs),'remaining':planned-len(jobs),'note':'Exhausted agents are retained outcomes, not rerun answers. Counts cover only cases executed in this invocation.'}
        common.save(root/(args.phase+'-invocation-completed.json'),completion)
        if len(jobs)==planned:common.save(root/('paged-completed.json' if args.phase=='paged' else 'completed.json'),completion)
    replay.server.shutdown()


if __name__=='__main__':main()
