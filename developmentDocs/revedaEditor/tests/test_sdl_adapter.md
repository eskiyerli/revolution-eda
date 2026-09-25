# `revedaEditor\tests\test_sdl_adapter.py`

**Module:** `revedaEditor.tests.test_sdl_adapter`

## Purpose

Contract tests for the versioned core SDL plugin adapter.

## Classes

- `_SdlPlugins`
  - `provides()`
  - `applyPluginMenus()`

## Functions

- `initQapp()`
- `_record()`
- `_source()`
- `test_sdl_adapter_capability_is_negotiable()`
- `test_adapter_creates_stamps_and_describes_instance()`
- `test_adapter_resolves_layout_before_pcell()`
- `test_adapter_refuses_every_mutation_when_read_only()`
- `test_overlay_api_does_not_invalidate_connectivity()`
- `test_connectivity_lifecycle_signals_are_emitted()`
- `test_plugin_actions_follow_read_only_safety_property()`
- `test_plugin_loader_registers_action_safety()`
- `_layoutEditorForPluginMenu()`
- `test_active_sdl_capability_replaces_free_load_action()`
- `test_inactive_sdl_capability_keeps_free_load_action()`

## Depends on

- [[revedaEditor\backend\__init__|revedaEditor.backend.__init__]]
- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\pluginsLoader|revedaEditor.backend.pluginsLoader]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
