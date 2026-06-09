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
            self.appMainW = app.appMainW
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
        self.centralW.viewNameCB.currentTextChanged.connect(self._onViewChanged)

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

    def _onViewChanged(self, viewName: str):
        """React to a different view being selected in the top-cell combo."""
        self._schViewItem = libm.getViewItem(self.cellItem, viewName)
        if self._schViewItem is None:
            self.configDict = {}
            return
        if self._schViewItem.viewType != "schematic":
            self.configDict = {}
            return
        # Schematic selected – rebuild the instance config table.
        newConfigDict = dict()
        schTuple = ddef.viewNameTuple(self.libraryName, self.cellName,
                                      self._schViewItem.viewName)
        existingEditor = self.appMainW.openViews.get(schTuple)
        if existingEditor is not None:
            existingEditor.createConfigView(self.viewItem, newConfigDict, set(), {})
        else:
            tempSchematic = sced.schematicEditor(self._schViewItem, self.libraryDict,
                                               self.libraryView)
            try:
                tempSchematic.loadSchematic()
                tempSchematic.createConfigView(self.viewItem, newConfigDict, set(), {})
            finally:
                if self.appMainW.openViews.get(schTuple) is tempSchematic:
                    self.appMainW.openViews.pop(schTuple, None)
                tempSchematic.close()
        self.configDict = newConfigDict

    def loadConfig(self):
        """Load config data from file."""
        try:
            with open(self.viewItem.viewPath) as configFile:
                items = json.load(configFile)

            schematicName = items[1]["reference"]
            self.configDict = items[2]

            self.centralW.libraryNameEdit.setText(self.libraryName)
            self.centralW.cellNameEdit.setText(self.cellName)

            schematicViewsList = [self.cellItem.child(row).viewName for row in
                            range(self.cellItem.rowCount()) if self.cellItem.child(row).viewType == "schematic"]
            self.centralW.viewNameCB.blockSignals(True)
            self.centralW.viewNameCB.clear()
            self.centralW.viewNameCB.addItems(schematicViewsList)
            self.centralW.viewNameCB.setCurrentText(schematicName)
            self.centralW.viewNameCB.blockSignals(False)

            self.centralW.switchViewsEdit.setText(", ".join(self.appMainW.switchViewList))
            self.centralW.stopViewsEdit.setText(", ".join(self.appMainW.stopViewList))
            self._schViewItem = libm.getViewItem(self.cellItem, schematicName)
            if self._schViewItem.viewType == "schematic":
                schematicViewNameTuple = ddef.viewNameTuple(
                    self.libraryName, self.cellName, self._schViewItem.viewName)
                if self.appMainW.openViews.get(schematicViewNameTuple):
                    self.editorWindow = self.appMainW.openViews[schematicViewNameTuple]
                    self.appMainW.openViews[schematicViewNameTuple].raise_()
                else:
                    self.editorWindow = sced.schematicEditor(self._schViewItem,
                                                             self.libraryDict, self.libraryView)
                    self.editorWindow.loadSchematic()
                    self.editorWindow.show()
            else:
                self.configDict = {}
            self._refreshConfigTable()

        except Exception as e:
            self.appMainW.logger.error(f'Error loading config: {e}')
            self.configDict = {}

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
        if self._schViewItem is None:
            self.appMainW.logger.error('No schematic view item available')
            return
        if self._schViewItem.viewType != "schematic":
            self.configDict = {}
            return

        # Save current user selections
        self.updateConfigDict()
        savedSelections = {cellName: values[1] for cellName, values in self._configDict.items()}

        newConfigDict = dict()
        schTuple = ddef.viewNameTuple(self.libraryName, self.cellName,
                                      self._schViewItem.viewName)
        existingEditor = self.appMainW.openViews.get(schTuple)
        if existingEditor is not None:
            existingEditor.createConfigView(self.viewItem, newConfigDict, set(), savedSelections)
        else:
            tempSchematic = sced.schematicEditor(self._schViewItem, self.libraryDict,
                                                   self.libraryView)
            try:
                tempSchematic.loadSchematic()
                tempSchematic.createConfigView(self.viewItem, newConfigDict, set(), savedSelections)
            finally:
                if self.appMainW.openViews.get(schTuple) is tempSchematic:
                    self.appMainW.openViews.pop(schTuple, None)
                tempSchematic.close()

        self.configDict = newConfigDict

    def _refreshConfigTable(self):
        oldTable = self.centralW.configViewTable
        self.centralW.confModel = configModel(self.configDict)
        self.centralW.configViewTable = configTable(self.centralW.confModel, self.centralW)
        self.centralW.configDictLayout.removeWidget(oldTable)
        oldTable.deleteLater()
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
        items.insert(0, {"viewType": "config"})
        if self._schViewItem is not None:
            items.insert(1, {"reference": self._schViewItem.viewName})
        else:
            items.insert(1, {"reference": ""})
        items.insert(2, self._configDict)
        with self.configFilePathObj.open(mode="w+") as configFile:
            json.dump(items, configFile, indent=4)


