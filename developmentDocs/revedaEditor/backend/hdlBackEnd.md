# `revedaEditor/backend/hdlBackEnd.py`

**Module:** `revedaEditor.backend.hdlBackEnd`

## Purpose

Container classes describing HDL text views (`verilogaC`, `spiceC`, `spectreC`, `vacaskC`).

## Classes

- `verilogaC` — This class represents an imported verilog-A module.
  - `stripComments()`
  - `oneLiners()`
  - `findPinsParams()`
  - `pathObj()`
  - `pathObj()`
  - `pinOrder()`
  - `pinOrder()`
  - `netlistLine()`
  - `vaModule()`
  - internals: `_parseParameter()`
- `spiceC`
  - `pinOrder()`
  - `netlistLine()`
  - `subcktLineExtract()`
  - `extractSubcktParams()`
  - `pathObj()`
- `spectreC` — Parse a Spectre subcircuit file to extract name, pins, and parameters.
  - `pinOrder()`
  - `netlistLine()`
  - `subcktLineExtract()`
  - `extractSubcktParams()`
  - `pathObj()`
- `vacaskC` — Parse a VACASK subcircuit file to extract name, pins, and parameters.
  - `pinOrder()`
  - `netlistLine()`
  - `subcktLineExtract()`
  - `extractSubcktParams()`
  - `pathObj()`

## Used by

- [[revedaEditor/fileio/createSymbols|revedaEditor.fileio.createSymbols]]
