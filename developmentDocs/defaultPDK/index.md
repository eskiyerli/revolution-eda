# `defaultPDK`

Bundled minimal PDK: layers, process definitions, callbacks, pcells.

## Modules

- [[defaultPDK/__init__|__init__.py]] — Default PDK package marker
- [[defaultPDK/callbacks|callbacks.py]] — PDK callbacks evaluated by PyLabels/parameter resolution (`Quantity`-rendered values)
- [[defaultPDK/layoutLayers|layoutLayers.py]] — Layout layer definitions (`layLayer` dataclasses) for the default PDK
- [[defaultPDK/pcells|pcells.py]] — Parameterized-cell classes for the default PDK; exposed through the `pcells` registry dict
- [[defaultPDK/process|process.py]] — Process definitions: GDS layer map, via definitions, path defaults, dbu scale (`fabproc`)
- [[defaultPDK/schLayers|schLayers.py]] — Schematic layer definitions (`edLayer` dataclasses)
- [[defaultPDK/symLayers|symLayers.py]] — Symbol layer definitions (`edLayer` dataclasses)
