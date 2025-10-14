# Copilot Instructions for Revolution EDA

This guide enables AI coding agents to be productive in the Revolution EDA codebase. It summarizes architecture, workflows, conventions, and integration points unique to this project.

## Architecture Overview
- **Monolithic Python Application**: Core logic in `reveda.py`, with modular subfolders for plugins, PDKs, and editors.
- **Plugin System**: Extensible via `plugins/` (e.g., `revedasim` for simulation, `revedaPlot` for plotting). Plugins are loaded automatically at startup.
- **PDK Support**: Technology files in `gf180_pdk/`, `ihp_pdk/`, and `defaultPDK/`. Each PDK is a Python module with required files: `__init__.py`, `callbacks.py`, `schLayers.py`, `symLayers.py`, `layoutLayers.py`, `pcells.py`.
- **Library Management**: Schematic and layout libraries are managed via a browser UI and can be extended by adding paths.
- **Data Flow**: Schematic/symbol editors generate JSON-based files. Simulation and plotting plugins operate on these outputs.

## Developer Workflows
- **Install from PyPI**: `pip install revolution-eda`; run with `reveda`.
- **Install from Source**: Use Poetry: `poetry install` then `poetry run reveda`.
- **PDK Setup**: Clone PDK repo and set `REVEDA_PDK_PATH` in `.env` or via the Options dialog. Restart required after changing PDK.
- **Plugin Usage**: Plugins are auto-loaded. Simulation (Xyce) and plotting (PyQtGraph) are integrated via `revedasim` and `revedaPlot`.
- **Testing**: No explicit test runner found; validate by running the app and using plugin features interactively.

## Project-Specific Conventions
- **JSON File Format**: All schematic and symbol data is stored in human-readable JSON.
- **Python-Based Parametric Cells**: Layout and symbol parameters can be Python functions for dynamic behavior.
- **Logging**: Error, warning, and info messages are logged persistently.
- **Config-Driven Netlisting**: Netlisting and simulation views are selected via config files and UI dialogs.
- **PDK Modules**: Each PDK must implement the required Python files for callbacks, layers, and parametric cells.

## Integration Points & Dependencies
- **External Simulators**: Xyce required for simulation; path must be configured.
- **Plotting**: PyQtGraph (and optionally matplotlib) for waveform visualization.
- **Python Packages**: `polars`, `numpy`, `quantiphy`, `pyqtgraph`, `PySide6`.
- **Environment Variables**: `REVEDA_PDK_PATH` for PDK location; `REVEDA_VA_MODULE_PATH` for Verilog-A modules.

## Key Files & Directories
- `reveda.py`: Main entry point.
- `plugins/revedasim/`: Simulation plugin (Xyce integration).
- `plugins/revedaPlot/`: Plotting plugin (PyQtGraph integration).
- `defaultPDK/`, `gf180_pdk/`, `ihp_pdk/`: Technology modules.
- `library.json`: Example library configuration.
- `README.md`: Detailed feature and installation info.

## Example Patterns
- **PDK Module Structure**:
  ```python
  # __init__.py, callbacks.py, schLayers.py, symLayers.py, layoutLayers.py, pcells.py
  # Each defines technology-specific logic for schematic/layout/symbol editing
  ```
- **Plugin Registration**:
  ```python
  # Plugins in plugins/ are auto-discovered and loaded at startup
  ```
- **Simulation Workflow**:
  1. Create schematic/symbol
  2. Configure simulation in UI
  3. Run simulation (Xyce)
  4. View results in revedaPlot

---

For unclear or incomplete sections, please provide feedback or point to additional documentation to improve these instructions.