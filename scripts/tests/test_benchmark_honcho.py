"""Deletion readback must reach the native API and must not hide other errors."""

from unittest import TestCase
from unittest.mock import Mock

from scripts.tests.benchmark_support import load_script

HONCHO = load_script("benchmark_honcho", "scripts/benchmark_targets/honcho.py")


class HonchoReadbackTests(TestCase):
    def test_deleted_scope_requires_native_not_found(self):
        session = Mock()
        error = RuntimeError("not found")
        error.status_code = 404
        session.search.side_effect = error
        ids, contexts, native, _ = HONCHO._search(session, "query", {}, deleted_scope=True)
        session.search.assert_called_once_with(query="query", limit=5)
        self.assertEqual((ids, contexts), ([], []))
        self.assertEqual(native, [{"deleted_scope_search_http_status": 404}])
        error.status_code = 503
        with self.assertRaises(HONCHO.HonchoProductFailure):
            HONCHO._search(session, "query", {}, deleted_scope=True)


    def test_unmapped_native_context_is_not_hidden(self):
        from types import SimpleNamespace
        message = SimpleNamespace(id="foreign", content="foreign canary", peer_id="p",
            session_id="s", workspace_id="w", metadata={}, created_at=None, token_count=2)
        session = Mock(); session.search.return_value = [message]
        ids, contexts, native, _ = HONCHO._search(session, "query", {})
        self.assertEqual(ids, [])
        self.assertEqual(contexts, [{"evidence_id": None, "text": "foreign canary"}])
        self.assertEqual(native[0]["id"], "foreign")
