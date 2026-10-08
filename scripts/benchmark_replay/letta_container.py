"""Execute the installed Letta CLI inside an isolated benchmark container."""

import json
import os
from pathlib import Path
import subprocess
import sys

phase = sys.argv[1]
state = Path("/state")
state.joinpath("home").mkdir(exist_ok=True)
if phase == "seed":
    result = subprocess.run(["letta", "connect", "openai-compatible", "--backend", "local",
        "--base-url", os.environ["CHAT_API_BASE"], "--api-key", os.environ["CHAT_API_KEY"]],
        capture_output=True, text=True, check=True)
    args = ["--new-agent"]
else:
    args = ["--agent", json.loads((state / "agent.json").read_text())["agent_id"], "--new"]
prompt = json.loads((state / ("seed-prompt.json" if phase == "seed" else "repair-prompt.json")).read_text())["prompt"]
os.execvp("letta", ["letta", "--backend", "local", *args,
    "--model", "openai-compatible/deepseek/deepseek-v4.1-flash",
    "--tools", "Read,Edit,Write,Bash",
    "--no-skills", "--no-mods", "--reflection-trigger", "off", "--max-turns", "6",
    "--yolo", "--output-format", "json", "-p", prompt])
