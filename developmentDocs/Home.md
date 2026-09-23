# Revolution EDA — Development Docs

This folder is an **Obsidian vault**: open `developmentDocs/` as a vault and the
`[[wikilinks]]` between module notes resolve into a navigable graph.

The per-file notes under each package folder are **generated** by
`scripts/generate_devdocs.py` — re-run it after structural changes instead of
editing generated notes by hand. The hand-written notes are this file,
[[Architecture]], and [[DataFormats]].

## Start here

- [[Architecture]] — layering, the "one semantic model, many input channels"
  principle, editor/scene/item responsibilities, and the Phase 1–7 feature map.
- [[DataFormats]] — the on-disk JSON contracts: cellview files, lock/autosave
  sidecars, `reveda.conf`, `bindkeys.json`.

## Package map

- [[reveda|reveda.py]] — application entrypoint
- [[revedaEditor/index|revedaEditor]] — the application package
  - [[revedaEditor/backend/index|backend]] — non-GUI layer: library model, undo
    commands, loaders, lock/autosave state, correspondence, project management
  - [[revedaEditor/checks/index|checks]] — schematic check rules
  - [[revedaEditor/common/index|common]] — shared graphics items and
    geometry/parameter helpers
  - [[revedaEditor/connectivity/index|connectivity]] — the unified connectivity
    engine
  - [[revedaEditor/fileio/index|fileio]] — JSON encoders/loaders, GDS stream
    in/out, importers, schema validation
  - [[revedaEditor/gui/index|gui]] — windows, dialogs, editor chrome
  - [[revedaEditor/netlisting/index|netlisting]] — netlist writers
  - [[revedaEditor/rcextraction/index|rcextraction]] — RC extraction pipeline
  - [[revedaEditor/resources/index|resources]] — compiled Qt resources +
    shipped `bindkeys.json`
  - [[revedaEditor/scenes/index|scenes]] — QGraphicsScene subclasses per editor
  - [[revedaEditor/tests/index|tests]] — the pytest suite
- [[defaultPDK/index|defaultPDK]] — bundled minimal PDK
- [[scripts/index|scripts]] — build/licensing tooling

## Key entry points for common tasks

| Task | Start at |
|---|---|
| Add an editor action/shortcut | [[revedaEditor/gui/editorWindow\|editorWindow]] + `resources/bindkeys.json` |
| Change what a cellview saves | [[revedaEditor/fileio/layoutEncoder\|layoutEncoder]] / [[revedaEditor/fileio/schematicEncoder\|schematicEncoder]] / [[revedaEditor/fileio/symbolEncoder\|symbolEncoder]] |
| Change how a cellview loads | [[revedaEditor/fileio/loadJSON\|loadJSON]] |
| Connectivity / net names | [[revedaEditor/connectivity/index\|connectivity]] package |
| Schematic↔layout sync | [[revedaEditor/backend/correspondence\|correspondence]] + [[revedaEditor/scenes/layoutScene\|layoutScene]] |
| Locks / autosave / session | [[revedaEditor/backend/cellviewState\|cellviewState]] + [[revedaEditor/backend/projectManager\|projectManager]] |
| Undoable edits | [[revedaEditor/backend/undoStack\|undoStack]] command classes |
| PDK-provided behavior | [[defaultPDK/index|defaultPDK]] modules |
