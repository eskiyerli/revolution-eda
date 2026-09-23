# `revedaEditor/backend/processManager.py`

**Module:** `revedaEditor.backend.processManager`

## Purpose

`ProcessManager` — QProcess-based launcher for external tools (simulators, checkers) from editor windows.

## Classes

- `Process`
- `ProcessManager(QObject)`
  - `add_process()`
  - `start_next_process()`
  - `process_finished()`
  - `handle_output()`
  - `stop_all()`
  - `maxProcesses()`
  - `maxProcesses()`
- `ProcessRunner`
  - `handle_output()`
  - `handle_error()`
  - `process_finished()`

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
