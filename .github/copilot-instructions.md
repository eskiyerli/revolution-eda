# Copilot Instructions for Revolution EDA

This guide enables AI coding agents to be immediately productive in the Revolution EDA
codebase, a professional custom IC design environment written in Python with PySide6 GUI
framework.

## Architecture Overview

**Application Structure**: Revolution EDA is a monolithic PySide6 desktop application.
`reveda.py` creates the `revedaApp` class, loads `.env`, resolves `REVEDA_PDK_PATH` /
`REVEDA_PLUGIN_PATH` / `REVEDA_VA_MODULE_PATH`, sets up `reveda.log`, and opens
`revedaEditor/gui/revedaMain.py:MainWindow`.

The three primary editors are:

- **Schematic Editor**: Creates circuit netlists with instances and connections
- **Symbol Editor**: Generates visual representations with pins and labels
- **Layout Editor**: Handles geometric cells (rectangles, polygons, paths, vias) with
  parametric cell support

Editor creation is centralized in `revedaEditor/gui/editorFactory.py` and view opening is
routed through `revedaEditor/backend/libraryModelView.py`. Standard view types (`schematic`,
`layout`, `symbol`) are opened by `EditorFactory`; other view types fall through to plugins
via `pluginsLoader.openCellView()` / `createCellView()`.

**Module Layout**:

- `revedaEditor/gui/` — windows, menus, dialogs, and editor chrome
- `revedaEditor/scenes/` — interaction/state for each editor (`editorScene.py`,
  `schematicScene.py`, `symbolScene.py`, `layoutScene.py`)
- `revedaEditor/common/` — reusable graphics items (`shapes.py`, `layoutShapes.py`,
  `net.py`, `labels.py`)
- `revedaEditor/backend/` — data definitions, undo stack, PDK/plugin loaders, library
  model, license manager, process manager
- `revedaEditor/fileio/` — JSON encoders/decoders, GDS/Spice/Verilog-A/xschem importers
- `revedaEditor/netlisting/` — netlist backends (Xyce, Spectre, VaCask)
- `revedaEditor/checks/` — schematic checks (ERC)

**Plugin System**: Plugins live in a separate directory pointed to by `REVEDA_PLUGIN_PATH`.
`revedaEditor/backend/pluginsLoader.py` scans that directory with `pkgutil.iter_modules()`,
imports packages by folder name, then reads each plugin's `config.json` for menu wiring.
Plugins are standalone Python packages that can be proprietary. Current plugins:

- `aiTerminal` — AI-assisted design modification (Claude, Gemini, Mistral agents)
- `revedasim` — Xyce circuit simulation with custom view type (`revbench`)
- `revedaPlot` — PyQtGraph waveform viewing

If a plugin handles custom views, it exposes `viewTypes` plus `openCellView()` and/or
`createCellView()` from the package root.

**PDK Architecture**: Each PDK (e.g., `gf180_pdk/`, `ihp_pdk/`, `defaultPDK/`) is a Python
package with required files:

- `__init__.py`: Imports all submodules
- `callbacks.py`: Instance parameter computation classes (inherits from `baseInst`)
- `schLayers.py`, `symLayers.py`, `layoutLayers.py`: Layer definitions using `edLayer`/
  `layLayer` dataclasses from `revedaEditor/backend/dataDefinitions.py`
- `pcells.py`: Parametric cell definitions (for layout generation)
- `process.py`: Process-specific constants
- `config.json`: Optional; adds PDK-specific menu actions (e.g., DRC with KLayout)

PDK loading is handled by `revedaEditor/backend/pdkLoader.py` which imports submodules as
`<pdk_name>.<module>`.

**Licensing Architecture**:

- `revedaLicense/` — proprietary module containing the real implementation
  (`licenseManager.py`). Compiled to `.pyd`/`.so` for distribution; never committed to the
  public repo.
