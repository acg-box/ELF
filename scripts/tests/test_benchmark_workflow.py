"""Verify workflow isolation, fresh-session inputs, and stopping without paid calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.tests.benchmark_support import REPO
from benchmark_pilot.corpus import digest, save
from benchmark_pilot.workflow import conversation, source_record, workflow_schemas
from benchmark_pilot.workspace import frozen_files
from benchmark_pilot.runtime import Runtime


class WorkflowTests(unittest.TestCase):
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
