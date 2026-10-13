"""Verify real Git sources, chronology, and the recorded no-spend budget stop."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
FIXTURE = REPO / 'config/benchmark/real-project-pilot'
sys.path.insert(0, str(REPO / 'scripts'))
from benchmark_budget import reservation


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest = read(ROOT / 'manifest.json')
    assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    for name, digest in manifest.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    freeze = read(FIXTURE / 'freeze.json')
    assert sha((FIXTURE / 'workload.json').read_bytes()) == freeze['workload_sha256']
    assert sha((FIXTURE / 'sources.jsonl.gz').read_bytes()) == freeze['sources_sha256']
    work = read(FIXTURE / 'workload.json')
    sources = {row['source_id']: row for row in map(json.loads, gzip.decompress((FIXTURE / 'sources.jsonl.gz').read_bytes()).splitlines())}
    assert len(sources) == freeze['source_count'] == 7
    for source in sources.values():
        raw = subprocess.check_output(['git', 'show', source['commit'] + ':' + source['path']], cwd=REPO)
        assert raw.decode() == source['text'] and sha(raw) == source['sha256']
        blob = subprocess.check_output(['git', 'rev-parse', source['commit'] + ':' + source['path']], cwd=REPO).decode().strip()
        assert blob == source['blob']
    seen = set()
    stages = {s['checkpoint']: s for s in work['checkpoints']}
    for stage in work['checkpoints']:
        seen.update(stage['new_source_ids'])
        assert set(stage['visible_source_ids']) == seen
        for key in seen:
            subprocess.run(['git', 'merge-base', '--is-ancestor', sources[key]['commit'], stage['commit']], cwd=REPO, check=True)
    assert all(task['checkpoint'] in stages for task in work['tasks'])
    conditions = {c['id']: set(c['tools']) for c in work['conditions']}
    assert conditions['no_elf'] <= conditions['source_only'] <= conditions['full_elf']
    assert conditions['full_elf'] - conditions['source_only'] == {'memory_recall'}
    assert work['controls']['same_questions_and_source_access']
    result = read(ROOT / 'preflight.json')
    quote = read(ROOT / 'pricing.json')
    assert quote['captured_at'] == result['captured_at']
    endpoint = quote['endpoint']
    assert endpoint['provider_name'] == 'DeepSeek' and endpoint['max_completion_tokens'] == result['output_tokens']
    now = datetime.datetime.fromisoformat(result['captured_at'])
    assert now.utcoffset() == datetime.timedelta(0)
    hhmm = now.hour * 100 + now.minute
    prices = endpoint['pricing']
    active = {k: float(prices[k]) for k in ('prompt', 'completion')}
    for override in prices.get('overrides', []):
        if override.get('utc_days') and now.strftime('%A').lower() not in override['utc_days']:
            continue
        start, end = override.get('utc_start', 0), override.get('utc_end', 0)
        inside = start == end or (start <= hhmm < end if start < end else hhmm >= start or hhmm < end)
        if inside:
            active = {k: float(override[k]) for k in active}
    per_million = {k: v * 1_000_000 for k, v in active.items()}
    assert per_million == result['active_prices_usd_per_million']
    minimum = reservation(0, 'chat', result['output_tokens'], per_million['prompt'], per_million['completion'])
    assert abs(minimum - result['minimum_request_reservation_usd']) < 1e-9
    assert abs(result['opening_paid_usd'] + sum(r['reserved_usd'] for r in result['unsettled']) - result['opening_exposure_usd']) < 1e-9
    assert abs(result['remaining_usd'] - (result['ceiling_usd'] - result['opening_exposure_usd'])) < 1e-9
    assert minimum > result['remaining_usd']
    assert result['ledger_sha256_before'] == result['ledger_sha256_after']
    assert result['planned_cells'] == freeze['planned_cells'] == len(work['tasks']) * len(conditions) == 12
    assert result['executed_cells'] == result['new_provider_requests'] == result['new_paid_usd'] == 0
    assert result['scores'] is None and result['latency_measurements'] is None
    assert result['status'] == 'blocked_budget_before_execution'
    print(json.dumps({'source_integrity': 'passed', 'chronology': 'passed', 'sources': len(sources),
                      'planned_cells': result['planned_cells'], 'executed_cells': 0,
                      'experiment_status': result['status'], 'new_paid_usd': 0}))


if __name__ == '__main__':
    main()
