# `revedaEditor\tests\test_sdl_free_baseline.py`

**Module:** `revedaEditor.tests.test_sdl_free_baseline`

## Purpose

Regression contract for the SDL functionality already released on master.

## Classes

- `_Combo`
  - `setCurrentText()`
  - `currentText()`
- `_Dialog`
  - `exec()`

## Functions

- `_sysRecord()`
- `_writeLibrary()`
- `_schematicTuple()`
- `_sceneFor()`
- `_fakeEditorForChooser()`
- `_patchChooser()`
- `test_free_editor_exposes_only_master_sdl_action()`
- `test_free_schematic_editor_has_no_layout_probe_action()`
- `test_free_load_chooser_replaces_scene_and_calls_master_loader()`
- `test_free_load_chooser_confirms_before_wiping_scene()` — Non-empty scene: user must approve the destructive replace.
- `test_free_load_chooser_cancel_does_not_mutate()`
- `test_free_loader_warns_and_cancel_preserves_existing_instances()`
- `test_free_loader_creates_layout_instances_with_master_transform()`
- `test_free_loader_applies_existing_pcell_parameter_map()`
- `test_free_loader_skips_missing_required_pcell_parameter()`
- `test_free_loader_skips_missing_layout_view()`

## Depends on

- [[defaultPDK\__init__|defaultPDK.__init__]]
- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor\gui\schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
