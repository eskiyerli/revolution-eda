# `revedaEditor/fileio`

File-format layer: JSON encoders/loaders, GDS stream in/out, netlist and report importers, schema validation.

## Modules

- [[revedaEditor/fileio/__init__|__init__.py]] — Package marker for file format importers/exporters/encoders
- [[revedaEditor/fileio/createSymbols|createSymbols.py]] — Symbol generation from schematics (Create→Symbol): derives symbol pins from schematic pins and emits `symbol.json`
- [[revedaEditor/fileio/exportGDS|exportGDS.py]] — GDS/OAS stream-out: walks the layout scene through hierarchy into `gdstk`, honoring `layerMap`/`cellNameMap`/`flattenDepth` stream options
- [[revedaEditor/fileio/extractedSchematic|extractedSchematic.py]] — `klayoutSchematicGenerator`
- [[revedaEditor/fileio/importGDS|importGDS.py]] — GDS stream-in: `gdsImporter` reads gdstk records into `lib/cell/layout.json` files, with merge mode that appends to existing cells
- [[revedaEditor/fileio/importLayp|importLayp.py]] — `.lyp` layer-properties XML import (KLayout-style) converting layer definitions/stipples into Revolution EDA layer data
- [[revedaEditor/fileio/importSpectre|importSpectre.py]] — Spectre netlist/model import into cellviews
- [[revedaEditor/fileio/importSpice|importSpice.py]] — SPICE subcircuit import
- [[revedaEditor/fileio/importVacask|importVacask.py]] — VACASK netlist import into cellviews
- [[revedaEditor/fileio/importVeriloga|importVeriloga.py]] — Verilog-A module import into cellviews
- [[revedaEditor/fileio/importXschemSym|importXschemSym.py]] — Xschem symbol-file import/conversion into symbol cellviews
- [[revedaEditor/fileio/importlvsdb|importlvsdb.py]] — KLayout LVS database (`.lvsdb`) parser producing error markers (`LVSErrorRect`) for the results browser
- [[revedaEditor/fileio/importlyrdb|importlyrdb.py]] — KLayout DRC XML report (`.lyrdb`) to dictionary/marker conversion
- [[revedaEditor/fileio/layoutEncoder|layoutEncoder.py]] — `layoutEncoder` — json.JSONEncoder mapping layout scene items to `Rect/Path/Via/Pin/Label/Polygon/Inst/Pcell/Multipart` records…
- [[revedaEditor/fileio/loadJSON|loadJSON.py]] — JSON→scene reconstruction: `schematicItems`/`layoutItems` loaders, symbol pin locators, draft-symbol fallback for missing libraries, PCell…
- [[revedaEditor/fileio/schemaValidation|schemaValidation.py]] — JSON-schema validation of design files (`schemas/*.schema.json`) with readable error formatting
- [[revedaEditor/fileio/schematicEncoder|schematicEncoder.py]] — `schematicEncoder` — scene items → `sys/scn/scp/txt/pin/label/attr/net` JSON records
- [[revedaEditor/fileio/spiceNetlist|spiceNetlist.py]] — SPICE/extracted-netlist parsing utilities: subcircuit hierarchy trees, device-line parsing
- [[revedaEditor/fileio/symbolEncoder|symbolEncoder.py]] — `symbolEncoder` — symbol scene items → `symbol.json` records
