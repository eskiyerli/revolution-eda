# `revedaEditor\gui\textEditor.py`

**Module:** `revedaEditor.gui.textEditor`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `BaseHighlighter(QSyntaxHighlighter)`
  - `highlightBlock()`
  - `highlightComments()`
- `JsonHighlighter(BaseHighlighter)`
- `VerilogAHighlighter(BaseHighlighter)`
  - `highlightComments()`
  - `highlightSingleLineComments()`
  - `highlightMultiLineComments()`
- `XyceHighlighter(BaseHighlighter)`
  - `highlightComments()`
  - `highlightSingleLineComments()`
- `textEditor(QMainWindow)`
  - `initEditor()`
  - `createActions()`
  - `createMenus()`
  - `createToolbar()`
  - `openFile()`
  - `saveFile()`
  - `saveAsFile()`
  - `reloadFile()`
  - `changeFont()`
  - `findText()`
  - `replaceText()`
  - `updateStatus()`
  - `closeEvent()`
- `jsonEditor(textEditor)`
  - `initEditor()`
- `verilogaEditor(textEditor)`
  - `initEditor()`
  - `openFile()`
  - `saveAsFile()`
- `spiceEditor(textEditor)`
  - `initEditor()`
  - `openFile()`
  - `saveAsFile()`
- `SpectreHighlighter(BaseHighlighter)` — Syntax highlighter for Spectre netlist files.
  - `highlightComments()`
  - `highlightSingleLineComments()`
  - `highlightMultiLineComments()`
- `VacaskHighlighter(BaseHighlighter)` — Syntax highlighter for VACASK netlist files.
  - `highlightComments()`
  - `highlightSingleLineComments()`
  - `highlightMultiLineComments()`
- `spectreEditor(textEditor)`
  - `initEditor()`
  - `openFile()`
  - `saveAsFile()`
- `vacaskEditor(textEditor)`
  - `initEditor()`
  - `openFile()`
  - `saveAsFile()`
- `spefEditor(textEditor)`
  - `openFile()`
  - `saveAsFile()`

## Functions

- `main()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]

## Used by

- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
