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
from typing import ClassVar

from PySide6.QtGui import (QAction, QIcon, QStandardItem, QStandardItemModel, )
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGroupBox, QHeaderView,
                               QMainWindow, QTableView, QVBoxLayout, QWidget, )

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
        self.configFilePathObj = self.viewItem.viewPath
        self.cellItem: libb.cellItem = self.viewItem.parent()
        self.libItem: libb.libraryItem = self.cellItem.parent()
        self.libraryName = self.libItem.libraryName
        self.cellName = self.cellItem.cellName
        self.viewName = self.viewItem.viewName

        self._schViewItem = None
        self.editorWindow = None
        self._configDict = {}
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance found")
        self.appMainW = app.appMainW

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

    @staticmethod
    def _splitViewList(text: str) -> list:
        """Parse a comma-separated view list, dropping empty entries."""
        return [viewName.strip() for viewName in text.split(",") if viewName.strip()]

    def _uiSwitchViews(self) -> list:
        return self._splitViewList(self.centralW.switchViewsEdit.text())

    def _uiStopViews(self) -> list:
        return self._splitViewList(self.centralW.stopViewsEdit.text())

    def _configFromView(self, schViewItem: libb.viewItem | None,
                        savedSelections: dict) -> dict:
        """Run createConfigView on a schematic view item.

        Reuses an already-open editor when possible (restoring its own
        switch/stop lists afterwards); otherwise builds a temporary editor that
        is never registered in openViews and is deleted without saving.
        """
        newConfigDict = {}
        if schViewItem is None or schViewItem.viewType != "schematic":
            return newConfigDict
        cellItem = schViewItem.parent()
        libItem = cellItem.parent()
        schTuple = ddef.viewNameTuple(libItem.libraryName, cellItem.cellName,
                                      schViewItem.viewName)
        switchViews = self._uiSwitchViews()
        stopViews = self._uiStopViews()
        existingEditor = self.appMainW.openViews.get(schTuple)
        if existingEditor is not None:
            prevSwitch = existingEditor.switchViewList
            prevStop = existingEditor.stopViewList
            try:
                existingEditor.switchViewList = switchViews
                existingEditor.stopViewList = stopViews
                existingEditor.createConfigView(newConfigDict, set(), savedSelections)
            finally:
                existingEditor.switchViewList = prevSwitch
                existingEditor.stopViewList = prevStop
        else:
            tempSchematic = sced.schematicEditor(schViewItem, self.libraryDict,
                                                 self.libraryView)
            try:
                tempSchematic.switchViewList = switchViews
                tempSchematic.stopViewList = stopViews
                tempSchematic.loadSchematic(register=False)
                tempSchematic.createConfigView(newConfigDict, set(), savedSelections)
            finally:
                tempSchematic.deleteLater()
        return newConfigDict

    def _openSchematicView(self):
        """Ensure the referenced top schematic editor exists and is visible."""
        if self._schViewItem is None or self._schViewItem.viewType != "schematic":
            self.editorWindow = None
            return
        schTuple = ddef.viewNameTuple(self.libraryName, self.cellName,
                                      self._schViewItem.viewName)
        existingEditor = self.appMainW.openViews.get(schTuple)
        if existingEditor is not None:
            self.editorWindow = existingEditor
            existingEditor.show()
            existingEditor.raise_()
            return
        self.editorWindow = sced.schematicEditor(self._schViewItem, self.libraryDict,
                                                 self.libraryView)
        self.editorWindow.switchViewList = self._uiSwitchViews()
        self.editorWindow.stopViewList = self._uiStopViews()
        self.editorWindow.loadSchematic()
        self.editorWindow.show()

    def _onViewChanged(self, viewName: str):
        """React to a different view being selected in the top-cell combo."""
        self._schViewItem = libm.getViewItem(self.cellItem, viewName)
        self._openSchematicView()
        self.configDict = self._configFromView(self._schViewItem, {})

    def loadConfig(self):
        """Load config data from file."""
        try:
            with self.configFilePathObj.open(mode="r") as configFile:
                items = json.load(configFile)

            header = items[1] if len(items) > 1 else {}
            schematicViewName = header.get("reference", "")
            # Per-config switch/stop lists; fall back to app defaults for
            # config files written before these keys existed.
            switchViews = header.get("switchViews") or self.appMainW.switchViewList
            stopViews = header.get("stopViews") or self.appMainW.stopViewList
            self._configDict = items[2] if len(items) > 2 else {}

            self.centralW.libraryNameEdit.setText(self.libraryName)
            self.centralW.cellNameEdit.setText(self.cellName)

            schematicViewsList = [self.cellItem.child(row).viewName for row in
                                  range(self.cellItem.rowCount()) if
                                  self.cellItem.child(row).viewType == "schematic"]
            viewCB = self.centralW.viewNameCB
            viewCB.blockSignals(True)
            viewCB.clear()
            viewCB.addItems(schematicViewsList)
            if schematicViewName in schematicViewsList:
                viewCB.setCurrentText(schematicViewName)
            viewCB.blockSignals(False)

            self.centralW.switchViewsEdit.setText(", ".join(switchViews))
            self.centralW.stopViewsEdit.setText(", ".join(stopViews))

            self._schViewItem = libm.getViewItem(self.cellItem, schematicViewName)
            if self._schViewItem is None:
                self.appMainW.logger.warning(
                    f"Config reference '{schematicViewName}' not found in "
                    f"{self.libraryName}/{self.cellName}")
            self._openSchematicView()
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
        # Preserve the views currently selected in the table.
        self.updateConfigDict()
        savedSelections = {cellName: values[1] for cellName, values in
                           self._configDict.items()}
        self.configDict = self._configFromView(self._schViewItem, savedSelections)

    def _refreshConfigTable(self):
        oldTable = self.centralW.configViewTable
        self.centralW.confModel = configModel(self.configDict)
        self.centralW.configViewTable = configTable(self.centralW.confModel,
                                                    self.centralW)
        self.centralW.configDictLayout.removeWidget(oldTable)
        oldTable.deleteLater()
        self.centralW.configDictLayout.addWidget(self.centralW.configViewTable)

    def updateConfigDict(self):
        self.centralW.configViewTable.updateModel()
        newConfigDict = {}
        model = self.centralW.confModel
        for row in range(model.rowCount()):
            libItem = model.item(row, 0)
            cellItem = model.item(row, 1)
            viewItem = model.item(row, 2)
            viewsItem = model.item(row, 3)
            if not all((libItem, cellItem, viewItem, viewsItem)):
                continue
            newConfigDict[cellItem.text()] = [libItem.text(), viewItem.text(),
                                              self._splitViewList(viewsItem.text())]
        self._configDict = newConfigDict

    def saveCell(self):
        self.updateConfigDict()
        items = [
            {"viewType": "config"},
            {"reference": self.centralW.viewNameCB.currentText(),
             "switchViews": self._uiSwitchViews(),
             "stopViews": self._uiStopViews()},
            self._configDict,
        ]
        with self.configFilePathObj.open(mode="w+") as configFile:
            json.dump(items, configFile, indent=4)

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
                        libraryDict: dict, libraryView):
    """Create a new config view from dialog parameters."""
    selectedSchName = dlg.viewNameCB.currentText()
    selectedSchItem = libm.getViewItem(cellItem, selectedSchName)
    if selectedSchItem is None:
        return None
    switchViewList = configEditor._splitViewList(dlg.switchViews.text())
    stopViewList = configEditor._splitViewList(dlg.stopViews.text())

    newConfigDict = dict()
    tempSchematic = sced.schematicEditor(selectedSchItem, libraryDict, libraryView)
    try:
        tempSchematic.switchViewList = switchViewList
        tempSchematic.stopViewList = stopViewList
        tempSchematic.loadSchematic(register=False)
        tempSchematic.createConfigView(newConfigDict, set())
    finally:
        tempSchematic.deleteLater()

    items = [
        {"viewType": "config"},
        {"reference": selectedSchName,
         "switchViews": switchViewList,
         "stopViews": stopViewList},
        newConfigDict,
    ]
    with viewItem.viewPath.open(mode="w+") as configFile:
        json.dump(items, configFile, indent=4)

    configWindow = configEditor(viewItem, libraryDict, libraryView)
    configWindow.loadConfig()
    return configWindow


