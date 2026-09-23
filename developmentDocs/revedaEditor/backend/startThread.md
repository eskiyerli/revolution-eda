# `revedaEditor/backend/startThread.py`

**Module:** `revedaEditor.backend.startThread`

## Purpose

Thin `QThread` wrapper used to run background work off the GUI thread.

## Classes

- `workerSignals(QObject)` — Defines the signals available from a running worker thread.
- `startThread(QRunnable)` — A thread class to execute a given function as a runnable task.
  - `run()`

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/libraryBrowser|revedaEditor.gui.libraryBrowser]]
