# AGENTS.md — Repository-Specific Rules for Automated Agents

These instructions define repository-specific execution rules and scope limits for this repository.

---

## 1. Execution Model

## 1.1 Workspace Automation (cargo make)

- `Makefile.toml` is the source of truth for task names and behavior.
- Run `cargo make` from the repository root, and use it whenever an equivalent task exists.
- Run standalone commands only when `Makefile.toml` does not cover the capability or cannot produce the required effect for the current task.
- When task details are needed, inspect `Makefile.toml` directly or run `cargo make --list-all-steps`.

## Rust channel policy

Use the unversioned `stable` channel for Rust builds and tests. Use the
unversioned `nightly` channel for Rust formatting. Do not select numbered
compiler versions or dated nightly versions in local tasks, CI, or container
builds. Rust container images must follow the stable release with a floating
distribution tag.
