# `revedaEditor/gui/editorTypes.py`

**Module:** `revedaEditor.gui.editorTypes`

## Purpose

`Protocol` definitions typing the editor-window/container contract (`EditorContainer`, `BaseEditor`).

## Classes

- `EditorContainer(Protocol)`
- `BaseEditor(Protocol)` — Protocol defining the interface all editors must implement.
  - `centralW()`
  - `viewItem()`
  - `libraryDict()`
  - `libraryView()`
  - `checkSaveCell()`
  - `saveCell()`
  - `show()`

## Used by

- [[revedaEditor/gui/editorFactory|revedaEditor.gui.editorFactory]]
