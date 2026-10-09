"""Prepare a separate native Hindsight continuation from a retained checkpoint."""
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_hindsight_resume(descriptor, root, inputs, oracle, providers, image_digest, scripts):
    state = json.loads(Path(descriptor).read_text())
    previous = Path(state['original_artifact_root'])
    bundle_path = previous / 'bundle.json'
    bundle = json.loads(bundle_path.read_text())
    if (bundle['target']['id'] != 'hindsight' or bundle['workload_group'] != 'scale-1000'
            or bundle['providers'] != providers or bundle['image_digest'] != image_digest
            or not bundle['cleanup']['passed'] or bundle['coverage']['native_completed'] != 0):
        raise ValueError('Continuation requires a cleaned failed Hindsight scale condition with unchanged providers and client image')
    if digest(bundle_path) != state['original_bundle_sha256']:
        raise ValueError('Retained Hindsight bundle changed')
    if (json.loads((previous / 'input/workload.json').read_text()) != inputs
            or json.loads((previous / 'oracle.json').read_text()) != oracle):
        raise ValueError('Continuation must preserve the entire workload and oracle')
    actions = inputs['actions']
    if (actions[0]['action'] != 'ingest' or actions[0]['scope'] != 'scale-1000'
            or len(actions[0]['items']) != 1000 or any(a['action'] != 'query' for a in actions[1:])):
        raise ValueError('Continuation supports the frozen scale-1000 ingest and all queries only')
    receipts = json.loads((previous / 'artifacts/deep-state/scale-1000-ingest-progress.json').read_text())
    if len(receipts) != 50 or any(row.get('success') is not True for row in receipts):
        raise ValueError('All original source batches must have completed before continuation')
    archive = Path(state['archive'])
    if digest(archive) != state['archive_sha256']:
        raise ValueError('Native checkpoint changed')
    runtime, cache = Path(state['postgres_runtime']), Path(state['reranker_cache'])
    if not (runtime / 'bin/postgres').is_file() or not cache.is_dir():
        raise ValueError('Retained native runtime and reranker cache are required; do not download replacements')
    native = root / 'native-state'
    native.mkdir()
    copied = native / 'checkpoint.dump'
    shutil.copy2(archive, copied)
    if digest(copied) != state['archive_sha256']:
        raise ValueError('Copied checkpoint differs from the original')
    provenance = {'mode': 'retained_state_continuation', 'target': 'hindsight',
        'original_bundle_sha256': digest(bundle_path), 'original_source': bundle['source'],
        'original_duration_seconds': bundle['duration_seconds'], 'checkpoint_sha256': digest(copied),
        'retained_source_records': 1000, 'scope': 'scale-1000',
        'boundary': 'Restore native database and worker identity, finish pending consolidation, then execute every query. No source reingestion. Preserve original cost and elapsed time; this is not fresh-run latency.'}
    marker = root / 'artifacts/deep-state/hindsight-resume.json'
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps(provenance, indent=2) + '\n')
    override = root / 'resume-compose.json'
    override.write_text(json.dumps({'services': {'hindsight': {
        'command': ['python3', '/restore-start.py'],
        'volumes': [f'{copied}:/restore/checkpoint.dump:ro',
                    f'{runtime}:/restore/postgres-runtime:ro',
                    f'{cache}:/home/hindsight/.cache/huggingface/hub:ro',
                    f'{scripts / "benchmark_deep/restore_hindsight.py"}:/restore-start.py:ro']}}}, indent=2) + '\n')
    return provenance, override
