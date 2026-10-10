#!/usr/bin/env python3
"""Compare native retrieval and native answers under the cumulative budget gateway."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, secrets, subprocess, time, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from benchmark_deep.complex_documents import workload as pdf_workload
from benchmark_deep.memory_comparison import workload as memory_workload
from benchmark_targets.hindsight import contexts_from_native
from benchmark_runner.answers import request_answers

class AnswerContractError(ValueError):
    def __init__(self, message, receipt):
        super().__init__(message)
        self.receipt = receipt


def decode_answer(response, case_id):
    choice = response['choices'][0]
    if choice['finish_reason'] == 'length':
        raise ValueError('Reader output limit')
    answers = json.loads(choice['message']['content'])['answers']
    parsed = answers[0] if isinstance(answers, list) and len(answers) == 1 else answers
    if (not isinstance(parsed, dict) or parsed.get('case_id') != case_id
            or not isinstance(parsed.get('text'), str) or not parsed['text'].strip()
            or not isinstance(parsed.get('supported'), bool)):
        raise ValueError('Reader must return one identified, nonempty answer with a support flag')
    return parsed


REPO=Path(__file__).resolve().parents[1]
HS_IMAGE='ghcr.io/vectorize-io/hindsight@sha256:acf5e76bd9a5b65f9f7c540a3414007c7f874b34346587dac7e4feab7ae80cba'
HS_NAME='elf-native-comparison-hindsight'
HS='http://127.0.0.1:19888'; RF='http://127.0.0.1:19380/api/v1'
SIDE='http://127.0.0.1:19889'
CHAT='deepseek/deepseek-v4.1-flash'; EMB='qwen/qwen3-embedding-8b'
EXCLUDED={'complex-002','complex-005','complex-020','complex-023'}
INSTRUCTION='Answer the question using only stored evidence. Return concise requested values. If there is no supported answer, say exactly unknown. Do not invent facts. Cite your sources when available.'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')


def freeze(path,value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('Frozen protocol or workload changed: '+path.name)
    else:
        save(path,value)


def api(base,path,body=None,method=None,token=None,timeout=300):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,
        method=method or ('POST' if body is not None else 'GET'),headers={'Content-Type':'application/json',**({'Authorization':token} if token else {})})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=json.load(r);headers=dict(r.headers)
    if base==RF:
        if data.get('code',0)!=0:
            message=str(data.get('message'))
            for credential in (token, os.environ.get('LITELLM_API_KEY'), os.environ.get('EMBEDDING_API_KEY')):
                if credential:message=message.replace(credential.removeprefix('Bearer '),'[redacted]')
            raise RuntimeError(f'RAGFlow {path}: {data.get("code")}: {message}')
        data=data.get('data')
    return data,headers


def ready(url,seconds=600):
    start=time.monotonic()
    while time.monotonic()-start<seconds:
        try:
            with urllib.request.urlopen(url,timeout=3) as r:
                if r.status==200:return
        except Exception:time.sleep(3)
    raise TimeoutError('Service readiness: '+url)


def start_hindsight(root):
    inspection=subprocess.run(['docker','inspect',HS_NAME],capture_output=True,text=True)
    if inspection.returncode==0:
        owned=json.loads(inspection.stdout)[0]
        if owned['Config']['Labels'].get('elf.benchmark')!='native-comparison' or owned['Config']['Image']!=HS_IMAGE:
            raise RuntimeError('Existing Hindsight container is not this experiment')
        return
    env=dict(os.environ)
    base=env['LITELLM_BASE_URL'].replace('127.0.0.1','host.docker.internal')
    values={'LLM_PROVIDER':'openai','LLM_API_KEY':env['LITELLM_API_KEY'],'LLM_BASE_URL':base,'LLM_MODEL':CHAT,
        'LLM_REASONING_EFFORT':'low','LLM_MAX_CONCURRENT':'1','LLM_MAX_RETRIES':'0',
        'EMBEDDINGS_PROVIDER':'openai','EMBEDDINGS_OPENAI_API_KEY':env['EMBEDDING_API_KEY'],
        'EMBEDDINGS_OPENAI_BASE_URL':base,'EMBEDDINGS_OPENAI_MODEL':EMB,'EMBEDDINGS_OPENAI_DIMENSIONS':'1536',
        'EMBEDDINGS_MAX_CONCURRENT_REQUESTS':'1','RERANKER_LOCAL_FORCE_CPU':'true'}
    env.update({'HINDSIGHT_API_'+k:v for k,v in values.items()})
    cmd=['docker','run','-d','--name',HS_NAME,'--label','elf.benchmark=native-comparison',
         '--add-host','host.docker.internal:host-gateway','-p','127.0.0.1:19888:8888','-p','127.0.0.1:19889:8899',
         '-v','elf-native-comparison-hindsight-data:/home/hindsight/.pg0',
         '-v',str(REPO/'scripts/benchmark_deep/native_sidecar.py')+':/native-sidecar.py:ro',
         '-v',str(root)+':/experiment']
    for k in values:cmd+=['-e','HINDSIGHT_API_'+k]
    with (root/'hindsight-start.log').open('w') as f:subprocess.run(cmd+[HS_IMAGE],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)


def register(root, context_tokens=32768):
    password=secrets.token_hex(20)
    encrypted=subprocess.check_output(['openssl','pkeyutl','-encrypt','-pubin','-inkey',str(root/'stack/public.pem'),'-pkeyopt','rsa_padding_mode:pkcs1'],input=base64.b64encode(password.encode()))
    _,headers=api(RF,'/users',{'nickname':'Native benchmark','email':'native-'+secrets.token_hex(8)+'@example.test','password':base64.b64encode(encrypted).decode()})
    auth=next(v for k,v in headers.items() if k.lower()=='authorization')
    token,_=api(RF,'/system/tokens',{},token=auth)
    auth='Bearer '+token['token']
    configure_rag_provider(auth, context_tokens=context_tokens)
    path=root/'private-auth.json';save(path,{'authorization':auth});path.chmod(0o600)
    return auth


def configure_rag_provider(auth, update=False, context_tokens=32768):
    # A resumed budget gateway has a new ephemeral token and may use a new port.
    if not update:
        api(RF,'/providers',{'provider_name':'OpenAI-API-Compatible'},method='PUT',token=auth)
    path='/providers/OpenAI-API-Compatible/instances'+('/native_benchmark' if update else '')
    api(RF,path,{'instance_name':'native_benchmark','api_key':os.environ['LITELLM_API_KEY'],
        'base_url':os.environ['LITELLM_BASE_URL'].replace('127.0.0.1','host.docker.internal'),
        'model_info':[{'model_name':EMB,'model_type':['embedding'],'max_tokens':8192,'extra':{'max_dimension':1536,'dimensions':[1536]}},
                      {'model_name':CHAT,'model_type':['chat'],'max_tokens':context_tokens}]},method='PUT' if update else 'POST',token=auth)


def ingest_rag(root,auth,scope,items):
    from benchmark_targets.ragflow import upload,request
    os.environ.update(RAGFLOW_URL=RF.removesuffix('/api/v1'),RAGFLOW_API_KEY=auth.removeprefix('Bearer '))
    file=root/(scope+'-rag-state.json')
    if file.exists():return json.loads(file.read_text())
    ds=request('POST','/datasets',{'name':'native-'+scope,'embedding_model':EMB+'@native_benchmark@OpenAI-API-Compatible','parser_id':'general','permission':'me'})
    state={'dataset_id':ds['id'],'documents':{}}
    for item in items:state['documents'][item['evidence_id']]=upload(ds['id'],item)
    save(file,state)
    request('POST',f'/datasets/{ds["id"]}/chunks',{'document_ids':list(state['documents'].values())})
    return state


def wait_rag(state,auth):
    start=time.monotonic()
    while time.monotonic()-start<2400:
        d,_=api(RF,f'/datasets/{state["dataset_id"]}/documents?page_size=100',token=auth)
        statuses=[v.get('ingestion_status') for v in d['docs']]
        if statuses and all(x=='COMPLETED' for x in statuses):return d
        if any(x in ('FAILED','CANCELED') for x in statuses):raise RuntimeError('RAGFlow parse failed '+str(statuses))
        time.sleep(5)
    raise TimeoutError('RAGFlow parsing exceeds 2400s')


def ingest_hindsight(root,scope,items):
    bank='/v1/default/banks/native-'+scope
    done=root/(scope+'-hindsight-ingest.json')
    if done.exists():return bank
    api(HS,bank,{},method='PUT')
    records=[{'content':i['text'],'document_id':i['evidence_id'],**({'timestamp':i['timestamp']} if 'timestamp' in i else {})} for i in items]
    retained=root/(scope+'-hindsight-retain.json')
    if not retained.exists():
        result,_=api(HS,bank+'/memories',{'async':True,'items':records})
        save(retained,result)
    start=time.monotonic()
    while time.monotonic()-start<1800:
        states={s:api(HS,bank+'/operations?status='+s+'&limit=1')[0] for s in ('pending','processing','failed')}
        if states['failed']['operations']:raise RuntimeError('Hindsight ingest operation failed')
        if not any(states[s]['operations'] for s in ('pending','processing')):save(done,states);return bank
        time.sleep(3)
    raise TimeoutError('Hindsight consolidation exceeds 1800s')


def labeled(rows):
    parts=[]
    for i,r in enumerate(rows):
        label=r.get('evidence_id') or ','.join(r.get('source_evidence_ids') or []) or f'unidentified-{i}'
        parts.append('[Source: '+label+']\n'+r['text'])
    return '\n'.join(parts)


def score(expected,text):
    clean=re.sub(r'\[.*?\]|##\d+\$\$', '',text).strip()
    if not expected['supported']:return bool(re.fullmatch(r'unknown[.!]?',clean,re.I))
    return all(f.casefold() in text.casefold() for f in expected['facts']) and not any(f.casefold() in text.casefold() for f in expected['forbidden'])


def run_case(root,condition,q,expected,call,scorer=score):
    path=root/'cases'/condition/(q['case_id']+'.json')
    if path.exists():
        if json.loads(path.read_text())['status']=='completed':return
        archive=root/'attempts'/condition/(q['case_id']+'-'+str(time.time_ns())+'.json')
        archive.parent.mkdir(parents=True,exist_ok=True);path.rename(archive)
    start=time.monotonic()
    ledger=root.parent/'cost-calibration/budget-ledger.json'
    first=len(json.loads(ledger.read_text())['requests'])+1
    try:
        value=call();value.update(status='completed',correct=scorer(expected,value['text']))
    except Exception as e:
        msg=str(e)
        for key in ('LITELLM_API_KEY','EMBEDDING_API_KEY','RAGFLOW_API_KEY'):
            if os.environ.get(key):msg=msg.replace(os.environ[key],'[redacted]')
        value={'status':'failed','error':type(e).__name__+': '+msg,'correct':None}
        if isinstance(e,AnswerContractError):value['failed_receipt']=e.receipt
    value.update(condition=condition,case_id=q['case_id'],question=q['question'],lane=q['lane'],split=q.get('split','diagnostic'),seconds=time.monotonic()-start,expected=expected)
    value.update(first_ordinal=first,last_ordinal=len(json.loads(ledger.read_text())['requests']))
    save(path,value);print(json.dumps({k:value[k] for k in ('condition','case_id','status','correct','seconds')}),flush=True)


def shared_answer(q,rows,native,max_tokens=8192,reasoning_effort="low",timeout=300):
    budget,_=api(SIDE,'/tokens',{'text':labeled(rows),'max_tokens':4096})
    env={'BENCHMARK_CHAT_API_BASE':os.environ['LITELLM_BASE_URL'],'BENCHMARK_CHAT_API_KEY':os.environ['LITELLM_API_KEY'],'BENCHMARK_CHAT_MODEL':CHAT,'BENCHMARK_CHAT_REASONING_EFFORT':reasoning_effort}
    answer=request_answers([{'case_id':q['case_id'],'question':q['question'],'context':budget['text']}],env,max_tokens=max_tokens,timeout=timeout)
    try:
        parsed=decode_answer(answer,q['case_id'])
    except (ValueError,KeyError,TypeError,IndexError) as error:
        raise AnswerContractError(str(error),{'context':budget,'native':native,'reader':answer}) from error
    return {'text':parsed['text'],'supported':parsed['supported'],'context':budget,'native':native,'reader':answer}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact-root',type=Path,required=True);args=ap.parse_args();root=args.artifact_root.resolve();root.mkdir(parents=True,exist_ok=True)
    pdf,po=pdf_workload();mem,mo=memory_workload()
    suites={'pdf':{'items':pdf['actions'][0]['items'],'queries':[q for q in pdf['actions'][1:] if q['case_id'] not in EXCLUDED],'oracle':po},'memory':{**mem,'oracle':mo}}
    freeze(root/'frozen-workloads.json',suites)
    freeze(root/'protocol.json',{'hindsight_version':'0.10.3','ragflow_version':'1.0.0-rc1','context_tokens':4096,'tokenizer':'cl100k_base proxy; not claimed to equal DeepSeek tokenization','hindsight_budget':'high','rag_page_size':64,'rag_threshold':0.0,'rag_vector_weight':0.3,'reader_max_tokens':8192,'native_max_tokens':8192,'chat':CHAT,'embedding':EMB,'embedding_dimensions':1536,'excluded_pdf_cases':sorted(EXCLUDED),'native_boundary':'Native reflect versus native retrieval-chat; different internal algorithms with metered costs. No full Agent workflow claim.'})
    start_hindsight(root);ready(HS+'/health')
    try:api(SIDE,'/tokens',{'text':'readiness'})
    except Exception:
        subprocess.run(['docker','exec','-d',HS_NAME,'sh','-c','python /native-sidecar.py > /experiment/sidecar.log 2>&1'],check=True)
    auth=register(root) if not (root/'private-auth.json').exists() else json.loads((root/'private-auth.json').read_text())['authorization']
    states={scope:ingest_rag(root,auth,scope,suite['items']) for scope,suite in suites.items()}
    banks={scope:ingest_hindsight(root,scope,suite['items']) for scope,suite in suites.items()}
    # Sidecar starts after the native image initializes its model dependencies.
    for _ in range(120):
        try:api(SIDE,'/tokens',{'text':'readiness'});break
        except Exception:time.sleep(2)
    else:raise TimeoutError('Tokenizer/reranker sidecar not ready')
    if not (root/'vllm-preflight.json').exists():
        api(RF,'/providers',{'provider_name':'VLLM'},method='PUT',token=auth)
        result,_=api(RF,'/providers/VLLM/instances',{'instance_name':'native_cpu','api_key':'local-benchmark-only','base_url':'http://host.docker.internal:19889/v1',
            'model_info':[{'model_name':'cross-encoder/ms-marco-MiniLM-L-6-v2','model_type':['rerank'],'max_tokens':512}]},token=auth)
        save(root/'vllm-preflight.json',{'configured':True})
    rerank='cross-encoder/ms-marco-MiniLM-L-6-v2@native_cpu@VLLM'
    def hindsight_lane():
        for scope in ('memory','pdf'):
            suite=suites[scope];bank=banks[scope]
            for q in sorted(suite['queries'],key=lambda q:q.get('split')!='dev'):
                expected=suite['oracle'][q['case_id']]
                def hs_recall():
                    raw,_=api(HS,bank+'/memories/recall',{'query':q['question'],'budget':'high','max_tokens':4096,'include':{'source_facts':{'max_tokens':8192}},'trace':True})
                    return shared_answer(q,contexts_from_native(raw,limit=None),raw)
                run_case(root,'hindsight-recall-budget',q,expected,hs_recall)
                def reflect():
                    raw,_=api(HS,bank+'/reflect',{'query':q['question']+'\n'+INSTRUCTION,'budget':'mid','max_tokens':8192,'include':{'facts':{},'tool_calls':{}}},timeout=600)
                    return {'text':raw['text'],'native':raw}
                run_case(root,'hindsight-reflect',q,expected,reflect)

    def ragflow_lane():
        for scope in ('memory','pdf'):
            suite=suites[scope];state=states[scope]
            save(root/(scope+'-parsed.json'),wait_rag(state,auth))
            chat_file=root/(scope+'-chat-config.json')
            if chat_file.exists():
                chat=json.loads(chat_file.read_text())
            else:
                chat,_=api(RF,'/chats',{'name':'native-'+scope,'dataset_ids':[state['dataset_id']],'llm_id':CHAT+'@native_benchmark@OpenAI-API-Compatible',
                    'llm_setting':{'temperature':0.1,'max_tokens':8192},'similarity_threshold':0.0,'vector_similarity_weight':0.3,'top_n':20,'top_k':1024,'rerank_id':rerank,
                    'prompt_config':{'system':INSTRUCTION+'\nEvidence:\n{knowledge}','empty_response':'unknown','quote':True,'refine_multiturn':False,'parameters':[{'key':'knowledge','optional':False}]}},token=auth)
                save(chat_file,chat)
            inverse={v:k for k,v in state['documents'].items()}
            for q in sorted(suite['queries'],key=lambda q:q.get('split')!='dev'):
                expected=suite['oracle'][q['case_id']]
                def rag_recall():
                    raw,_=api(RF,'/retrieval',{'question':q['question'],'dataset_ids':[state['dataset_id']],'page':1,'page_size':64,'similarity_threshold':0.0,'vector_similarity_weight':0.3,'top_k':1024,'rerank_id':rerank},token=auth)
                    rows=[{'evidence_id':inverse.get(c['document_id']),'text':c['content']} for c in raw['chunks']]
                    return shared_answer(q,rows,raw)
                run_case(root,'ragflow-retrieval-rerank',q,expected,rag_recall)
                def rag_chat():
                    raw,_=api(RF,'/chat/completions',{'chat_id':chat['id'],'messages':[{'role':'user','content':q['question']}],'stream':False,'max_tokens':8192,'store_history_messages':False},token=auth,timeout=600)
                    text=raw.get('answer') or raw.get('content')
                    if not text or '**ERROR**' in text:raise RuntimeError('Native chat returned no answer: '+json.dumps(raw))
                    return {'text':text,'native':raw}
                run_case(root,'ragflow-native-chat',q,expected,rag_chat)

    save(root/'execution.json',{'parallel_product_lanes':2,'serial_within_product':True,
        'cost_attribution':'Cumulative metered cost is authoritative. Per-case ordinal windows can overlap and must not be summed as exclusive per-product costs.',
        'latency_boundary':'Observed latency includes concurrent parsing/queries on the same host and gateway. Not an isolated performance comparison.'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(hindsight_lane),pool.submit(ragflow_lane)]
        for future in futures:future.result()
    rows=[json.loads(p.read_text()) for p in sorted((root/'cases').glob('*/*.json'))]
    save(root/'results.json',rows)
    return 0 if all(r['status']=='completed' for r in rows) else 1

if __name__=='__main__':raise SystemExit(main())
