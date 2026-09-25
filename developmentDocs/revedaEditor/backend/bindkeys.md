# `revedaEditor\backend\bindkeys.py`

**Module:** `revedaEditor.backend.bindkeys`

## Purpose

Bindkey configuration: key sequence -> QAction name.

## Functions

- `_readBindkeySection()` — Validate one parsed JSON file; return {section: {keyseq: actionName}}.
- `loadBindkeyMap()` — Load shipped defaults merged with the project-level override.
- `applyBindkeys()` — Apply configured shortcuts to a window's QAction attributes.

## Used by

- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor\tests\test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
