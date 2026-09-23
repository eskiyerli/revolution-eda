# `revedaEditor/gui/editorFactory.py`

**Module:** `revedaEditor.gui.editorFactory`

## Purpose

`EditorFactory.createEditor` — viewType → editor-class dispatch for the standard editors.

## Module docstring

Editor factory for creating appropriate editor instances based on view type.

## Classes

- `EditorFactory` — Factory for creating editor instances based on view type.
  - `registerEditor()`
  - `createEditor()`
  - `getSupportedViewTypes()`

## Functions

- `registerEditors()` — Register all editor types. Called during module initialization.

## Depends on

- [[revedaEditor/gui/editorTypes|revedaEditor.gui.editorTypes]]

## Used by

- [[revedaEditor/gui/__init__|revedaEditor.gui.__init__]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
