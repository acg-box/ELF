"""Native OpenKB SDK query, executed only by the pinned OpenKB interpreter."""

import asyncio
import json
import os
import sys
from pathlib import Path

from agents import ModelSettings, Runner, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from openkb.agent.query import MAX_TURNS, build_query_agent
from openkb.config import load_config


def jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(child) for child in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return jsonable(vars(value))
    return str(value)


async def main():
    kb_dir = Path(sys.argv[1])
    question = sys.argv[2]
    config = load_config(kb_dir / ".openkb" / "config.yaml")
    model = str(config["model"])
    language = str(config.get("language", "en"))
    agent = build_query_agent(str(kb_dir / "wiki"), model, language=language)
    reasoning_effort = os.environ.get("CHAT_REASONING_EFFORT", "high")
    model_settings = agent.model_settings.resolve(
        ModelSettings(reasoning=Reasoning(effort=reasoning_effort))
    )
    agent = agent.clone(
        model=OpenAIChatCompletionsModel(
            model=os.environ["CHAT_MODEL"],
            openai_client=AsyncOpenAI(
                base_url=os.environ["OPENAI_BASE_URL"],
                api_key=os.environ["OPENAI_API_KEY"],
            ),
        ),
        model_settings=model_settings,
    )
    result = await Runner.run(agent, question, max_turns=MAX_TURNS)
    print(
        json.dumps(
            {
                "final_output": result.final_output or "",
                "input_items": jsonable(result.to_input_list()),
                "transport": "openai_chat_completions",
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


set_tracing_disabled(True)
asyncio.run(main())
