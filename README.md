# Revolution EDA Schematic/Symbol Editors

## Introduction

Revolution EDA is a new generation of schematic and symbol editor targeting custom integrated
circuit design with integrated simulation and plotting capabilities.

## Core Features

1. **Advanced Symbol Creation**: Create symbols with both common symbol attributes and instance parameters. Instance parameters can be Python functions for dynamic parameter calculation.
2. **Automatic Symbol Generation**: Generate symbols automatically from schematics and Verilog-A modules with support for circles, lines, rectangles, and arches.
3. **Verilog-A Integration**: Clear separation between model and instance parameters for Verilog-A symbols.
4. **JSON-Based File Format**: Human-readable JSON format allows easy inspection and editing with text editors.
5. **Configuration-Driven Netlisting**: Config view support similar to commercial tools for choosing simulation views.
6. **Hierarchical Netlisting**: Full hierarchical netlisting capability with Xyce simulator support.
7. **Python-Powered Labels**: Labels support Python functions enabling professional PDK development.
8. **Comprehensive Library Management**: Familiar library browser for creating, renaming, copying, and deleting libraries, cells, and views.
9. **Persistent Configuration**: Save and restore configuration parameters.
10. **Comprehensive Logging**: Error, warning, and info message logging.

## Plugin Architecture

Revolution EDA features a modular plugin architecture that enables extensible functionality:

- **Plugin System**: Dynamic plugin loading and management
- **Simulation Integration**: Seamless integration with Xyce circuit simulator with VACASK integration is planned for Q2 2026.
- **Plotting Capabilities**: Advanced waveform visualization and analysis
- **Extensible Framework**: Easy development of custom plugins

## Simulation and Plotting

### Simulation Features
- **Xyce Simulator Integration**: Full support for Xyce circuit simulator
- **Parameter Sweeps**: Multi-dimensional parameter sweep capabilities
- **Analysis Types**: Support for DC, AC, transient, noise, and harmonic balance analyses
- **Output Management**: Flexible output signal selection and processing
- **Process Management**: Efficient simulation job management

### Plotting Features
- **Interactive Waveform Viewer**: Advanced plotting with zoom, pan, and measurement tools
- **Multi-Plot Support**: Combined and separate plot views
- **Parameter Sweep Visualization**: Automatic plotting of parametric simulation results
- **Export Capabilities**: High-quality plot export functionality
- **Real-time Updates**: Live plot updates during simulation

## Installation

### Prerequisites

- Python 3.12 or 3.13
- [Poetry](https://python-poetry.org/docs/#installation) dependency management tool

### From Source

```bash
# Clone the repository
git clone https://github.com/eskiyerli/revolution-eda.git
cd revolution-eda

# Install dependencies
poetry install

# Run the application
poetry run reveda
```

To use preliminerary IHP PDK, clone the ihp_pdk repository preferably to another directory:
```bash
git clone https://github.com/eskiyerli/ihp_pdk.git
```

If you would like to use preliminary IHP PDK, make sure that `REVEDA_PDK_PATH` variable in `.env` file points to where it is downloaded. For example, you had cloned the repository under the same directory where `revolution-eda` repo is cloned, `.env` file content could be:
```
REVEDA_PDK_PATH=../ihp_pdk
```
You could also clone `example_libraries` repo to have some ideal elements and IHP sg13g2_pr library. The second library also three layout parametric cells included for `rsil`, `cap_cmim` and `sg13_lv_nmos`. There is no guarantee given that these parametric cells are error-free and can be used with the relevant IHP process.

Once again, the user can clone the relevant repository to download the example libraries:
```bash
git clone https://github.com/eskiyerli/exampleLibraries.git
```
User Library Path Editor to add the paths to downloaded libraries to library browser.

## Attribution

- Some icons by [Yusuke Kamiyamane](http://p.yusukekamiyamane.com/). Licensed under
  a [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/).
