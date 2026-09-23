# `revedaEditor/backend/pluginsLoader.py`

**Module:** `revedaEditor.backend.pluginsLoader`

## Purpose

Plugin discovery over `REVEDA_PLUGIN_PATH` (`pkgutil` scan, `config.json` menu wiring, `viewTypes` dispatch to plugin `openCellView`/`createCellView`).

## Classes

- `pluginsLoader`
  - `applyPluginMenus()`
  - `createCellView()`
  - `openCellView()`
  - internals: `__repr__()`, `_plugin_requires_license()`, `_wrap_callback_with_license()`, `_loadPluginMenus()`, `_check_license_or_prompt()`

## Depends on

- [[revedaEditor/backend/__init__|revedaEditor.backend.__init__]]
- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]

## Used by

- [[reveda|reveda]]
