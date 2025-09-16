#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

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
wireErrorLayer = replace(wireLayer, name="wireError", pcolor=QColor("red"), bcolor= QColor("red"), z=1)
selectedWireLayer = replace(wireLayer, name="selectedWire", pcolor=QColor("blue"), bcolor =
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
schematicPinNameLayer = replace(schematicPinLayer, name="schematicPin", pcolor = QColor(
    'yellow'), bcolor = QColor('yellow'))

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
selectedSchematicPinPen = QPen(
    selectedSchematicPinLayer.pcolor,
    selectedSchematicPinLayer.pwidth,
    selectedSchematicPinLayer.pstyle,
)
textPen = QPen(textLayer.pcolor, textLayer.pwidth, textLayer.pstyle)
selectedTextPen = QPen(
    selectedTextLayer.pcolor, selectedTextLayer.pwidth, selectedTextLayer.pstyle
)
guideLinePen = QPen(guideLineLayer.pcolor, guideLineLayer.pwidth, guideLineLayer.pstyle)
wirePen = QPen(wireLayer.pcolor, wireLayer.pwidth, wireLayer.pstyle)

selectedWirePen = QPen(
    selectedWireLayer.pcolor, selectedWireLayer.pwidth, selectedWireLayer.pstyle
)
stretchWirePen = QPen(QColor("red"), wireLayer.pwidth, wireLayer.pstyle)
errorWirePen = QPen(wireErrorLayer.pcolor, wireErrorLayer.pwidth, wireErrorLayer.pstyle)
ignoreSymbolPen = QPen(
    ignoreSymbolLayer.pcolor, ignoreSymbolLayer.pwidth, ignoreSymbolLayer.pstyle
)
hilightPen = QPen(
    wireHilightLayer.pcolor, wireHilightLayer.pwidth, wireHilightLayer.pstyle
)
otherPen = QPen(otherLayer.pcolor, otherLayer.pwidth, otherLayer.pstyle)
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

