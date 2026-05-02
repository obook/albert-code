# Architecture - Albert Code

## Overview

Albert Code is a CLI coding agent powered by the Albert API (the OpenAI-compatible endpoint operated by the French government), with optional support for Anthropic, Mistral, Vertex AI and any OpenAI-compatible backend. The project is written in Python (>=3.12) and exposes two entry points: an interactive Textual-based terminal UI (`albert-code`) and an Agent Client Protocol server (`albert-acp`) used by IDE integrations such as Zed.

The codebase follows a layered architecture with strict separation between pure domain logic, presentation adapters, and protocol adapters.

## Module map

The package `albert_code/` is split into four top-level subpackages plus a setup helper. Pure logic lives in `core/`; the user-facing layers (`cli/`, `acp/`) depend on it but never the other way around.

```
albert_code/
  core/                              (pure logic, no UI / protocol imports)
    agent_loop.py                    Main agent execution loop (turn orchestration)
    middleware.py                    Conversation middleware pipeline
    config.py                        Pydantic settings, single source of truth
    system_prompt.py                 System prompt assembly
    types.py                         Domain types (LLMMessage, AgentStats, ...)
    output_formatters.py             Code-block / markdown formatting
    programmatic.py                  Non-interactive (-p) API
    proxy_setup.py                   HTTP proxy configuration
    logger.py                        Structured logging
    utils.py                         Misc utilities (UTC time, name matching)

    llm/                             LLM backend abstraction
      backend/
        base.py                      APIAdapter protocol
        factory.py                   BackendFactory (provider selection)
        anthropic.py                 Anthropic native API
        mistral.py                   Mistral API
        vertex.py                    Google Vertex AI
        generic.py                   OpenAI-compatible (Albert, etc.)
      types.py                       LLMMessage, ChunkEvent
      message_utils.py               Message manipulation helpers
      format.py                      Tool call resolution
      quota.py, throttling.py        Rate limiting, quota tracking
      exceptions.py                  Context overflow, auth failures

    tools/                           Tool framework + implementations
      base.py                        BaseTool, ToolStreamEvent
      manager.py                     Tool discovery, indexing, dispatch
      builtins/                      Bash, Read, Write, Edit, Grep, Glob,
                                     WebSearch, WebFetch, AskUserQuestion,
                                     Task, Todo
      mcp/                           Model Context Protocol integration
        registry.py                  MCP server registry (stdio + HTTP)
        tools.py                     Proxy tool wrappers, tool listing
      mcp_sampling.py                MCP sampling handler
      ui.py, utils.py                Tool rendering helpers

    skills/                          Custom-skill plugin system
      manager.py                     Skill discovery (global + project-local)
      models.py, parser.py           Frontmatter parsing

    agents/                          Agent profiles (default, plan, ...)

    session/
      session_logger.py              Append-only conversation log
      session_loader.py              Deserialise prior session
      session_migration.py           Schema upgrade

    auth/
      crypto.py                      Symmetric encryption for stored creds
      github.py                      GitHub OAuth (used by teleport)

    paths/
      config_paths.py                XDG / macOS / Windows config dir
      global_paths.py                Sessions, skills, prompts, .env path
      local_config_walk.py           Project-local .vibe.toml lookup

    teleport/                        Remote sandbox (Vibe Nuage)
      teleport.py, nuage.py, git.py

    telemetry/
      send.py                        Opt-in anonymous events

    autocompletion/                  Path / file indexing for @-mentions
    prompts/                         Built-in system prompts

  cli/                               Interactive terminal UI (Textual)
    entrypoint.py                    Argparse, --setup, --install, --resume
    cli.py                           High-level CLI orchestration
    commands.py                      Slash-command registry
    history_manager.py               Persistent input history
    clipboard.py                     Cross-platform copy
    terminal_setup.py                Capability detection
    autocompletion/                  Path + slash-command completion
    update_notifier/                 Update checker (ports/adapters)
      ports/                         Update gateway, cache repository
      adapters/                      GitHub gateway, PyPI gateway, FS cache
    textual_ui/
      app.py                         AlbertApp (root Textual App)
      handlers/event_handler.py      User input -> agent loop bridge
      external_editor.py             $EDITOR integration
      ansi_markdown.py               Markdown -> ANSI for terminal rendering
      windowing/                     Message history pagination
      notifications/                 Desktop notifications (ports/adapters)
      widgets/
        messages.py                  User / assistant / bash messages
        tools.py, tool_widgets.py    Tool-call rendering + approval UI
        chat_input/                  Multiline input + completion popup
        approval_app.py              Modal: tool approval
        question_app.py              Modal: ask-user-question
        config_app.py                Modal: config editor
        session_picker.py            Modal: resume past session
        banner.py, loading.py,
        spinner.py, status_message.py
        teleport_message.py
        context_progress.py          Token usage gauge

  acp/                               Agent Client Protocol server (IDE bridge)
    entrypoint.py                    Bootstraps the ACP server
    acp_agent_loop.py                AcpAgent implementation
    acp_logger.py                    ACP message log adapter
    utils.py                         ACP message construction helpers
    tools/
      base.py                        BaseAcpTool wrapper
      builtins/                      ACP-adapted Bash, Read, Write,
                                     SearchReplace, Todo
      session_update.py              ACP session synchronisation

  setup/                             First-run UX
    onboarding/                      Wizard framework + screens
    trusted_folders/                 Trust-prompt dialog

tests/                               Pytest suite
  snapshots/                         Textual UI snapshot tests
  ...
```

