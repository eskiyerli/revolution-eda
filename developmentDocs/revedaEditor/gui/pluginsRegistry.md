# `revedaEditor\gui\pluginsRegistry.py`

**Module:** `revedaEditor.gui.pluginsRegistry`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `DownloadThread(QThread)`
  - `run()`
- `PluginRegistryWindow(QMainWindow)`
  - `fetch_registry()`
  - internals: `_initUI()`, `_installedVersion()`, `_onSelect()`, `_on_item_activated()`, `_on_download()`, `_install_entry()`, `_on_download_complete()`, `_on_download_error()`, `_askRestartAfterInstall()`, `_showInstallSuccess()`, `_get_current_entry()`, `_track_download()` … (+9)

## Depends on

- [[revedaEditor\backend\__init__|revedaEditor.backend.__init__]]
- [[revedaEditor\backend\fileUtils|revedaEditor.backend.fileUtils]]

## Used by

- [[revedaEditor\tests\test_plugin_discovery|revedaEditor.tests.test_plugin_discovery]]
