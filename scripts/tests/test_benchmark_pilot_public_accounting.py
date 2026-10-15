"""Verify opening settlements and partial evidence without provider calls."""
import gzip
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.tests.benchmark_support import REPO
from benchmark_pilot.corpus import save
from benchmark_pilot.export import export
from benchmark_pilot.report import measurements
from benchmark_pilot.verify_export import explicit_cost, verify
from benchmark_budget import totals

ARMS=['no_elf','source_only','full_elf']
def fixture(root, prior=0, historical_cost='absent', historical_status='uncertain', formal_arms=None, calibration_limit=None, invalid_arm=None, failed_arm=None):
    f=root/'fixture'; f.mkdir(parents=True)
    source={'id':'s1','title':'record','timestamp':'2026-10-15T00:00:00Z','text':'record','stage':0,'sha256':hashlib.sha256(b'record').hexdigest()}
    (f/'sources.jsonl.gz').write_bytes(gzip.compress((json.dumps(source)+'\n').encode(),mtime=0))
    save(f/'checkpoints.json',[{'id':'initial'}])
    tasks=[{'id':name,'phase':phase,'stage':0,'question':'record'} for name,phase in [('cal0','calibration'),('cal1','calibration'),('task','formal')]]
    save(f/'tasks.json',tasks)
    save(f/'oracle.json',[{'id':t['id'],'criteria':[{'obligation':'record','patterns':['record']}]} for t in tasks])
    save(f/'protocol.json',{'conditions':ARMS,'formal_repetitions':1,'calibration_repetitions':1,'max_tool_calls':32,'max_evidence_bytes':65536,'embedding_dimensions':4096,'model':'openai/gpt-6-luna','reasoning':'medium','max_output_tokens':128000})
    save(f/'freeze.json',{'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in f.iterdir() if p.is_file()}})
    requests=[{'ordinal':1,'kind':'chat','status':historical_status,'reserved_usd':0.02,'usage':{} if historical_cost=='absent' else {'cost':historical_cost}}]
    reviews={}
    selected=[(task,arm) for task in tasks if task['phase']=='calibration' for arm in ARMS]
    if calibration_limit is not None: selected=selected[:calibration_limit]
    selected += [(tasks[-1],arm) for arm in (ARMS if formal_arms is None else formal_arms)]
    for index,(task,arm) in enumerate(selected):
        before_paid,before_exposure=totals({'prior_paid_usd':prior,'requests':requests})
        status='completed'
        if task['phase']=='formal' and arm==invalid_arm: status='invalid_answer'
        if task['phase']=='formal' and arm==failed_arm: status='transport_failed'
        request={'ordinal':len(requests)+1,'kind':'chat','status':'completed','reserved_usd':0.02,'usage':{'cost':0.001,'prompt_tokens':100,'completion_tokens':20,'total_tokens':120},'model':'openai/gpt-6-luna','requested_max_tokens':128000,'reasoning_effort':'medium'}
        requests.append(request)
        after_paid,after_exposure=totals({'prior_paid_usd':prior,'requests':requests})
        cell=task['id']+'--'+arm+'--1'
        passed=status=='completed'
        save(root/'cases'/cell/'result.json',{'cell':cell,'task_id':task['id'],'phase':task['phase'],'condition':arm,'repetition':1,'status':status,'seconds':1,'tool_calls':1,'evidence_bytes':10,'stage':0,'pid':100+index,'answer':{'text':'record','claims':[]} if passed else {},'all_references_seen':passed,'claim_bindings':{'claims':[{'binding_verified':True}]} if passed else {},'usage_before':{'requests':len(requests)-1,'paid_usd':before_paid,'exposure_usd':before_exposure},'usage_after':{'requests':len(requests),'paid_usd':after_paid,'exposure_usd':after_exposure}})
        save(root/'cases'/cell/'trace.json',[])
        reviews[cell]={'accepted':passed,'passed_criteria':int(passed),'flags':[] if passed else ['invalid_format' if status=='invalid_answer' else 'incomplete']}
    save(root/'review.json',reviews)
    save(root/'budget-ledger.json',{'prior_paid_usd':prior,'ceiling_usd':10,'requests':requests})
    save(root/'exploration.json',{'prior_request_count':1})
    save(root/'native-stage-0.json',{'stage':0,'sources_verified':1,'vectors':{},'notes':[]})
    save(root/'write-rejection-audit.json',{'candidates':0,'first_gate_outcomes':{}})
    save(root/'backup/restore-receipt.json',{'source_count':1,'postgres_state_equal':True,'qdrant':[],'image_manifests':{}})
    return f

def exported(root, **kwargs):
    fixture(root,**kwargs)
    destination=root/'public'
    export(root,destination)
    result=subprocess.run([sys.executable,'-I',str(destination/'verify.py')],cwd=destination,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    return destination,json.loads((destination/'measurements.json').read_text())

def rehash(root,name):
    p=root/'manifest.json'; v=json.loads(p.read_text()); v['files'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest(); save(p,v)

def reject_modified_counts(root,data):
    for arm in data['summary']:
        data['summary'][arm]['matched_content_cells']+=1
    save(root/'measurements.json',data); rehash(root,'measurements.json')
    try: verify(root)
    except (AssertionError,ValueError): return
    raise AssertionError('Fabricated matched totals were accepted')


class PublicAccountingTests(unittest.TestCase):
    def test_opening_balance_unknown_costs_and_cell_deltas_reconcile(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for i, cost in enumerate(('absent', None, -1, '0', 0.0, 0.005)):
                destination, data = exported(base / str(i), prior=0.25, historical_cost=cost)
                ledger = json.loads((base / str(i) / 'budget-ledger.json').read_text())
                paid, exposure = totals(ledger)
                self.assertAlmostEqual(data['new_budget']['paid_usd'], paid)
                self.assertAlmostEqual(data['new_budget']['exposure_usd'], exposure)
                self.assertEqual(data['new_budget']['prior_paid_usd'], 0.25)
                expected = 0.25 + (cost if isinstance(cost, (float, int)) and cost >= 0 else 0)
                self.assertAlmostEqual(data['exploration']['paid_usd'], expected)
                self.assertAlmostEqual(data['exploration']['exposure_usd'], exposure - 0.009)
                self.assertTrue(all(abs(cell['paid_usd'] - 0.001) < 1e-8 for cell in data['cells']))
                reject_modified_counts(destination, data)
            exported(base / 'unknown-completed', prior=0.25, historical_cost=None,
                     historical_status='completed')
            _, legacy = exported(base / 'legacy')
            self.assertEqual(legacy['new_budget']['prior_paid_usd'], 0)

    def test_partial_pairs_and_invalid_answers_keep_their_correct_denominators(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for i, options in enumerate(({}, {'formal_arms': ARMS[:2]},
                    {'formal_arms': [], 'calibration_limit': 2},
                    {'failed_arm': 'source_only'}, {'invalid_arm': 'source_only'})):
                destination, data = exported(base / str(i), **options)
                self.assertEqual({s['planned'] for s in data['summary'].values()}, {1})
                matched = 0 if ('formal_arms' in options or 'failed_arm' in options) else 1
                self.assertTrue(all(s['matched_content_cells'] == matched for s in data['summary'].values()))
                if 'invalid_arm' in options:
                    self.assertEqual(data['summary']['source_only']['matched_criteria'], 1)
                    self.assertEqual(data['summary']['source_only']['matched_accepted'], 0)
                if options.get('formal_arms') == ARMS[:2]:
                    altered = json.loads(json.dumps(data))
                    altered['summary']['full_elf']['planned'] = 0
                    save(destination / 'measurements.json', altered)
                    rehash(destination, 'measurements.json')
                    with self.assertRaises(AssertionError):
                        verify(destination)
                reject_modified_counts(destination, data)

    def test_standalone_cost_validation_matches_the_gateway(self):
        from benchmark_budget import explicit_cost as gateway_cost
        for cost in (None, -1, math.nan, math.inf, '0', 0, 0.2):
            row = {'usage': {'cost': cost}}
            self.assertEqual(explicit_cost(row), gateway_cost(row))
