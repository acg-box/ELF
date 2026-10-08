"""Protect scope separation, reuse, and the evaluator/product boundary."""

import json
import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_deep.fixtures import workload


class DeepContractTests(unittest.TestCase):
    def test_mem0_deep_query_uses_native_filter_and_result_limit(self):
        from benchmark_deep.drivers import mem0_action
        from types import SimpleNamespace
        from unittest.mock import Mock

        class NativeMemory:
            def search(self, query, *, filters, top_k):
                self_request.assertEqual(query, "Find the approved value")
                self_request.assertEqual(top_k, 5)
                return {"results": [{"memory": filters["user_id"],
                    "metadata": {"evidence_id": "source"}}]}

        self_request = self
        memory_class = SimpleNamespace(from_config=Mock(return_value=NativeMemory()))
        with patch.dict(sys.modules, {"mem0": SimpleNamespace(Memory=memory_class)}), \
                patch("benchmark_targets.mem0.mem0_config", return_value={}), \
                patch("benchmark_targets.unit_runtime.wait_port"):
            for scope in ("scope-a", "scope-b"):
                result = mem0_action({"action": "query", "scope": scope,
                    "question": "Find the approved value"}, Path("/unused"))
                self.assertEqual(result["contexts"], [{"evidence_id": "source", "text": scope}])

    def test_hindsight_readiness_uses_the_deep_action_budget(self):
        from benchmark_deep.drivers import hindsight_action, INGEST_TIMEOUT_SECONDS, ACTION_TIMEOUT_SECONDS

        with patch("benchmark_targets.hindsight.ready"), \
                patch("benchmark_targets.hindsight.request", return_value={"success": True}), \
                patch("benchmark_targets.hindsight.drain", return_value={}) as drain:
            hindsight_action({"scope": "scale-100", "action": "ingest", "items": []}, Path("/unused"))
            self.assertEqual(drain.call_args.kwargs["timeout_seconds"], INGEST_TIMEOUT_SECONDS)
            hindsight_action({"scope": "mutations", "action": "delete", "evidence_id": "example"}, Path("/unused"))
            self.assertEqual(drain.call_args.kwargs["timeout_seconds"], ACTION_TIMEOUT_SECONDS)

    def test_hindsight_long_readiness_can_complete_after_default_deadline(self):
        from benchmark_targets.hindsight import drain

        busy = {"operations": [{"status": "pending"}]}
        quiet = {"operations": []}
        with patch("benchmark_targets.hindsight.request", side_effect=[busy, quiet, quiet, quiet] + [quiet] * 4), \
                patch("benchmark_targets.hindsight.time.monotonic", side_effect=[0, 181]), \
                patch("benchmark_targets.hindsight.time.sleep"):
            result = drain("/bank", timeout_seconds=5400)
            self.assertTrue(all(not value["operations"] for value in result.values()))
        with patch("benchmark_targets.hindsight.request", side_effect=[busy, quiet, quiet, quiet]), \
                patch("benchmark_targets.hindsight.time.monotonic", side_effect=[0, 181]):
            with self.assertRaises(TimeoutError):
                drain("/bank")

    def test_gbrain_import_uses_deep_ingestion_budget(self):
        from benchmark_deep.drivers import gbrain_action, INGEST_TIMEOUT_SECONDS

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "gbrain-ready").write_text("initialized")
            with patch("benchmark_targets.gbrain.invoke", return_value=({}, 1)) as invoke, \
                    patch("benchmark_deep.drivers.subprocess.run"):
                gbrain_action({"scope": "scale-100", "action": "ingest", "items": []}, root)
            imports = [call for call in invoke.call_args_list if call.args[1][0] == "import"]
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0].kwargs["timeout"], INGEST_TIMEOUT_SECONDS)

    def test_gbrain_update_refresh_uses_embed_source_flag(self):
        from benchmark_deep.drivers import gbrain_action

        def native(home, args):
            if args[0] == "embed":
                self.assertNotIn("--source-id", args)
                self.assertEqual(args[args.index("--source") + 1], "mutations")
                return {"embedded": 1}, 1
            return {"revision": "r1"}, 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "gbrain-ready").write_text("initialized")
            with patch("benchmark_targets.gbrain.invoke", side_effect=native):
                result = gbrain_action({"scope": "mutations", "action": "update",
                    "evidence_id": "source", "text": "corrected"}, root)
            self.assertEqual(result["refresh"], {"embedded": 1})
            self.assertEqual(result["readback"]["revision"], "r1")

    def test_gbrain_cli_preserves_default_and_explicit_deadlines(self):
        from benchmark_targets.gbrain import invoke
        import subprocess

        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "offline-test", "EMBEDDING_API_BASE": "http://offline.invalid"}), \
                patch("benchmark_targets.gbrain.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, "{}", "")) as run:
            invoke(Path("/unused"), ["search", "example"])
            self.assertEqual(run.call_args.kwargs["timeout"], 180)
            invoke(Path("/unused"), ["import", "/unused"], timeout=5400)
            self.assertEqual(run.call_args.kwargs["timeout"], 5400)

    def test_elf_native_process_uses_image_config_working_directory(self):
        from benchmark_deep.drivers import rust_action
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def native(args, **kwargs):
                self.assertEqual(kwargs["cwd"], "/")
                self.assertEqual(args[args.index("--config") + 1], "/opt/elf/elf.docker.toml")
                Path(args[args.index("--evidence-out") + 1]).write_text(
                    json.dumps({"jobs": [{"contexts": []}]}))
                return subprocess.CompletedProcess(args, 0)
            with patch("benchmark_deep.drivers.subprocess.run", side_effect=native):
                result = rust_action("elf", {"scope": "session", "action": "ingest",
                    "items": [], "operation_id": "operation-000"}, root)
            self.assertEqual(result["process_exit"], 0)

    def test_fixed_groups_preserve_every_case_and_native_dependency(self):
        inputs, oracle = workload()
        combined = {}
        for group in ('scale-100', 'scale-1000', 'session', 'conflicts', 'isolation', 'mutations'):
            selected, expected = workload(group)
            self.assertFalse(combined.keys() & expected.keys())
            combined.update(expected)
            scopes = {a['scope'] for a in selected['actions']}
            self.assertEqual(selected['actions'], [a for a in inputs['actions'] if a['scope'] in scopes])
            if group == 'isolation':
                self.assertEqual(scopes, {'scope-a', 'scope-b'})
                self.assertEqual([a['action'] for a in selected['actions'][:2]], ['ingest', 'ingest'])
        self.assertEqual(combined, oracle)
        behavior, expected = workload('behavior')
        self.assertEqual(len(expected), 42)
        self.assertFalse(any(a['scope'].startswith('scale-') for a in behavior['actions']))
        with self.assertRaises(ValueError):
            workload('scope-a')

    def test_scale_ingests_once_per_size_and_has_absent_controls(self):
        inputs, oracle = workload()
        self.assertEqual(len(oracle), 62)
        for size in (100, 1000):
            actions = [a for a in inputs["actions"] if a["scope"] == f"scale-{size}"]
            self.assertEqual([a["action"] for a in actions], ["ingest"] + ["query"] * 10)
            self.assertEqual(len(actions[0]["items"]), size)
            self.assertEqual(sum(not oracle[a["case_id"]]["supported"] for a in actions[1:]), 2)
        self.assertEqual(workload(), (inputs, oracle))

    def test_both_scopes_are_populated_before_canary_reads(self):
        inputs, oracle = workload()
        actions = [a for a in inputs["actions"] if a["scope"].startswith("scope-")]
        self.assertEqual([a["action"] for a in actions[:2]], ["ingest", "ingest"])
        self.assertEqual({a["scope"] for a in actions[:2]}, {"scope-a", "scope-b"})
        for action in actions[2:]:
            expected = oracle[action["case_id"]]
            foreign = "scope-b" if action["scope"] == "scope-a" else "scope-a"
            self.assertEqual(len(expected["forbidden"]), 6)
            self.assertTrue(all(foreign in word for word in expected["forbidden"]))

    def test_oracle_keys_never_enter_product_input(self):
        inputs, oracle = workload()
        forbidden = {"facts", "evidence", "forbidden", "supported", "expected_answer"}

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(inputs)
        self.assertTrue(oracle)

    def test_mutations_precede_restart_queries_without_reingestion(self):
        inputs, _ = workload()
        actions = [a["action"] for a in inputs["actions"] if a["scope"] == "mutations"]
        self.assertEqual(actions, ["ingest"] + ["update"] * 6 + ["query"] * 6 + ["delete"] * 6 + ["query"] * 6)

class DeepGroundingTests(unittest.TestCase):
    def test_correct_value_without_case_context_is_not_a_supported_answer(self):
        from benchmark_deep.scoring import score_answer
        expected={'supported':True,'facts':['current-2-green']}
        answer={'supported':True,'text':'current-2-green'}
        scored=score_answer(expected,answer,'Dune-2 used retired-2-blue.')
        self.assertTrue(scored['answer_matches_expected'])
        self.assertFalse(scored['fact_in_supplied_context'])
        self.assertFalse(scored['correct'])
        self.assertTrue(score_answer(expected,answer,'The approved route is current-2-green.')['correct'])


class DeepProcessTests(unittest.TestCase):
    def test_action_timeout_stops_native_descendant_and_retains_failure(self):
        source = Path(__file__).resolve().parents[1] / 'benchmark-deep-unit.py'
        spec = importlib.util.spec_from_file_location('deep_unit_timeout_test', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input').mkdir()
            (root / 'input/workload.json').write_text(json.dumps({'actions': [
                {'action': 'ingest', 'scope': 'probe', 'items': []},
                {'action': 'query', 'scope': 'probe', 'case_id': 'probe-query'},
            ]}))
            fake = root / 'native.py'
            fake.write_text('''import os, signal, subprocess, sys, time
from pathlib import Path
root = Path(__file__).parent
if '--leaf' in sys.argv:
    def stop(signum, frame):
        (root / 'stopped').write_text('terminated')
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    (root / 'child.pid').write_text(str(os.getpid()))
    print('native-started', flush=True)
    time.sleep(30)
else:
    child = subprocess.Popen([sys.executable, __file__, '--leaf'])
    def stop(signum, frame):
        child.wait(timeout=3)
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    child.wait()
''')
            try:
                with patch.object(module, '__file__', str(fake)), \
                     patch.object(module, 'INGEST_TIMEOUT_SECONDS', 1), \
                     patch.dict(os.environ, {'BENCHMARK_DEEP_ROOT': str(root)}), \
                     patch.object(sys, 'argv', [str(source), '--target', 'elf']):
                    self.assertEqual(module.main(), 1)
                self.assertEqual((root / 'stopped').read_text(), 'terminated')
                with self.assertRaises(ProcessLookupError):
                    os.kill(int((root / 'child.pid').read_text()), 0)
                result = json.loads((root / 'artifacts/deep-result.json').read_text())
                self.assertEqual([r['status'] for r in result['results']], ['failed', 'blocked_by_ingest'])
                self.assertIn('native-started', (root / 'artifacts/deep-state/operation-000.log').read_text())
            finally:
                if (root / 'child.pid').exists():
                    try:
                        os.kill(int((root / 'child.pid').read_text()), signal.SIGTERM)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
