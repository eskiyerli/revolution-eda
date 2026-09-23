# `revedaEditor/fileio/importlyrdb.py`

**Module:** `revedaEditor.fileio.importlyrdb`

## Purpose

KLayout DRC XML report (`.lyrdb`) to dictionary/marker conversion.

## Module docstring

KLayout DRC XML report to dictionary converter using lxml.
Handles nested categories, cells, and DRC violations with polygons.

## Classes

- `DRCErrorPolygon(QGraphicsPolygonItem)`
  - `errorCategory()`
  - `errorCategory()`
  - `cell()`
  - `cell()`
  - internals: `__repr__()`, `__str__()`
- `DRCOutput`
  - `parseDRCOutput()`
  - `parseCategories()`
  - `parseCells()`
  - `xmltoDict()`
  - `parseViolations()`

## Functions

- `main()` — Main function to parse DRC file and print JSON-like dict.

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
