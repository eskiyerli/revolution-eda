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

When downloading from PyPI, consider downloading the source package to access *exampleLibraries*.

## Getting Started

1. Install Revolution EDA from PyPI
2. Launch the application
3. Load example libraries to explore features
4. Create or import your circuit designs
5. Set up simulation parameters
6. Run simulations and analyze results with the integrated plotter

## Attribution

- Some icons by [Yusuke Kamiyamane](http://p.yusukekamiyamane.com/). Licensed under
  a [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/).
