"""Host benchmark docker responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess

from .runtime import command


TARGET_IMAGE_ENV = {
    target: f"BENCHMARK_{target.upper()}_IMAGE"
    for target in (
        "elf",
        "pageindex",
        "openviking",
        "graphiti",
        "graphrag",
        "openkb",
        "honcho",
    )
}


def image_id(image: str) -> str:
    completed = command(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        check=False,
    )
    value = completed.stdout.strip()
    if completed.returncode or not value.startswith("sha256:"):
        raise RuntimeError(f"Docker image is unavailable: {image}")
    return value


def build_image(image: str, dockerfile: str, stage: str | None = None) -> str:
    source_commit = command(["git", "rev-parse", "HEAD"]).stdout.strip()
    completed = command(
        [
            "docker",
            "build",
            "--file",
            dockerfile,
            "--tag",
            image,
            *(["--target", stage] if stage else []),
            "--build-arg",
            f"ELF_SOURCE_COMMIT={source_commit}",
            ".",
        ],
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout[-8000:])
    return image_id(image)


def build_images(
    manifest: dict[str, Any], targets: list[dict[str, Any]], *, skip_build: bool
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    tags: dict[str, str] = {}
    digests: dict[str, str] = {}
    failures: dict[str, str] = {}
    main_targets = [target for target in targets if not target.get("image")]
    main_image = manifest["runner"]["image"]
    if main_targets:
        try:
            main_digest = (
                image_id(main_image)
                if skip_build
                else build_image(main_image, "docker/benchmark/Dockerfile")
            )
            if skip_build and any(target["id"] == "elf" for target in main_targets):
                expected = command(["git", "rev-parse", "HEAD"]).stdout.strip()
                revision = command(["docker", "image", "inspect", "--format",
                    '{{ index .Config.Labels "org.opencontainers.image.revision" }}', main_image]).stdout.strip()
                if revision != expected:
                    raise RuntimeError("cached ELF image source differs from HEAD; rebuild without --skip-build")
            for target in main_targets:
                tags[target["id"]] = main_image
                digests[target["id"]] = main_digest
        except Exception as error:
            for target in main_targets:
                failures[target["id"]] = f"benchmark unit image build failed: {error}"
    for target in targets:
        if not target.get("image"):
            continue
        target_id = target["id"]
        try:
            digest = (
                image_id(target["image"])
                if skip_build
                else build_image(target["image"], target["dockerfile"], target.get("build_target"))
            )
            if skip_build and target_id == "elf":
                expected = command(["git", "rev-parse", "HEAD"]).stdout.strip()
                revision = command(["docker", "image", "inspect", "--format",
                    '{{ index .Config.Labels "org.opencontainers.image.revision" }}', target["image"]]).stdout.strip()
                if revision != expected:
                    raise RuntimeError("cached ELF image source differs from HEAD; rebuild without --skip-build")
            tags[target_id] = target["image"]
            digests[target_id] = digest
        except Exception as error:
            failures[target_id] = f"{target_id} image build failed: {error}"
    return tags, digests, failures


def cleanup_project(project: str, compose_file: Path, env: dict[str, str]) -> dict[str, Any]:
    try:
        down = command(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "--file",
                str(compose_file),
                "down",
                "--volumes",
                "--remove-orphans",
                "--timeout",
                "15",
            ],
            env=env,
            check=False,
            timeout=90,
        )
        down_exit_code = down.returncode
        down_output = down.stdout[-4000:]
    except subprocess.TimeoutExpired as error:
        down_exit_code = 124
        down_output = str(error)
    remaining: dict[str, list[str]] = {}
    inspection_errors: list[str] = []
    for kind, args in (
        ("containers", ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"]),
        ("volumes", ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"]),
        ("networks", ["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"]),
    ):
        try:
            inspected = command(args, check=False)
            remaining[kind] = inspected.stdout.split()
            if inspected.returncode:
                inspection_errors.append(f"{kind} inspection exited {inspected.returncode}")
        except Exception as error:
            remaining[kind] = []
            inspection_errors.append(f"{kind} inspection failed: {type(error).__name__}")
    return {
        "down_exit_code": down_exit_code,
        "down_output": down_output,
        "remaining": remaining,
        "inspection_errors": inspection_errors,
        "passed": down_exit_code == 0
        and not inspection_errors
        and not any(remaining.values()),
    }


def compose_project_logs(project: str, compose_file: Path, env: dict[str, str]) -> str:
    """Capture dependency logs before Compose removes the isolated project."""
    try:
        completed = command(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "--file",
                str(compose_file),
                "logs",
                "--no-color",
                "--timestamps",
            ],
            env=env,
            check=False,
            timeout=60,
        )
    except Exception as error:
        return f"Compose dependency log capture failed: {type(error).__name__}\n"
    if completed.returncode:
        return (
            f"Compose dependency log capture exited {completed.returncode}\n"
            + completed.stdout
        )
    return completed.stdout


def project_images(project: str, compose_file: Path, env: dict[str, str]) -> list[dict[str, Any]]:
    try:
        completed = command(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "--file",
                str(compose_file),
                "images",
                "--format",
                "json",
            ],
            env=env,
            check=False,
            timeout=30,
        )
    except Exception as error:
        return [
            {
                "classification": "harness_failed",
                "message": f"image provenance failed: {type(error).__name__}",
            }
        ]
    if completed.returncode:
        return [{"classification": "harness_failed", "message": "image provenance unavailable"}]
    try:
        decoded = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        decoded = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    return decoded if isinstance(decoded, list) else [decoded]


def compose_project_name(run_id: str, suite_id: str, target_id: str) -> str:
    token = hashlib.sha256(f"{run_id}:{suite_id}:{target_id}".encode()).hexdigest()[:10]
    return f"elfb-{token}-{target_id}"[:63]

