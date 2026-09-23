# `revedaEditor/backend/projectManager.py`

**Module:** `revedaEditor.backend.projectManager`

## Purpose

Project open/switch orchestration and `reveda.conf` persistence: paths, view lists, window geometry, autosave prefs, and the `openCellviews` session; plus the QSettings-backed recent-projects store.

## Module docstring

Project management for Revolution EDA.

Provides ProjectManager (orchestrates project loading, switching, and state persistence)
and RecentProjectsStore (QSettings-backed recent project tracking).

## Classes

- `RecentProjectsStore` — QSettings-backed persistence for recently opened project directories.
  - `projects()`
  - `add()`
  - `remove()`
  - internals: `_load()`, `_save()`
- `ProjectManager` — Orchestrates project loading, switching, and state persistence.
  - `active_project()`
  - `open_project()`
  - `switch_project()`
  - `save_current_state()`
  - internals: `_load_env()`, `_load_library_json()`, `_read_lib_def_file()`, `_load_reveda_conf()`, `_resolve_pdk_path()`, `_resolve_plugin_path()`, `_copy_env_template()`, `_apply_state()`

## Used by

- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
