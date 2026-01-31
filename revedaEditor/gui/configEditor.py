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

from PySide6.QtCore import (Qt, )
from PySide6.QtGui import (QAction, QIcon, QStandardItem, QStandardItemModel, )
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGroupBox, QMainWindow,
                               QTableView, QVBoxLayout, QWidget, )

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.gui.editFunctions as edf
import revedaEditor.gui.schematicEditor as sced
import revedaEditor.resources.resources  # noqa: F401


class configEditor(QMainWindow):
    def __init__(self, viewItem: libb.viewItem, libraryDict: dict, libraryView):
        super().__init__()
        self.viewItem = viewItem
        self.libraryDict = libraryDict
        self.libraryView = libraryView
        self.configFilePathObj = viewItem.data(Qt.ItemDataRole.UserRole + 2)
        self.cellItem: libb.cellItem = self.viewItem.parent()
        self.libItem: libb.libraryItem = self.cellItem.parent()
        self.libraryName = self.libItem.libraryName
        self.cellName = self.cellItem.cellName
        self.viewName = self.viewItem.viewName

        self._schViewItem = None
        self._schematicEditor = None
        self._configDict = {}
        app = QApplication.instance()
        if app is not None:
            self.appMainW = app.mainW
            print(self.appMainW.openViews)
        else:
            raise RuntimeError("No QApplication instance found")

        self.setWindowTitle("Edit Config View")
        self.setMinimumSize(600, 700)
        self._createMenuBar()
        self._createActions()
        self._addActions()
        self._createTriggers()

        # Create central widget
        self.centralW = configEditorContainer(self)
        self.setCentralWidget(self.centralW)

    @property
    def configDict(self) -> dict:
        return self._configDict

    @configDict.setter
    def configDict(self, value):
        self._configDict = value
        self._refreshConfigTable()

    @property
    def schViewItem(self) -> libb.viewItem | None:
        return self._schViewItem

    @schViewItem.setter
    def schViewItem(self, value: libb.viewItem):
        self._schViewItem = value

    def loadConfig(self):
        """Load config data from file."""
        try:
            with open(self.viewItem.viewPath) as configFile:
                items = json.load(configFile)

            schematicName = items[1]["reference"]
            self._configDict = items[2]

            self.centralW.libraryNameEdit.setText(self.libraryName)
            self.centralW.cellNameEdit.setText(self.cellName)

            schViewsList = [self.cellItem.child(row).viewName for row in
                            range(self.cellItem.rowCount()) if
                            self.cellItem.child(row).viewType == "schematic"]
            self.centralW.viewNameCB.addItems(schViewsList)
            self.centralW.viewNameCB.setCurrentText(schematicName)

            self.centralW.switchViewsEdit.setText(", ".join(self.appMainW.switchViewList))
            self.centralW.stopViewsEdit.setText(", ".join(self.appMainW.stopViewList))
            configViewNameTuple = ddef.viewTuple(self.libraryName, self.cellName,
                                                 self.viewName)
            if self.appMainW.openViews.get(configViewNameTuple, None):
                self.appMainW.openViews[configViewNameTuple].raise_()
            else:
                self.show()
            self._schViewItem = libm.getViewItem(self.cellItem, schematicName)
            schematicViewNameTuple = ddef.viewTuple(self.libraryName, self.cellName,
                                                    self._schViewItem.viewName)
            if self.appMainW.openViews.get(schematicViewNameTuple):
                self.editorWindow = self.appMainW.openViews[schematicViewNameTuple]
                self.appMainW.openViews[schematicViewNameTuple].raise_()
            else:
                self.editorWindow = sced.schematicEditor(self._schViewItem,
                                                         self.libraryDict, self.libraryView)
                self.editorWindow.loadSchematic()
                self.editorWindow.show()
            self._refreshConfigTable()

        except Exception as e:
            self.appMainW.logger.error(f'Error loading config: {e}')
            self._configDict = {}

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
        self.saveAction.triggered.connect(self.saveCell)

    def updateClick(self):
        newConfigDict = dict()
        if self._schViewItem is not None:
            topSchematicWindow = sced.schematicEditor(self._schViewItem, self.libraryDict,
                                                      self.libraryView, )
        else:
            self.appMainW.logger.error('No schematic view item available')
            return
        topSchematicWindow.loadSchematic()
        topSchematicWindow.createConfigView(self.viewItem, newConfigDict, set())
        self._configDict = newConfigDict
        self._refreshConfigTable()

    def _refreshConfigTable(self):
        self.centralW.confModel = configModel(self.configDict)
        self.centralW.configDictLayout.removeWidget(self.centralW.configViewTable)
        self.centralW.configViewTable = configTable(self.centralW.confModel)
        self.centralW.configDictLayout.addWidget(self.centralW.configViewTable)

    def updateConfigDict(self):
        self.centralW.configViewTable.updateModel()
        self._configDict = dict()
        model = self.centralW.confModel
        for i in range(model.rowCount()):
            viewList = [item.strip() for item in
                        model.itemFromIndex(model.index(i, 3)).text().split(",")]
            self._configDict[model.item(i, 1).text()] = [model.item(i, 0).text(),
                                                         model.item(i, 2).text(),
                                                         viewList, ]

    def saveCell(self):
        # configFilePathObj = self.viewItem.data(Qt.ItemDataRole.UserRole + 2)
        self.updateConfigDict()
        items = list()
        items.insert(0, {"viewName": "config"})
        if self._schViewItem is not None:
            items.insert(1, {"reference": self._schViewItem.viewName})
        else:
            items.insert(1, {"reference": ""})
        items.insert(2, self._configDict)
        with self.configFilePathObj.open(mode="w+") as configFile:
            json.dump(items, configFile, indent=4)

    def checkSaveCell(self):
        self.saveCell()

    def closeEvent(self, event):
        try:
            cellViewNameTuple = ddef.viewTuple(self.libraryName, self.cellName,
                                               self.viewItem.viewName)
            self.appMainW.openViews.pop(cellViewNameTuple, None)
        except Exception as e:
            self.appMainW.logger.error(f"Unexpected error: {e}")
        finally:
            event.accept()
            super().closeEvent(event)


