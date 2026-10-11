"""Artifact and reference helpers; no database or provider side effects."""
import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / 'config/benchmark/evidence/2026-10-10-elf-language-provenance'


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def cases():
    return [json.loads(line) for line in gzip.decompress((EVIDENCE / 'cases.jsonl.gz').read_bytes()).splitlines()]


def labeled(rows):
    return '\n'.join('[Source: ' + row['evidence_id'] + ']\n' + row['text'] for row in rows)
