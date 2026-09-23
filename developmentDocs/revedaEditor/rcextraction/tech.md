# `revedaEditor/rcextraction/tech.py`

**Module:** `revedaEditor.rcextraction.tech`

## Purpose

RCX technology-file (process stackup) parsing.

## Module docstring

Technology file loader and layer stackup definitions.

A tech file defines the physical properties of each layer needed for
parasitic extraction: sheet resistance, thickness, height above substrate,
dielectric constants, and via resistance.

Supports process corners (nom, hrhc, lrhc, hrlc, lrlc) where R and C
values vary while physical geometry (thickness, height) stays the same.

## Classes

- `LayerInfo` — Physical properties of a single routing layer.
- `ViaInfo` — Physical properties of a via type.
- `CouplingModel` — Interlayer coupling capacitance model.
- `TechFile` — Complete technology definition for RC extraction.
  - `layer_by_number()`
  - `layer_by_name()`
  - `via_by_name()`
  - `via_between()`

## Functions

- `load_tech_file()` — Load a technology definition from a JSON file.
- `_load_with_corners()` — Load tech file using corner-specific R/C overlaid on base geometry.
- `_load_flat()` — Load legacy flat tech file (no corners, all values inline).
