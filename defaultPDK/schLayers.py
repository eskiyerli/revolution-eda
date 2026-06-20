# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

# This module includes all the base definitions for schematic drawings.
from dataclasses import replace

from PySide6.QtCore import (Qt)
from PySide6.QtGui import (QColor, QPen, QBrush)

import revedaEditor.backend.dataDefinitions as ddef

# schematic layers

wireLayer = ddef.edLayer(
    name="wire",
    pcolor=QColor("cyan"),
    pwidth=2,
    pstyle=Qt.SolidLine,
    z=0,
    bcolor=QColor("cyan"),
    bstyle=Qt.SolidPattern,
    visible=True,
    selectable=True,
)
wireErrorLayer = replace(wireLayer, name="wireError", pcolor=QColor("red"),
                         bcolor=QColor("red"), z=1)
selectedWireLayer = replace(wireLayer, name="selectedWire", pcolor=QColor("blue"), bcolor=
QColor("blue"), z=2)
wireHilightLayer = ddef.edLayer(
    name="wireHilightLayer",
    pcolor=QColor("darkMagenta"),
    pwidth=5,
    z=6,
    bcolor=QColor("darkMagenta"),
    bstyle=Qt.SolidPattern,
    visible=True,
    selectable=False,
)
wireProbeLayer = ddef.edLayer(
    name="wireProbeLayer",
    pcolor=QColor("orange"),
    pwidth=5,
    pstyle=Qt.DashLine,
    z=6,
    bcolor=QColor("orange"),
    bstyle=Qt.SolidPattern,
    visible=True,
    selectable=False,
)
guideLineLayer = replace(
    wireLayer, name="guideLine", pcolor=QColor("gray"), pstyle=Qt.DashLine, z=7
)
textLayer = ddef.edLayer(
    name="text", pcolor=QColor("white"), pwidth=1, z=4, visible=True, selectable=True
)

schematicPinLayer = ddef.edLayer(
    name="schematicPin",
    pcolor=QColor("red"),
    pwidth=1,
    z=3,
    bcolor=QColor("red"),
    bstyle=Qt.SolidPattern,
    visible=True,
    selectable=True,
)
selectedSchematicPinLayer = replace(
    schematicPinLayer, name="selectedSchematicPin", pcolor=QColor("yellow"), z=4
)
selectedTextLayer = replace(
    textLayer, name="selectedText", pcolor=QColor("yellow"), z=5
)
schematicPinNameLayer = replace(schematicPinLayer, name="schematicPin", pcolor=QColor(
    'yellow'), bcolor=QColor('yellow'))

ignoreSymbolLayer = ddef.edLayer(
    name="ignoreLayer",
    pcolor=QColor("red"),
    pwidth=5,
    z=6,
    visible=True,
    selectable=False,
)
otherLayer = ddef.edLayer(
    name="otherLayer",
    pcolor=QColor("gray"),
    bcolor=QColor("gray"),
    pwidth=1,
    z=0,
    visible=True,
    selectable=False,
)

draftLayer = ddef.edLayer(
    name="draftLayer",
    pcolor=QColor("gray"),
    pwidth=2,
    z=10,
    bcolor=QColor("gray"),
    bstyle=Qt.DiagCrossPattern,
    visible=True,
    selectable=True,
)
# schematic pens
schematicPinPen = QPen(
    schematicPinLayer.pcolor, schematicPinLayer.pwidth, schematicPinLayer.pstyle
)
schematicPinPen.setCosmetic(True)
selectedSchematicPinPen = QPen(
    selectedSchematicPinLayer.pcolor,
    selectedSchematicPinLayer.pwidth,
    selectedSchematicPinLayer.pstyle,
)
selectedSchematicPinPen.setCosmetic(True)
textPen = QPen(textLayer.pcolor, textLayer.pwidth, textLayer.pstyle)
textPen.setCosmetic(True)
selectedTextPen = QPen(
    selectedTextLayer.pcolor, selectedTextLayer.pwidth, selectedTextLayer.pstyle
)
selectedTextPen.setCosmetic(True)
guideLinePen = QPen(guideLineLayer.pcolor, guideLineLayer.pwidth, guideLineLayer.pstyle)
guideLinePen.setCosmetic(True)
wirePen = QPen(wireLayer.pcolor, wireLayer.pwidth, wireLayer.pstyle)
wirePen.setCosmetic(True)

selectedWirePen = QPen(
    selectedWireLayer.pcolor, selectedWireLayer.pwidth, selectedWireLayer.pstyle
)
selectedWirePen.setCosmetic(True)
stretchWirePen = QPen(QColor("red"), wireLayer.pwidth, wireLayer.pstyle)
stretchWirePen.setCosmetic(True)
errorWirePen = QPen(wireErrorLayer.pcolor, wireErrorLayer.pwidth, wireErrorLayer.pstyle)
errorWirePen.setCosmetic(True)
ignoreSymbolPen = QPen(
    ignoreSymbolLayer.pcolor, ignoreSymbolLayer.pwidth, ignoreSymbolLayer.pstyle
)
ignoreSymbolPen.setCosmetic(True)
hilightPen = QPen(
    wireHilightLayer.pcolor, wireHilightLayer.pwidth, wireHilightLayer.pstyle
)
hilightPen.setCosmetic(True)
probePens = []
_probeColors = [
    QColor("orange"),
    QColor("cyan"),
    QColor("lime"),
    QColor("magenta"),
    QColor("yellow"),
    QColor("red"),
    QColor("deepskyblue"),
    QColor("hotpink"),
]
for _c in _probeColors:
    _p = QPen(_c, wireProbeLayer.pwidth, wireProbeLayer.pstyle)
    _p.setCosmetic(True)
    probePens.append(_p)
otherPen = QPen(otherLayer.pcolor, otherLayer.pwidth, otherLayer.pstyle)
otherPen.setCosmetic(True)
draftPen = QPen(draftLayer.pcolor, draftLayer.pwidth, draftLayer.pstyle)
draftPen.setCosmetic(True)

# schematic brushes
schematicPinBrush = QBrush(schematicPinLayer.bcolor, schematicPinLayer.bstyle)
wireBrush = QBrush(wireLayer.bcolor, wireLayer.bstyle)
selectedWireBrush = QBrush(selectedWireLayer.bcolor, selectedWireLayer.bstyle)
errorWireBrush = QBrush(wireErrorLayer.bcolor, wireErrorLayer.bstyle)
selectedSchematicPinBrush = QBrush(
    selectedSchematicPinLayer.bcolor, selectedSchematicPinLayer.bstyle
)
otherBrush = QBrush(otherLayer.bcolor, otherLayer.bstyle)
draftBrush = QBrush(draftLayer.bcolor, draftLayer.bstyle)

# crossing dot diameter
crossingDotDiameter = 2
