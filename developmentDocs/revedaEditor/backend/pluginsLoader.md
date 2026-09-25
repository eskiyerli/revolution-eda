# `revedaEditor\backend\pluginsLoader.py`

**Module:** `revedaEditor.backend.pluginsLoader`

## Purpose

Module in `revedaEditor\backend`.

## Classes

- `pluginsLoader(QObject)`
  - `provides()`
  - `capabilityProvider()`
  - `pluginVersion()`
  - `checkForUpdates()`
  - `applyPluginMenus()`
  - `createCellView()`
  - `openCellView()`
  - internals: `_registerPluginMetadata()`, `_plugin_is_active()`, `_fetchRegistry()`, `_installedVersions()`, `_loadCachedUpdates()`, `_onRegistryFetched()`, `_onRegistryError()`, `__repr__()`, `_plugin_requires_license()`, `_wrap_callback_with_license()`, `_loadPluginMenus()`, `_check_license_or_prompt()`

## Depends on

- [[revedaEditor\__init__|revedaEditor.__init__]]
- [[revedaEditor\backend\__init__|revedaEditor.backend.__init__]]
- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\startThread|revedaEditor.backend.startThread]]

## Used by

- [[reveda|reveda]]
- [[revedaEditor\tests\test_plugin_api|revedaEditor.tests.test_plugin_api]]
- [[revedaEditor\tests\test_sdl_adapter|revedaEditor.tests.test_sdl_adapter]]