def createNewConfigView(cellItem: libb.cellItem, viewItem: libb.viewItem, dlg,
                        libraryDict: dict, designView, ):
    """Create a new config view from dialog parameters."""
    selectedSchName = dlg.viewNameCB.currentText()
    selectedSchItem = libm.getViewItem(cellItem, selectedSchName)

    schematicWindow = sced.schematicEditor(selectedSchItem, libraryDict, designView, )
    schematicWindow.loadSchematic()
    switchViewList = [viewName.strip() for viewName in dlg.switchViews.text().split(",")]
    stopViewList = [viewName.strip() for viewName in dlg.stopViews.text().split(",")]
    schematicWindow.switchViewList = switchViewList
    schematicWindow.stopViewList = stopViewList

    # clear netlisted cells list
    newConfigDict = dict()  # create an empty newconfig dict
    schematicWindow.createConfigView(viewItem, newConfigDict, set())
    configFilePathObj = viewItem.data(Qt.ItemDataRole.UserRole + 2)
    items = list()
    items.insert(0, {"cellView": "config"})
    items.insert(1, {"reference": selectedSchName})
    items.insert(2, newConfigDict)
    with configFilePathObj.open(mode="w+") as configFile:
        json.dump(items, configFile, indent=4)
    configWindow = configEditor(viewItem, libraryDict, designView)
    configWindow.loadConfig()

    return configWindow


def openConfigEditWindow(schematicItem: libb.viewItem, configItem: libb.viewItem,
                         libraryDict: dict, designView, appMainW, ) -> configEditor:
    """Open an existing config view for editing."""
    schematicName = schematicItem.viewName
    cellItem = schematicItem.parent()
    libItem = cellItem.parent()

    configWindow = configEditor(configItem, libraryDict, designView)
    configWindow.schViewItem = schematicItem
    configWindow.centralW.libraryNameEdit.setText(libItem.libraryName)
    configWindow.centralW.cellNameEdit.setText(cellItem.cellName)

    schViewsList = [cellItem.child(row).viewName for row in range(cellItem.rowCount()) if
                    cellItem.child(row).viewType == "schematic"]
    configWindow.centralW.viewNameCB.addItems(schViewsList)
    configWindow.centralW.viewNameCB.setCurrentText(schematicName)
    configWindow.centralW.switchViewsEdit.setText(", ".join(appMainW.switchViewList))
    configWindow.centralW.stopViewsEdit.setText(", ".join(appMainW.stopViewList))
    configWindow.loadConfig()

    return configWindow


class configEditorContainer(QWidget):
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
        self.confModel = configModel(self.parent.configDict or {})
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
            ["Library", "Cell Name", "View Found", "View To ", "Use"])
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
        self.configModel = model
        self.setModel(self.configModel)
        self.combos = []
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        for row in range(self.configModel.rowCount()):
            combo = QComboBox()
            items = [item.strip() for item in
                     self.configModel.item(row, 3).text().split(",")]
            combo.addItems(items)
            combo.setCurrentText(self.configModel.item(row, 2).text())
            self.setIndexWidget(self.configModel.index(row, 3), combo)
            self.combos.append(combo)

    def updateModel(self):
        for row, combo in enumerate(self.combos):
            self.configModel.setItem(row, 2, QStandardItem(combo.currentText()))
