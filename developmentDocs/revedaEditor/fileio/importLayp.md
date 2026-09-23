# `revedaEditor/fileio/importLayp.py`

**Module:** `revedaEditor.fileio.importLayp`

## Purpose

`.lyp` layer-properties XML import (KLayout-style) converting layer definitions/stipples into Revolution EDA layer data.

## Functions

- `parse_source_field()` — Parse the source field to extract name, purpose, gdsLayer, and dataType.
- `safe_get_text()` — Safely get text from an XML element, returning default if element is None or has no text.
- `safe_get_color()` — Safely parse color text, returning default color if parsing fails.
- `safe_get_bool()` — Safely parse boolean text.
- `safe_get_int()` — Safely parse integer text.
- `parseLyp()` — Parse a LYP (Layer Properties) file and generate layoutLayers.py file.
- `process_dither_patterns()` — Process custom dither patterns from the LYP file.

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/gui/stippleEditor|revedaEditor.gui.stippleEditor]]

## Used by

- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
