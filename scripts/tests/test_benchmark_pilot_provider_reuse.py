"""A changed extractor must reach the budget gateway, not replay the old proposal."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_pilot.reuse import RecordedProvider


class ProviderReuseTests(unittest.TestCase):
    def test_fresh_extractor_bypasses_recorded_proposals_and_retains_embedding_cache(self):
        original = {'model': 'reader', 'messages': [{'content':
            'Return an instance matching this JSON Schema:\nold instructions\n[{"content":"same original"}]'}]}
        changed = {'model': 'reader', 'messages': [{'content':
            'Return an instance matching this JSON Schema:\nnew instructions\n[{"content":"same original"}]'}]}
        embedding = {'model': 'qwen/qwen3-embedding-8b', 'input': ['same original'], 'dimensions': 4096}
        old = {'choices': [{'message': {'content': '{"notes":[{"text":"old proposal"}]}'}}]}
        fresh = {'choices': [{'message': {'content': '{"notes":[{"text":"new proposal"}]}'}}]}
        vector = {'data': [{'embedding': [0.0] * 4096}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipts = root / 'receipts'
            receipts.mkdir()
            for index, body, response in [(1, original, old), (2, embedding, vector)]:
                (receipts / f'{index}.json').write_text(json.dumps({'request': body, 'response': response}))
            provider = RecordedProvider(root, [receipts], 'http://budget-gateway/v1', 'local', frozen_extraction=False)
            opener = urllib.request.urlopen
            forwarded = []
            def dispatch(request, **kwargs):
                if request.full_url.startswith(provider.base):
                    return opener(request, **kwargs)
                forwarded.append((request.full_url, json.loads(request.data)))
                return io.BytesIO(json.dumps(fresh).encode())
            def send(endpoint, body):
                request = urllib.request.Request(provider.base + endpoint, data=json.dumps(body).encode())
                with urllib.request.urlopen(request, timeout=5) as response:
                    return json.load(response)
            try:
                with patch('urllib.request.urlopen', side_effect=dispatch):
                    self.assertEqual(send('/chat/completions', changed), fresh)
                    self.assertEqual(send('/embeddings', embedding), vector)
            finally:
                provider.close()
            self.assertEqual(forwarded, [('http://budget-gateway/v1/chat/completions', changed)])
            audit = [json.loads(line) for line in (root / 'provider-reuse.jsonl').read_text().splitlines()]
            self.assertEqual([(row['kind'], row['reused']) for row in audit], [('extraction', False), ('embedding', True)])
