# Revolution EDA Schematic/Symbol Editors

## Introduction

Revolution EDA is a new generation of schematic, symbol and layout editors targeting custom 
integrated
circuit design extendible with plugins.

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
- **Extensible Framework**: Easy development of custom plugins


## Installation

### Prerequisites

- Python 3.12 or 3.13

### From PyPI

```bash
pip install revolution-eda
```

After installation, start the program with:

```bash
reveda
```

### From Source

```bash
# Clone the repository
git clone https://github.com/eskiyerli/revolution-eda.git
cd revolution-eda

# Install dependencies (requires Poetry)
poetry install

# Run the application
poetry run reveda
```

## PDK Support

To use preliminary IHP PDK:

```bash
git clone https://github.com/eskiyerli/ihp_pdk.git
```

For example libraries with ideal elements and IHP sg13g2_pr library:

```bash
git clone https://github.com/eskiyerli/exampleLibraries.git
```

Use Library Path Editor to add the paths to downloaded libraries to library browser.

## Attribution

- Some icons by [Yusuke Kamiyamane](http://p.yusukekamiyamane.com/). Licensed under
  a [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/).
