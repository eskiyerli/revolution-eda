# Architecture

Revolution EDA is a monolithic **PySide6** desktop application. Libraries are
file-backed: every cellview is a human-readable JSON file on disk, and that
JSON is the real runtime contract — plugins, PDKs, importers and headless
tooling all consume it.

Guiding principle: **one semantic model, many input channels**. Connectivity,
parameters, and correspondence live in Qt-free backend modules so the GUI,
aiTerminal operations, importers, and tests all share the same semantics.

## Layers

```
reveda.py                     entrypoint: app, env, paths, logging, restart loop
└── gui/                      QMainWindow/QDialog chrome
    │   revedaMain            MainWindow: menus, openViews registry, session
    │   editorWindow          base editor: actions, locks, autosave, bindkeys
    │   {schematic,layout,symbol}Editor   per-view chrome + containers
    └── scenes/               QGraphicsScene state machines
        │   editorScene       edit modes, selection, undo stack, readOnly
        │   {schematic,layout,symbol}Scene  per-view editing + save/load
        └── common/           graphics items (shapes, layoutShapes, net, labels)
backend/                      Qt-free core: library model, undoStack commands,
                              cellviewState (locks/autosave), correspondence,
                              projectManager, pdkLoader, pluginsLoader
connectivity/                 unified connectivity engine (records + scenes)
fileio/                       JSON encoders/loaders + GDS/netlist importers
netlisting/                   Spectre/VACASK/Xyce writers
rcextraction/                 parasitic extraction pipeline
defaultPDK/                   bundled PDK (layers, process, pcells, callbacks)
```

## Runtime object graph

`QApplication` (`revedaApp`) → `app.appMainW` (`MainWindow`) →
`openViews: {viewNameTuple → editorWindow}`. Each editor owns a container
(`centralW`) with a `.scene` and a `.view`. The library browser's
`designView` (`BaseDesignLibrariesView`) opens cellviews via
`EditorFactory.createEditor` and registers them in `openViews`.

Important lifetime rule: QGraphicsItems are kept alive by
`scene.itemsRefSet` — dropping the last Python wrapper lets the C++ item be
deleted, which is why loaders and tests hold references.

## Editing semantics

- All scene edits go through `QUndoCommand`s in
  [[revedaEditor/backend/undoStack|backend/undoStack]] pushed onto
  `scene.undoStack` — never mutate items ad hoc.
- Edit modes live in `scene.editModes`; mouse events dispatch by mode in the
  scene's `mouse*Event` handlers.
- `scene.readOnly` (set by lock contention or the Read Only action) makes the
  scene's event filter swallow all mouse events.
- Saved geometry is scene-origin-relative in the encoders
  (`*_Encoder._subtract_point`).

## The semantic core (Qt-free)

- [[revedaEditor/connectivity/index|connectivity]] — `graph.py` union-find +
  `adapters.py` (records AND live items) + `resolve.py` (name resolution) +
  `netexpr.py` (netSet/inherited connections). One engine feeds schematic net
  naming, layout net highlight, netlisters, and diagnostics.
- [[revedaEditor/backend/correspondence|backend/correspondence]] — the `sdl`
  record ties layout instances to their source schematic instances; sync,
  flylines and cross-probing build on it.
- [[revedaEditor/common/params|common/params]] — CDF-lite typed parameter
  model (`ParamDef`), schematic labels ↔ pcell kwargs.
- [[revedaEditor/backend/cellviewState|backend/cellviewState]] — `.lock` /
  `.autosave` sidecar files (see [[DataFormats]]).

## Feature map (phases)

| Phase | Delivered | Where |
|---|---|---|
| 1 | Unified connectivity, name resolution | `connectivity/` |
| 2 | Typed parameters (CDF-lite) | `common/params.py` |
| 3 | Net expressions, inherited connections | `connectivity/netexpr.py`, `netlisting/exprSupport.py` |
| 4 | Schematic UX: find/replace, bus ripper, clipboard, markers, EIP | `scenes/schematicScene.py`, `gui/findDialogue.py` |
| 5 | Layout UX: mosaics, multipart, item grouping, boolean ops, flatten/make-cell, stream options, rulers | `common/layout*.py`, `scenes/layoutScene.py`, `fileio/exportGDS.py` |
| 6 | XL-lite: `sdl` records, incremental sync, flylines, cross-probing | `backend/correspondence.py`, `scenes/layoutScene.py` |
| 7 | Locks, autosave/crash recovery, bindkeys, session restore | `backend/cellviewState.py`, `backend/bindkeys.py`, `gui/editorWindow.py`, `gui/revedaMain.py`, `backend/projectManager.py` |

## Extensibility surfaces

- **PDK**: `REVEDA_PDK_PATH` package exposing `callbacks.py`, `process.py`,
  `schLayers.py`, `symLayers.py`, `layoutLayers.py`, `pcells.py`, plus
  `config.json` menu items (`pdkLoader.importPDKModule`).
- **Plugins**: `REVEDA_PLUGIN_PATH` packages with `config.json` menu wiring;
  custom view types via `viewTypes` + `openCellView`/`createCellView`.
- **Configuration**: `reveda.conf` (project state + session), `bindkeys.json`
  (key→QAction maps, defaults in `resources/`), `.env` (paths).

## Testing

`revedaEditor/tests/` — offscreen-Qt pytest suite (`conftest.py` provides the
`qapp` fixture and a `qtbot` shim). `sceneTestUtils.py` builds scenes with a
stubbed `editorWindow`/`appMainW`. Qt-free backend modules are tested
directly. Run with `poetry run pytest revedaEditor/tests/`.