### Layering rules

- `core/` has no import of `textual`, `acp`, or anything from `cli/` / `acp/` / `setup/`.
- `cli/` imports `core/` freely; `acp/` imports `core/` freely. Neither imports the other.
- `setup/` is only used by the entry points before the agent loop starts.
- Network exit points are concentrated in `core/llm/backend/*`, `core/tools/builtins/webfetch.py`, `core/tools/builtins/websearch.py`, `core/tools/mcp/*`, `core/teleport/nuage.py`, and `cli/update_notifier/adapters/*`.

## Entry points

Both entry points are declared in `pyproject.toml`:

```
[project.scripts]
albert-code = "albert_code.cli.entrypoint:main"
albert-acp  = "albert_code.acp.entrypoint:main"
```

### `albert-code` (interactive CLI)

`cli/entrypoint.py` parses arguments, runs first-run onboarding when needed, validates the trusted-folder status of the working directory, builds a `VibeConfig`, then either:

- launches `AlbertApp` (Textual TUI) for interactive use, or
- runs the programmatic loop (`core/programmatic.py`) for `-p / --prompt` invocations, with all tools auto-approved and machine-readable output (`text` / `json` / `streaming`).

### `albert-acp` (ACP server)

`acp/entrypoint.py` boots an ACP server reading `initialize` / `prompt` / `set_session_model` over stdio, delegates each prompt to `acp/acp_agent_loop.py`, and re-uses the same `core` building blocks (tool manager, LLM backends, middleware) wrapped in `BaseAcpTool` adapters that emit ACP session updates.

## Data flow

### Interactive turn (CLI)

```
User types in chat-input widget
  -> textual_ui/handlers/event_handler.py
  -> core/agent_loop.py (next turn)
       -> middleware pipeline (context warning, price limit, turn limit,
                               auto-compact, read-only guard, todo-focus)
       -> core/llm/format.py (build messages + tool definitions)
       -> core/llm/backend/<provider>.py (single network exit)
       -> streaming chunks
            -> textual widgets (incremental rendering)
       -> tool calls extracted from response
            -> tool manager dispatches to builtin / MCP / skill
            -> approval modal (unless agent profile auto-approves)
            -> tool result fed back to LLM
  -> session/session_logger.py (append message + stats to disk)
```

### ACP turn (IDE)

```
IDE -> ACP request (stdio JSON-RPC)
  -> acp/entrypoint.py
  -> acp/acp_agent_loop.py
       -> same core/agent_loop.py and core/tools / core/llm
       -> ACP session-update events emitted as the turn streams
  -> ACP response back to IDE
```

### Tool invocation

```
agent_loop                         (one decoded tool call)
  -> tools/manager.py              (resolve by name + glob/regex filters)
  -> BaseTool subclass.invoke()    (async generator of ToolStreamEvent)
       -> for MCP: tools/mcp/tools.py proxies to a stdio or HTTP MCP server
       -> for builtins: direct Python implementation
  -> aggregated result + truncation marker
  -> back into the LLM message list
```

## Key design decisions

**Pure-vs-IO split.** `core/` is meant to be importable from any host (CLI, ACP server, future SDK) without dragging in Textual or stdio glue. The agent loop, middleware pipeline, LLM backends and tool framework all live there. The CLI and ACP packages are thin adapters that wire I/O, approval prompts, and rendering around the same core.

**Pluggable LLM backends.** `core/llm/backend/factory.py` selects between `anthropic`, `mistral`, `vertex` and `generic` (OpenAI-compatible, used for Albert). Each backend converts the canonical `LLMMessage` / `AvailableTool` model into the provider's wire format and parses the streaming response back into common `ChunkEvent`s. Adding a provider means implementing one `APIAdapter`.

