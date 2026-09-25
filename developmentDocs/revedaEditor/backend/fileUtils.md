# `revedaEditor\backend\fileUtils.py`

**Module:** `revedaEditor.backend.fileUtils`

## Purpose

Shared file-system helpers for application boundaries.

## Functions

- `safeExtractZip()` — Extract an archive only when every member stays under destination.
- `atomicWriteText()` — Write text to a temporary sibling and replace path atomically.

## Used by

- [[revedaEditor\gui\libraryRegistry|revedaEditor.gui.libraryRegistry]]
- [[revedaEditor\gui\pdkRegistry|revedaEditor.gui.pdkRegistry]]
- [[revedaEditor\gui\pluginsRegistry|revedaEditor.gui.pluginsRegistry]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_file_hardening|revedaEditor.tests.test_file_hardening]]
