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


from dataclasses import replace

from PySide6.QtCore import (Qt)
from PySide6.QtGui import (QColor, QPen, QBrush)

import revedaEditor.backend.dataDefinitions as ddef

# These layers are builtin layers that are used to create schematic and symbols
# layers are not real layers to draw on but a collection of attributes that a particular
# class of shapes can inherit from.

symbolLayer = ddef.edLayer(name="symbol", pcolor=QColor("green"), pwidth=4, z=2,
                           pstyle=Qt.SolidLine, visible=True, selectable=True)
stretchSymbolLayer = replace(symbolLayer, name="stretchSymbol", pcolor=QColor("red"), z=2)
selectedSymbolLayer = replace(symbolLayer, name="selectedSymbol", pcolor=QColor("blue"),
                              z=3)

symbolPinLayer = ddef.edLayer(name="symbolPin", pcolor=QColor("red"), pwidth=1, z=2,
                              bcolor=QColor("red"), bstyle=Qt.SolidPattern, visible=True,
                              selectable=True)

selectedSymbolPinLayer = replace(symbolPinLayer, name="selectedSymbolPin",
                                 pcolor=QColor("yellow"), z=4)

labelLayer = ddef.edLayer(name="label", pcolor=QColor(255, 255, 153), pwidth=1, z=5,
                          bcolor=QColor(Qt.yellow), bstyle=Qt.SolidPattern,
                          visible=True,
                          selectable=True)
selectedLabelLayer = replace(labelLayer, name="selectedLabel", pcolor=QColor("yellow"), z=6,
                             bcolor=QColor(204, 204, 0))
draftLayer = replace(symbolLayer, pcolor=QColor("gray"), bcolor=QColor("gray"), z=0)

# Symbol Pens
symbolPen = QPen(symbolLayer.pcolor, symbolLayer.pwidth, symbolLayer.pstyle)
symbolPen.setCosmetic(True)
stretchSymbolPen = QPen(stretchSymbolLayer.pcolor, stretchSymbolLayer.pwidth,
                        stretchSymbolLayer.pstyle)
selectedSymbolPen = QPen(selectedSymbolLayer.pcolor, selectedSymbolLayer.pwidth,
                         selectedSymbolLayer.pstyle)

symbolPinPen = QPen(symbolPinLayer.pcolor, symbolPinLayer.pwidth, symbolPinLayer.pstyle)

selectedSymbolPinPen = QPen(selectedSymbolPinLayer.pcolor, selectedSymbolPinLayer.pwidth,
                            selectedSymbolPinLayer.pstyle)

labelPen = QPen(labelLayer.pcolor, labelLayer.pwidth, labelLayer.pstyle)
selectedLabelPen = QPen(selectedLabelLayer.pcolor, selectedLabelLayer.pwidth,
                        selectedLabelLayer.pstyle)
draftPen = QPen(draftLayer.pcolor, draftLayer.pwidth, draftLayer.pstyle)
defaultPen = QPen(draftLayer.pcolor, draftLayer.pwidth, draftLayer.pstyle)

# Brushes
symbolBrush = QBrush(symbolLayer.bcolor, symbolLayer.bstyle)
symbolPinBrush = QBrush(symbolPinLayer.bcolor, symbolPinLayer.bstyle)

selectedSymbolBrush = QBrush(selectedSymbolLayer.bcolor, selectedSymbolLayer.bstyle)

selectedSymbolPinBrush = QBrush(selectedSymbolPinLayer.bcolor,
                                selectedSymbolPinLayer.bstyle)
draftBrush = QBrush(draftLayer.bcolor, draftLayer.bstyle)
labelBrush = QBrush(labelLayer.bcolor, labelLayer.bstyle)
selectedLabelBrush = QBrush(selectedLabelLayer.bcolor, selectedLabelLayer.bstyle)
