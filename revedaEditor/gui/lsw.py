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
import os
import pathlib
from pathlib import Path

import numpy as np
from PySide6.QtCore import (Signal, Qt, QModelIndex)
from PySide6.QtGui import (
    QPainter,
    QStandardItemModel,
    QStandardItem,
    QBrush,
    QColor,
    QPixmap,
    QImage,
)
from PySide6.QtWidgets import (QTableView, QStyledItemDelegate,
                               QStyle)

from revedaEditor.backend.pdkLoader import importPDKModule

fabproc = importPDKModule('process')
laylyr = importPDKModule('layoutLayers')


class layerDataModel(QStandardItemModel):
    _file_content_cache = {}
    _pixmap_cache = {}

    def __init__(self, data: list):
        super().__init__()
        self._data = data or []
        self.setColumnCount(5)  # Set the number of columns

        # Set the headers for the columns
        self.setHeaderData(0, Qt.Orientation.Horizontal, "")
        self.setHeaderData(1, Qt.Orientation.Horizontal, "Layer")
        self.setHeaderData(2, Qt.Orientation.Horizontal, "Purp.")
        self.setHeaderData(3, Qt.Orientation.Horizontal, "V")
        self.setHeaderData(4, Qt.Orientation.Horizontal, "S")

        for row, layer in enumerate(self._data):
            self.insertRow(row)
            # bitmap = QBitmap.fromImage(QPixmap(layer.btexture).scaled(5, 5).toImage())
            reveda_pdk_path = os.environ.get("REVEDA_PDK_PATH", None)
            if reveda_pdk_path is None:
                reveda_pdk_pathobj = Path(__file__).parents[2].joinpath(
                    "defaultPDK")
            else:
                reveda_pdk_pathobj = pathlib.Path(reveda_pdk_path)

            texturePath = reveda_pdk_pathobj.joinpath(layer.btexture)
            _pixmap = QPixmap.fromImage(self.createImage(texturePath,
                                                         layer.bcolor, 1))
            # Create a brush with black background
            brush = QBrush(QColor('black'))
            # Set the texture pattern over the black background
            brush.setTexture(_pixmap)
            item = QStandardItem()
            item.setBackground(brush)
            self.setItem(row, 0, item)
            self.setItem(row, 1, QStandardItem(layer.name))
            self.setItem(row, 2, QStandardItem(layer.purpose))
            item = QStandardItem()
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if layer.selectable else Qt.CheckState.Unchecked)
            self.setItem(row, 3, item)
            item = QStandardItem()
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if layer.visible else Qt.CheckState.Unchecked)
            self.setItem(row, 4, item)

    def createData(self, layerlist: list) -> list:
        [
            self._data.append(
                (
                    layer.name,
                    layer.visible,
                    layer.selectable,
                    layer.btexture,
                    layer.bcolor,
                )
            )
            for layer in layerlist
        ]

    @classmethod
    def readFileContent(cls, filePath):
        if filePath not in cls._file_content_cache:
            try:
                with open(filePath, "r") as file:
                    cls._file_content_cache[filePath] = file.read()
            except FileNotFoundError:
                print(f"Error: Stipple not found: {filePath}")
                return ""
            except Exception as e:
                print(f"Error reading Stipple file {filePath}: {e}")
                return ""
        return cls._file_content_cache[filePath]

    @classmethod
    def createImage(cls, filePath: Path, color: QColor, scale: int = 1):
        content = cls.readFileContent(str(filePath))

        # Use numpy's loadtxt for faster parsing of text data
        data = np.loadtxt(content.splitlines(), dtype=np.uint8)

        # Scale up the pattern by repeating each pixel
        data_scaled = np.repeat(np.repeat(data, scale, axis=0), scale, axis=1)

        height, width = data_scaled.shape

        # Create QImage with Format_ARGB32 (not premultiplied)
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        # Fill with transparent pixels first
        image.fill(Qt.black)

        # Create painter to draw on the image
        painter = QPainter(image)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))

        # Draw solid rectangles for each pixel that should be colored
        for i in range(height):
            for j in range(width):
                if data_scaled[i, j] == 1:  # Draw colored pixel
                    painter.drawRect(j, i, 1, 1)

        painter.end()
        return image


class TextureDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 0 and option.state & QStyle.State_Selected:
            # Get the original brush from the model
            brush = index.data(Qt.BackgroundRole)
            if brush:
                # Create a semi-transparent version
                painter.fillRect(option.rect, brush)
                # Add selection overlay with transparency
                selectionColor = option.palette.highlight().color()
                selectionColor.setAlpha(100)  # Adjust alpha as needed
                painter.fillRect(option.rect, selectionColor)
            return
        super().paint(painter, option, index)


class layerViewTable(QTableView):
    columnTexture = 0
    columnName = 1
    columnPurpose = 2
    columnVisible = 3
    columnSelectable = 4

    dataSelected = Signal(str, str)
    layerSelectable = Signal(str, str, bool)
    layerVisible = Signal(str, str, bool)

    def __init__(self, parent=None, model: layerDataModel = None):
        super().__init__(parent)
        self._model = model
        self.parent = parent
        self.layoutScene = self.parent.scene
        self.setModel(self._model)

        self.setupUi()
        self.connectSignals()

    def setupUi(self):
        """Initialize UI components"""
        self.selectedRow: int = -1
        self.resizeColumnsToContents()
        self.setShowGrid(False)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        # Set custom delegate for texture column
        self.setItemDelegateForColumn(self.columnTexture, TextureDelegate(self))

    def connectSignals(self):
        """Connect signal handlers"""
        self._model.dataChanged.connect(self.onDataChanged)
        self.clicked.connect(self.onClicked)

    def getLayerInfo(self, row: int) -> tuple[str, str]:
        """Helper method to get layer name and purpose"""
        return (
            self._model.item(row, self.columnName).text(),
            self._model.item(row, self.columnPurpose).text()
        )

    def onDataChanged(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: list):
        if Qt.ItemDataRole.CheckStateRole not in roles:
            return

        row, column = topLeft.row(), topLeft.column()
        item = self._model.item(row, column)
        isChecked = item.checkState() == Qt.CheckState.Checked
        layerName, layerPurpose = self.getLayerInfo(row)

        if column == self.columnSelectable:
            self.layerSelectable.emit(layerName, layerPurpose, isChecked)
        elif column == self.columnVisible:
            self.layerVisible.emit(layerName, layerPurpose, isChecked)

    def onClicked(self, index):
        """Handle mouse clicks on the table"""
        # The index comes from the view's current model which may be a proxy.
        # Map through the proxy (if any) to get the source-model row.
        sourceIndex = index
        proxyModel = self.model()
        if hasattr(proxyModel, "mapToSource"):
            sourceIndex = proxyModel.mapToSource(index)
        row = sourceIndex.row()

        # Get layer info and emit selection
        layerName, layerPurpose = self.getLayerInfo(row)
        self.dataSelected.emit(layerName, layerPurpose)

    def onSelectionChanged(self, selected, deselected):
        if selected.indexes():
            indices = selected.indexes()
            # Get the first selected index to determine the row
            firstIndex = indices[0]
            # Map through proxy model if present
            proxyModel = self.model()
            if hasattr(proxyModel, "mapToSource"):
                firstIndex = proxyModel.mapToSource(firstIndex)
            row = firstIndex.row()
            
            # Get the layer name and purpose from the correct columns
            layerNameIndex = self._model.index(row, self.columnName)
            layerPurposeIndex = self._model.index(row, self.columnPurpose)
            
            layerName = self._model.data(layerNameIndex)
            layerPurpose = self._model.data(layerPurposeIndex)
            
            self.dataSelected.emit(layerName, layerPurpose)

    def updateAllLayers(self, visible: bool = None, selectable: bool = None):
        """Helper method to update all layers' visibility or selectability"""
        if visible is not None:
            state, column = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked, self.columnVisible
            for layer in laylyr.pdkAllLayers:
                layer.visible = visible
        else:
            state, column = Qt.CheckState.Checked if selectable else Qt.CheckState.Unchecked, self.columnSelectable
            for layer in laylyr.pdkAllLayers:
                layer.selectable = selectable
            # Update scene items selectability
            for item in self.layoutScene.items():
                if item.parentItem() is None and hasattr(item, 'layer'):
                    item.setEnabled(selectable)

        for row in range(self._model.rowCount()):
            self._model.item(row, column).setCheckState(state)

    def noLayersVisible(self):
        self.updateAllLayers(visible=False)

    def allLayersVisible(self):
        self.updateAllLayers(visible=True)

    def noLayersSelectable(self):
        self.updateAllLayers(selectable=False)

    def allLayersSelectable(self):
        self.updateAllLayers(selectable=True)
