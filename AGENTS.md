# AGENTS.md

## Quick orientation
- `reveda.py` is the app entrypoint. It creates `revedaApp`, loads `.env`, resolves `REVEDA_PDK_PATH` / `REVEDA_PLUGIN_PATH`, sets up `reveda.log`, and then opens `revedaEditor/gui/revedaMain.py:MainWindow`.
- This is a monolithic PySide6 desktop app. The main editing surfaces are `schematic`, `symbol`, and `layout`; editor creation is centralized in `revedaEditor/gui/editorFactory.py` and view opening is routed through `revedaEditor/backend/libraryModelView.py`.
- Libraries are file-backed. Editors read/write human-readable JSON cell views; plugins and PDKs consume those files rather than a service API.

## Architecture that matters when changing code
- `revedaEditor/gui/` owns windows, menus, dialogs, and editor chrome; `revedaEditor/scenes/` owns interaction/state for each editor; `revedaEditor/common/` owns reusable graphics items (`shapes.py`, `layoutShapes.py`, `net.py`, `labels.py`).
- JSON I/O is the real contract: `revedaEditor/fileio/loadJSON.py` reconstructs scenes, while `schematicEncoder.py`, `symbolEncoder.py`, and `layoutEncoder.py` define persisted keys such as `sys/scn/scp/txt`, `rect/line/pin/label/attr`, and `Inst/Rect/Path/Via/Pin/Label/Polygon/Pcell`.
- Layout PCells are resolved dynamically: `loadJSON.py:createPcellInstance()` expects the cell JSON header `{"cellView": "pcell"}` and looks up the class in `pcells.pcells`.
- Standard view types (`schematic`, `layout`, `symbol`) are opened by `EditorFactory`; other view types fall through to plugins via `pluginsLoader.openCellView()` / `createCellView()`.

## PDK conventions
- A PDK is a Python package pointed to by `REVEDA_PDK_PATH`; `revedaEditor/backend/pdkLoader.py` imports submodules as `<pdk_name>.<module>`.
- Working PDKs expose the same module set as `defaultPDK/`: `callbacks.py`, `process.py`, `schLayers.py`, `symLayers.py`, `layoutLayers.py`, and `pcells.py` or `pcells/`.
- Layer definitions must use the dataclasses in `revedaEditor/backend/dataDefinitions.py`: `edLayer` for schematic/symbol, `layLayer` for layout. Example: `defaultPDK/schLayers.py` builds derived layers with `dataclasses.replace(...)`.
- Callback classes read instance labels and usually convert them with `quantiphy.Quantity`; see `ihp_pdk/callbacks.py` (`cap_cmim`, `baseInst`) and `gf180_pdk/callbacks.py`.
- PyLabels are executable conventions, not plain text: `revedaEditor/common/labels.py:createPyLabel()` looks up a callback class whose name matches `parentItem.cellName` and renders the returned value with `Quantity(...).render(prec=3)`.
- Layout-only PDK menu actions come from `config.json`; `ihp_pdk/config.json` adds `Check -> DRC with KLayout` by pointing at `klayoutDRC.klayoutDRCClick`.

## Plugin conventions
- Plugins are only loaded if `REVEDA_PLUGIN_PATH` is set. `pluginsLoader` scans that directory with `pkgutil.iter_modules()`, imports packages by folder name, then reads each plugin's `config.json`.
- `config.json` is used for menu wiring, not discovery. Required runtime fields are effectively `menu_items[].location/menu/action/callback`; `apply` must match the actual Qt window class name (for example `schematicEditor`, `layoutEditor`, `symbolEditor`).
- If a plugin handles custom views, expose `viewTypes` plus `openCellView()` and/or `createCellView()` from the package root. `plugins/revedasim/__init__.py` is the canonical example (`viewTypes = ['revbench']`).
- Keep import side effects small: a failing plugin import is logged and the plugin is skipped.

## Developer workflows
- Install and run from source with Poetry:
  - `poetry install`
  - `poetry run reveda`
- Restart the app after changing `.env`, switching PDKs/plugins, or editing plugin `config.json`; startup is when discovery/import happens.
- Use `reveda.log` in the repo root first when debugging plugin loading, PDK import failures, JSON load failures, or missing menus.
- There are a few focused tests under `revedaEditor/tests/` (for example `test_labels_nlp.py`, `test_net.py`, `test_symbol_pins.py`), but validation is still largely manual GUI testing.
- Standalone packaging is driven by Nuitka directives embedded in `reveda.py`; plugin repos also keep their own compile scripts such as `plugins/revedasim/compileNuitka.sh`.

## Codebase-specific patterns to preserve
- Scene edits are expected to be undoable. Reuse commands in `revedaEditor/backend/undoStack.py` instead of mutating `QGraphicsScene` state ad hoc.
- Saved geometry is scene-origin-relative in many encoders (`*_Encoder._subtract_point(...)`); preserve that convention when adding new JSON fields.
- Symbol instances tolerate missing libraries by creating a draft placeholder (`loadJSON.py:createDraftSymbol()`); avoid turning unresolved references into hard crashes.
- Many UI extensions are convention-based: menus are injected by config, PDK modules are imported by fixed filenames, and callbacks are found by symbol/cell names. Renames across those boundaries break runtime discovery.
- If you need representative examples, use `defaultPDK/` for minimal built-in behavior, `ihp_pdk/` for a complete external PDK, and `plugins/aiTerminal`, `plugins/revedasim`, and `plugins/revedaPlot` for plugin patterns.

