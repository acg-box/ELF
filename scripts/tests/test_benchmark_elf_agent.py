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
from benchmark_agent.tools import project_note,execute,schemas
from benchmark_agent.runner import parse_answer,finalize_recorded
from benchmark_agent.analysis import case_metrics


class AgentBoundaries(unittest.TestCase):
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
            restarted=Replay(p,'unused','token',root/'replay.jsonl',current)
            self.assertEqual(restarted.resolve('/v1/embeddings',{'input':'new query'})['data'][0]['embedding'],v)

if __name__=='__main__':unittest.main()
