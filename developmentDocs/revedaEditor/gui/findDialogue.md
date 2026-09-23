# `revedaEditor/gui/findDialogue.py`

**Module:** `revedaEditor.gui.findDialogue`

## Purpose

Non-modal find/replace dialog and the check-marker browser for the schematic editor.

## Module docstring

Find/replace dialog for schematic editors.

Searches instances, nets and pins by name pattern (shell wildcards) and
optional property filter, backed by `schematicScene.findItems` — nets
resolve through the unified connectivity engine so a hit selects every
member wire of the electrical net. Selecting a row zooms to the hit;
Replace renames via `schematicScene.replaceHitName`.

## Classes

- `findDialogue(QDialog)` — Non-modal find/replace panel for one schematic scene.
  - `runFind()`
  - internals: `_kind()`, `_selectedHit()`, `_zoomToSelected()`, `_replaceSelected()`, `_replaceAll()`, `_applyReplace()`
- `markerBrowserDialogue(QDialog)` — Non-modal browser for check violations (`scene.lastCheckViolations`).
  - `refresh()`
  - internals: `_zoomToSelected()`

## Depends on

- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
