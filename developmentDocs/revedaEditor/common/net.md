# `revedaEditor/common/net.py`

**Module:** `revedaEditor.common.net`

## Purpose

Schematic wire/bus graphics items (`schematicNet`), net-name label items, and name-strength machinery.

## Classes

- `NetMode(IntEnum)`
- `netNameStrengthEnum(IntEnum)`
- `schematicNet(QGraphicsItem)`
  - `createEmptyNameItem()`
  - `draftLine()`
  - `draftLine()`
  - `shape()`
  - `boundingRect()`
  - `paint()`
  - `sceneEvent()`
  - `contextMenuEvent()`
  - `itemChange()`
  - `mousePressEvent()`
  - `mouseReleaseEvent()`
  - `generateEndPointNetDict()`
  - `initializeSnapLines()`
  - `updateSnapLines()`
  - `parseArrayNotation()`
  - `hoverEnterEvent()`
  - `hoverLeaveEvent()`
  - `isParallel()`
  - `isOrthogonal()`
  - `notParallel()`
  - `findOverlapNets()`
  - `inheritNetName()`
  - `mergeNetName()`
  - `clearName()`
  - `inherit()`
  - `name()`
  - `name()`
  - `nameStrength()`
  - `nameStrength()`
  - `netExpr()`
  - `netExpr()`
  - `nameConflict()`
  - `nameConflict()`
  - `endPoints()`
  - `otherEnd()`
  - `sceneOtherEnd()`
  - `sceneEndPoints()`
  - `sceneEndPoints()`
  - `offset()`
  - `offset()`
  - `width()`
  - `width()`
  - `highlight()`
  - `unhighlight()`
  - `highlighted()`
  - `highlighted()`
  - `probe()`
  - `unprobe()`
  - `probed()`
  - `probed()`
  - `sceneShapeRect()`
  - `angle()`
  - `angle()`
  - `mode()`
  - `nameItem()`
  - `nameItem()`
  - `annotationItem()`
  - `annotationItem()`
  - `clearAnnotation()`
  - internals: `_snapEndPoint()`, `_extractRect()`, `_clickMargin()`, `_getPen()`, `__repr__()`, `_finishSnapLines()`, `_namesMatch()`, `_clearFlightLines()`, `_unhighlightConnectedNets()`, `__hash__()`, `__eq__()`
- `netAnnotation(QGraphicsSimpleTextItem)`
  - `parent()`
  - `value()`
  - `value()`
- `netName(QGraphicsSimpleTextItem)`
  - `paint()`
  - `nameConflict()`
  - `nameConflict()`
  - `nameStrength()`
  - `nameStrength()`
  - `updateVisibility()`
  - `name()`
  - `name()`
  - `parent()`
  - `parent()`
  - `mouseReleaseEvent()`
- `netFlightLine(QGraphicsPathItem)`
  - `paint()`
  - internals: `__repr__()`, `_createPath()`
- `guideLine(QGraphicsLineItem)`
  - `draftLine()`
  - `draftLine()`
  - `sceneEndPoints()`
  - `name()`
  - `name()`
  - `nameStrength()`
  - `nameStrength()`
  - `netExpr()`
  - `netExpr()`
  - `inherit()`
  - `width()`
  - `horizontalFirst()`
  - internals: `__repr__()`, `_finishSnapLines()`

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]

## Used by

- [[revedaEditor/checks/schematic|revedaEditor.checks.schematic]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/extractedSchematic|revedaEditor.fileio.extractedSchematic]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/fileio/schematicEncoder|revedaEditor.fileio.schematicEncoder]]
- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/lvsResults|revedaEditor.gui.lvsResults]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/tests/test_connectivity|revedaEditor.tests.test_connectivity]]
- [[revedaEditor/tests/test_net|revedaEditor.tests.test_net]]
- [[revedaEditor/tests/test_netexpr|revedaEditor.tests.test_netexpr]]
- [[revedaEditor/tests/test_netlisting|revedaEditor.tests.test_netlisting]]
- [[revedaEditor/tests/test_schematic_checks|revedaEditor.tests.test_schematic_checks]]
- [[revedaEditor/tests/test_schematic_ux|revedaEditor.tests.test_schematic_ux]]
- [[revedaEditor/tests/test_wire_editing|revedaEditor.tests.test_wire_editing]]
