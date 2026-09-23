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

"""Schematic editor module for Revolution EDA.

This module provides the schematicEditor class for editing circuit schematics,
creating symbols, and generating netlists. It supports hierarchical designs,
config views, and plugin integration.
"""

from __future__ import annotations

import json
import pathlib
from copy import deepcopy
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QGridLayout, QMenu, QMessageBox, QToolBar,
)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.checks.schematic as schk
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.labels as lbl
import revedaEditor.common.params as prm
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.symbolEncoder as symenc
import revedaEditor.gui.editorViews as edv
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.findDialogue as finddlg
import revedaEditor.gui.propertyDialogues as pdlg
import revedaEditor.gui.toolsDialogues as tdlg
import revedaEditor.scenes.schematicScene as schscn
from revedaEditor.gui.editorFactory import EditorFactory
from revedaEditor.netlisting import spectreNetlist, vacaskNetlist, xyceNetlist

if TYPE_CHECKING:
    pass


class schematicEditor(edw.editorWindow):
    """Schematic editor window for creating and editing circuit schematics.

    Provides tools for drawing wires, placing instances, creating pins,
    and generating netlists. Supports hierarchical navigation and symbol
    generation from schematics.

    Attributes:
        MAJOR_GRID_DEFAULT: Default spacing for major grid dots/lines.
        SNAP_GRID_DEFAULT: Default grid snapping resolution.
    """
    centralW: schematicContainer

    MAJOR_GRID_DEFAULT = 20
    SNAP_GRID_DEFAULT = 10

    def __init__(self, viewItem: libb.viewItem, libraryDict: dict, libraryView) -> None:
        """Initialize the schematic editor.

        Args:
            viewItem: The view item representing this schematic cellview.
            libraryDict: Dictionary of available libraries.
            libraryView: The library browser view for accessing other cells.
        """
        super().__init__(viewItem, libraryDict, libraryView)
        self.setWindowTitle(f"Schematic Editor - {self.cellName} - {self.viewName}")
        self.setWindowIcon(QIcon(":/icons/edLayer-shape.png"))
        self.symbolChooser: fd.selectCellViewDialog | None = None
        self.majorGrid = self.MAJOR_GRID_DEFAULT
        self.snapGrid = self.SNAP_GRID_DEFAULT
        self.snapTuple = (self.snapGrid, self.snapGrid)
        # Schematic check rules applied by Check -> View Errors; all on by default.
        self.enabledCheckRules = {rule.ruleId for rule in
                                  schk.SCHEMATIC_RULES}
        self.symbolViews = ["symbol"]  # only symbol can be instantiated in schematic
        self._schematicContextMenu()

    def init_UI(self):
        self.resize(1600, 800)
        self._createActions()
        self._createMenuBar()
        self._createToolBars()
        self._addActions()
        self._createTriggers()
        self._createShortcuts()
        self.centralW = schematicContainer(self)
        self.setCentralWidget(self.centralW)

    def __repr__(self):
        return f'schematicEditor({self.libName}-{self.cellName}-{self.viewName})'

    def _createActions(self):
        super()._createActions()
        self.netNameAction = QAction("Net Name", self)
        self.netNameAction.setToolTip("Set Net Name")
        self.netNameAction.setShortcut(Qt.Key.Key_L)
        self.hilightNetAction = QAction("Highlight Net", self)
        self.hilightNetAction.setToolTip("Highlight Selected Net Connections")
        self.hilightNetAction.setCheckable(True)
        self.probeNetAction = QAction("Probe Net", self)
        self.probeNetAction.setToolTip("Probe a Net and Trace It Through Hierarchy")
        self.probeNetAction.setCheckable(True)
        self.removeProbeNetAction = QAction("Remove Probe", self)
        self.removeProbeNetAction.setToolTip("Remove a Probe by Clicking a Probed Net")
        self.removeProbeNetAction.setCheckable(True)
        self.removeAllProbesAction = QAction("Remove All Probes", self)
        self.removeAllProbesAction.setToolTip("Remove All Net Probes Across the Hierarchy")
        self.showResolvedNamesAction = QAction("Show Resolved Net Names", self)
        self.showResolvedNamesAction.setToolTip(
            "Display resolved net names on wires, including inherited "
            "connections and net expressions")
        self.showResolvedNamesAction.setCheckable(True)
        self.renumberInstanceAction = QAction("Renumber Instances", self)
        self.renumberInstanceAction.setToolTip("Renumber Instances")
        self.ungroupItemsAction = QAction("Ungroup Items", self)
        self.ungroupItemsAction.setToolTip(
            "Release the selected schematic mosaic into independent instances")
        simulationIcon = QIcon("icons/application-run.png")
        self.simulateAction = QAction(simulationIcon, "Revolution EDA SAE...", self)
        self.descendInPlaceAction = QAction("Descend Edit-in-Place", self)
        self.descendInPlaceAction.setToolTip(
            "Render the selected instance's schematic ghosted inside this "
            "scene for in-place editing")
        self.ascendInPlaceAction = QAction("Ascend from Edit-in-Place", self)
        self.ascendInPlaceAction.setToolTip("Remove edit-in-place ghosts")
        self.saveInPlaceAction = QAction("Save In-Place Edits", self)
        self.saveInPlaceAction.setToolTip(
            "Write ghosted child items back to their cellview files")
        self.findRelatedEditors = QAction("Find Related Editors", self)
        self.findAction = QAction("Find/Replace...", self)
        self.findAction.setToolTip(
            "Find and replace instances, nets and pins by name")
        self.pasteAction.setToolTip("Paste items from the system clipboard")
        self.checkRulesAction = QAction("Check Rules Setup...", self)
        self.checkRulesAction.setToolTip(
            "Select which schematic check rules are applied")
        self.probeLayoutAction = QAction("Probe in Layout", self)
        self.probeLayoutAction.setToolTip(
            "Cross-probe selected symbols/nets into the layout editor")
        # Repurpose the base-class check action for schematic rule checking.
        self.viewCheckAction.setText("Check Schematic")
        self.viewCheckAction.setToolTip(
            "Run enabled schematic check rules without saving")

    def _addActions(self):
        super()._addActions()
        # file menu: Check Schematic ahead of Check-Save
        self.menuFile.insertAction(self.checkCellAction,
                                   self.viewCheckAction)
        # edit menu
        self.menuEdit.addAction(self.findAction)
        self.menuEdit.addAction(self.netNameAction)
        self.menuEdit.addAction(self.ungroupItemsAction)
        # self.menuEdit.removeAction(self.stretchAction)

        self.propertyMenu = self.menuEdit.addMenu("Properties")
        self.propertyMenu.addAction(self.objPropAction)

        # hierarchy submenu
        self.hierMenu = self.menuEdit.addMenu("Hierarchy")
        self.hierMenu.addAction(self.goUpAction)
        self.hierMenu.addAction(self.goDownAction)
        self.hierMenu.addSeparator()
        self.hierMenu.addAction(self.descendInPlaceAction)
        self.hierMenu.addAction(self.ascendInPlaceAction)
        self.hierMenu.addAction(self.saveInPlaceAction)

        # create menu
        self.menuCreate.addAction(self.createInstAction)
        self.menuCreate.addAction(self.createNetAction)
        self.menuCreate.addAction(self.createBusAction)
        self.menuCreate.addAction(self.createPinAction)
        self.menuCreate.addAction(self.createTextAction)
        self.menuCreate.addAction(self.createSymbolAction)

        # check menu
        self.menuCheck.addAction(self.checkRulesAction)
        self.menuCheck.addAction(self.viewErrorsAction)
        self.menuCheck.addAction(self.deleteErrorsAction)

        # tools menu
        self.menuTools.addAction(self.hilightNetAction)
        self.menuTools.addAction(self.probeNetAction)
        self.menuTools.addAction(self.removeProbeNetAction)
        self.menuTools.addAction(self.removeAllProbesAction)
        self.menuTools.addAction(self.renumberInstanceAction)
        self.menuTools.addAction(self.showResolvedNamesAction)
        self.menuTools.addAction(self.probeLayoutAction)
        self.menuTools.addAction(self.findRelatedEditors)
        # utilities Menu
        self.selectMenu = self.menuUtilities.addMenu("Selection")
        self.selectMenu.addAction(self.selectDeviceAction)
        self.selectMenu.addAction(self.selectNetAction)
        self.selectMenu.addAction(self.selectPinAction)
        self.selectMenu.addAction(self.selectTextAction)
        self.selectMenu.addSeparator()
        self.selectMenu.addAction(self.removeSelectFilterAction)
        self.simulationMenu = QMenu("&Simulation")
        # help menu
        self.simulationMenu.addAction(self.netlistAction)
        self.editorMenuBar.insertMenu(self.menuHelp.menuAction(), self.simulationMenu)
        # self.menuHelp = self.editorMenuBar.addMenu("&Help")
        if hasattr(self._app, 'pluginsObj') and hasattr(self._app.pluginsObj, 'applyPluginMenus'):
            self._app.pluginsObj.applyPluginMenus(self)

    def _createTriggers(self):
        super()._createTriggers()

        self.createNetAction.triggered.connect(self.createNetClick)
        self.createBusAction.triggered.connect(self.createBusClick)
        self.createInstAction.triggered.connect(self.createInstClick)
        self.createPinAction.triggered.connect(self.createPinClick)
        self.createTextAction.triggered.connect(self.createNoteClick)
        self.createSymbolAction.triggered.connect(self.createSymbolClick)

        self.objPropAction.triggered.connect(self.objPropClick)
        self.netlistAction.triggered.connect(self.createNetlistClick)
        self.ignoreAction.triggered.connect(self.ignoreClick)
        self.goDownAction.triggered.connect(self.goDownClick)
        self.descendInPlaceAction.triggered.connect(self.descendInPlaceClick)
        self.ascendInPlaceAction.triggered.connect(self.ascendInPlaceClick)
        self.saveInPlaceAction.triggered.connect(self.saveInPlaceClick)
        self.checkRulesAction.triggered.connect(self.checkRulesClick)
        self.viewCheckAction.triggered.connect(self.checkErrorsClick)
        self.viewErrorsAction.triggered.connect(self.viewErrorsClick)
        self.deleteErrorsAction.triggered.connect(self.deleteErrorsClick)

        self.hilightNetAction.triggered.connect(self.hilightNetClick)
        self.probeNetAction.triggered.connect(self.probeNetClick)
        self.removeProbeNetAction.triggered.connect(self.removeProbeNetClick)
        self.removeAllProbesAction.triggered.connect(self.removeAllProbesClick)
        self.netNameAction.triggered.connect(self.createNetNameClick)
        self.selectDeviceAction.triggered.connect(self.selectDeviceClick)
        self.selectNetAction.triggered.connect(self.selectNetClick)
        self.selectPinAction.triggered.connect(self.selectPinClick)
        self.selectTextAction.triggered.connect(self.selectTextClick)
        self.removeSelectFilterAction.triggered.connect(self.removeSelectFilterClick)
        self.renumberInstanceAction.triggered.connect(self.renumberInstanceClick)
        self.ungroupItemsAction.triggered.connect(
            lambda: self.centralW.scene.ungroupSelectedItems())
        self.showResolvedNamesAction.triggered.connect(
            self.showResolvedNamesClick)
        self.findRelatedEditors.triggered.connect(self.findRelatedEditorsClick)
        self.probeLayoutAction.triggered.connect(
            lambda: self.centralW.scene.probeLayout())
        self.findAction.triggered.connect(self.findClick)

    def _createToolBars(self):
        super()._createToolBars()
        self.toolbar.addAction(self.objPropAction)
        self.toolbar.addAction(self.viewPropAction)

        self.schematicToolbar = QToolBar("Schematic Toolbar", self)
        self.addToolBar(self.schematicToolbar)
        self.schematicToolbar.addAction(self.createInstAction)
        self.schematicToolbar.addAction(self.createNetAction)
        self.schematicToolbar.addAction(self.createBusAction)
        self.schematicToolbar.addAction(self.createPinAction)
        # self.schematicToolbar.addAction(self.createLabelAction)
        self.schematicToolbar.addAction(self.createSymbolAction)
        self.schematicToolbar.addSeparator()
        self.schematicToolbar.addAction(self.viewCheckAction)
        self.schematicToolbar.addSeparator()
        self.schematicToolbar.addAction(self.goDownAction)
        self.schematicToolbar.addSeparator()
        self.schematicToolbar.addAction(self.selectDeviceAction)
        self.schematicToolbar.addAction(self.selectNetAction)
        self.schematicToolbar.addAction(self.selectPinAction)
        self.schematicToolbar.addAction(self.selectTextAction)
        self.schematicToolbar.addAction(self.removeSelectFilterAction)

    def _schematicContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.ignoreAction)
        self.centralW.scene.itemContextMenu.addAction(self.goDownAction)
        self.centralW.scene.itemContextMenu.addSeparator()
        self.centralW.scene.itemContextMenu.addAction(self.probeNetAction)
        self.centralW.scene.itemContextMenu.addAction(self.removeProbeNetAction)

    def _createShortcuts(self):
        super()._createShortcuts()
        self.createInstAction.setShortcut(Qt.Key.Key_I)
        self.createNetAction.setShortcut(Qt.Key.Key_W)
        self.createPinAction.setShortcut(Qt.Key.Key_P)
        self.goDownAction.setShortcut("Shift+E")
        self.findAction.setShortcut("Ctrl+F")
        # unset stretch shortcut for schematic editor
        # self.stretchAction.setShortcut("")

    def createNetClick(self, s):
        self.centralW.scene.editModes.setMode("drawWire")

    def createBusClick(self, s):
        self.centralW.scene.editModes.setMode("drawBus")

    def createInstClick(self, s):
        # create a designLibrariesView
        libraryModel = lmview.symbolViewsModel(self.libraryDict, self.symbolViews)
        self.symbolChooser = fd.selectCellViewDialog(self, libraryModel)
        if self.symbolChooser.exec() != QDialog.DialogCode.Accepted:
            return
        instanceTuple = ddef.viewNameTuple(
            self.symbolChooser.libNamesCB.currentText(),
            self.symbolChooser.cellCB.currentText(),
            self.symbolChooser.viewCB.currentText())
        self.centralW.scene.newInstanceTuple = instanceTuple
        # Parameter values belong to one selected symbol; never carry values
        # from a previous placement choice into another symbol.
        self.centralW.scene.pendingInstanceParams = None
        self.centralW.scene.pendingInstanceArraySpec = None
        if not self._configureSchematicInstanceParams():
            self.centralW.scene.newInstanceTuple = None
            return
        self.centralW.scene.editModes.setMode("addInstance")

    def editActivePlacementOptions(self) -> bool:
        """Open the F3 form for the active schematic placement command."""
        scene = self.centralW.scene
        if scene.editModes.addInstance:
            self._configureSchematicInstanceParams()
        elif scene.editModes.drawPin:
            self._configureSchematicPin(activate=False)
        else:
            return False
        return True

    def _configureSchematicInstanceParams(self) -> bool:
        """Edit persistent symbol labels for the instance being placed."""
        scene = self.centralW.scene
        if scene.newInstanceTuple is None:
            self.messageLine.setText("Choose an instance before opening options")
            return False
        preview = scene.instSymbol(scene.newInstanceTuple, QPoint(0, 0),
                                   allocateName=False)
        if preview is None:
            self.messageLine.setText("Unable to load the selected symbol")
            return False
        if scene.pendingInstanceParams:
            scene._applyPendingInstanceParams(preview)
        labelRows, missingCarriers = scene.instanceLabelRows(preview)
        if missingCarriers:
            message = ("paramDefs without matching NLP labels: "
                       + ", ".join(missingCarriers))
            self.logger.warning(message)
            self.messageLine.setText(message)
        def refreshPreview(values):
            callbackPreview = scene.instSymbol(
                scene.newInstanceTuple, QPoint(0, 0), allocateName=False)
            if callbackPreview is None:
                return {}
            for name, value in values.items():
                label = (callbackPreview.labels.get(f"@{name.lstrip('@')}")
                         or callbackPreview.labels.get(name))
                if label is not None:
                    label.labelValue = value
            scene._resolveInstanceLabels(callbackPreview)
            pyLabelType = lbl.symbolLabel.labelTypes[2]
            return {
                name: str(label.labelValue)
                for name, label in callbackPreview.labels.items()
                if label.labelType == pyLabelType
            }

        paramsDlg = pdlg.placeInstanceDialog(
            self, labelRows, initialValues=scene.pendingInstanceParams,
            onValuesChanged=refreshPreview, sourceTuple=scene.newInstanceTuple,
            arraySpec=getattr(scene, "pendingInstanceArraySpec", None))

        def updateComputedRows(values):
            for row in paramsDlg.labelRows:
                if row.get("isPyLabel") and row["labelName"] in values:
                    row["setValue"](values[row["labelName"]])

        # Keep callbacks in sync while values are being entered, not only at
        # placement time.  The preview remains detached from the scene.
        paramsDlg._onValuesChanged = lambda values: updateComputedRows(
            refreshPreview(values))
        paramsDlg.refreshPreview()
        if paramsDlg.exec() != QDialog.DialogCode.Accepted:
            return False
        scene.pendingInstanceParams = paramsDlg.paramValues()
        scene.pendingInstanceArraySpec = paramsDlg.arraySpec()
        return True

    def _symbolParamDefs(self, instanceTuple) -> tuple[list, list[str]]:
        """Return editable definitions and definitions lacking label carriers."""
        try:
            libraryPath = self.libraryDict.get(instanceTuple.libraryName)
            if libraryPath is None:
                return [], []
            file = libraryPath.joinpath(
                instanceTuple.cellName, f"{instanceTuple.viewName}.json")
            if not file.exists():
                return [], []
            items = lj.schematicItems._load_sym_json(str(file))
            if items is None:
                return [], []
            attrs = {
                item["nam"]: item["def"] for item in items[2:]
                if isinstance(item, dict) and item.get("type") == "attr"
            }
            labelNames = [
                item.get("nam", "") for item in items[2:]
                if isinstance(item, dict)
                and item.get("type") == "label"
                and item.get("lt") == "NLPLabel"
            ]
            bindings, missing = prm.paramDefLabelBindings(
                prm.paramDefsFromSymattrs(attrs), labelNames)
            return [pdef for pdef, _labelName in bindings], missing
        except Exception as error:
            self.logger.error(f"paramDefs lookup failed: {error}")
            return [], []

    def createPinClick(self, s):
        self._configureSchematicPin(activate=True)

    def _configureSchematicPin(self, activate: bool = False) -> bool:
        """Edit pending schematic pin values without abandoning draw mode."""
        scene = self.centralW.scene
        dlg = pdlg.createSchematicPinDialog(self)
        dlg.pinName.setText(scene.pinName or "")
        dlg.pinType.setCurrentText(scene.pinType or "")
        dlg.pinDir.setCurrentText(scene.pinDir or "")
        dlg.netExprEdit.setText(scene.pinExpr or "")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        scene.pinName = dlg.pinName.text()
        scene.pinType = dlg.pinType.currentText()
        scene.pinDir = dlg.pinDir.currentText()
        scene.pinExpr = dlg.netExprEdit.text().strip()
        if activate:
            scene.editModes.setMode("drawPin")
        return True

    def createNoteClick(self, s):
        textDlg = pdlg.noteTextEdit(self)
        if textDlg.exec() == QDialog.DialogCode.Accepted:
            noteText = textDlg.plainTextEdit.toPlainText()
            noteFontFamily = textDlg.familyCB.currentText()
            noteFontSize = textDlg.fontsizeCB.currentText()
            noteFontStyle = textDlg.fontStyleCB.currentText()
            noteAlign = textDlg.textAlignmCB.currentText()
            noteOrient = textDlg.textOrientCB.currentText()
            self.centralW.scene.textTuple = (noteText, noteFontFamily, noteFontStyle,
                                             noteFontSize, noteAlign, noteOrient,)
            self.centralW.scene.editModes.setMode("drawText")

    def createSymbolClick(self, s):
        self.createSymbol()

    def objPropClick(self, s):
        self.centralW.scene.editModes.setMode("selectItem")
        self.centralW.scene.viewObjProperties()

    def renumberInstanceClick(self, s):
        self.centralW.scene.renumberInstances()

    def checkSaveCell(self):
        self.centralW.scene.nameSceneNets()
        self.centralW.scene.saveSchematic(self.file)
        self._clearAutosave()
        self.centralW.scene.reloadScene()
        if hasattr(self.centralW.scene, 'reapplyProbesAfterReload'):
            self.centralW.scene.reapplyProbesAfterReload()
        if self.parentEditor:
            self.parentEditor.centralW.scene.reloadScene()
            self.parentEditor.centralW.scene.reapplyProbesAfterReload()

    def saveCell(self):
        self.centralW.scene.saveSchematic(self.file)
        self._clearAutosave()
        self.centralW.scene.reloadScene()
        self.centralW.scene.reapplyProbesAfterReload()

    def loadSchematic(self, register: bool = True):
        try:
            self.logger.info(f'Loading schematic from {self.cellName} - {self.viewName}')
            self.centralW.scene.loadDesign(self._resolveLoadPath())
            if register:
                viewNameTuple = ddef.viewNameTuple(self.libItem.libraryName,
                                                   self.cellItem.cellName,
                                                   self.viewName)
                self.appMainW.openViews[viewNameTuple] = self
        except Exception as e:
            self.logger.error(f"Error during loading schematic for {self.cellName}: {e}")

    def createConfigView(self, newConfigDict: dict, processedCells: set,
                         savedSelections: dict = None):
        """Recursively build configuration view by traversing schematic hierarchy.

        Walks through all symbol instances in the schematic and determines
        the appropriate view to use for each based on switchViewList. Reuses
        already-open editors for nested schematics; temporary editors are
        never registered in openViews and are deleted without saving.

        Args:
            newConfigDict: Dictionary to populate with cell->view mappings.
            processedCells: Set tracking already-processed cells to avoid cycles.
            savedSelections: Dict of cellName->viewName for preserving user selections.
        """
        if savedSelections is None:
            savedSelections = {}

        sceneSymbolSet = self.centralW.scene.findSceneSymbolSet()
        for item in sceneSymbolSet:
            libItem = libm.getLibItem(self.libraryView.libraryModel, item.libraryName)
            cellItem = libm.getCellItem(libItem, item.cellName)
            if libItem is None or cellItem is None:
                continue
            viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]
            viewNames = [viewItem.viewName for viewItem in viewItems]
            # switchViewList holds view *types*; collect all views whose type
            # is netlistable, in switch-list priority order. Within a type an
            # exact name match wins over variants (e.g. "schematic" over
            # "schematic2").
            typeRank = {viewType: rank for rank, viewType in
                        enumerate(self.switchViewList)}
            netlistableViews = [view.viewName for view in sorted(
                (view for view in viewItems if view.viewType in typeRank),
                key=lambda view: (typeRank[view.viewType],
                                  view.viewName != view.viewType))]
            itemSwitchViewList = deepcopy(netlistableViews)
            viewDict = dict(zip(viewNames, viewItems))
            itemCellTuple = ddef.cellTuple(libItem.libraryName, cellItem.cellName)
            if itemCellTuple not in processedCells:
                if cellLine := newConfigDict.get(cellItem.cellName):
                    netlistableViews = [cellLine[1]]

                # Check if user had previously selected a view for this cell
                if cellItem.cellName in savedSelections:
                    savedView = savedSelections[cellItem.cellName]
                    if savedView in viewNames:
                        netlistableViews = [savedView]

                for viewName in netlistableViews:
                    match viewDict[viewName].viewType:
                        case "schematic":
                            newConfigDict[cellItem.cellName] = [libItem.libraryName,
                                                                viewName,
                                                                itemSwitchViewList, ]
                            schTuple = ddef.viewNameTuple(libItem.libraryName,
                                                          cellItem.cellName,
                                                          viewName)
                            schematicObj = self.appMainW.openViews.get(schTuple)
                            if schematicObj is not None:
                                prevSwitch = schematicObj.switchViewList
                                prevStop = schematicObj.stopViewList
                                try:
                                    schematicObj.switchViewList = self.switchViewList
                                    schematicObj.stopViewList = self.stopViewList
                                    schematicObj.createConfigView(newConfigDict,
                                                                  processedCells,
                                                                  savedSelections)
                                finally:
                                    schematicObj.switchViewList = prevSwitch
                                    schematicObj.stopViewList = prevStop
                            else:
                                schematicObj = schematicEditor(viewDict[viewName],
                                                               self.libraryDict,
                                                               self.libraryView, )
                                try:
                                    schematicObj.switchViewList = self.switchViewList
                                    schematicObj.stopViewList = self.stopViewList
                                    schematicObj.loadSchematic(register=False)
                                    schematicObj.createConfigView(newConfigDict,
                                                                  processedCells,
                                                                  savedSelections)
                                finally:
                                    schematicObj.deleteLater()
                            break
                        case _:
                            newConfigDict[cellItem.cellName] = [libItem.libraryName,
                                                                viewName,
                                                                itemSwitchViewList, ]
                            # Don't traverse into non-schematic views
                            break
                processedCells.add(itemCellTuple)

    def closeEvent(self, event):
        try:
            if self._lockHeld:
                self.centralW.scene.saveSchematic(self.file)
            if self.parentEditor is not None:
                self.parentEditor.centralW.scene.reloadScene()
                parentScene = self.parentEditor.centralW.scene
                if hasattr(parentScene, 'reapplyProbesAfterReload'):
                    parentScene.reapplyProbesAfterReload()
            cellViewNameTuple = ddef.viewNameTuple(self.libName, self.cellName,
                                                   self.viewName)
            self.appMainW.openViews.pop(cellViewNameTuple, None)
        except Exception as e:
            self.appMainW.logger.error(f"Error in closing schematic editor window"
                                       f":{self.cellName}-{self.viewName}:{e}")
        finally:
            event.accept()
            super().closeEvent(event)

    def createNetlistClick(self, s):
        dlg = fd.netlistExportDialogue(self)
        dlg.libNameEdit.setText(self.libName)
        dlg.cellNameEdit.setText(self.cellName)
        netlistableViews = self._getNetlistableViews()
        dlg.viewNameCombo.addItems(netlistableViews)

        if hasattr(self.appMainW, "outputPrefixPath"):
            dlg.netlistDirEdit.setText(str(self.appMainW.outputPrefixPath))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._startNetlisting(dlg)

    def _getNetlistableViews(self):
        views = [self.viewItem.viewName]
        config_items = [self.cellItem.child(row) for row in range(self.cellItem.rowCount())
                        if self.cellItem.child(row).viewType == "config"]

        for item in config_items:
            with item.data(Qt.ItemDataRole.UserRole + 2).open(mode="r") as f:
                config = json.load(f)
                if config[1]["reference"] == self.viewItem.viewName:
                    views.append(item.viewName)

        return views

    def _startNetlisting(self, dlg: fd.netlistExportDialogue):
        # try:
        self.appMainW.simulationOutputPath = pathlib.Path(dlg.netlistDirEdit.text())
        selectedViewName = dlg.viewNameCombo.currentText()

        self.switchViewList = [item.strip() for item in
                               dlg.switchViewEdit.text().split(",")
                               if item.strip()]
        self.stopViewList = [item.strip() for item in
                             dlg.stopViewEdit.text().split(",")
                             if item.strip()]

        subDirPath = self.appMainW.simulationOutputPath / self.libName / self.cellName / selectedViewName
        subDirPath.mkdir(parents=True, exist_ok=True)

        netlistFilePath = subDirPath / f"{self.cellName}_{selectedViewName}.cir"
        topSubCkt = dlg.topAsSubcktCheckBox.isChecked()
        netlistFormat = dlg.netlistFormatCombo.currentText()

        # Find the viewItem for the selected view name instead of using self.viewItem
        selectedViewItem = libm.findViewItem(self.libraryView.libraryModel, self.libName,
                                            self.cellName, selectedViewName)
        if not selectedViewItem:
            self._scene.logger.error(f"View {selectedViewName} not found for {self.libName}/{self.cellName}")
            return

        netlistObj = self.createNetlistObject(selectedViewItem, netlistFilePath, topSubCkt, netlistFormat)

        if netlistObj:
            with self.measureDuration():
                netlistObj.writeNetlist()

    def createNetlistObject(self, viewItem: libb.viewItem, filePath: pathlib.Path,
                            topSubCkt: bool, netlistFormat: str = "Spice/Xyce"):
        # Select the appropriate netlister class based on format
        if netlistFormat == "Spice/Xyce":
            netlisterClass = xyceNetlist
        elif netlistFormat == "Spectre":
            netlisterClass = spectreNetlist
        elif netlistFormat == "VACASK":
            netlisterClass = vacaskNetlist
        else:
            netlisterClass = xyceNetlist  # Default fallback

        if viewItem.viewType == "schematic":
            return netlisterClass(self, filePath, False, topSubCkt)
        elif viewItem.viewType == "config":
            netlistObj = netlisterClass(self, filePath, True, topSubCkt)
            configItem = libm.findViewItem(self.libraryView.libraryModel, self.libName,
                                           self.cellName, viewItem.viewName)
            if configItem:
                configPath = configItem.data(Qt.ItemDataRole.UserRole + 2)
                if configPath:
                    with configPath.open(mode="r") as f:
                        jsonData = json.load(f)
                    if len(jsonData) > 2:
                        netlistObj.configDict = jsonData[2]
                    # Apply the config's own switch/stop view lists so views
                    # beyond the app defaults can be netlisted.
                    header = jsonData[1] if len(jsonData) > 1 else {}
                    if header.get("switchViews"):
                        netlistObj.switchViewList = header["switchViews"]
                    if header.get("stopViews"):
                        netlistObj.stopViewList = header["stopViews"]
            return netlistObj
        return None

    def goDownClick(self, s):
        self.centralW.scene.goDownHier()

    def ignoreClick(self, s):
        self.centralW.scene.ignoreSymbol()

    def createNetNameClick(self, s):
        dlg = pdlg.netNameDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.centralW.scene.netNameString = dlg.netNameEdit.text().strip()
            self.centralW.scene._netNameAuto = None
            self.centralW.scene.editModes.setMode('nameNet')
        self.messageLine.setText("Select a net to attach the name")

    def hilightNetClick(self, s):
        self.centralW.scene.hilightNets()

    def probeNetClick(self, s):
        self.centralW.scene.probeNets()

    def removeProbeNetClick(self, s):
        self.centralW.scene.removeProbeMode()

    def showResolvedNamesClick(self, s):
        self.centralW.scene.toggleResolvedNames(
            self.showResolvedNamesAction.isChecked())

    def removeAllProbesClick(self, s):
        self.probeNetAction.setChecked(False)
        self.removeProbeNetAction.setChecked(False)
        self.centralW.scene.probeMode = False
        self.centralW.scene.removeProbeMode_ = False
        self.centralW.scene.clearProbe()

    def selectDeviceClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectDevice")
        self.messageLine.setText("Select Only Instances")

    def selectNetClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectNet")
        self.messageLine.setText("Select Only Nets")

    def selectPinClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectPin")
        self.messageLine.setText("Select Only Pins")

    def selectTextClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectText")
        self.messageLine.setText("Select Only Text")

    def removeSelectFilterClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectAll")
        self.messageLine.setText("Select All Objects")

    def createSymbol(self) -> None:
        """
        Create a symbol view for a schematic.
        """
        oldSymbolItem = False

        askViewNameDlg = pdlg.symbolNameDialog(self.file.parent, self.cellName, self, )
        if askViewNameDlg.exec() == QDialog.DialogCode.Accepted:
            symbolViewName = askViewNameDlg.symbolViewsCB.currentText()
            if symbolViewName in askViewNameDlg.symbolViewNames:
                oldSymbolItem = True
            if oldSymbolItem:
                deleteSymViewDlg = fd.deleteSymbolDialog(self.cellName, symbolViewName,
                                                         self)
                if deleteSymViewDlg.exec() == QDialog.DialogCode.Accepted:
                    self.generateSymbol(symbolViewName)
            else:
                self.generateSymbol(symbolViewName)

    def _parse_pin_names(self, text: str) -> list[str]:
        """Parse comma-separated pin names, filtering empty strings."""
        return [name.strip() for name in text.split(",") if name.strip()]

    def _categorize_pins(self, schematic_pins: list[shp.schematicPin]) -> dict:
        """Categorize pins by direction."""
        pin_dirs = shp.schematicPin.pinDirs
        return {
            'input': [pin.pinName for pin in schematic_pins if pin.pinDir == pin_dirs[0]],
            'output': [pin.pinName for pin in schematic_pins if pin.pinDir == pin_dirs[1]],
            'inout': [pin.pinName for pin in schematic_pins if pin.pinDir == pin_dirs[2]]}

    def _create_pin_map(self, schematic_pins: list[shp.schematicPin]) -> dict:
        """Create mapping from pin name to pin object."""
        return {pin.pinName: pin for pin in schematic_pins}

    def _draw_pins(self, symbol_scene, pin_names: list[str], locations: list[QPoint],
                   offsets: QPoint, pin_map: dict, default_dir: str) -> None:
        """Draw pins and their connecting lines."""
        for name, loc in zip(pin_names, locations):
            symbol_scene.lineDraw(loc, loc + offsets)
            if name in pin_map:
                symbol_scene.addItem(pin_map[name].toSymbolPin(loc))
            else:
                symbol_scene.addItem(shp.symbolPin(loc, name, default_dir, "Signal"))

    def generateSymbol(self, symbolViewName: str) -> None:
        # Get schematic pins and categorize them
        schematic_pins = list(self.centralW.scene.findSceneSchemPinsSet())
        pin_categories = self._categorize_pins(schematic_pins)
        pin_map = self._create_pin_map(schematic_pins)

        # Setup dialog with categorized pins
        dlg = pdlg.symbolCreateDialog(self)
        dlg.leftPinsEdit.setText(", ".join(pin_categories['input']))
        dlg.rightPinsEdit.setText(", ".join(pin_categories['output']))
        dlg.topPinsEdit.setText(", ".join(pin_categories['inout']))

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Create symbol view and editor
        libItem = libm.getLibItem(self.libraryView.libraryModel, self.libName)
        cellItem = libm.getCellItem(libItem, self.cellName)
        symbolViewItem = libb.createCellView(self, symbolViewName, cellItem)

        symbolWindow = EditorFactory.createEditor("symbol", symbolViewItem,
                                                  self.libraryDict, self.libraryView)

        try:
            # Parse pin configurations
            pin_names = {'left': self._parse_pin_names(dlg.leftPinsEdit.text()),
                         'right': self._parse_pin_names(dlg.rightPinsEdit.text()),
                         'top': self._parse_pin_names(dlg.topPinsEdit.text()),
                         'bottom': self._parse_pin_names(dlg.bottomPinsEdit.text())}

            stub_length = int(float(dlg.stubLengthEdit.text().strip()))
            pin_distance = int(float(dlg.pinDistanceEdit.text().strip()))

            # Calculate rectangle dimensions
            rect_x_dim = (max(len(pin_names['top']),
                              len(pin_names['bottom'])) + 1) * pin_distance
            rect_y_dim = (max(len(pin_names['left']),
                              len(pin_names['right'])) + 1) * pin_distance

        except ValueError:
            self.logger.error("Enter valid value")
            return

        # Draw symbol components
        sceneSymbol = symbolWindow.centralW.scene
        sceneSymbol.rectDraw(QPoint(0, 0), QPoint(rect_x_dim, rect_y_dim))

        # Add labels
        sceneSymbol.labelDraw(QPoint(int(0.25 * rect_x_dim), int(0.4 * rect_y_dim)),
                              "[@cellName]", "NLPLabel", "12", "Center", "R0", "Instance")
        sceneSymbol.labelDraw(QPoint(int(rect_x_dim), int(-0.1 * rect_y_dim)),
                              "[@instName]", "NLPLabel", "12", "Center", "R0", "Instance")

        # Calculate pin locations and draw pins
        pin_configs = [(pin_names['left'],
                        [QPoint(-stub_length, (i + 1) * pin_distance) for i in
                         range(len(pin_names['left']))], QPoint(stub_length, 0), 'Input'),
                       (pin_names['right'],
                        [QPoint(rect_x_dim + stub_length, (i + 1) * pin_distance) for i in
                         range(len(pin_names['right']))], QPoint(-stub_length, 0), 'Output'),
                       (pin_names['top'],
                        [QPoint((i + 1) * pin_distance, -stub_length) for i in
                         range(len(pin_names['top']))], QPoint(0, stub_length), 'Inout'),
                       (pin_names['bottom'],
                        [QPoint((i + 1) * pin_distance, rect_y_dim + stub_length) for i in
                         range(len(pin_names['bottom']))], QPoint(0, -stub_length), 'Inout')]

        for names, locations, offset, default_dir in pin_configs:
            self._draw_pins(sceneSymbol, names, locations, offset, pin_map, default_dir)

        # Add symbol attributes
        all_pin_names = (pin_names['left'] + pin_names['right'] +
                         pin_names['top'] + pin_names['bottom'])
        sceneSymbol.attributeList = [
            symenc.symbolAttribute("SpiceNetlistLine", "X@instName %pinOrder @cellName"),
            symenc.symbolAttribute("SpectreNetlistLine",
                                   "X@instName  ( %pinOrder ) @cellName"),
            symenc.symbolAttribute("VacaskNetlistLine", "@instName ( %pinOrder ) @cellName"),
            symenc.symbolAttribute("lvsNetlistLine", "X@instName %pinOrder @cellName"),
            symenc.symbolAttribute("pinOrder", ", ".join(all_pin_names))]

        # Finalize and show
        symbolWindow.checkSaveCell()
        self.libraryView.reworkDesignLibrariesView(self.appMainW.libraryDict)

        openCellViewTuple = ddef.viewNameTuple(self.libName, self.cellName, symbolViewName)
        self.appMainW.openViews[openCellViewTuple] = symbolWindow
        symbolWindow.show()

    def checkRulesClick(self):
        dlg = pdlg.schematicCheckRulesDialogue(
            self, schk.SCHEMATIC_RULES, self.enabledCheckRules)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.enabledCheckRules = dlg.selectedRuleIds()

    def undoClick(self, s):
        scene = self.centralW.scene
        if getattr(scene, '_wireChainActive', False):
            # Mid-wire: the chain's commands live in an open macro not yet
            # on the stack, so a plain undo would revert an older, unrelated
            # action. Pop the last vertex (or drop the draft) instead.
            if scene.editModes.drawWire or scene.editModes.drawBus:
                scene.popWireVertex()
            else:
                scene._finishWire()
            return
        super().undoClick(s)

    def checkErrorsClick(self):
        self.centralW.scene.checkErrors(self.enabledCheckRules)
        self.logger.info("Schematic Errors checked.")

    def deleteErrorsClick(self):
        self.centralW.scene.deleteErrors()
        self.logger.info("Schematic Errors checked.")

    def findRelated(self, editor, visited, openWindows):
        if editor in visited or editor not in openWindows:
            return
        visited.add(editor)
        if hasattr(editor, 'parentEditor') and editor.parentEditor:
            self.findRelated(editor.parentEditor, visited, openWindows)
        for w in openWindows:
            if hasattr(w, 'parentEditor') and w.parentEditor == editor:
                self.findRelated(w, visited, openWindows)

    def findRelatedEditorsClick(self):
        openWindows = {w for w in QApplication.instance().topLevelWidgets() if
                       isinstance(w, schematicEditor)}
        relatedEditors = set()
        self.findRelated(self, relatedEditors, openWindows)
        dlg = tdlg.findProjectEditors(self)
        relatedEditorNameList = [editor.cellName for editor in relatedEditors]
        dlg.relatedEditorsCB.addItems(relatedEditorNameList)
        dlg.relatedEditorsCB.setCurrentIndex(0)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            relatedEditorName = dlg.relatedEditorsCB.currentText()
            relatedEditor = next((editor for editor in relatedEditors if
                                  editor.cellName == relatedEditorName), None)
            if relatedEditor:
                relatedEditor.show()
                relatedEditor.raise_()
                relatedEditor.activateWindow()

    def descendInPlaceClick(self):
        scene = self.centralW.scene
        group = scene.descendInPlace()
        if group is None:
            self.messageLine.setText(
                "Select an instance to descend into")
            return
        # Ghost children become selectable so property edits proxy through.
        scene.setEipEditable(True)
        self.messageLine.setText(
            "Edit-in-place: ghost children editable; 'Save In-Place Edits' "
            "writes the child cellview")

    def ascendInPlaceClick(self):
        scene = self.centralW.scene
        scene.setEipEditable(False)
        removed = scene.ascendInPlace()
        self.messageLine.setText(f"Removed {removed} ghost group(s)")

    def saveInPlaceClick(self):
        written = self.centralW.scene.saveInPlaceEdits()
        self.messageLine.setText(f"Saved {written} child cellview(s)")

    def viewErrorsClick(self):
        """Open the non-modal check-violation browser (reused if open)."""
        dlg = getattr(self, "_markerDlg", None)
        if dlg is None or not dlg.isVisible():
            dlg = finddlg.markerBrowserDialogue(self)
            self._markerDlg = dlg
        dlg.refresh()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def findClick(self):
        """Open the non-modal find/replace panel (reused if already open)."""
        dlg = getattr(self, "_findDlg", None)
        if dlg is None or not dlg.isVisible():
            dlg = finddlg.findDialogue(self)
            self._findDlg = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()


class schematicContainer(edw.editorContainer):
    scene: schscn.schematicScene
    view: edv.schematicView

    def __init__(self, parent: schematicEditor):
        super().__init__(parent=parent)
        self.editorWindow = parent
        self.scene = schscn.schematicScene(self)
        self.view = edv.schematicView(self.scene, self)
        self.init_UI()

    def init_UI(self):
        # layout statements, using a grid layout
        gLayout = QGridLayout()
        gLayout.setSpacing(5)
        gLayout.setContentsMargins(0, 0, 0, 0)  # remove outer gaps
        gLayout.addWidget(self.view, 0, 0)
        gLayout.setColumnStretch(0, 5)
        gLayout.setRowStretch(0, 6)
        self.setLayout(gLayout)


