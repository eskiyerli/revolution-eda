# `revedaEditor/gui/pluginsRegistry.py`

**Module:** `revedaEditor.gui.pluginsRegistry`

## Purpose

Plugin registry window with background download thread.

## Classes

- `DownloadThread(QThread)`
  - `run()`
- `PluginRegistryWindow(QMainWindow)`
  - `fetch_registry()`
  - internals: `_initUI()`, `_onSelect()`, `_on_item_activated()`, `_on_download()`, `_install_entry()`, `_on_download_complete()`, `_on_download_error()`, `_get_current_entry()`, `_track_download()`, `_get_binary_url()`, `_plugin_requires_license()`, `_app_root()` … (+6)
