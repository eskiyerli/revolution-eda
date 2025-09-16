# Revolution EDA Schematic/Symbol Editors

## Introduction

Revolution EDA can

1. Create symbols with both symbol attributes that are common to all instances as well instance
   parameters. Instance parameters can be also python functions that allow the dynamic
   calculation of parameters for each instance.
2. Symbols can be created automatically from schematics and verilog-a modules.
3. Verilog-a symbols have a clear separation between model and instance parameters.
4. File formats are json-based allowing easy inspection and editing with a text editor if
   needed. Using Git for version control is a distinct possibility now.
5. Netlsting process can be guided by a config view like commercial tools allowing designer to
   choose between different views for simulation.
6. Netlisting is geared towards Xyce although not everything has not been implemented yet, for
   example subcircuit parameters.

# Installation

After PyPi installation, just issue `reveda` command to start the program.

## Attribution

- Some icons by [Yusuke Kamiyamane](http://p.yusukekamiyamane.com/). Licensed under
  a [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/).