def openConfigEditWindow(schematicItem: libb.viewItem, configItem: libb.viewItem,
                         libraryDict: dict, designView, ) -> configEditor:
    """Open an existing config view for editing."""
    configWindow = configEditor(configItem, libraryDict, designView)
    configWindow.schViewItem = schematicItem
    configWindow.loadConfig()
    return configWindow


    def closeEvent(self, event):
        try:
            cellViewNameTuple = ddef.viewNameTuple(self.libraryName, self.cellName,
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
    items.insert(0, {"viewType": "config"})
    items.insert(1, {"reference": selectedSchName})
    items.insert(2, newConfigDict)
    with configFilePathObj.open(mode="w+") as configFile:
        json.dump(items, configFile, indent=4)
    configWindow = configEditor(viewItem, libraryDict, designView)
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
        self.configViewTable = configTable(self.confModel, self)
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
            ["Library", "Cell Name", "View Found", "View To Use"])
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
    def __init__(self, model: configModel, parentContainer):
        super().__init__()
        self.configModel = model
        self.parentContainer = parentContainer
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
            combo.currentTextChanged.connect(lambda text, r=row: self._onComboChanged(r, text))
            self.setIndexWidget(self.configModel.index(row, 3), combo)
            self.combos.append(combo)

    def _onComboChanged(self, row: int, viewName: str):
        """Remove child instance rows when non-schematic view is selected."""
        if viewName == "schematic":
            return
        
        cellName = self.configModel.item(row, 1).text()
        libraryName = self.configModel.item(row, 0).text()
        
        # Get the parent editor
        parentEditor = self.parentContainer.parent
        if not hasattr(parentEditor, '_schViewItem') or parentEditor._schViewItem is None:
            return
            
        # Find all cells that would be instantiated by this cell
        childCells = self._findChildCells(libraryName, cellName, parentEditor)
        
        # Remove rows for child cells in reverse order
        rowsToRemove = []
        for r in range(self.configModel.rowCount()):
            if r != row:
                rCellName = self.configModel.item(r, 1).text()
                if rCellName in childCells:
                    rowsToRemove.append(r)
        
        for r in sorted(rowsToRemove, reverse=True):
            self.configModel.removeRow(r)
            self.combos.pop(r)
    
    def _findChildCells(self, libraryName: str, cellName: str, parentEditor) -> set:
        """Find all cells that are instantiated within the given cell."""
        childCells = set()
        try:
            libItem = libm.getLibItem(parentEditor.libraryView.libraryModel, libraryName)
            if not libItem:
                return childCells
            cellItem = libm.getCellItem(libItem, cellName)
            if not cellItem:
                return childCells
            
            # Find schematic view of this cell
            schViewItem = None
            for row in range(cellItem.rowCount()):
                viewItem = cellItem.child(row)
                if viewItem.viewType == "schematic":
                    schViewItem = viewItem
                    break
            
            if not schViewItem:
                return childCells
            
            # Load the schematic and find all instantiated cells
            schTuple = ddef.viewNameTuple(libraryName, cellName, schViewItem.viewName)
            existingEditor = parentEditor.appMainW.openViews.get(schTuple)
            
            if existingEditor:
                sceneSymbolSet = existingEditor.centralW.scene.findSceneSymbolSet()
                for item in sceneSymbolSet:
                    childCells.add(item.cellName)
            else:
                # Create temporary editor to read hierarchy
                tempSchematic = sced.schematicEditor(schViewItem, parentEditor.libraryDict,
                                                    parentEditor.libraryView)
                try:
                    tempSchematic.loadSchematic()
                    sceneSymbolSet = tempSchematic.centralW.scene.findSceneSymbolSet()
                    for item in sceneSymbolSet:
                        childCells.add(item.cellName)
                finally:
                    if parentEditor.appMainW.openViews.get(schTuple) is tempSchematic:
                        parentEditor.appMainW.openViews.pop(schTuple, None)
                    tempSchematic.close()
        except Exception as e:
            parentEditor.appMainW.logger.error(f"Error finding child cells: {e}")
        
        return childCells

    def updateModel(self):
        for row, combo in enumerate(self.combos):
            self.configModel.setItem(row, 2, QStandardItem(combo.currentText()))
