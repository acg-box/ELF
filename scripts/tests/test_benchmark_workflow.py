"""Verify workflow isolation, fresh-session inputs, and stopping without paid calls."""
import json
import io
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import Mock, patch

from scripts.tests.benchmark_support import REPO
from benchmark_pilot.corpus import digest, save
from benchmark_pilot.workflow import conversation, source_record, workflow_schemas
from benchmark_pilot.workspace import bounded_shell_result, frozen_files
from benchmark_pilot.runtime import Runtime
from benchmark_pilot.runner import ingest


class WorkflowTests(unittest.TestCase):
    def test_shell_output_bound_counts_json_escaping_and_complete_unicode(self):
        raw = ('quoted "line" \\ newline\n中文\n' * 1000).encode()
        for cap in (100, 1000, 12000):
            value = bounded_shell_result(0, raw, len(raw), 1.5, cap)
            self.assertLessEqual(len(json.dumps(value, ensure_ascii=False).encode()), cap)
            self.assertTrue(raw.decode().startswith(value['output']))
            self.assertTrue(value['truncated'])
        complete = bounded_shell_result(0, b'line', 4, 0.1, 200)
        self.assertEqual(complete['output'], 'line')
        self.assertFalse(complete['truncated'])

    def test_exhausted_output_budget_does_not_disable_file_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root / 'budget-ledger.json', {'requests': []})
            workspace = Mock()
            workspace.snapshot.return_value = ['HANDOFF.md']
            workspace.shell.return_value = {'exit_code': 0, 'output': '', 'truncated': True}
            def response(messages, condition, closing, protocol, required, tools):
                name, arguments = ('finish_work', {'summary': 'saved'}) if required else ('shell', {'command': 'write handoff'})
                return {}, {'choices': [{'message': {'role': 'assistant', 'tool_calls': [{
                    'id': name, 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}}]}
            protocol = {'condition': 'no_elf', 'max_evidence_bytes': 0,
                        'max_tool_result_bytes': 12000, 'max_rounds': 2, 'max_tool_calls': 4}
            with patch('benchmark_pilot.workflow.request', side_effect=response):
                result = conversation(root, REPO, workspace, None, [], {}, protocol, 'Save handoff', 0)
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['evidence_bytes'], 0)
            self.assertGreater(result['output_omitted_control_bytes'], 0)
            workspace.shell.assert_called_once()
            self.assertEqual(workspace.shell.call_args.args[-1], 0)

    def test_runtime_owner_is_identical_in_memory_and_persistent_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = Runtime(root, REPO, owner='elf-workflow-unit')
            self.assertEqual(runtime.owner, 'elf-workflow-unit')
            self.assertEqual(json.loads((root / 'runtime.json').read_text())['owner'], runtime.owner)
            self.assertEqual(Runtime(root, REPO).owner, runtime.owner)

    def test_baselines_have_full_file_execution_and_no_memory_tools(self):
        names = {arm: {t['function']['name'] for t in workflow_schemas(arm)}
                 for arm in ('no_elf', 'source_only', 'full_elf')}
        self.assertEqual(names['no_elf'], {'shell', 'finish_work'})
        self.assertTrue(names['no_elf'] <= names['source_only'] <= names['full_elf'])
        self.assertNotIn('elf_searches_create', names['source_only'])
        self.assertIn('elf_docs_search_l0', names['source_only'])
        self.assertIn('elf_evidence_pack', names['full_elf'])

    def test_fixture_tampering_stops_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'future.txt'
            p.write_text('future requirement')
            save(root / 'freeze.json', {'files': {p.name: digest(p.read_bytes())}})
            frozen_files(root)
            p.write_text('changed after freeze')
            with self.assertRaises(ValueError):
                frozen_files(root)

    def test_new_session_does_not_receive_prior_messages_or_hidden_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root / 'budget-ledger.json', {'requests': []})
            save(root / 'session-0/trace.json', [{'private': 'PRIOR_TRANSCRIPT_CANARY'}])
            workspace = Mock()
            workspace.snapshot.return_value = ['HANDOFF.md']
            protocol = {'condition': 'no_elf', 'max_evidence_bytes': 4096,
                        'max_tool_result_bytes': 2048, 'max_rounds': 2, 'max_tool_calls': 4}
            def response(messages, *args):
                serialized = json.dumps(messages)
                self.assertNotIn('PRIOR_TRANSCRIPT_CANARY', serialized)
                self.assertIn('CURRENT_REQUEST', serialized)
                return {}, {'choices': [{'finish_reason': 'tool_calls', 'message': {
                    'role': 'assistant', 'tool_calls': [{'id': 'finish', 'function': {
                        'name': 'finish_work', 'arguments': '{"summary":"partial work"}'}}]}}]}
            with patch('benchmark_pilot.workflow.request', side_effect=response):
                result = conversation(root, REPO, workspace, None, [], {}, protocol, 'CURRENT_REQUEST', 1)
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['scripted_requirement_updates'], 1)
            self.assertIsNone(result['observed_human_corrections'])
            with self.assertRaises(FileExistsError):
                conversation(root, REPO, workspace, None, [], {}, protocol, 'CURRENT_REQUEST', 1)

    def test_record_identity_preserves_versions_and_original_utf8(self):
        before = source_record('HANDOFF.md', '主体与条件', 0, 'revision', 'time', True)
        after = source_record('HANDOFF.md', '条件已更新', 1, 'revision', 'time', True)
        self.assertNotEqual(before['id'], after['id'])
        self.assertEqual(before['sha256'], digest('主体与条件'.encode()))
        self.assertEqual(before['text'], '主体与条件')
        self.assertEqual(before['kind'], 'work_record')
        self.assertEqual(source_record('source.py', 'code', 0, 'revision', 'time')['kind'], 'blob')

    def test_work_records_use_chat_provenance_instead_of_a_fictitious_git_blob(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = Mock()
            runtime.api.return_value = {'doc_id': 'doc', 'content_hash': 'hash'}
            source = source_record('HANDOFF.md', 'A previous agent plan.', 1, 'base',
                                   '2026-10-15T00:00:00Z', True)
            source['canonical_uri'] = 'elf-workflow://case/1/HANDOFF.md?sha256=' + source['sha256']
            with patch('benchmark_pilot.runner.usage', return_value={}), \
                    patch('benchmark_pilot.runner.verify_state'):
                ingest(runtime, root, [source], 1, {'conditions': ['source_only']})
            body = runtime.api.call_args.args[1]
            reference = body['source_ref']
            self.assertEqual((reference['doc_type'], reference['source_kind']), ('chat', 'chat_excerpt'))
            self.assertEqual((reference['thread_id'], reference['role']), ('case', 'assistant'))
            self.assertEqual(reference['trust_label'], 'unverified')
            self.assertNotIn('commit_sha', reference)
            self.assertNotIn('repo', reference)
            self.assertEqual(body['content'], source['text'])

    def test_expected_policy_rejection_keeps_original_bytes_and_records_incomplete_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = source_record('code.py', 'token = secrets.token_hex(24)', 0, 'base', 'time')
            runtime = Mock()
            runtime.api.side_effect = urllib.error.HTTPError('http://local', 400, 'rejected', {},
                io.BytesIO(b'{"message":"content contains secrets."}'))
            with patch('benchmark_pilot.runner.usage', return_value={}), \
                    patch('benchmark_pilot.runner.verify_state') as verify:
                ingest(runtime, root, [source], 0, {'conditions': ['source_only'],
                                                  'record_source_policy_rejections': True})
            receipt = json.loads(next((root / 'ingest').glob('*-source-rejected.json')).read_text())
            self.assertEqual(receipt['sha256'], digest(source['text'].encode()))
            self.assertEqual(verify.call_args.args[2], [])
            self.assertEqual(source['text'], 'token = secrets.token_hex(24)')
            self.assertFalse((root / 'documents.json').exists())
