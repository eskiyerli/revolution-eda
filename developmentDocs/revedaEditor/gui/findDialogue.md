# `revedaEditor\gui\findDialogue.py`

**Module:** `revedaEditor.gui.findDialogue`

## Purpose

Find/replace dialog for schematic editors.

## Classes

- `findDialogue(QDialog)` — Non-modal find/replace panel for one schematic scene.
  - `runFind()`
  - internals: `_kind()`, `_selectedHit()`, `_zoomToSelected()`, `_replaceSelected()`, `_replaceAll()`, `_applyReplace()`
- `markerBrowserDialogue(QDialog)` — Non-modal browser for check violations (`scene.lastCheckViolations`).
  - `refresh()`
  - internals: `_zoomToSelected()`

## Depends on

- [[revedaEditor\gui\editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor\gui\schematicEditor|revedaEditor.gui.schematicEditor]]
