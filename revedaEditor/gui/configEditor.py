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

import json

# import numpy as np
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QMainWindow,
    QTableView,
    QVBoxLayout,
    QWidget,
)

import revedaEditor.resources.resources
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.gui.editFunctions as edf
import revedaEditor.gui.schematicEditor as sced
import revedaEditor.backend.libBackEnd as libb

# from hashlib import new


class configViewEdit(QMainWindow):
    def __init__(self, appMainW: QMainWindow, schViewItem: libb.viewItem, configDict: dict, viewItem: libb.viewItem):
        super().__init__()
        self.appMainW = appMainW  # app mainwindow
        self.schViewItem = schViewItem
        self.configDict = configDict
        self.viewItem = viewItem
        self.configFilePathObj = viewItem.data(Qt.UserRole + 2)

        self.setWindowTitle("Edit Config View")
        self.setMinimumSize(500, 600)
        self._createMenuBar()
        self._createActions()
        self._addActions()
        self._createTriggers()
        self.centralWidget = configViewEditContainer(self)
        self.setCentralWidget(self.centralWidget)

    def _createMenuBar(self):
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)  # for mac
        self.fileMenu = self.mainMenu.addMenu("&File")
        self.editMenu = self.mainMenu.addMenu("&Edit")
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _createActions(self):
        updateIcon = QIcon(":/icons/arrow-circle.png")
        self.updateAction = QAction(updateIcon, "Update", self)
        saveIcon = QIcon(":/icons/database--plus.png")
        self.saveAction = QAction(saveIcon, "Save", self)

    def _addActions(self):
        self.fileMenu.addAction(self.updateAction)
        self.fileMenu.addAction(self.saveAction)

    def _createTriggers(self):
        self.updateAction.triggered.connect(self.updateClick)
        self.saveAction.triggered.connect(self.saveClick)

    def updateClick(self):
        newConfigDict = self.updateConfigDict()
        if self.appMainW.libraryBrowser is None:
            self.appMainW.createLibraryBrowser()
        topSchematicWindow = sced.schematicEditor(
            self.schViewItem,
            self.appMainW.libraryDict,
            self.appMainW.libraryBrowser.libBrowserCont.designView,
        )
        topSchematicWindow.loadSchematic()
        topSchematicWindow.createConfigView(
            self.viewItem,
            self.configDict,
            newConfigDict,
            topSchematicWindow.processedCells,
        )
        self.configDict = newConfigDict

        self.centralWidget.confModel = configModel(self.configDict)
        # self.centralWidget.configDictGroup.setVisible(False)
        self.centralWidget.configDictLayout.removeWidget(
            self.centralWidget.configViewTable
        )
        self.centralWidget.configViewTable = configTable(self.centralWidget.confModel)
        self.centralWidget.configDictLayout.addWidget(
            self.centralWidget.configViewTable
        )

    def updateConfigDict(self):
        self.centralWidget.configViewTable.updateModel()
        self.configDict = dict()
        newConfigDict = dict()
        model = self.centralWidget.confModel
        for i in range(model.rowCount()):
            viewList = [
                item.strip()
                for item in model.itemFromIndex(model.index(i, 3)).text().split(",")
            ]
            self.configDict[model.item(i, 1).text()] = [
                model.item(i, 0).text(),
                model.item(i, 2).text(),
                viewList,
            ]
        return newConfigDict

    def saveClick(self):
        # configFilePathObj = self.viewItem.data(Qt.UserRole + 2)
        self.updateConfigDict()
        items = list()
        items.insert(0, {"viewName": "config"})
        items.insert(1, {"reference": self.schViewItem.viewName})
        items.insert(2, self.configDict)
        with self.configFilePathObj.open(mode="w+") as configFile:
            json.dump(items, configFile, indent=4)

    def closeEvent(self, event):
        try:
            cellViewTuple = ddef.viewTuple(
                self.viewItem.parent().parent().libraryName,
                self.viewItem.parent().cellName,
                self.viewItem.viewName,
            )
            self.appMainW.openViews.pop(cellViewTuple, None)
        except Exception as e:
            self.appMainW.logger.error(f"Unexpected error: {e}")
        finally:
            event.accept()
            super().closeEvent(event)

class configViewEditContainer(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.mainLayout = QVBoxLayout()
        topCellGroup = QGroupBox("Top Cell")
        topCellLayout = QFormLayout()
        self.libraryNameEdit = edf.longLineEdit()
        topCellLayout.addRow(edf.boldLabel("Library:"), self.libraryNameEdit)
        self.cellNameEdit = edf.longLineEdit()
        topCellLayout.addRow(edf.boldLabel("Cell:"), self.cellNameEdit)
        self.viewNameCB = QComboBox()
        topCellLayout.addRow(edf.boldLabel("View:"), self.viewNameCB)
        topCellGroup.setLayout(topCellLayout)
        self.mainLayout.addWidget(topCellGroup)
        viewGroup = QGroupBox("Switch/Stop Views")
        viewGroupLayout = QFormLayout()
        viewGroup.setLayout(viewGroupLayout)
        self.switchViewsEdit = edf.longLineEdit()
        viewGroupLayout.addRow(edf.boldLabel("View List:"), self.switchViewsEdit)
        self.stopViewsEdit = edf.longLineEdit()
        viewGroupLayout.addRow(edf.boldLabel("Stop List:"), self.stopViewsEdit)
        self.mainLayout.addWidget(viewGroup)
        self.configDictGroup = QGroupBox("Cell View Configuration")
        self.confModel = configModel(self.parent.configDict)
        self.configDictLayout = QVBoxLayout()
        self.configViewTable = configTable(self.confModel)
        self.configDictLayout.addWidget(self.configViewTable)
        self.configDictGroup.setLayout(self.configDictLayout)
        self.mainLayout.addWidget(self.configDictGroup)
        self.setLayout(self.mainLayout)


class configModel(QStandardItemModel):
    def __init__(self, configDict: dict):
        row = len(configDict.keys())
        column = 4
        super().__init__(row, column)
        self.setHorizontalHeaderLabels(
            ["Library", "Cell Name", "View Found", "View To ", "Use"]
        )
        for i, (k, v) in enumerate(configDict.items()):
            item = QStandardItem(v[0])
            self.setItem(i, 0, item)
            item = QStandardItem(k)
            self.setItem(i, 1, item)
            item = QStandardItem(v[1])
            self.setItem(i, 2, item)
            item = QStandardItem(", ".join(v[2]))
            self.setItem(i, 3, item)


class configTable(QTableView):
    def __init__(self, model: configModel):
        super().__init__()
        self.model = model
        self.setModel(self.model)
        self.combos = list()
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setEditTriggers(QTableView.NoEditTriggers)
        for row in range(self.model.rowCount()):
            self.combos.append(QComboBox())
            items = [
                item.strip()
                for item in self.model.itemFromIndex(self.model.index(row, 3))
                .text()
                .split(",")
            ]
            self.combos[-1].addItems(items)
            self.combos[-1].setCurrentText(
                self.model.itemFromIndex(self.model.index(row, 2)).text()
            )
            self.setIndexWidget(self.model.index(row, 3), self.combos[-1])

    def updateModel(self):
        for row in range(self.model.rowCount()):
            item = QStandardItem(self.combos[row].currentText())
            self.model.setItem(row, 2, item)
