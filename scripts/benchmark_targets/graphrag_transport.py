"""Use JSON-object transport while retaining GraphRAG's typed output validation."""
from __future__ import annotations

import functools
import json
from typing import Any


def json_object_request(kwargs: dict[str, Any]) -> dict[str, Any]:
    from pydantic import BaseModel

    response = kwargs.get("response_format")
    if not isinstance(response, type) or not issubclass(response, BaseModel):
        return kwargs
    return {**kwargs, "response_format": {"type": "json_object"},
        "messages": [*kwargs["messages"], {"role": "user", "content":
            "Return only a JSON object that matches this output schema: "
            + json.dumps(response.model_json_schema(), sort_keys=True)}]}


def install_json_transport() -> None:
    import litellm

    if getattr(litellm.completion, "_elf_json_transport", False):
        return
    sync, asynchronous = litellm.completion, litellm.acompletion

    @functools.wraps(sync)
    def completion(*args, **kwargs):
        return sync(*args, **json_object_request(kwargs))

    @functools.wraps(asynchronous)
    async def acompletion(*args, **kwargs):
        return await asynchronous(*args, **json_object_request(kwargs))

    completion._elf_json_transport = True
    litellm.completion, litellm.acompletion = completion, acompletion


if __name__ == "__main__":
    install_json_transport()
    from graphrag.cli.main import app

    app()
