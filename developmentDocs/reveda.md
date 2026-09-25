# `reveda.py`

**Module:** `reveda`

## Purpose

Application entrypoint: builds `revedaApp` (a QApplication subclass), resolves the project directory, loads `.env`, configures `reveda.log`, discovers the PDK/plugins, opens :class:`MainWindow`, and drives the project-switch restart loop.

## Classes

- `resilientFileHandler(logging.FileHandler)` — FileHandler that silently retries on transient I/O errors (e.g. OneDrive sync).
  - `emit()`
- `revedaApp(QApplication)` — Revolution EDA application with plugin support and path management.
  - `reloadLicenseModule()`
  - `updatePDKPath()`
  - `updatePluginsPath()`
  - `update_env_file()`
  - internals: `_resolveDefaultProjectDir()`, `_userProjectsDir()`, `_confirmOrPickProjectDir()`, `_ensureEnvFile()`, `_getCentralDirectory()`, `_ensureCentralDirectory()`, `_setupLicensePath()`, `_setupPluginPath()`, `_setupLogger()`, `_setupPaths()`

## Functions

- `_early_load_env()` — Parse --project arg and load the correct .env before revedaEditor imports.
- `_create_splash()` — Create a splash screen shown during project switching.
- `main()`

## Depends on

- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\backend\pluginsLoader|revedaEditor.backend.pluginsLoader]]
- [[revedaEditor\gui\pythonConsole|revedaEditor.gui.pythonConsole]]
- [[revedaEditor\gui\revedaMain|revedaEditor.gui.revedaMain]]
