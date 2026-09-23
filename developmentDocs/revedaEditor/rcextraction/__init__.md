# `revedaEditor/rcextraction/__init__.py`

**Module:** `revedaEditor.rcextraction.__init__`

## Purpose

Package marker for the RC-extraction flow.

## Module docstring

RC parasitic extraction (PEX), vendored into Revolution EDA.

This subpackage computes parasitic R and C from a pre-solved extraction
database (`.rcx.json`) produced by the LVS "Export for PEX" step. It was
formerly a standalone `rcextraction` package; it is vendored here so it
ships with Revolution EDA without an extra PyPI dependency.

The subpackage is pure Python (no third-party runtime dependency beyond the
standard library) and is intentionally free of any `revedaEditor` imports,
so the extraction engine stays independent of the GUI.

Public modules:
    rcx_schema  -- the `.rcx.json` schema (RcxDatabase and friends)
    tech        -- technology file loader (layer R/C models, corners)
    extractor   -- the extraction engine (`extract`)
    netlist     -- output writers (`get_writer`: spice/spef/spectre/vacask)
    rcxExport   -- builds a `.rcx.json` from LVS results
