# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Commands

### Installation and Setup
```bash
# Install from PyPI
pip install revolution-eda

# Install from source using Poetry
poetry install

# Run the application
poetry run reveda
# Or if installed from PyPI
reveda
```

### Development Workflow
```bash
# Run tests
poetry run pytest revedaEditor/tests/

# Run specific test file
poetry run pytest revedaEditor/tests/test_schematicScene.py

# Format code (using Black)
poetry run black .

# Install development dependencies
poetry install --with dev

# Build with Nuitka (compile to executable)
poetry run nuitka reveda.py
```

### PDK and Plugin Management
```bash
# Clone and setup IHP PDK
git clone https://github.com/eskiyerli/ihp_pdk.git
# Set REVEDA_PDK_PATH in .env file to point to PDK location

# Clone example libraries
git clone https://github.com/eskiyerli/exampleLibraries.git
```

## Architecture Overview

### Core Application Structure
- **Entry Point**: `reveda.py` - Main application entry with plugin system and path management
- **GUI Framework**: PySide6-based application with custom editors for schematic, symbol, and layout design
- **Plugin Architecture**: Extensible via `plugins/` directory with automatic plugin discovery
- **PDK System**: Technology-specific modules in `defaultPDK/`, `gf180_pdk/`, `ihp_pdk/`

### Key Components

#### Main Application (`reveda.py`)
- `revedaApp` class manages plugins, paths, and environment variables
- Dynamic plugin loading from `REVEDA_PLUGIN_PATH`
- PDK path management via `REVEDA_PDK_PATH` environment variable
- Logging system with file-based persistence

#### Editor Architecture (`revedaEditor/`)
- **GUI Layer** (`gui/`): Main window (`revedaMain.py`), editors, browsers, dialogs
- **Scenes** (`scenes/`): Graphics scenes for schematic, symbol, and layout editing
- **Backend** (`backend/`): Data definitions, library management, HDL processing
- **File I/O** (`fileio/`): JSON-based file format, GDS import/export, various format imports
- **Common** (`common/`): Shared components (shapes, nets, labels)

#### Scene Hierarchy
- `editorScene` - Base class for all editor scenes
- `schematicScene` - Schematic editor with wire routing and component placement
- `symbolScene` - Symbol editor for creating device symbols
- `layoutScene` - Physical layout editor with GDS support

### Data Flow and File Format
- **Primary Format**: Human-readable JSON for schematics, symbols, and layouts
- **Library Management**: JSON-based library definitions (`library.json`)
- **Configuration**: Persistent settings via `reveda.conf`
- **Netlisting**: Hierarchical netlist generation with config-driven view selection

### Plugin System
- Plugins auto-discovered in `plugins/` directory or `REVEDA_PLUGIN_PATH`
- Key plugins:
  - `revedasim`: Xyce simulator integration for circuit simulation
  - `revedaPlot`: PyQtGraph-based waveform plotting and visualization
- Plugin registration via dynamic import at startup

### PDK (Process Design Kit) System
Each PDK module must implement:
- `__init__.py` - Package initialization
- `callbacks.py` - Technology-specific callbacks
- `schLayers.py` - Schematic layer definitions
- `symLayers.py` - Symbol layer definitions  
- `layoutLayers.py` - Layout layer definitions
- `pcells.py` - Parametric cells (Python-based)

## Important Development Notes

### Environment Variables
- `REVEDA_PDK_PATH`: Path to PDK directory (defaults to `defaultPDK/`)
- `REVEDA_PLUGIN_PATH`: Path to plugins directory
- `REVEDA_VA_MODULE_PATH`: Path to Verilog-A modules

### Testing
- Test files located in `revedaEditor/tests/`
- Uses pytest framework
- Tests cover core functionality like netlisting, schematic scene operations, and symbol handling
- Run individual tests for specific components during development

### Code Patterns
- **JSON Persistence**: All design data stored in human-readable JSON format
- **Python Parametric Cells**: Layout and symbol parameters can be Python functions
- **Signal/Slot Architecture**: Heavy use of PySide6 signals for inter-component communication
- **Thread Pool Management**: Background operations handled via QThreadPool
- **Undo/Redo System**: Command pattern implementation for all editor operations

### Development Dependencies
- Python 3.12 or 3.13 (specified in pyproject.toml)
- PySide6 6.10.0 for GUI framework
- Key libraries: polars, numpy, gdstk (GDS handling), quantiphy, pyqtgraph
- Development tools: pytest, black (formatter), nuitka (compiler)

### Integration Points
- **Xyce Simulator**: External simulator integration via `revedasim` plugin
- **GDS Files**: Import/export via gdstk library
- **Verilog-A**: Module integration for device modeling
- **PyQtGraph**: Waveform plotting and data visualization

### Common Patterns for Extension
1. **Adding New PDK**: Create directory with required Python modules following existing pattern
2. **Plugin Development**: Create module in plugins directory with proper registration
3. **New Editor Features**: Extend appropriate scene class and add GUI components
4. **File Format Support**: Add importers in `fileio/` directory following existing patterns

## Key Configuration Files
- `.env`: Environment variable definitions for paths
- `pyproject.toml`: Poetry dependency management and project metadata
- `library.json`: Library browser configuration
- `reveda.conf`: Application configuration persistence