**Middleware pipeline.** Cross-cutting concerns (context-window warnings, price ceiling, turn limit, auto-compaction, read-only mode in plan agent, todo-focus reminder) are not hard-coded in the loop; they are middleware classes implementing `before_turn()` and composed into a list. This keeps the agent loop short and lets agent profiles enable or disable safety nets independently.

**Agent profiles.** A profile is a (mode, middleware set, allowed tools) bundle stored as TOML. Built-in profiles are `default`, `plan` (read-only + plan-first), `accept-edits` (auto-approve file edits) and `auto-approve`. User profiles in `~/.albert-code/agents/<name>.toml` override or extend them. The active profile is selectable via `--agent` or `Shift+Tab` at runtime.

**Tools as a stable interface.** Built-in tools and MCP tools share the same `BaseTool` contract, which yields async streaming events. The MCP integration is a proxy: `core/tools/mcp/tools.py` instantiates `BaseTool` subclasses on the fly that forward calls to a stdio or HTTP MCP server. Skills (custom Python tools) plug in the same way. The agent loop never has to know what is built-in versus remote.

**Session persistence.** Every interactive turn is appended to a JSONL log under `~/.albert-code/sessions/`. Resuming (`--continue` / `--resume`) replays the log into the agent state. A migration module handles schema upgrades when the on-disk format changes.

**Programmatic mode.** `-p` skips the TUI entirely, runs through `core/programmatic.py`, auto-approves all tools, and emits the final answer (or the streamed messages) on stdout. Combined with `--max-turns`, `--max-price`, `--enabled-tools`, this is the CI / scripting surface.

**Trusted folders.** Before the agent can touch the filesystem, the working directory must be on the trust list. The first time a directory is used, `setup/trusted_folders/trust_folder_dialog.py` asks the user explicitly. The decision is persisted globally.

**Update notifier.** The CLI checks PyPI for a newer version on startup (with a filesystem cache), shows release notes from `whats_new.md`, and offers an in-place upgrade. The check is implemented as a ports/adapters module so the gateway (`PyPI` or `GitHub`) and the cache backend can be swapped or mocked in tests.

**Snapshot-tested TUI.** `tests/snapshots/` uses `pytest-textual-snapshot` to capture the rendered TUI as SVG and assert it byte-for-byte against the committed baseline. Visual regressions are caught at CI time; intentional UI changes regenerate the baseline with `pytest --snapshot-update`.

**Telemetry is opt-in.** `core/telemetry/send.py` only emits events when telemetry is explicitly enabled in the config. The default-off behaviour is enforced in `VibeConfig`.

## Security boundaries

The `core/` / `cli/` / `acp/` split serves three security goals:

1. **Auditable network surface.** All HTTPS traffic to the model providers is concentrated in `core/llm/backend/*`. Web tools (`webfetch`, `websearch`) and MCP HTTP transports are the only other outbound endpoints, plus the update notifier (PyPI / GitHub) and the teleport client (Vibe Nuage). Any new exit point is visible in code review.
2. **Filesystem mediation.** Filesystem-modifying tools (`Bash`, `Write`, `Edit`) require the working directory to be in the trusted-folder list. In `plan` mode, the read-only middleware blocks them entirely.
3. **Approval gating.** In interactive mode, tool calls go through the `approval_app.py` modal unless the agent profile (`accept-edits`, `auto-approve`) opts out. The user can deny a single call without aborting the turn.

Input / output handling:

- **Outbound:** the system prompt and conversation history are sent verbatim to the configured provider; secrets in the conversation are the user's responsibility to scrub. The teleport flow encrypts credentials at rest via `core/auth/crypto.py`.
- **Inbound:** streamed model output is rendered through `cli/textual_ui/ansi_markdown.py`, which strips control sequences before display.

## Tests and CI

- `pytest --ignore tests/snapshots` runs the unit and integration suites (~1400 tests) under `pytest-xdist`.
- `pytest tests/snapshots` runs the Textual snapshot suite. Failures upload a diff report (`snapshot_report.html`) as a CI artifact.
- `pre-commit` enforces `pyright`, `ruff check --fix --unsafe-fixes`, `ruff format --check`, `typos`, and `action-validator`.
- The GitHub Actions workflow (`.github/workflows/ci.yml`) runs all three jobs in parallel on every push to `main` and every PR.

## Configuration

`VibeConfig` (Pydantic settings) is the single source of truth. It is loaded from:

1. `~/.config/albert-code/config.toml` (XDG_CONFIG_HOME) - global defaults.
2. The nearest `.vibe.toml` walking up from the current directory - project overrides.
3. Environment variables (prefix `ALBERT_CODE_`) - CI and one-off overrides.
4. `~/.albert-code/.env` - secrets (API keys).

`/config` (or `/model`) opens the in-app editor; `/reload` re-reads from disk after manual edits.
