# `revedaEditor/scenes`

QGraphicsScene subclasses holding editing state per editor type.

## Modules

- [[revedaEditor/scenes/__init__|__init__.py]] — Package marker for the editor scenes
- [[revedaEditor/scenes/editorScene|editorScene.py]] — `editorScene` — QGraphicsScene base: edit modes, selection machinery, undo stack, mouse dispatch, grid settings, read-only event filter,…
- [[revedaEditor/scenes/layoutScene|layoutScene.py]] — `layoutScene` — layout editing state: `saveLayoutCell`/`loadDesign`, connectivity + net highlighting, SDL incremental sync, flylines,…
- [[revedaEditor/scenes/schematicScene|schematicScene.py]] — `schematicScene` — wires/pins/labels/instances editing: `saveSchematic`/`loadDesign`, `nameSceneNets`, checks + markers, EIP ghost…
- [[revedaEditor/scenes/symbolScene|symbolScene.py]] — `symbolScene` — symbol drawing editing: `saveSymbolCell`/`loadDesign`, attribute list
