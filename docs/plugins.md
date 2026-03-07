# Revolution EDA — Plugins Guide

This document summarizes the Revolution EDA plugin system, how plugins are discovered and loaded, how to install and configure plugins (manual and via the "Install Plugin" dialog), and development tips for plugin authors.

Quick checklist
- [ ] Understand plugin discovery and where plugins live
- [ ] Learn required plugin layout and `config.json` fields
- [ ] Install a plugin manually or with the Install Plugin dialog
- [ ] Troubleshoot common failures with `reveda.log`

1. Overview

Purpose
- Plugins extend core functionality (simulators, plot viewers, AI agents, importers, exporters, etc.).
- They are loaded at application startup and can expose UI integrations, background services, or CLI-like hooks.

Auto-discovery & loading
- At startup, Revolution EDA enumerates available plugins via Python's `pkgutil.iter_modules()` and imports them. See `reveda.py:_setup_plugins()` for the exact discovery and import logic.
- Typical log messages are written to `reveda.log` (e.g., `Found plugin:` / `Failed to load plugin:`). The app logger is initialized in `reveda.py:_setup_logger()`.
- Default search locations:
  - The repository `plugins/` folder (root-level `plugins/` in the project)
  - Additional folders specified by environment variable `REVEDA_PLUGIN_PATH` (must be set before app start)

Relevant files
- `reveda.py` (entry point and plugin setup)
- `plugins/` (plugin packages shipped with the repo)
- `plugins.json` and `plugins.json.orig` (metadata/config of enabled plugins)
- `reveda.log` (runtime diagnostics)

2. Expected plugin layout

Minimum structure for a plugin package:
- `plugins/<plugin_name>/` (directory)
  - `__init__.py` (must be present to make the directory importable)
  - `config.json` (plugin metadata — name, version, type, entrypoint, etc.)
  - implementation modules (e.g., `myplugin.py`, `main.py`, `agent.py`)
  - `README.md` (recommended)
  - optional: `compileNuitka.ps1` / `compileNuitka.sh`, `tests/`, resources/

Repository examples
- `plugins/aiTerminal/` — AI agent example (`aiTerminal.py`, `claudeAiAgent.py`, `config.json`)
- `plugins/revedasim/` — simulator plugin (complex example)
- `plugins/revedaPlot/` — plotting UI plugin

Best practices
- Keep code readable and import-safe (use try/except around optional imports).
- Do not perform heavy work at import time — prefer lazy initialization on first use.

3. Plugin contracts & interfaces

General
- Plugins must expose predictable entrypoints so the host app can consume them.
- Typical mechanism: `config.json` declares an `entry` module and optionally a class name or function.
- Plugins should use the application's logger (`revedaApp.logger`) for messages instead of printing to stdout.

Simulator plugin contract (example)
- Look at `plugins/revedasim/baseSimulator.py` for the abstract interface. Typical methods:
  - `initialize()` — prepare simulator backend and validate configuration
  - `runSimulation()` — execute a simulation run and return results or status
  - `shutdown()` / cleanup hooks (optional)
- The host uses factories like `simulatorFactory.py` to instantiate plugin simulator classes.

AI agent plugin contract
- See `plugins/aiTerminal/claudeAiAgent.py` and `geminiAiAgent.py` for examples.
- Expected method signature: `process_request(user_request: str) -> tuple[bool, str]` (return a success flag and response string).
- Helpers such as `read_design()` / `write_design()` and `validate_paths()` are used by agents to read/write design JSON safely.

Plot/UI plugins
- Should expose a small launch function or class that the host can call to open the plugin UI (for example, `revedaPlot/revedaPlotMain.py` exposes plotting entrypoints).

4. Installing and configuring plugins

Manual installation
1. Validate that the plugin folder contains `__init__.py` and `config.json`.
2. Copy the plugin folder into the app `plugins/` folder (e.g., `plugins/myPlugin/`). On Windows, use File Explorer or PowerShell copy; ensure files are not locked.
3. Restart the application.
4. Check `reveda.log` for discovery / load messages.

Using `REVEDA_PLUGIN_PATH`
- Set `REVEDA_PLUGIN_PATH` environment variable to point to an additional directory with plugins.
- The app will include that path during discovery. A restart is required after changing the environment variable.

`plugins.json`
- The top-level `plugins.json` may be updated by the Install Plugin dialog. It contains metadata and which plugins are enabled.
- Keep a backup (`plugins.json.orig`) when changing it manually.

5. Install Plugin dialog — UI flow and behavior

Purpose
- The Install Plugin dialog provides a guided, safer process for adding third-party plugins without manual file operations.

