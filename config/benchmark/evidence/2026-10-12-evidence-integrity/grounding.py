"""Audit target-specific absence evidence in this frozen English memory fixture."""
import json
from pathlib import Path
import re

from benchmark_agent.analysis import citation_sources,note_evidence
from benchmark_agent.tools import project_note


def audit_absence(root):
    root=Path(root);work=json.loads((root/'workload.json').read_text());origins=citation_sources(root);rows=[]
    def negative(value):
        text=json.dumps(value,ensure_ascii=False).lower()
        return bool(re.search(r'no budget owner|budget owner.{0,80}(?:unassigned|not.{0,20}appointed)|unassigned.{0,40}budget owner',text))
    for path in sorted((root/'cases').glob('*/*-3.json')):
        case=json.loads(path.read_text());case_id=case['query']['case_id'];project=int(case_id.split('-')[1]);target={i['evidence_id'] for i in work['items'][project*4:project*4+4]};evidence=[]
        def inspect(identity,value,via):
            if origins.get(identity,set()) & target and negative(value):evidence.append({'identity':identity,'via':via,'source_ids':sorted(origins[identity] & target)})
        for note in json.loads((root/'initial'/path.name).read_text())['notes']:
            inspect(note['note_id'],note_evidence(project_note(note,'notes')),'initial')
        for step in case.get('trace',[]):
            for tool in step['tools']:
                name=tool['name'];result=tool['result']
                if 'error' in result:continue
                if name=='get_note':inspect(result['note_id'],note_evidence(result),'get_note')
                elif name in ('get_search','search_notes'):
                    for item in result['items']:inspect(item['note_id'],{'summary':item.get('summary'),'text':item.get('text')},name)
                elif name=='query_graph':
                    for fact in result.get('facts',[]):inspect(fact['fact_id'],{'subject':result.get('subject'),'predicate':fact.get('predicate'),'object':fact.get('object')},name)
                elif name=='read_document':inspect(result['metadata']['doc_id'],result['excerpt']['excerpt'],name)
                elif name=='search_documents':
                    for item in result.get('items',[]):inspect(item['doc_id'],item.get('snippet'),name)
        text=case.get('text','').lower()
        asserts=bool(re.search(r'no budget owner (?:had been|has been|was|is)|no (?:one|appointed budget owner)|role (?:remained|remains|was|is) unassigned',text))
        rows.append({'condition':case['condition'],'case_id':case_id,'target_absence_evidence_seen':bool(evidence),'evidence':evidence,'asserts_absence':asserts,'unsupported_absence_assertion':asserts and not evidence,'boundary':'This checks availability of a target-origin negative statement, not complete claim-level entailment. Other-topic negatives do not establish absence for this topic. Calibrated unknown remains distinct from asserting that nobody was appointed.'})
    return rows


def summarize_quality(analysis,reviews,issues,absence):
    bad_citations={(row['condition'],row['case_id']) for row in issues}
    bad_absence={(row['condition'],row['case_id']) for row in absence if row['unsupported_absence_assertion']}
    truth={(row['condition'],row['case_id']):row['correct'] for row in reviews}
    output=[]
    for summary in analysis['summary']:
        if summary['stage']!='primary':continue
        keys=[(row['condition'],row['case_id']) for row in analysis['cases'] if row['condition']==summary['condition'] and row['split']==summary['split'] and row['phase']=='primary']
        output.append({**summary,'cases_with_citation_defects':sum(key in bad_citations for key in keys),'unsupported_absence_assertions':sum(key in bad_absence for key in keys),'joint_diagnostic_pass':sum(truth.get(key,False) and key not in bad_citations and key not in bad_absence for key in keys)})
    return output
