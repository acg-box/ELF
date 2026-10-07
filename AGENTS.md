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

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Do not enumerate, preload, or search wikis at task start. Use retrieval when the user asks for it, when unfamiliar architecture or dependency behavior materially affects the task, or when source inspection leaves an important uncertainty. Stop once the question is grounded.
- When those conditions apply and OpenWiki retrieval tools are available, use `openwiki_search` for just-in-time context and `openwiki_read` for the relevant complete sections. If search returns `workspace_required`, ask which listed workspace to use and retry with its ID.
- Use `openwiki_list_workspaces` or `openwiki_list_wikis` when workspace membership itself needs to be discovered.
- If the retrieval tools are unavailable, read `openwiki/quickstart.md` and follow its links to the relevant pages.
- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->
