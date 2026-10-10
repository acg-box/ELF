#!/usr/bin/env python3
"""Extract the frozen PDF fixture with bounded OpenRouter Mistral OCR calls."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from benchmark_budget import CHAT_MODEL, Ledger, NoRedirect, totals
from benchmark_deep.complex_documents import ROOT


def annotation_text(response):
    annotations = (response.get('choices') or [{}])[0].get('message', {}).get('annotations', [])
    if not annotations:
        annotations = response.get('error', {}).get('metadata', {}).get('file_annotations', [])
    texts, images = [], 0
    for item in annotations:
        if item.get('type') != 'file':
            continue
        for part in item['file']['content']:
            if part['type'] == 'text':
                texts.append(part['text'])
            elif part['type'] == 'image_url':
                images += 1
    if not texts or not '\n'.join(texts).strip():
        raise ValueError('OCR returned no original parsed text annotations')
    return '\n'.join(texts), images


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--ceiling', type=float, default=20)
    parser.add_argument('--tranche', type=float, default=0.5)
    parser.add_argument('--fixture-root', type=Path, default=ROOT)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    documents = json.loads((args.fixture_root / 'oracle-source.json').read_text())
    limit = args.limit if args.limit is not None else len(documents)
    if not 1 <= limit <= len(documents) or not 0 < args.tranche <= args.ceiling:
        parser.error('Use a valid document limit and positive bounded limits')
    key = os.environ['OPENROUTER_API_KEY']
    root = args.artifact_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = args.ledger.with_suffix('.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        ledger = Ledger(args.ledger, args.ceiling, args.tranche)
        for doc in documents[:limit]:
            identity = doc['evidence_id']
            receipt = root / (identity + '.json')
            text_path = root / (identity + '.txt')
            raw = (args.fixture_root / doc['file']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != doc['sha256']:
                raise ValueError('Frozen PDF digest mismatch')
            pages = doc.get('pages', 2 if doc['kind'] == 'crosspage' else 1)
            if not isinstance(pages, int) or not 1 <= pages <= 100:
                raise ValueError('Fixture must declare a bounded positive page count')
            if receipt.exists():
                saved = json.loads(receipt.read_text())
                if saved['source_sha256'] != doc['sha256'] or saved['pages'] != pages:
                    raise ValueError('Existing OCR receipt belongs to a different source')
                result = saved['response']
                if text_path.exists():
                    if text_path.read_text() != annotation_text(result)[0]:
                        raise ValueError('Saved OCR text differs from original annotations')
                    continue
            else:
                body = {'model': CHAT_MODEL, 'max_tokens': 16, 'stream': False,
                        'reasoning': {'effort': 'low'},
                        'provider': {'only': ['deepseek'], 'allow_fallbacks': False,
                                     'max_price': {'prompt': 0.3, 'completion': 1.2}},
                        'plugins': [{'id': 'file-parser', 'pdf': {'engine': 'mistral-ocr'}}],
                        'messages': [{'role': 'user', 'content': [
                            {'type': 'text', 'text': 'Acknowledge receipt only. Do not summarize or rewrite the document.'},
                            {'type': 'file', 'file': {'filename': identity + '.pdf',
                             'file_data': 'data:application/pdf;base64,' + base64.b64encode(raw).decode()}}]}]}
                # Reserve $0.02/page for OCR plus 32,768 input tokens/page and chat overhead.
                # OCR fees are not proven included in usage.cost: retain this reserve even on success.
                reserve = pages * (0.02 + 32768 * 0.3 / 1_000_000) + 0.003
                row = ledger.reserve(reserve, 'document_ocr')
                if row is None:
                    raise RuntimeError('Local OCR budget exhausted')
                request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                    data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key,
                                                            'Content-Type': 'application/json'})
                start = time.monotonic()
                try:
                    with opener.open(request, timeout=180) as response:
                        result = json.load(response)
                except urllib.error.HTTPError as error:
                    try:
                        result = json.load(error)
                    except ValueError:
                        result = {'error': {'message': 'unreadable upstream error'}}
                    ledger.finish(row, status='provider_failed', http_status=error.code,
                                  seconds=time.monotonic()-start)
                    receipt.write_text(json.dumps({'source_sha256': doc['sha256'], 'pages': pages,
                                                  'response': result}, indent=2).replace(key, '[redacted]')+'\n')
                    raise RuntimeError('OCR HTTP failure: ' + str(error.code)) from None
                except Exception:
                    ledger.finish(row, status='uncertain', seconds=time.monotonic()-start)
                    raise
                ledger.finish(row, status='completed_cost_unknown', usage=result.get('usage', {}),
                              model=result.get('model'), provider=result.get('provider'),
                              generation_id=result.get('id'), pages=pages, engine='mistral-ocr',
                              billing_boundary='usage.cost retained; per-page OCR fee inclusion unverified; full reserve retained',
                              seconds=time.monotonic()-start)
                receipt.write_text(json.dumps({'source_sha256': doc['sha256'], 'pages': pages,
                                              'response': result}, indent=2)+'\n')
            text, images = annotation_text(result)
            text_path.write_text(text)
            print(json.dumps({'document': identity, 'parsed_characters': len(text),
                              'image_parts_not_ingested': images, 'usage': result.get('usage'),
                              'cumulative_paid_and_exposure': totals(ledger.value)}), flush=True)
    finally:
        lock.unlink()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
