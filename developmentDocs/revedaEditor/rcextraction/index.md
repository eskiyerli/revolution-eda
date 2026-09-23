# `revedaEditor/rcextraction`

RC-extraction pipeline (technology parsing, geometry reader, extractor, netlist emission).

## Modules

- [[revedaEditor/rcextraction/__init__|__init__.py]] — Package marker for the RC-extraction flow
- [[revedaEditor/rcextraction/extractor|extractor.py]] — Unified RC extractor consuming the RCX database: parasitic R/C modeling, device pin anchoring, coupling capacitance
- [[revedaEditor/rcextraction/layoutGeometry|layoutGeometry.py]] — Record-driven layout geometry reader feeding the extractor
- [[revedaEditor/rcextraction/netlist|netlist.py]] — Parasitic (DSPF-style) netlist emission for extraction results
- [[revedaEditor/rcextraction/rcxExport|rcxExport.py]] — RCX database export helpers
- [[revedaEditor/rcextraction/rcx_schema|rcx_schema.py]] — RCX database schema definitions
- [[revedaEditor/rcextraction/tech|tech.py]] — RCX technology-file (process stackup) parsing