- `revedaEditor/backend/licenseManager.py` — open-source compatibility shim. Re-exports
  from `revedaLicense` when present, or provides stubs so the base app starts without it.
- Plugins import from `revedaEditor.backend.licenseManager`, never directly from
  `revedaLicense`.
- License validation uses Ed25519 signatures with XOR-obfuscated public key.

**Data Flow**: Editors → JSON files (via `revedaEditor/fileio/`) → Plugin consumption
(simulation netlists, layout GDS). JSON is human-readable; all serialization uses `orjson`.

## Developer Workflows

**Development Install** (Python 3.12–3.14):

```bash
cd revolution-eda
poetry install
poetry run reveda
```

**PDK Configuration**: Set `REVEDA_PDK_PATH` in `.env` (relative or absolute path). App
restart required; fallback is `defaultPDK/` if path invalid.

**Plugin Development**: Create a module in the plugins directory. Plugin loading happens at
startup via `pluginsLoader`. Plugins are auto-discovered via `pkgutil.iter_modules()`.
`config.json` wires menu items; `apply` field must match the Qt window class name (e.g.,
`schematicEditor`, `layoutEditor`, `symbolEditor`).

**Running from Source**: `poetry run reveda` starts the app. Logs go to `reveda.log` in
the working directory.

**Standalone Builds (Nuitka)**:

- Nuitka directives are embedded in `reveda.py` (comment block near the top).
- Linux builds: `build_linux.sh` — iterates over Python 3.12/3.13/3.14, locating Poetry
  virtualenvs at `$POETRY_VENV_BASE` (default `$HOME/.poetryenvs/*py3.XX`). Output goes to
  `$HOME/dist/revolution-eda/` with per-version `.tar.gz` artifacts.
- Windows builds: `build_windows.ps1` — same pattern, output to
  `C:\Users\eskiye50\dist\revolution-eda\` with per-version `.zip` artifacts.
- `defaultPDK` is compiled as a separate Nuitka module (`--module
  --include-package=defaultPDK`) and deployed alongside the main binary.
- Plugin builds follow the same pattern (e.g., `plugins/aiTerminal/build_linux.sh`).
- Qt translation files are excluded (`--noinclude-dlls='**/translations/*.qm'`); the app
  is English-only.

**Version**: 0.9.0 (in `pyproject.toml`)

## Critical Architectural Patterns

**1. PDK Layer System**: Layers are `edLayer` (schematic/symbol) or `layLayer` (layout)
dataclasses with GDS mapping:

```python
# From defaultPDK/schLayers.py
edLayer(name="metal1", gdsLayer=34, datatype=0, pcolor=QColor(...))
```

Used by scene rendering to control visibility, selectability, z-ordering. Derived layers
are built with `dataclasses.replace(...)`.

**2. Parametric Cells**: Layout PCells are resolved dynamically:
`loadJSON.py:createPcellInstance()` expects the cell JSON header `{"cellView": "pcell"}`
and looks up the class in `pcells.pcells`. Parameters are computed at instantiation time
via callbacks in `callbacks.py`:

```python
class dnwpw(baseInst):
    def __init__(self, labels_dict):
        self.r_w = Quantity(labels_dict['@r_w'].labelValue)
    def area_parm(self):
        return self.r_w * self.r_l
