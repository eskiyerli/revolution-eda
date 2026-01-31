# Copilot Instructions for Revolution EDA

This guide enables AI coding agents to be immediately productive in the Revolution EDA
codebase, a professional custom IC design environment written in Python with PySide6 GUI
framework.

## Architecture Overview

**Application Structure**: Revolution EDA is a monolithic PySide6 desktop application (
`reveda.py` → `revedaApp` class) that manages three primary editors through `revedaEditor/`
submodule:

- **Schematic Editor**: Creates circuit netlist with instances and connections
- **Symbol Editor**: Generates visual representations with pins and labels
- **Layout Editor**: Handles geometric cells (rectangles, polygons, paths, vias) with
  parametric cell support

**Plugin System**: Plugins in `plugins/` (e.g., `revedasim` for Xyce simulation,
`revedaPlot` for PyQtGraph waveform viewing) are auto-discovered via
`pkgutil.iter_modules()` in `reveda.py:_setup_plugins()`. Plugins are standalone Python
packages that can be proprietary.

**PDK Architecture**: Each PDK (e.g., `gf180_pdk/`, `ihp_pdk/`, `defaultPDK/`) is a Python
module with six required files:

- `__init__.py`: Imports all submodules
- `callbacks.py`: Instance parameter computation classes (inherits from `baseInst`)
- `schLayers.py`, `symLayers.py`, `layoutLayers.py`: Layer definitions using `edLayer`/
  `layLayer` dataclasses
- `pcells.py`: Parametric cell definitions (for layout generation)
- `process.py`: Process-specific constants

**Data Flow**: Editors → JSON files (via `revedaEditor/fileio/`) → Plugin consumption (
simulation netlists, layout GDS). JSON is human-readable; all schematic/symbol data uses
orjson serialization.

## Developer Workflows

**Development Install** (Python 3.12+):

```bash
cd revolution-eda
poetry install
poetry run reveda
```

**PDK Configuration**: Set `REVEDA_PDK_PATH` in `.env` (relative or absolute path). App
restarts required; fallback is `defaultPDK/` if path invalid.

**Plugin Development**: Create a module in `plugins/` directory. Plugin loading happens at
startup via `_setup_plugins()` in `reveda.py`. Plugins auto-discovered via
`pkgutil.iter_modules()`.

**Running from Source**: `poetry run reveda` starts the app. Logs go to `reveda.log` in
project root (initialized via `revedaApp._setup_logger()`).

**Build to Standalone**: Uses Nuitka with PySide6 plugin. Compilation flags in `reveda.py`
header (lines 24-57); output goes to `--output-dir` (Linux: `/home/eskiyerli/dist`, Darwin:
app bundle).

**Version**: 0.8.7 (in `pyproject.toml`)

## Critical Architectural Patterns

**1. PDK Layer System**: Layers are `edLayer` (schematic/symbol) or `layLayer` (layout)
dataclasses with GDS mapping:

```python
# From defaultPDK/schLayers.py
edLayer(name="metal1", gdsLayer=34, datatype=0, pcolor=QColor(...))
```

Used by scene rendering to control visibility, selectability, z-ordering.

**2. Parametric Cells**: Layout cells inherit from implicit base (see `pcells.py` patterns);
parameters computed at instantiation time via callbacks in `callbacks.py`:

```python
class dnwpw(baseInst):
    def __init__(self, labels_dict):
        self.r_w = Quantity(labels_dict['@r_w'].labelValue)
    def area_parm(self):
        return self.r_w * self.r_l  # Returns computed parameter
```

**3. JSON Structure**: Schematic cells stored as JSON objects with "instances", "nets", "
annotations" keys. Symbol/layout JSON differs but follows same pattern (see `loadJSON.py`
for parsing logic, ~640 lines).

**4. Plugin Registration Contract**: Plugins must expose interfaces expected by calling
code (e.g., `revedasim.baseSimulator.BaseSimulator` abstract class with `initialize()`,
`runSimulation()` methods). Check plugin consumer code for expectations.

**5. Quantiphy Integration**: Physical quantities (resistors, widths) use
`quantiphy.Quantity` for unit parsing. Always construct with unit strings:
`Quantity('1.8u')` for 1.8 microns.

## Project-Specific Conventions

- **Label Computation**: Labels can be Python code strings evaluated at render time (see
  `revedaEditor/common/labels.py` for `labelType` enum handling `Instance Param`,
  `Expression`, etc.)
- **Config-Driven Netlisting**: Simulation configs select netlist view via UI dialogs;
  multiple netlisting backends possible (Xyce primary)
- **Persistent Logging**: All significant operations logged to `reveda.log` via
  `revedaApp.logger` (initialized in `_setup_logger()`)
- **Undo/Redo**: Managed by `revedaEditor/backend/undoStack.py`; all edits must be
  reversible
- **Scene Management**: Uses Qt graphics scenes (`QGraphicsScene` subclasses) with custom
  shapes inheriting from `symbolShape` base class
