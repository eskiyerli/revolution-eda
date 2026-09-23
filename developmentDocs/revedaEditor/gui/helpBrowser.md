# `revedaEditor/gui/helpBrowser.py`

**Module:** `revedaEditor.gui.helpBrowser`

## Purpose

Markdown documentation browser plus about/license dialogs.

## Classes

- `MarkdownViewer(QTextBrowser)`
  - `loadMarkdownFile()`
  - `processImages()`
  - `handleLinkClick()`
  - `addStyling()`
- `helpBrowser(QMainWindow)`
  - `addToHistory()`
  - `updateNavigationButtons()`
  - `goHome()`
  - `goBack()`
  - `goForward()`
  - `handleNavigation()`
  - `printDocument()`
- `aboutDialog(QDialog)`
- `licenseDialog(QDialog)`
  - internals: `_loadLicenseText()`

## Functions

- `_resolve_docs_path()` — Return the absolute path to the docs directory.

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