```

**3. JSON I/O Contract**: JSON I/O is the real contract between components.
`revedaEditor/fileio/loadJSON.py` reconstructs scenes, while encoders define persisted
keys:

- Schematic: `sys/scn/scp/txt` (instances, nets, annotations)
- Symbol: `rect/line/pin/label/attr`
- Layout: `Inst/Rect/Path/Via/Pin/Label/Polygon/Pcell`

Saved geometry is scene-origin-relative in many encoders
(`*_Encoder._subtract_point(...)`).

**4. Plugin Registration Contract**: Plugins must expose interfaces expected by calling
code. `config.json` fields: `menu_items[].location/menu/action/callback`; `apply` must
match the actual Qt window class name. For custom views, expose `viewTypes` plus
`openCellView()` / `createCellView()`.

**5. Quantiphy Integration**: Physical quantities (resistors, widths) use
`quantiphy.Quantity` for unit parsing. Always construct with unit strings:
`Quantity('1.8u')` for 1.8 microns.

**6. PyLabels**: Executable conventions, not plain text.
`revedaEditor/common/labels.py:createPyLabel()` looks up a callback class whose name
matches `parentItem.cellName` and renders the returned value with
`Quantity(...).render(prec=3)`.

**7. Undo/Redo**: All scene edits must be undoable. Reuse commands in
`revedaEditor/backend/undoStack.py` instead of mutating `QGraphicsScene` state ad hoc.

**8. Draft Symbols**: Symbol instances tolerate missing libraries by creating a draft
placeholder (`loadJSON.py:createDraftSymbol()`); avoid turning unresolved references into
hard crashes.

## Project-Specific Conventions

- **Convention-Based Discovery**: Menus are injected by config, PDK modules are imported by
  fixed filenames, and callbacks are found by symbol/cell names. Renames across those
  boundaries break runtime discovery.
- **Config-Driven Netlisting**: Simulation configs select netlist view via UI dialogs;
  multiple netlisting backends: Xyce (primary), Spectre, VaCask.
- **Persistent Logging**: All significant operations logged to `reveda.log` via
  `revedaApp.logger`.
- **Scene Management**: Uses Qt graphics scenes (`QGraphicsScene` subclasses) with custom
  shapes inheriting from `symbolShape` base class.
- **AI Agent Integration**: The `aiTerminal` plugin provides AI-assisted design
  modification. Agents (`claudeAiAgent.py`, `geminiAiAgent.py`, `mistralAiAgent.py`)
  inherit from `baseAiAgent.py`, read/write design JSON, and validate paths against library
  directories. Agents communicate via design JSON mutations.

## File I/O & Import/Export

- **Encoders**: `schematicEncoder.py`, `symbolEncoder.py`, `layoutEncoder.py`
- **Loader**: `loadJSON.py` — universal loader for all three editor types
- **Import Plugins**: `importGDS.py`, `importSpice.py`, `importVeriloga.py`,
  `importXschemSym.py`, `importLayp.py` (KLayout layer properties), `importlvsdb.py`,
  `importlyrdb.py` (KLayout DRC/LVS results)
- **Export**: `exportGDS.py`
- **Symbol Generation**: `createSymbols.py` (auto-generate symbols from netlists)
- **Use `orjson` not standard `json`**: Significantly faster; configured in `pyproject.toml`

## Integration Points & Dependencies

| Component          | Purpose       | Notes                                                        |
|--------------------|---------------|--------------------------------------------------------------|
| **PySide6**        | GUI framework | Version ≥6.11.1; includes WebEngineWidgets for help browser  |
| **polars**         | Data tables   | Used for layer/pin/net management; faster than pandas        |
| **numpy**          | Numerics      | Layout coordinate computations                               |
| **quantiphy**      | Unit handling | Mandatory for PDK parameters                                 |
| **gdstk**          | GDS I/O       | Layout export/import; version ~1.0.0                         |
| **orjson**         | JSON I/O      | Fast serialization for all cell views                        |
| **cryptography**   | Licensing     | Ed25519 signature verification                               |
| **markdown**       | Help system   | Renders documentation in help browser                        |
| **lxml**           | XML parsing   | Used by import plugins                                       |
| **anthropic**      | AI agent      | Claude integration in aiTerminal plugin                      |
| **google-genai**   | AI agent      | Gemini integration in aiTerminal plugin                      |
| **mistralai**      | AI agent      | Mistral integration in aiTerminal plugin                     |
| **httpx**          | HTTP client   | Used by AI agent APIs                                        |
| **python-dotenv**  | Config        | Loads `.env` for path configuration                          |

**Environment Variables**:

- `REVEDA_PDK_PATH`: PDK location (relative to `reveda.py` or absolute)
- `REVEDA_PLUGIN_PATH`: Plugin directory (optional; defaults to `plugins/`)
- `REVEDA_VA_MODULE_PATH`: Central Verilog-A module repository path
- `POETRY_VENV_BASE`: Override Poetry virtualenv location for build scripts

## Common Workflows by Component

**Adding a New Layer Type**:

1. Define in `<pdk>/schLayers.py` (or `symLayers.py`/`layoutLayers.py`)
2. Set GDS layer/datatype numbers
3. Configure color/visibility with `QColor()`
4. Use in cells; scene auto-renders based on layer settings

**Creating a Parametric Cell**:

1. Add class to `<pdk>/pcells.py`
2. Implement instance parameter extraction in `<pdk>/callbacks.py`
3. Reference by name in schematic instance properties
4. Parameters computed at instantiation; layout drawn based on results

**Debugging Plugin Loading**:

- Check `reveda.log` for plugin loading messages
- Verify plugin module has `__init__.py` and `config.json`
- Ensure `REVEDA_PLUGIN_PATH` is set correctly in `.env`
- A failing plugin import is logged and the plugin is skipped

**Adding a New Netlist Backend**:

1. Create a new file in `revedaEditor/netlisting/` following the pattern of
   `xyceNetlist.py` or `spectreNetlist.py`
2. Register in the simulation plugin's configuration

## Testing & Validation

- Limited unit tests in `revedaEditor/tests/`: `test_labels_nlp.py`, `test_net.py`,
  `test_netlisting.py`, `test_symbol_pins.py`
- Run tests: `poetry run pytest revedaEditor/tests/`
- For GUI changes: run app with `poetry run reveda`, interact with UI, verify `reveda.log`
- For PDK changes: restart app with new `REVEDA_PDK_PATH`, verify layer colors/parameters
- Validation is still largely manual GUI testing

## Key Files to Know

| File                                      | Purpose                                              |
|-------------------------------------------|------------------------------------------------------|
| `reveda.py`                               | Entry point; app init, PDK/plugin path management    |
| `revedaEditor/gui/revedaMain.py`          | MainWindow class; menu/toolbar setup                 |
| `revedaEditor/gui/editorFactory.py`       | Centralized editor creation                          |
| `revedaEditor/backend/dataDefinitions.py` | `edLayer`, `layLayer`, `editModes` dataclasses       |
| `revedaEditor/backend/libraryModelView.py`| View opening routing                                 |
| `revedaEditor/backend/pluginsLoader.py`   | Plugin discovery and loading                         |
| `revedaEditor/backend/pdkLoader.py`       | PDK module import                                    |
| `revedaEditor/backend/licenseManager.py`  | License shim (re-exports from revedaLicense)         |
| `revedaEditor/fileio/loadJSON.py`         | Universal JSON loader for all editors                |
| `revedaEditor/common/shapes.py`           | Graphics scene shape classes                         |
| `revedaEditor/common/layoutShapes.py`     | Layout-specific shape classes                        |
| `revedaEditor/netlisting/xyceNetlist.py`  | Primary netlist backend                              |
| `build_linux.sh`                          | Linux Nuitka build script                            |
| `build_windows.ps1`                       | Windows Nuitka build script                          |
| `defaultPDK/`                             | Built-in minimal PDK; reference for PDK development  |

---

**Tips for New Contributors**: Start by understanding the JSON file format (inspect a saved
schematic with a text editor), then trace how `loadJSON.py` reconstructs it in the GUI.
Understand the PDK structure by examining `defaultPDK/` and one real PDK (`gf180_pdk/` or
`ihp_pdk/`). Most GUI interactions ultimately serialize to JSON and trigger shape redraws.
For plugin patterns, study `plugins/aiTerminal` and `plugins/revedasim`.