def openConfigEditWindow(schematicItem: libb.viewItem, configItem: libb.viewItem,
                         libraryDict: dict, libraryView) -> configEditor:
    """Open an existing config view for editing.

    If *schematicItem* points to a different schematic view than the one
    stored in the config file, it is applied as the reference: the combo,
    the opened schematic, and the table are updated accordingly.
    """
    configWindow = configEditor(configItem, libraryDict, libraryView)
    configWindow.loadConfig()
    currentSchItem = configWindow.schViewItem
    if (schematicItem is not None and schematicItem.viewType == "schematic"
            and (currentSchItem is None
                 or schematicItem.viewName != currentSchItem.viewName)):
        configWindow.schViewItem = schematicItem
        viewCB = configWindow.centralW.viewNameCB
        viewCB.blockSignals(True)
        viewCB.setCurrentText(schematicItem.viewName)
        viewCB.blockSignals(False)
        configWindow._openSchematicView()
        configWindow.configDict = configWindow._configFromView(schematicItem, {})
    return configWindow


class configEditorContainer(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parentEditor = parent
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
        viewGroupLayout.addRow(edf.boldLabel("Switch View Types:"),
                               self.switchViewsEdit)
        self.stopViewsEdit = edf.longLineEdit()
        viewGroupLayout.addRow(edf.boldLabel("Stop View Types:"),
                               self.stopViewsEdit)
        self.mainLayout.addWidget(viewGroup)
        self.configDictGroup = QGroupBox("Cell View Configuration")
        self.confModel = configModel(self.parentEditor.configDict)
        self.configDictLayout = QVBoxLayout()
        self.configViewTable = configTable(self.confModel, self)
        self.configDictLayout.addWidget(self.configViewTable)
        self.configDictGroup.setLayout(self.configDictLayout)
        self.mainLayout.addWidget(self.configDictGroup)
        self.setLayout(self.mainLayout)


class configModel(QStandardItemModel):
    HEADERS: ClassVar[list] = ["Library", "Cell Name", "View To Use",
                               "Available Views"]

    def __init__(self, configDict: dict):
        super().__init__(len(configDict), 4)
        self.setHorizontalHeaderLabels(self.HEADERS)
        for i, (cellName, values) in enumerate(configDict.items()):
            libName, viewName, viewList = self._normalizeEntry(values)
            self.setItem(i, 0, QStandardItem(libName))
            self.setItem(i, 1, QStandardItem(cellName))
            self.setItem(i, 2, QStandardItem(viewName))
            self.setItem(i, 3, QStandardItem(", ".join(viewList)))

    @staticmethod
    def _normalizeEntry(values) -> tuple:
        """Return (libraryName, viewName, candidateViews) for a config entry."""
        if isinstance(values, (list, tuple)):
            libName = str(values[0]) if len(values) > 0 else ""
            viewName = str(values[1]) if len(values) > 1 else ""
            candidates = values[2] if len(values) > 2 else []
            if isinstance(candidates, str):
                candidates = [v.strip() for v in candidates.split(",") if v.strip()]
            return libName, viewName, list(candidates)
        return "", str(values), []


class configTable(QTableView):
    def __init__(self, model: configModel, parentContainer):
        super().__init__(parentContainer)
        self.configModel = model
        self.parentContainer = parentContainer
        self.setModel(self.configModel)
        self.combos = []
        self.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        for row in range(self.configModel.rowCount()):
            self._addViewCombo(row)

    def _addViewCombo(self, row: int):
        combo = QComboBox(self)
        items = configEditor._splitViewList(self.configModel.item(row, 3).text())
        currentView = self.configModel.item(row, 2).text()
        if currentView and currentView not in items:
            items.insert(0, currentView)
        combo.addItems(items)
        # Set the current view before connecting so construction does not
        # trigger a table rebuild.
        combo.setCurrentText(currentView)
        combo.currentTextChanged.connect(
            lambda text, cb=combo: self._onComboChanged(cb, text))
        self.setIndexWidget(self.configModel.index(row, 2), combo)
        self.combos.append(combo)

    def _onComboChanged(self, combo: QComboBox, viewName: str):
        """Re-derive the whole table on any view selection change.

        A full rebuild prunes rows that became unreachable under non-schematic
        selections and restores sub-hierarchy rows when a cell is switched back
        to schematic. User selections are preserved through updateClick's
        savedSelections mechanism.
        """
        if combo not in self.combos:
            return
        parentEditor = self.parentContainer.parentEditor
        if parentEditor is not None:
            parentEditor.updateClick()

    def updateModel(self):
        for row, combo in enumerate(self.combos):
            viewItem = self.configModel.item(row, 2)
            if viewItem is not None:
                viewItem.setText(combo.currentText())
