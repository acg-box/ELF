"""Diagnose frozen graph reachability; never supply diagnostic paths to the reader."""
import json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / '2026-10-12-grounded-evidence'

def read(name):
    return json.loads((BASE / name).read_text())


def path_to(adj, start, target, max_hops):
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        if len(path) == max_hops:
            continue
        for other, label in sorted(adj[node]):
            if other not in seen:
                seen.add(other)
                queue.append((other, path + [label]))
    return None


def diagnose():
    entities = {e['entity_id']: e for e in read('graph_entities.json')}
    facts = read('graph_facts.json')
    notes = {n['note_id']: n for n in read('native-notes.json')}
    evidence = defaultdict(list)
    for link in read('graph_fact_evidence.json'):
        evidence[link['fact_id']].append(link['note_id'])
    graphs = {key: defaultdict(list) for key in ('directed', 'undirected', 'source_incidence')}
    for fact in facts:
        subject, obj, fid = fact['subject_entity_id'], fact['object_entity_id'], fact['fact_id']
        if obj:
            graphs['directed'][subject].append((obj, fid))
            graphs['undirected'][subject].append((obj, fid))
            graphs['undirected'][obj].append((subject, fid))
        for note_id in evidence[fid]:
            for pointer in notes[note_id]['source_ref'].get('evidence', []):
                doc = pointer['source'].get('document', {}).get('ref', {}).get('doc_id')
                if not doc:
                    continue
                for node in (subject, obj):
                    if node:
                        graphs['source_incidence'][node].append(('source:' + doc, doc))
                        graphs['source_incidence']['source:' + doc].append((node, doc))
    rows = []
    for group, name in enumerate(['Larch', 'Cobalt', 'Reed', 'Sable', 'Cedar', 'ACCT-N', 'ACCT-S', 'EGRET-CN', 'DELTA-8']):
        names = [name] + (['白鹭项目'] if group == 7 else [])
        starts = [key for key, e in entities.items() if any(n.casefold() in e['canonical'].casefold() for n in names)]
        targets = [key for key, e in entities.items() if e['canonical'] == f'REPLAY-{group}-632']
        findings = {}
        for mode, adj in graphs.items():
            paths = [{'start': a, 'target': b, 'path': p} for a in starts for b in targets
                     if (p := path_to(adj, a, b, 3 if mode != 'source_incidence' else 4)) is not None]
            findings[mode] = paths
        rows.append({'group': group, 'project': name, 'start_entities': [entities[x]['canonical'] for x in starts], **findings})
    return {
        'facts': len(facts),
        'entity_objects': sum(f['object_entity_id'] is not None for f in facts),
        'scalar_objects': sum(f['object_entity_id'] is None for f in facts),
        'unknown_valid_from': sum(f['valid_from'] is None for f in facts),
        'known_valid_to': sum(f['valid_to'] is not None for f in facts),
        'distinct_predicates': len({f['predicate'] for f in facts}),
        'canonical_fragments': {label: [e['canonical'] for e in entities.values() if label in e['canonical']] for label in ['ACCT-N', 'ACCT-S', 'EGRET-CN', 'DELTA-8']},
        'groups': rows,
        'boundary': 'Read-only structural diagnosis. Source incidence means shared provenance, not identity, causality, temporal validity, or a permissible new semantic edge. No diagnostic path is passed to the model. Name candidates are tried separately, never merged.',
    }


if __name__ == '__main__':
    result = diagnose()
    expected = ROOT / 'graph-diagnostics.json'
    if expected.exists():
        assert result == json.loads(expected.read_text())
    else:
        expected.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({**{k: result[k] for k in ('facts', 'entity_objects', 'scalar_objects', 'unknown_valid_from')},
                      'reachable_groups': {mode: sum(bool(row[mode]) for row in result['groups']) for mode in ('directed', 'undirected', 'source_incidence')}}))
