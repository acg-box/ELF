"""Protect source isolation and receipt replay in the ELF agent experiment."""
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_agent.replay import Replay
from benchmark_agent.schedule import run_jobs
from benchmark_agent.tools import project_note,execute,schemas
from benchmark_agent.runner import parse_answer,finalize_recorded,run
from benchmark_agent.analysis import case_metrics,evidence_payload


class AgentBoundaries(unittest.TestCase):
    def test_case_scheduler_keeps_jobs_distinct_and_stops_after_failure(self):
        import threading
        barrier=threading.Barrier(2);seen=[]
        def call(job):
            barrier.wait(timeout=5)
            seen.append(job)
        run_jobs(list(range(4)),call,2)
        self.assertEqual(sorted(seen),list(range(4)))
        seen=[]
        def fail(job):
            seen.append(job)
            raise RuntimeError('Retain failed case')
        with self.assertRaises(RuntimeError):run_jobs(list(range(4)),fail,1)
        self.assertEqual(seen,[0])

    def test_native_expansion_only_in_source_conditions(self):
        calls=[]
        def api(path):
            calls.append(path)
            return {'note':{'note_id':'n','text':'derived'},'sources':[{'excerpt':{'excerpt':'original subject'}}],'complete':True} if path.endswith('/evidence') else {'note_id':'n','text':'derived'}
        expanded=execute(api,'source','get_note',{'note_id':'n'},True)
        self.assertEqual(calls[-1],'/v2/notes/n/evidence')
        self.assertIn('original subject',json.dumps(evidence_payload('get_note',expanded)))
        notes=execute(api,'notes','get_note',{'note_id':'n'},True)
        self.assertNotIn('source_evidence',notes)
        self.assertEqual(calls[-1],'/v2/notes/n')

    def test_grounded_selector_contract_and_failed_audit_do_not_resample(self):
        schema=next(t['function']['parameters'] for t in schemas('source',True) if t['function']['name']=='read_document')
        self.assertEqual(len(schema['oneOf']),2)
        answer={'text':'Wrong but retained.','supported':True,'citations':['n'],'claims':[{'text':'Wrong but retained.','state':'supported','citations':[{'kind':'note','note_id':'n','quote':'not present'}]}]}
        response={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(answer)}}]}
        with patch('benchmark_agent.runner.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result=run(lambda *args:(_ for _ in ()).throw(ValueError('audit unavailable')),'notes','question',[],'http://local','token',grounded=True)
        self.assertEqual(result['text'],answer['text'])
        self.assertEqual(result['status'],'completed')
        self.assertIn('claim_binding_error',result)
        self.assertEqual(call.call_count,1)

    def test_query_echo_is_not_retrieved_evidence(self):
        value={'items':[],'query_plan':{'query':'REPLAY-0-632'}}
        self.assertNotIn('REPLAY-0-632',json.dumps(evidence_payload('search_notes',value)))
        value={'subject':{'canonical':'REPLAY-0-632'},'facts':[]}
        self.assertNotIn('REPLAY-0-632',json.dumps(evidence_payload('query_graph',value)))

    def test_transport_resume_reuses_completed_tools_and_refuses_final_answers(self):
        message={'role':'assistant','content':None,'tool_calls':[{'id':'a','function':{'name':'get_note','arguments':'{}'}}]}
        prior=[{'turn':0,'response':{'choices':[{'message':message}]},'tools':[{'name':'get_note','arguments':{},'result':{'text':'already read'}}]}]
        answer={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({'text':'answer','supported':True,'citations':[]})}}]}
        requests=[]
        def reply(req,**kwargs):requests.append(json.loads(req.data));return io.BytesIO(json.dumps(answer).encode())
        with patch('benchmark_agent.runner.urllib.request.urlopen',side_effect=reply):
            result=run(lambda *args:self.fail('Do not repeat completed tools'),'notes','question',[],'http://local','token',prior_trace=prior)
        self.assertEqual(result['tool_calls'],1)
        self.assertEqual(result['trace'][0],prior[0])
        self.assertEqual(json.loads(requests[0]['messages'][-1]['content']),{'text':'already read'})
        with self.assertRaises(ValueError):run(None,'notes','question',[],'unused','token',prior_trace=[{'response':answer,'tools':[]}])

    def test_cached_expansion_is_a_read_without_touch_or_new_search(self):
        calls=[]
        execute(lambda *args:(calls.append(args) or {}),'paged','get_search',{'search_id':'session','top_k':24})
        self.assertEqual(calls,[('/v2/searches/session?top_k=24&touch=false',)])
        self.assertTrue(any(t['function']['name']=='get_search' for t in schemas('notes')))

    def test_original_budget_reserves_a_final_answer_without_more_retrieval(self):
        call={'id':'a','function':{'name':'get_note','arguments':'{"note_id":"n"}'}}
        responses=[{'choices':[{'message':{'role':'assistant','tool_calls':[call]}}]},
                   {'choices':[{'message':{'role':'assistant','content':'{"text":"observed","supported":true,"citations":["n"]}'}}]}]
        sent=[];executed=[]
        def reply(request,**kwargs):
            sent.append(json.loads(request.data));return io.BytesIO(json.dumps(responses.pop(0)).encode())
        with patch('benchmark_agent.runner.urllib.request.urlopen',side_effect=reply):
            result=run(lambda *args:(executed.append(args) or {'note_id':'n','text':'observed'}),'notes','question',[],'http://local','token',max_rounds=2,max_calls=1)
        self.assertEqual((len(sent),len(executed),result['status']),(2,1,'completed'))
        self.assertNotIn('tools',sent[-1])
        self.assertEqual(sent[-1]['max_tokens'],393216)
        self.assertEqual(result['tool_calls'],1)

    def test_finalization_preserves_tools_without_supplying_oracle(self):
        message={'role':'assistant','content':None,'tool_calls':[{'id':'a','function':{'name':'get_note','arguments':'{}'}},{'id':'b','function':{'name':'get_note','arguments':'{}'}}]}
        case={'query':{'question':'Which fact?'},'expected':{'facts':['SECRET_ORACLE']},'trace':[{'response':{'choices':[{'message':message}]},'tools':[{'result':{'text':'observed'}}]}]}
        requests=[]
        def reply(req,**kwargs):
            requests.append(json.loads(req.data));return io.BytesIO(b'{"choices":[]}')
        with patch('benchmark_agent.runner.urllib.request.urlopen',side_effect=reply):finalize_recorded(case,[],'http://local','token',123)
        request=requests[0]
        self.assertNotIn('tools',request)
        self.assertNotIn('SECRET_ORACLE',json.dumps(request))
        outputs=[m for m in request['messages'] if m['role']=='tool']
        self.assertEqual([m['tool_call_id'] for m in outputs],['a','b'])
        self.assertEqual(json.loads(outputs[0]['content']),{'text':'observed'})
        self.assertIn('error',json.loads(outputs[1]['content']))

    def test_no_tool_control_retains_invalid_output_without_resampling(self):
        response={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'<invented tool call>'}}]}
        with patch('benchmark_agent.runner.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result=run(None,'initial','question',[],'http://unused','token',max_rounds=1,max_calls=0)
        self.assertEqual(result['status'],'invalid_answer')
        self.assertEqual(result['text'],'<invented tool call>')
        self.assertEqual(result['tool_calls'],0)
        self.assertFalse(result['format_compliant'])
        self.assertEqual(call.call_count,1)

    def test_fenced_answer_is_retained_as_format_failure_without_resampling(self):
        raw=json.dumps({'text':'answer','supported':True,'citations':['note']})
        self.assertFalse(parse_answer('Explanation\n```json\n'+raw+'\n```')['format_compliant'])
        self.assertTrue(parse_answer(raw)['format_compliant'])
        with self.assertRaises(ValueError):parse_answer('```json\n'+raw+'\n```\n```json\n'+raw+'\n```')
        with self.assertRaises(ValueError):parse_answer('{"text":"x","supported":true,"citations":[3]}')

    def test_graph_use_requires_following_a_previously_returned_link(self):
        tools=[{'name':'query_graph','arguments':{'surface':'A'},'result':{'subject':{'entity_id':'a'},'facts':[{'object':{'entity':{'entity_id':'b'}},'evidence_note_ids':['n']}]}},
               {'name':'query_graph','arguments':{'entity_id':'b'},'result':{'subject':{'entity_id':'b'},'facts':[]}},
               {'name':'get_note','arguments':{'note_id':'n'},'result':{'note_id':'n','text':'fact'}}]
        case={'condition':'graph','query':{'case_id':'test','split':'test','lane':'cross_session'},'status':'completed','text':'fact','citations':['n','invented'],'expected':{'facts':['fact']},'trace':[{'tools':tools,'response':{'usage':{'cost':0.01}}}]}
        row=case_metrics(case,[])
        self.assertEqual(len(row['graph_object_follows']),1)
        self.assertEqual(row['graph_object_follows'][0]['facts'],0)
        self.assertEqual(row['graph_evidence_note_follows'],['n'])
        self.assertEqual(row['unseen_citations'],['invented'])
        self.assertEqual(row['chat_cost_usd'],0.01)

    def test_source_disabled_conditions_do_not_receive_original_quotes(self):
        note={'text':'derived','source_ref':{'evidence':[{'quote':'original'}]},'structured':{'facts':['derived fact']}}
        for condition in ['notes','graph']:
            self.assertNotIn('source_ref',project_note(note,condition))
        self.assertIn('source_ref',project_note(note,'source'))
        self.assertIn('source_ref',note)

    def test_unavailable_tool_cannot_call_api(self):
        calls=[]
        with self.assertRaises(ValueError):execute(lambda *args:calls.append(args),'notes','query_graph',{'surface':'project'})
        self.assertEqual(calls,[])

    def test_excerpts_must_verify(self):
        with self.assertRaises(ValueError):execute(lambda *args:{'verification':{'verified':False}},'source','read_document',{'doc_id':'doc','chunk_id':'chunk'})

    def test_graph_subject_and_time_reach_native_endpoint(self):
        calls=[]
        execute(lambda *args:calls.append(args),'graph','query_graph',{'entity_id':'entity','as_of':'2026-08-01T00:00:00Z'})
        self.assertEqual(calls[0][0],'/v2/graph/query')
        self.assertEqual(calls[0][1]['subject'],{'entity_id':'entity'})
        self.assertEqual(calls[0][1]['as_of'],'2026-08-01T00:00:00Z')

    def test_replay_requires_matching_extraction_and_keeps_full_vector(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'receipts.gz';v=[0.1]*4096
            row={'ordinal':1,'request':{'input':['same','same'],'dimensions':4096},'response':{'data':[{'index':0,'embedding':v},{'index':1,'embedding':[0.2]*4096}]}}
            p.write_bytes(gzip.compress(json.dumps(row).encode()))
            replay=Replay(p,'unused','token',root/'replay.jsonl')
            result=replay.resolve('/v1/embeddings',{'input':'same'})
            self.assertEqual(result['data'][0]['embedding'],v)
            with self.assertRaises(ValueError):replay.resolve('/v1/chat/completions',{'messages':[{'role':'user','content':'unseen'}]})
            current=root/'current';current.mkdir()
            (current/'2.json').write_text(json.dumps({'request':{'input':'new query','dimensions':4096},'response':{'data':[{'index':0,'embedding':v}]}}))
            messages=[{'role':'system','content':'You are a memory extraction engine current'}]
            response={'choices':[{'message':{'content':'{"notes":[]}'},'finish_reason':'stop'}]}
            (current/'3.json').write_text(json.dumps({'request':{'messages':messages},'response':response}))
            restarted=Replay(p,'unused','token',root/'replay.jsonl',current)
            self.assertEqual(restarted.resolve('/v1/embeddings',{'input':'new query'})['data'][0]['embedding'],v)
            live=Replay(p,'unused','token',root/'replay.jsonl',current,live_extraction=True)
            self.assertEqual(live.resolve('/v1/chat/completions',{'messages':messages}),response)

if __name__=='__main__':unittest.main()
