"""Readbacks must query each native graph, including deletion checks."""
import asyncio
from types import SimpleNamespace
from scripts.tests.benchmark_support import BenchmarkCase, load_script

G = load_script('benchmark_graphiti_scope', 'scripts/benchmark_targets/graphiti.py')


class GraphitiScopeTests(BenchmarkCase):
    def test_readback_preserves_multiple_native_graphs(self):
        data = {'default': {}, 'a': {'ua': 'a'}, 'b': {'ub': 'b'}}
        class Driver:
            _init_task = None
            def __init__(self, database='default'): self.database = database
            def clone(self, database): return Driver(database)
        class Node:
            @staticmethod
            async def get_by_uuids(driver, uuids):
                return [SimpleNamespace(uuid=key, group_id=value)
                        for key,value in data[driver.database].items() if key in uuids]
        identities = {'a': {'group_id':'a','episode_identity':{'ua':'ea'}},
                      'b': {'group_id':'b','episode_identity':{'ub':'eb'}}}
        driver = Driver()
        rows = asyncio.run(G._verify_warm_state(Node,driver,identities,[]))
        self.assertEqual({r.uuid for r in rows},{'ua','ub'})
        self.assertEqual(driver.database,'default')
        identities['a']['episode_identity'] = {}
        with self.assertRaises(G.GraphitiAdapterFailure):
            asyncio.run(G._verify_warm_state(Node,driver,identities,['ua']))
        data['a'].clear()
        rows = asyncio.run(G._verify_warm_state(Node,driver,identities,['ua']))
        self.assertEqual([r.uuid for r in rows],['ub'])
