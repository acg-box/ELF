"""Keep independent GraphRAG cases observable after native failures."""
from pathlib import Path
import json
import subprocess
import tempfile
from unittest import mock

from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_targets import graphrag as G


class BenchmarkGraphRAGTests(BenchmarkCase):
    def test_native_failures_preserve_other_cases_and_cold_results(self):
        jobs = [{"job_id": name, "corpus": {"items": [{"evidence_id": "e_fact", "text": "old fact"}]},
                 "operations": [{"type": "update", "evidence_id": "e_fact", "text": "new fact"}]
                 if name in {"j_mutation", "j_after"} else []}
                for name in ("j_before", "j_empty", "j_mutation", "j_after")]
        queried = []
        def index(root, raw, job):
            if job['job_id'] == 'j_empty':
                raise G.GraphRAGProductFailure('Graph Extraction failed. No entities detected during extraction.')
            return 10
        def query(root, job, raw, source_map):
            phase = 'warm' if 'warm' in raw.parts else 'cold'
            queried.append((phase, job['job_id']))
            return {"job_id": job['job_id'], "classification": "completed", "contexts": [],
                    "evidence_ids": [], "returned_count": 0, "native_status": "completed", "failure": None}, {}
        def reindex(*args, **kwargs):
            if 'j_mutation' in str(kwargs['cwd']):
                raise G.GraphRAGProductFailure('rebuild failed local-test-credential')
            return 12
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(G, '_required_environment'), mock.patch.object(G, '_verify_version'), \
                 mock.patch('benchmark_targets.graphrag_transport.install_json_transport'), \
                 mock.patch.object(G, '_load_jobs', return_value=jobs), \
                 mock.patch.object(G, '_index_job', side_effect=index), \
                 mock.patch.object(G, '_index_readiness', return_value={'output_state_sha256': 'stable', 'tables': {}}), \
                 mock.patch.object(G, '_state_sha256', return_value='stable'), \
                 mock.patch.object(G, '_query_job', side_effect=query), \
                 mock.patch.object(G, '_materialize_job'), mock.patch.object(G, '_run_cli', side_effect=reindex), \
                 mock.patch.dict(G.os.environ, {'CHAT_API_KEY': 'local-test-credential'}):
                result = G.run_graphrag(root / 'input', root / 'artifacts', root / 'state')
            cold = result['phases']['cold']['jobs']; warm = result['phases']['warm']['jobs']
            self.assertEqual([x['classification'] for x in cold], ['completed', 'product_failed', 'completed', 'completed'])
            self.assertEqual([x['classification'] for x in warm], ['completed', 'product_failed', 'product_failed', 'completed'])
            self.assertEqual(warm[1]['native_status'], 'not_run')
            self.assertEqual(warm[2]['operations'], [])
            self.assertTrue(warm[3]['operations'][0]['native_success'])
            self.assertEqual(result['result_class'], 'product_failed')
            self.assertEqual(result['phases']['warm']['adapter_metadata']['native_index_count'], 3)
            self.assertEqual(queried, [('cold', 'j_before'), ('cold', 'j_mutation'), ('cold', 'j_after'),
                                      ('warm', 'j_before'), ('warm', 'j_after')])
            failures = [json.loads(p.read_text()) for p in (root / 'artifacts').rglob('failure.json')]
            self.assertEqual(len(failures), 3)
            self.assertTrue(any('No entities detected' in x['failure'] for x in failures))
            self.assertNotIn('local-test-credential', json.dumps(failures))
            self.assertIn('[redacted]', warm[2]['failure'])
            receipt = json.loads((root / 'state/cold-index.json').read_text())
            self.assertNotIn('j_empty', receipt['indexes'])
            self.assertEqual(len(receipt['indexes']), 3)

    def test_case_failure_keeps_adapter_and_timeout_classifications(self):
        job = {'job_id': 'j_one'}
        self.assertEqual(G._failed_case(job, G.GraphRAGAdapterFailure('index changed'))['classification'], 'adapter_failed')
        self.assertEqual(G._failed_case(job, subprocess.TimeoutExpired(['native'], 5))['classification'], 'timeout_failed')
