"""Benchmark adapters regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase, REPO, load_script

from pathlib import Path
import json
from unittest import mock
import tempfile
import types

GRAPHITI = load_script("benchmark_graphiti", "scripts/benchmark_targets/graphiti.py")

GRAPHRAG = load_script("benchmark_graphrag", "scripts/benchmark_targets/graphrag.py")


OPENVIKING = load_script(
    "benchmark_openviking", "scripts/benchmark_targets/openviking.py"
)


class BenchmarkAdaptersTests(BenchmarkCase):
    def test_graphiti_preserves_the_requested_response_schema(self) -> None:
        class ResponseModel:
            @staticmethod
            def model_json_schema() -> dict:
                return {
                    "type": "object",
                    "properties": {"items": {"type": "array"}},
                    "required": ["items"],
                }

        response_format = GRAPHITI._chat_response_format(ResponseModel)
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(
            response_format["json_schema"]["schema"], ResponseModel.model_json_schema()
        )
        self.assertFalse(response_format["json_schema"]["strict"])


    def test_graphiti_rejects_schema_documents_and_preserves_stale_native_contexts(
        self,
    ) -> None:
        class ResponseModel:
            @classmethod
            def model_validate(cls, value: object) -> None:
                if value != {"items": []}:
                    raise ValueError("not an instance")

        GRAPHITI._validate_response_instance(ResponseModel, {"items": []})
        with self.assertRaisesRegex(ValueError, "not an instance"):
            GRAPHITI._validate_response_instance(
                ResponseModel, {"type": "object", "properties": {}}
            )
        self.assertIn("one JSON instance", GRAPHITI.SCHEMA_INSTANCE_INSTRUCTION)
        self.assertIn("not return or describe the schema", GRAPHITI.SCHEMA_INSTANCE_INSTRUCTION)

        edge = types.SimpleNamespace(
            episodes=["live-episode", "deleted-episode"], fact="stale native fact"
        )

        class EpisodicNode:
            @staticmethod
            async def get_by_uuids(driver: object, uuids: list[str]) -> list[object]:
                del driver, uuids
                return [
                    types.SimpleNamespace(
                        uuid="live-episode", content="live native episode"
                    )
                ]

        contexts, native = GRAPHITI.asyncio.run(
            GRAPHITI._native_contexts_from_edges(
                EpisodicNode,
                object(),
                [edge],
                {"live-episode": "e_live", "deleted-episode": "e_deleted"},
            )
        )
        self.assertEqual(
            contexts,
            [
                {"evidence_id": "e_live", "text": "live native episode"},
                {"evidence_id": "e_deleted", "text": "stale native fact"},
            ],
        )
        self.assertEqual(len(native), 1)


    def test_openviking_uses_native_uri_prefixes_dimensions_and_mutations(self) -> None:
        source_map = {
            "viking://resources/job/source": "e_parent",
            "viking://resources/job/source/nested": "e_nested",
        }
        self.assertEqual(
            OPENVIKING._evidence_id_for_uri(
                "viking://resources/job/source/nested/content.md", source_map
            ),
            "e_nested",
        )
        ready = {
            "status": "success",
            "queue_status": {"Embedding": {"processed": 1, "error_count": 0}},
        }
        OPENVIKING._assert_add_result_ready(ready)
        with self.assertRaises(OPENVIKING.OpenVikingProductFailure):
            OPENVIKING._assert_add_result_ready(
                {
                    "status": "success",
                    "queue_status": {
                        "Embedding": {"processed": 0, "error_count": 1}
                    },
                }
            )

        class NativeNotFound(Exception):
            pass

        class Client:
            def __init__(self) -> None:
                self.deleted: list[str] = []

            def add_resource(self, path: str, **kwargs: object) -> dict[str, object]:
                self.updated_path = path
                return {**ready, "root_uri": kwargs["to"]}

            def rm(self, uri: str, **kwargs: object) -> dict[str, bool]:
                self.deleted.append(uri)
                return {"deleted": True}

            def read(self, uri: str) -> str:
                return f"native content from {uri}"

            def stat(self, uri: str) -> dict[str, bool]:
                if uri in self.deleted:
                    raise NativeNotFound(uri)
                return {"exists": True}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            update_path = root / "update.txt"
            delete_path = root / "delete.txt"
            update_path.write_text("old", encoding="utf-8")
            delete_path.write_text("delete", encoding="utf-8")
            client = Client()
            jobs = [
                {
                    "job_id": "j_mutation",
                    "operations": [
                        {
                            "type": "update",
                            "evidence_id": "e_update",
                            "text": "replacement",
                        },
                        {"type": "delete", "evidence_id": "e_delete"},
                    ],
                }
            ]
            maps = [
                {
                    "viking://resources/update": "e_update",
                    "viking://resources/delete": "e_delete",
                }
            ]
            historical_maps = [dict(maps[0])]
            paths = [{"e_update": str(update_path), "e_delete": str(delete_path)}]
            with mock.patch.object(
                OPENVIKING,
                "_not_found_error_type",
                return_value=NativeNotFound,
            ):
                receipts, native = OPENVIKING._apply_operations(
                    client, jobs, maps, paths, root / "raw"
                )
            contexts = OPENVIKING._contexts_from_find(
                client,
                {
                    "resources": [
                        {"uri": "viking://resources/update/content.md"}
                    ]
                },
                maps[0],
            )
            stale_contexts = OPENVIKING._contexts_from_find(
                client,
                {"resources": [{"uri": "viking://resources/delete/content.md"}]},
                historical_maps[0],
            )
            rendered_config = root / "state" / "ov.conf"
            with mock.patch.dict(
                OPENVIKING.os.environ,
                {
                    "EMBEDDING_API_BASE": "https://provider.test/v1",
                    "EMBEDDING_API_KEY": "protected",
                    "EMBEDDING_MODEL": "Qwen3-Embedding-8B",
                    "EMBEDDING_DIMENSIONS": "4096",
                },
                clear=False,
            ):
                OPENVIKING._write_config(root / "state")
            config = json.loads(rendered_config.read_text(encoding="utf-8"))
            updated_text = update_path.read_text(encoding="utf-8")

        self.assertEqual(
            [row["native_type"] for row in receipts["j_mutation"]],
            ["reindex_update", "delete"],
        )
        self.assertEqual(updated_text, "replacement")
        self.assertEqual(client.deleted, ["viking://resources/delete"])
        self.assertEqual(contexts[0]["evidence_id"], "e_update")
        self.assertEqual(stale_contexts[0]["evidence_id"], "e_delete")
        self.assertEqual(len(native[0]["operations"]), 2)
        self.assertEqual(
            native[0]["operations"][1]["deletion_readback"]["classification"],
            "absent",
        )
        self.assertEqual(config["storage"]["vectordb"]["dimension"], 4096)
        self.assertEqual(config["embedding"]["dense"]["dimension"], 4096)


    def test_readiness_repairs_remain_native_and_bounded(self) -> None:
        compose = (REPO / "docker/benchmark/compose.yml").read_text(encoding="utf-8")
        unit_image = (REPO / "docker/benchmark/Dockerfile").read_text(encoding="utf-8")
        honcho_image = (REPO / "docker/benchmark/honcho.Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn('EMBEDDING_SEND_DIM: "true"', compose)
        self.assertIn('OPENKB_TIMEOUT_SECONDS: "1200"', compose)
        self.assertIn('/benchmark/state:mode=1777', compose)
        self.assertIn("/opt/graphrag-venv/bin/python", compose)
        self.assertIn(
            "COPY config/local/tokenizer.wordlevel.json /config/local/tokenizer.wordlevel.json",
            unit_image,
        )
        self.assertIn("UV_PYTHON_INSTALL_DIR=/opt/uv-python", honcho_image)
        honcho_deriver = compose.split("  honcho-deriver:", 1)[1].split(
            "  elf-unit:", 1
        )[0]
        honcho_unit = compose.split("  honcho-unit:", 1)[1].split("\nvolumes:", 1)[0]
        self.assertNotIn("condition: service_healthy", honcho_deriver)
        self.assertNotIn("condition: service_healthy", honcho_unit)


    def test_graphrag_passes_the_frozen_embedding_dimension_explicitly(self) -> None:
        settings = GRAPHRAG._settings(Path("/benchmark/state/graphrag"))
        call_args = settings["embedding_models"]["benchmark_embedding"]["call_args"]
        self.assertEqual(call_args["dimensions"], 4096)
        self.assertEqual(call_args["allowed_openai_params"], ["dimensions"])
        self.assertEqual(settings["vector_store"]["vector_size"], 4096)


