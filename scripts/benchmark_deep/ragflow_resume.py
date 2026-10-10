"""Continue an unchanged PDF workload in its retained native dataset."""
import hashlib
import json
from pathlib import Path
import shutil


def prepare_ragflow_resume(original, root, inputs, oracle, providers, digest):
    original = Path(original)
    old = json.loads((original / 'bundle.json').read_text())
    if old['target']['id'] != 'ragflow' or old['providers'] != providers or old['image_digest'] != digest:
        raise ValueError('RAGFlow continuation requires the same target, providers, and client image')
    if json.loads((original / 'input/workload.json').read_text()) != inputs or json.loads((original / 'oracle.json').read_text()) != oracle:
        raise ValueError('RAGFlow continuation requires the unchanged workload and oracle')
    scope = inputs['actions'][0]['scope']
    if sum(a['action'] == 'ingest' for a in inputs['actions']) != 1:
        raise ValueError('RAGFlow continuation supports one retained dataset')
    source = original / 'artifacts/deep-state' / f'ragflow-{scope}.json'
    state = json.loads(source.read_text())
    if set(state['documents']) != {i['evidence_id'] for i in inputs['actions'][0]['items']}:
        raise ValueError('RAGFlow continuation requires all original source identities')
    dest = root / 'artifacts/deep-state'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest / source.name)
    continuation = {'kind': 'ragflow_retained_ingestion', 'scope': scope,
                    'original_bundle_sha256': hashlib.sha256((original / 'bundle.json').read_bytes()).hexdigest(),
                    'original_duration_seconds': old['duration_seconds'],
                    'boundary': 'Wait for retained native parsing, then rerun every question. Not a fresh ingestion or selective wrong-answer retry.'}
    (dest / 'ragflow-resume.json').write_text(json.dumps(continuation))
    return continuation
