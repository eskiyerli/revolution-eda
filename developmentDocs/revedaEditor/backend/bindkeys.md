# `revedaEditor/backend/bindkeys.py`

**Module:** `revedaEditor.backend.bindkeys`

## Purpose

Bindkey configuration: `{section: {keySeq: actionName}}` maps (shipped defaults in `resources/bindkeys.json` + project `bindkeys.json` override) applied to editor QActions; unknown actions/keys are skipped safely.

## Module docstring

Bindkey configuration: key sequence -> QAction name.

Shipped defaults live in `revedaEditor/resources/bindkeys.json`; a
project-level `bindkeys.json` in the run directory overrides them. The file
format groups bindings per editor view type so the same key can mean a
different action in schematic vs layout::

    {
        "*":         {"Shift+U": "redoAction", ...},
        "schematic": {"W": "createNetAction", ...},
        "layout":    {"W": "createPathAction", ...},
        "symbol":    {"W": "createLineAction", ...}
    }

Action names are `QAction` attribute names on the editor window (for example
`undoAction`). Unknown names or unparsable key sequences are skipped with a
warning so a bad config never breaks editing.

## Runtime flow

1. `revedaMain.MainWindow.__init__` calls `loadBindkeyMap(userPath=runPath/"bindkeys.json")`
   once at startup and stores the merged `{section: {keySeq: actionName}}` dict
   on `self.bindkeyMap`.
2. Each `editorWindow.__init__` calls `_applyConfiguredBindkeys()`, which reads
   `appMainW.bindkeyMap` and the window's `viewType`
   (`schematic`/`layout`/`symbol`) and calls
   `applyBindkeys(window, keyMap, viewType)`.
3. `applyBindkeys` applies the `"*"` section first, then the view-type section
   on top. It resolves each action name via `getattr(window, actionName)` —
   non-`QAction` attributes and unparsable `QKeySequence`s are warned + skipped.
   All sequences targeting one action are collected and set together via
   `action.setShortcuts(sequences)`, so multiple bindings coexist (e.g. `C` and
   `Ctrl+C` on `copyAction`).

Making an action bindable needs no registration: create a `QAction` attribute
on the window (e.g. `self.groupItemsAction`) and map keys to it in
`bindkeys.json` under the appropriate section.

## Functions

- `_readBindkeySection()` — Validate one parsed JSON file; return {section: {keyseq: actionName}}.
- `loadBindkeyMap()` — Load shipped defaults merged with the project-level override.
- `applyBindkeys()` — Apply configured shortcuts to a window's QAction attributes.

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor/tests/test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
