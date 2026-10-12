"""Protect source isolation and receipt replay in the ELF agent experiment."""
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_agent.replay import Replay
from benchmark_agent.tools import project_note,execute,schemas


class AgentBoundaries(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
