# Revolution EDA Documentation

Welcome to the documentation of Revolution EDA! This comprehensive guide is designed to provide you with all the information you need to effectively use our software for custom integrated circuit design.

Revolution EDA is a new generation electronic design automation package targeting custom integrated circuit design. It provides a complete schematic capture, symbol editing, and physical layout environment with integrated simulation and analysis capabilities through optional plugins. With a user-friendly interface, Python-based parameter management, and support for industry-standard formats, Revolution EDA offers a complete solution for designing and optimizing electronic circuits.

This documentation is organized to take you through the different stages of the design process, from installation and library setup to creating schematics, symbols, and layouts, and finally to netlisting and simulation. Each section provides detailed information on the features and functionalities, along with step-by-step instructions and examples to help you get started quickly.

Whether you are a student learning IC design or an experienced professional working on advanced mixed-signal circuits, Revolution EDA offers the flexibility and power you need to create sophisticated electronic designs. The software is built on modern Python technology (PySide6) and uses JSON-based file formats for maximum transparency and version control compatibility.



------

### [Installation](./installation.md)

Revolution EDA offers multiple installation methods. Whether installing via pip from PyPI, downloading pre-compiled binaries, or building from source using Poetry, the installation process is straightforward and well-documented. The software requires Python 3.12 or 3.13 and runs on Windows, macOS, and Linux.

------

### [Layout Editor](./layoutTutorial.md)

The layout editor is a full-featured tool for physical layout design of custom integrated circuits. It supports hierarchical layout design with rectangles, paths, polygons, pins, labels, vias, and Python-based parametric cells (pcells). The editor includes a Layer Selection Window (LSW) for layer visibility and selectability management, rulers for measurement, and GDS import/export capabilities.

------

### [Main Window](./revedaMainWindow.md)

The Revolution EDA main window is the starting point for all design activities. It provides access to the library browser, import tools, and application settings through a clean menu-driven interface. The window features an integrated Python REPL console that allows direct access to Revolution EDA's internal APIs for automation and scripting. The application uses a multi-threaded architecture with a configurable thread pool for efficient background processing.

------

### [Schematic Editor](./schematicTutorial.md)

The schematic editor is where circuit design begins. It is used to instantiate symbols and define the nets that connect them. The editor supports hierarchical design, Python-based instance parameter calculations, automatic symbol generation from schematics, net highlighting, and instance renumbering. It integrates seamlessly with the netlisting engine and optional simulation plugins for complete design flow support.

------

### [Symbol Editor](./symbolTutorial.md)

The symbol editor is used to create schematic representations of circuit components and hierarchical blocks. It supports drawing lines, rectangles, circles, arcs, and polygons, along with pins and labels. Symbols can have both common attributes shared across all instances and instance-specific parameters. The editor supports three types of labels: Normal (annotations), NLP labels (Natural Language Parameter labels with simple evaluation), and Python labels (dynamic calculation based on other parameters).

------

### [Config Editor](./configEditor.md)

The config view editor provides advanced control over the netlisting process, similar to commercial EDA tools. Using a config view, designers can specify exactly which cellview (schematic, veriloga, spice, or symbol) should be used for each cell in the design hierarchy. This is essential for large hierarchical designs where different abstraction levels are needed for different blocks. The config editor displays all cells in the hierarchy and allows per-cell view selection with customizable switch and stop view lists.
