# `revedaEditor/connectivity`

Unified connectivity engine shared by GUI scenes, decoded JSON records, importers and tests.

## Modules

- [[revedaEditor/connectivity/__init__|__init__.py]] — Package facade re-exporting the unified connectivity engine API used by GUI scenes, decoded JSON records, importers and tests
- [[revedaEditor/connectivity/adapters|adapters.py]] — Adapters converting decoded records and live scene items into engine shapes
- [[revedaEditor/connectivity/diagnostics|diagnostics.py]] — Headless semantic checks on decoded design arrays (dangling ends, param problems, layout record diagnostics)
- [[revedaEditor/connectivity/graph|graph.py]] — Union-find connectivity graph: merges shapes through geometric touch and via-stack rules into net groups
- [[revedaEditor/connectivity/layout|layout.py]] — Layout-domain connectivity analysis: `analyzeLayoutItems`, net naming, via stacks and PCell pin bridging
- [[revedaEditor/connectivity/netexpr|netexpr.py]] — Net-expression / inherited-connection (`netSet`) parsing and evaluation
- [[revedaEditor/connectivity/primitives|primitives.py]] — Shared primitives: shape-record normalization and point/segment/rect predicates consumed by the engine
- [[revedaEditor/connectivity/resolve|resolve.py]] — Net-name resolution — the single implementation behind `nameSceneNets` semantics (sheet pins, SET-strength wire names, conflict handling)