- **AI Agent Integration**: Design modification agents (Claude, Gemini) in
  `revedaEditor/backend/` inherit from base class, read/write design JSON, validate paths
  against library directories. Agents communicate via design JSON mutations (not direct API
  calls to parsers).

## File I/O & JSON Handling

- **Encoder/Decoder**: Custom classes in `revedaEditor/fileio/`:
    - `schematicEncoder.py`: Schematic JSON serialization
    - `symbolEncoder.py`: Symbol JSON serialization
    - `layoutEncoder.py`: Layout JSON serialization
    - `loadJSON.py`: Universal loader (641 lines, handles all three types)
- **Import Plugins**: `importGDS.py`, `importSpice.py`, `importVeriloga.py` for reverse
  engineering designs
- **Use `orjson` not standard `json`**: Significantly faster; configured in `pyproject.toml`

## Integration Points & Dependencies

| Component                               | Purpose       | Notes                                                            |
|-----------------------------------------|---------------|------------------------------------------------------------------|
| **PySide6**                             | GUI framework | Version ≥6.10.0; includes WebEngineWidgets for library browser   |
| **polars**                              | Data tables   | Used for layer/pin/net management; faster than pandas            |
| **numpy**                               | Numerics      | Layout coordinate computations                                   |
| **quantiphy**                           | Unit handling | Mandatory for PDK parameters                                     |
| **gdstk**                               | GDS I/O       | Layout export; version ~0.9.60                                   |
| **Xyce**                                | Simulator     | External; path configured via UI; revedasim plugin interfaces it |
| **PyQtGraph**                           | Plotting      | revedaPlot plugin dependency; very fast waveform rendering       |
| **anthropic** / **google-generativeai** | AI agents     | New additions for Claude/Gemini integration                      |

**Environment Variables**:

- `REVEDA_PDK_PATH`: PDK location (relative to `reveda.py` or absolute)
- `REVEDA_PLUGIN_PATH`: Plugin directory (optional; defaults to `plugins/`)
- `REVEDA_VA_MODULE_PATH`: Verilog-A module directory

## Common Workflows by Component

**Adding a New Layer Type**:

1. Define in `<pdk>/schLayers.py` (or `symLayers.py`/`layoutLayers.py`)
2. Set GDS layer/datatype numbers
3. Configure color/visibility in `Qt.Color()`
4. Use in cells; scene auto-renders based on layer settings

**Creating a Parametric Cell**:

1. Add class to `<pdk>/pcells.py`
2. Implement instance parameter extraction in `<pdk>/callbacks.py` (e.g., `dnwpw` class)
3. Reference by name in schematic instance properties
4. Parameters computed at instantiation; layout drawn based on results

**Debugging Plugin Loading**:

- Check `reveda.log` for `Found plugin:` / `Failed to load plugin:` messages
- Add breakpoints in `reveda.py:_setup_plugins()`
- Verify plugin module has `__init__.py`; must be importable via
  `importlib.import_module(name)`

**Implementing an AI Agent**:

1. Inherit from base class in `revedaEditor/backend/claudeAiAgent.py` or `geminiAiAgent.py`
2. Implement `process_request(user_request: str)` → `tuple[bool, str]`
3. Use `read_design()` and `write_design()` for JSON I/O; validate paths with
   `validate_paths()`
4. Pass system prompt via `get_context()` which includes library files and design schema
5. Return modified design as valid JSON (strip markdown formatting if model wraps in code
   blocks)

## Testing & Validation

- No centralized test runner; most validation is manual (run app, use features, check logs)
- Limited unit tests in `revedaEditor/tests/` (e.g., `test_netlisting.py`)
- For GUI changes: run app with `poetry run reveda`, interact with UI, verify `reveda.log`
  for errors
- For PDK changes: restart app with new `REVEDA_PDK_PATH`, verify layer colors/parameters
  appear correctly

## Key Files to Know

| File                                      | Lines  | Purpose                                                            |
|-------------------------------------------|--------|--------------------------------------------------------------------|
| `reveda.py`                               | 216    | Entry point; app initialization, PDK/plugin path management        |
| `revedaEditor/gui/revedaMain.py`          | ?      | MainWindow class; menu/toolbar setup                               |
| `revedaEditor/backend/dataDefinitions.py` | 255    | `edLayer`, `layLayer`, `editModes` dataclasses                     |
| `revedaEditor/fileio/loadJSON.py`         | 641    | Universal JSON loader for all three editors                        |
| `revedaEditor/common/shapes.py`           | ~2000+ | Graphics scene shape classes (symbolRectangle, symbolCircle, etc.) |
| `gf180_pdk/callbacks.py`                  | 368+   | Example PDK callbacks; study for pattern                           |

---

**Tips for New Contributors**: Start by understanding the JSON file format (inspect a saved
schematic with a text editor), then trace how `loadJSON.py` reconstructs it in the GUI.
Understand the PDK structure by examining `defaultPDK/` and one real PDK (`gf180_pdk/`).
Most GUI interactions ultimately serialize to JSON and trigger shape redraws.