Inputs accepted
- Local archive (ZIP) containing a plugin package
- Remote URL to a zip/release archive (http/https)
- Local folder path (already-unpacked plugin)

Dialog validation steps (typical)
1. Verify archive/folder integrity (able to read/unpack if archive).
2. Confirm presence of a top-level plugin directory containing `__init__.py` and `config.json`.
3. Parse `config.json` and present a summary: plugin name, version, type, required dependencies.
4. Check for conflicts (same plugin name already installed) and offer overwrite/rename/cancel.
5. On confirmation, copy or unpack files into the app `plugins/` directory (or the directory referenced by `REVEDA_PLUGIN_PATH` if the dialog supports installing there).
6. Update `plugins.json` to register the plugin (creating a backup of the previous file).
7. Prompt the user to restart the application for the plugin to be discovered and loaded.

User-visible error cases
- "Invalid plugin package" — missing `config.json` or `__init__.py`.
- "Conflict: plugin already exists" — plugin name collision.
- "Permission error copying files" — write access problem; suggest running app as a user with write rights or changing destination directory permissions.
- "Failed to verify plugin type" — unsupported plugin contract.

Behind the scenes (implementation notes)
- The dialog should perform only structural validation (not run arbitrary plugin code) before copying.
- Post-install validation should be performed on restart when the host imports the plugin and calls its initialization hooks.

6. Development tips for plugin authors

Dependencies & packaging
- Use `poetry` for dependency management and to match project conventions. See top-level `pyproject.toml` for project style.
- Keep the plugin a standard Python package with `__init__.py` and specify dependencies in a `pyproject.toml` or `requirements.txt` if needed.

Binary packaging
- If you provide compiled artifacts, include platform-specific build scripts in the plugin folder, e.g., `compileNuitka.ps1` / `compileNuitka.sh` (examples exist under `plugins/revedasim/` and `plugins/revedaPlot/`).

Testing
- Include a minimal `tests/` folder with smoke tests.
- Smoke test: copy plugin into `plugins/` and run the application; check `reveda.log` for initialization messages.

Metadata (`config.json`) — recommended fields

```json
{
  "name": "myPlugin",
  "version": "0.1.0",
  "type": "simulator|ai|plot|importer|exporter",
  "entry": "myPlugin.module:ClassNameOrFunction",
  "description": "Short description",
  "dependencies": ["packageA>=1.2.3"],
  "icon": "resources/icon.png"
}
```

Notes
- Use semantic versioning.
- Declare required dependencies so the operator knows what to install.

7. Troubleshooting & FAQ

Common problems
- Plugin not discovered
  - Ensure folder is inside `plugins/` or in a directory listed by `REVEDA_PLUGIN_PATH`.
  - Ensure `__init__.py` exists and the top-level directory name is the package name.

- ImportError / ModuleNotFoundError on plugin load
  - Missing third-party dependency: install plugin dependencies into the Python environment used by the app (use `poetry install` if the plugin provides a `pyproject.toml`).

- Runtime exceptions during initialization
  - Inspect `reveda.log` for stack traces and "Failed to load plugin:" messages. Remove the offending plugin to recover.

Debugging steps
1. Start the app and watch `reveda.log` for `Found plugin` / `Failed to load plugin` entries.
2. Try `python -c "import plugins.myPlugin"` against the same Python interpreter to reproduce import errors.
3. Temporarily move plugin folders out of `plugins/` to isolate the issue.

Recovery
- Remove or rename plugin folder in `plugins/` and restart the app. Restore `plugins.json.orig` if needed.

8. Appendix: Minimal plugin checklist

- [ ] Directory `plugins/<name>/`
- [ ] `__init__.py` present
- [ ] `config.json` with name, version, type, entry
- [ ] Implementation modules importable
- [ ] Optional: `README.md`, `tests/`, `compileNuitka.*`

Repository examples to study
- `plugins/aiTerminal/` — AI agent patterns and `config.json`
- `plugins/revedasim/` — simulator base and factory usage
- `plugins/revedaPlot/` — plotting UI example

Where to look next
- `reveda.py:_setup_plugins()` — plugin discovery logic
- `reveda.log` — runtime diagnostics and plugin load messages
- `plugins.json` / `plugins.json.orig` — installed/enabled plugin metadata

If you want, I can:
- Add a sample `Install Plugin` dialog wire-up (pseudo-code) describing the UI controls and the validation code path.
- Generate a minimal example plugin skeleton under `plugins/examplePlugin/` (I can create the files and a minimal `config.json`).


---
Document generated on: 2026-02-27

