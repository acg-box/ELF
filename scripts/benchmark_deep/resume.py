"""Copy a failed SAG scale condition and retain explicit continuation provenance."""

import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def completed_prefix(action, receipts):
    if not receipts or len(receipts) >= len(action['items']):
        raise ValueError('Continuation requires a nonempty incomplete prefix')
    for item, receipt in zip(action['items'], receipts):
        for phase in ('chunks', 'events'):
            result = receipt[phase]
            if (result['source_id'] != item['evidence_id']
                    or result['data_source_id'] != action['scope']
                    or result['relation_status'] != 'succeeded'
                    or result['vector_status'] != 'succeeded'
                    or result.get('failed_items')):
                raise ValueError('Retained SAG receipt does not prove the completed prefix')
    return len(receipts)


def prepare_sag_resume(previous, root, inputs, oracle, providers, image_digest):
    previous = Path(previous)
    bundle = json.loads((previous / 'bundle.json').read_text())
    if (bundle['target']['id'] != 'sag-engine'
            or bundle['workload_group'] != 'scale-1000'
            or bundle['providers'] != providers
            or bundle['image_digest'] != image_digest
            or not bundle['cleanup']['passed']
            or bundle['coverage']['native_completed'] != 0):
        raise ValueError('Continuation requires a cleaned failed SAG scale-1000 condition with unchanged providers and image')
    if (json.loads((previous / 'input/workload.json').read_text()) != inputs
            or json.loads((previous / 'oracle.json').read_text()) != oracle):
        raise ValueError('Continuation must preserve the complete workload and oracle')
    actions = inputs['actions']
    if actions[0]['action'] != 'ingest' or any(a['action'] != 'query' for a in actions[1:]):
        raise ValueError('Continuation only supports one ingest followed by all queries')
    state = previous / 'artifacts/deep-state'
    receipt_path = state / (actions[0]['scope'] + '-sag-progress.json')
    receipts = json.loads(receipt_path.read_text())
    count = completed_prefix(actions[0], receipts)
    destination = root / 'artifacts/deep-state'
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(state / 'sag-shared', destination / 'sag-shared')
    shutil.copy2(receipt_path, destination / receipt_path.name)
    hashes = {str(p.relative_to(state)): digest(p) for p in sorted((state / 'sag-shared').rglob('*')) if p.is_file()}
    for name, expected in hashes.items():
        if digest(destination / name) != expected:
            raise ValueError('Copied SAG state differs from the retained state')
    state_manifest = root / 'retained-state-files.json'
    state_manifest.write_text(json.dumps(hashes, sort_keys=True, indent=2) + '\n')
    provenance = {
        'mode': 'retained_state_continuation',
        'original_bundle_sha256': digest(previous / 'bundle.json'),
        'original_source': bundle['source'],
        'original_duration_seconds': bundle['duration_seconds'],
        'completed_source_records': count,
        'remaining_source_records': len(actions[0]['items']) - count,
        'scope': actions[0]['scope'],
        'receipt_sha256': digest(receipt_path),
        'state_file_count': len(hashes),
        'state_manifest_sha256': digest(state_manifest),
        'boundary': 'Resume native replace_current at the first incomplete source, then run every query. Continuation duration is not fresh-run latency; retain original attempt cost and duration.'}
    (destination / 'sag-resume.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return provenance


def retained_receipts(action, root):
    marker = root / 'sag-resume.json'
    if not marker.exists():
        return []
    provenance = json.loads(marker.read_text())
    if action['scope'] != provenance['scope']:
        raise ValueError('SAG continuation scope changed')
    path = root / (action['scope'] + '-sag-progress.json')
    if digest(path) != provenance['receipt_sha256']:
        raise ValueError('SAG continuation receipts changed before execution')
    receipts = json.loads(path.read_text())
    if completed_prefix(action, receipts) != provenance['completed_source_records']:
        raise ValueError('SAG continuation prefix changed')
    return receipts
