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
from __future__ import annotations

# import json
import pathlib

# import numpy as np
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import (
    QAction,
    QIcon,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QGraphicsRectItem,
)
from quantiphy import Quantity

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.gui.editorViews as edv
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.layoutDialogues as ldlg
import revedaEditor.gui.lsw as lsw
import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import lazyPDKModule
from revedaEditor.scenes.layoutScene import layoutScene

fabproc = lazyPDKModule("process")
laylyr = lazyPDKModule("layoutLayers")


class layoutEditor(edw.editorWindow):
    def __init__(self, viewItem: libb.viewItem, libraryDict: dict, libraryView) -> None:
        super().__init__(viewItem, libraryDict, libraryView)
        self.setWindowTitle(f"Layout Editor - {self.cellName} - {self.viewName}")
        self.setWindowIcon(QIcon(":/icons/edLayer-shape.png"))
        self.layoutViews = ["layout", "pcell"]
        self.dbu = fabproc.dbu
        # PDK grid values are in layout units (e.g. µm); convert to scene
        # units (dbu-scaled integers) for snapping and grid drawing.
        self.majorGrid = round(fabproc.majorGrid * self.dbu)
        self.snapGrid = round(fabproc.snapGrid * self.dbu)
        self.snapTuple = (self.snapGrid, self.snapGrid)
        self.lodThreshold = 0.02  # default instance LOD threshold
        self.layoutChooser = None
        self.gdsExportDirObj = (
            self.appMainW.runPath / "gdsExport" / self.libName / self.cellName
        )
        self.gdsExportDirObj.mkdir(parents=True, exist_ok=True)
        self._layoutContextMenu()
        # drc error polygons
        self._drcPolygons = []
        # lvs error rectangles
        self._lvsRectangles = []

    def init_UI(self):
        self.resize(1600, 800)
        self._createActions()
        self._createMenuBar()
        self._createToolBars()
        self._addActions()
        self._createTriggers()
        self._createShortcuts()
        # create container to position all widgets
        self.centralW = layoutContainer(self)
        self.setCentralWidget(self.centralW)

    def _createMenuBar(self):
        super()._createMenuBar()
        self.propertyMenu = self.menuEdit.addMenu("Properties")

    def _createActions(self):
        super()._createActions()
        self.renumberInstanceAction = QAction("Renumber Instances", self)
        self.renumberInstanceAction.setToolTip("Renumber Instances")
        cutIcon = QIcon(":/icons/cutter.png")
        self.cutAction = QAction(cutIcon, "Cut Item", self)
        self.cutAction.setToolTip("Cut selected objects")
        self.mergeAction = QAction("Merge Shapes", self)
        self.mergeAction.setToolTip("Merge selected paths, rectangles, or polygons")
        self.layerOpsAction = QAction("Layer Operations...", self)
        self.layerOpsAction.setToolTip(
            "Boolean (or/and/xor/not) and size (grow/shrink) operations on selected shapes")
        self.exportGDSAction = QAction("Export GDS", self)
        self.exportGDSAction.setToolTip("Export GDS from Layout")
        self.exportOASAction = QAction("Export OAS", self)
        self.exportGDSAction.setToolTip("Export OAS from Layout")
        self.sdlLoadAction = QAction("Load from Schematic...", self)
        self.sdlLoadAction.setToolTip("Create layout instances from schematic")
        self.highlightNetAction = QAction("Highlight Net", self)
        self.highlightNetAction.setToolTip(
            "Click a shape, pin, or label to highlight its whole net")
        self.clearNetHighlightsAction = QAction("Clear Net Highlights", self)
        self.clearNetHighlightsAction.setToolTip(
            "Remove all net highlight overlays")
        self.delSelectedRulerAction = QAction("Delete Selected Rulers", self)
        self.delSelectedRulerAction.setToolTip(
            "Delete the rulers in the current selection")
        self.multipartAction = QAction("Create Multipart...", self)
        self.multipartAction.setToolTip(
            "Guard ring, shielded path, or bus route (editable composite)")
        self.flattenAction = QAction("Flatten Selection", self)
        self.flattenAction.setToolTip(
            "Replace selected instances with their contents as shapes")
        self.makeCellAction = QAction("Make Cell From Selection...", self)
        self.makeCellAction.setToolTip(
            "Write selected items to a new cell and replace with an instance")
        self.groupItemsAction = QAction("Group Items", self)
        self.groupItemsAction.setToolTip(
            "Group selected items so they select/move/copy as one unit")
        self.ungroupItemsAction = QAction("Ungroup Items", self)
        self.ungroupItemsAction.setToolTip(
            "Explode selected groups back into their items")

    def _addActions(self):
        super()._addActions()
        self.selectMenu.addAction(self.selectDeviceAction)
        self.selectMenu.addAction(self.selectWireAction)
        self.selectMenu.addSeparator()
        self.selectMenu.addAction(self.removeSelectFilterAction)

        self.propertyMenu.addAction(self.objPropAction)
        self.menuEdit.addAction(self.stretchAction)
        self.menuEdit.addAction(self.cutAction)
        self.menuEdit.addAction(self.mergeAction)
        self.menuEdit.addAction(self.layerOpsAction)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.groupItemsAction)
        self.menuEdit.addAction(self.ungroupItemsAction)
        self.menuCreate.addAction(self.createInstAction)
        self.menuCreate.addAction(self.createRectAction)
        self.menuCreate.addAction(self.createPathAction)
        self.menuCreate.addAction(self.createPinAction)
        self.menuCreate.addAction(self.createLabelAction)
        self.menuCreate.addAction(self.createViaAction)
        self.menuCreate.addAction(self.createPolygonAction)
        self.menuCreate.addAction(self.multipartAction)
        self.menuCreate.addSeparator()
        self.menuCreate.addAction(self.rulerAction)
        self.menuCreate.addAction(self.delSelectedRulerAction)
        self.menuCreate.addAction(self.delRulerAction)
        self.menuTools.addAction(self.renumberInstanceAction)
        self.menuTools.addAction(self.exportGDSAction)
        self.menuTools.addAction(self.exportOASAction)
        self.menuTools.addSeparator()
        pluginsObj = getattr(self._app, "pluginsObj", None)
        if not (pluginsObj and pluginsObj.provides("sdl")):
            self.menuTools.addAction(self.sdlLoadAction)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.highlightNetAction)
        self.menuTools.addAction(self.clearNetHighlightsAction)

        # hierarchy submenu
        self.hierMenu = self.menuEdit.addMenu("Hierarchy")
        self.hierMenu.addAction(self.goUpAction)
        self.hierMenu.addAction(self.goDownAction)
        self.hierMenu.addSeparator()
        self.hierMenu.addAction(self.flattenAction)
        self.hierMenu.addAction(self.makeCellAction)

        if hasattr(self._app, "pluginsObj") and hasattr(
            self._app.pluginsObj, "applyPluginMenus"
        ):
            self._app.pluginsObj.applyPluginMenus(self)
        if hasattr(self._app, "pdkConfigObj") and hasattr(
            self._app.pdkConfigObj, "applyPDKMenus"
        ):
            self._app.pdkConfigObj.applyPDKMenus(self)

    def _layoutContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.goDownAction)
        self.centralW.scene.itemContextMenu.addAction(self.mergeAction)
        self.centralW.scene.itemContextMenu.addAction(self.groupItemsAction)
        self.centralW.scene.itemContextMenu.addAction(self.ungroupItemsAction)

    def _createToolBars(self):
        super()._createToolBars()
        self.layoutToolbar = QToolBar("Layout Toolbar", self)
        self.addToolBar(self.layoutToolbar)
        self.layoutToolbar.addAction(self.createInstAction)
        self.layoutToolbar.addAction(self.createRectAction)
        self.layoutToolbar.addAction(self.createPathAction)
        self.layoutToolbar.addAction(self.createPinAction)
        self.layoutToolbar.addAction(self.createLabelAction)
        self.layoutToolbar.addAction(self.createViaAction)
        self.layoutToolbar.addAction(self.createPolygonAction)
        self.layoutToolbar.addSeparator()
        self.layoutToolbar.addAction(self.rulerAction)
        self.layoutToolbar.addAction(self.delRulerAction)
        self.layoutToolbar.addSeparator()
        self.layoutToolbar.addAction(self.goDownAction)
        self.layoutToolbar.addSeparator()
        self.layoutToolbar.addAction(self.removeSelectFilterAction)
        self.layoutToolbar.addAction(self.selectWireAction)
        self.layoutToolbar.addAction(self.selectDeviceAction)

    def _createTriggers(self):
        super()._createTriggers()
        self.createInstAction.triggered.connect(self.createInstClick)
        self.createRectAction.triggered.connect(self.createRectClick)
        self.exportGDSAction.triggered.connect(self.exportGDSClick)
        self.exportOASAction.triggered.connect(self.exportOASClick)
        self.cutAction.triggered.connect(self.cutClick)
        self.mergeAction.triggered.connect(self.mergeClick)
        self.layerOpsAction.triggered.connect(self.layerOpsClick)
        self.createPathAction.triggered.connect(self.createPathClick)
        self.createPinAction.triggered.connect(self.createPinClick)
        self.createLabelAction.triggered.connect(self.createLabelClick)
        self.createViaAction.triggered.connect(self.createViaClick)
        self.createPolygonAction.triggered.connect(self.createPolygonClick)
        self.multipartAction.triggered.connect(self.createMultipartClick)
        self.rulerAction.triggered.connect(self.createRulerClick)
        self.delSelectedRulerAction.triggered.connect(self.delSelectedRulerClick)
        self.delRulerAction.triggered.connect(self.delRulerClick)
        self.deleteAction.triggered.connect(self.deleteClick)
        self.objPropAction.triggered.connect(self.objPropClick)
        self.goDownAction.triggered.connect(self.goDownClick)
        self.flattenAction.triggered.connect(self.flattenClick)
        self.makeCellAction.triggered.connect(self.makeCellClick)
        self.groupItemsAction.triggered.connect(
            lambda: self.centralW.scene.groupSelectedItems())
        self.ungroupItemsAction.triggered.connect(
            lambda: self.centralW.scene.ungroupSelectedItems())
        self.renumberInstanceAction.triggered.connect(self.renumberInstanceClick)
        self.sdlLoadAction.triggered.connect(self.sdlLoadClick)
        self.highlightNetAction.triggered.connect(self.highlightNetClick)
        self.clearNetHighlightsAction.triggered.connect(
            self.clearNetHighlightsClick)

    def _createShortcuts(self):
        super()._createShortcuts()
        self.createRectAction.setShortcut(Qt.Key.Key_R)
        self.createPathAction.setShortcut(Qt.Key.Key_W)
        self.createInstAction.setShortcut(Qt.Key.Key_I)
        self.createPinAction.setShortcut(Qt.Key.Key_P)
        self.createLabelAction.setShortcut(Qt.Key.Key_L)
        self.createViaAction.setShortcut(Qt.Key.Key_V)
        self.createPolygonAction.setShortcut(Qt.Key.Key_G)
        self.stretchAction.setShortcut(Qt.Key.Key_S)
        self.rulerAction.setShortcut(Qt.Key.Key_K)
        self.delSelectedRulerAction.setShortcut("Ctrl+K")
        self.delRulerAction.setShortcut("Shift+K")
        self.cutAction.setShortcut("Shift+C")
        self.mergeAction.setShortcut("Ctrl+M")
        self.groupItemsAction.setShortcut("Ctrl+G")
        self.ungroupItemsAction.setShortcut("Ctrl+Shift+G")

    def highlightNetClick(self, s):
        self.centralW.scene.editModes.setMode("highlightNet")
        self.messageLine.setText(
            "Highlight Net: click a shape, pin, or label. Esc to exit.")

    def clearNetHighlightsClick(self, s):
        self.centralW.scene.clearNetHighlights()
        self.messageLine.setText("Net highlights cleared")

    def cutClick(self):
        self.centralW.scene.editModes.setMode("cutShape")

    def mergeClick(self):
        self.centralW.scene.mergeSelectedItems()

    def layerOpsClick(self, s):
        dlg = ldlg.layerOpDialogue(self)
        if dlg.exec_() == QDialog.DialogCode.Accepted:
            amount = dlg.selectedAmount * (fabproc.dbu if fabproc else 1000)
            self.centralW.scene.booleanSelectedItems(dlg.selectedOp, amount)

    def flattenClick(self, s):
        self.centralW.scene.flattenSelection()

    def makeCellClick(self, s):
        dlg = ldlg.makeCellDialogue(self, sorted(self.libraryDict.keys()))
        if dlg.exec_() == QDialog.DialogCode.Accepted:
            if not dlg.cellName:
                self.messageLine.setText("Make Cell needs a cell name")
                return
            overwrite = False
            libPath = self.libraryDict.get(dlg.libName)
            if libPath is not None and (
                    pathlib.Path(libPath) / dlg.cellName / "layout.json"
            ).exists():
                answer = QMessageBox.question(
                    self, "Overwrite Cell",
                    f"{dlg.libName}/{dlg.cellName}/layout already exists.\n"
                    "Overwrite it?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
                overwrite = True
            self.centralW.scene.makeCellFromSelection(
                dlg.libName, dlg.cellName, overwrite=overwrite)

    def createRectClick(self, s):
        self.centralW.scene.editModes.setMode("drawRect")

    def createRulerClick(self, s):
        self.centralW.scene.editModes.setMode("drawRuler")
        self.messageLine.setText("Click on the first point of the ruler.")

    def delSelectedRulerClick(self, s):
        if self.centralW.scene.deleteSelectedRulers():
            self.messageLine.setText("Selected rulers deleted")
        else:
            self.messageLine.setText("No rulers selected")
        self.centralW.scene.editModes.setMode("selectItem")

    def delRulerClick(self, s):
        self.messageLine.setText("Deleting all rulers")
        self.centralW.scene.deleteAllRulers()
        self.centralW.scene.editModes.setMode("selectItem")

    def createPathClick(self, s):
        if not fabproc:
            self.messageLine.setText("Error: PDK process module not loaded")
            return

        def pathLayerChanged(dlg):
            pathTupleName = dlg.pathLayerCB.currentText()
            pathDefTuple = [
                item for item in fabproc.processPaths if item.name == pathTupleName
            ][0]
            dlg.pathWidth.setText(pathDefTuple.minWidth.__str__())
            dlg.pathWidthValidator.setRange(pathDefTuple.minWidth, pathDefTuple.maxWidth)
            dlg.startExtendEdit.setText(str(pathDefTuple.minWidth / 2))
            dlg.endExtendEdit.setText(str(pathDefTuple.minWidth / 2))

        dlg = ldlg.createPathDialogue(self)
        # paths are created on path layers
        processPathNames = [f"{pathTuple.name}" for pathTuple in fabproc.processPaths]
        dlg.pathLayerCB.addItems(processPathNames)
        selectedPathIndex = next(
            (
                index
                for index, pathTuple in enumerate(fabproc.processPaths)
                if pathTuple.layer == self.centralW.scene.selectEdLayer
            ),
            0,
        )
        dlg.pathLayerCB.setCurrentIndex(selectedPathIndex)
        defaultPathTuple = fabproc.processPaths[selectedPathIndex]
        dlg.pathLayerCB.currentIndexChanged.connect(lambda: pathLayerChanged(dlg))
        dlg.pathWidth.setText(defaultPathTuple.minWidth.__str__())
        dlg.pathWidthValidator.setRange(
            defaultPathTuple.minWidth, defaultPathTuple.maxWidth
        )
        dlg.startExtendEdit.setText(str(defaultPathTuple.minWidth / 2))
        dlg.endExtendEdit.setText(str(defaultPathTuple.minWidth / 2))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.centralW.scene.editModes.setMode("drawPath")
            if dlg.manhattanButton.isChecked():
                pathMode = 0
            elif dlg.diagonalButton.isChecked():
                pathMode = 1
            elif dlg.anyButton.isChecked():
                pathMode = 2
            elif dlg.horizontalButton.isChecked():
                pathMode = 3
            elif dlg.verticalButton.isChecked():
                pathMode = 4
            else:
                pathMode = 0
            if dlg.pathWidth.text().strip():
                pathWidth = fabproc.dbu * float(dlg.pathWidth.text().strip())
            else:
                pathWidth = fabproc.dbu * 1.0
            pathName = dlg.pathNameEdit.text()
            pathTupleName = dlg.pathLayerCB.currentText()
            pathTuple = [
                item for item in fabproc.processPaths if item.name == pathTupleName
            ][0]
            pathLayer = pathTuple.layer
            startExtend = float(dlg.startExtendEdit.text().strip()) * fabproc.dbu
            endExtend = float(dlg.endExtendEdit.text().strip()) * fabproc.dbu
            self.centralW.scene.newPathTuple = ddef.layoutPathTuple(
                pathName, pathLayer, pathMode, pathWidth, startExtend, endExtend
            )

    def editActivePlacementOptions(self) -> bool:
        """Open the F3 form for the current non-path layout placement mode."""
        scene = self.centralW.scene
        if scene.editModes.addVia:
            self._configureViaPlacement()
        elif scene.editModes.addInstance:
            self._configureLayoutInstanceOptions()
        elif scene.editModes.drawMultipart:
            self._configureMultipartPlacement()
        elif scene.editModes.drawPin:
            self._configureLayoutPinPlacement()
        elif scene.editModes.addLabel:
            self._configureLayoutLabelPlacement()
        elif scene.editModes.drawRuler:
            self._configureRulerOptions()
        else:
            return False
        return True

    def _configureRulerOptions(self) -> bool:
        """Edit ruler angle mode and edge snap (F3 during drawRuler)."""
        scene = self.centralW.scene
        dlg = ldlg.rulerOptionsDialogue(self)
        modeButtons = (dlg.manhattanButton, dlg.diagonalButton,
                       dlg.anyButton)
        if 0 <= scene.rulerMode < len(modeButtons):
            modeButtons[scene.rulerMode].setChecked(True)
        dlg.snapToEdgeCheck.setChecked(scene.rulerSnapToEdge)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        mode = next((i for i, button in enumerate(modeButtons)
                     if button.isChecked()), 0)
        scene.applyRulerMode(mode)
        scene.rulerSnapToEdge = dlg.snapToEdgeCheck.isChecked()
        self.messageLine.setText(
            f"Ruler: {scene._RULER_MODE_NAMES[mode]}, "
            f"snap {'on' if scene.rulerSnapToEdge else 'off'}")
        return True

    def _configureLayoutInstanceOptions(self) -> bool:
        """Prepare PCell values and mosaic geometry for the next placement."""
        scene = self.centralW.scene
        if scene.layoutInstanceTuple is None:
            self.messageLine.setText("Choose an instance before opening options")
            return False
        preview = scene.instLayout(scene.layoutInstanceTuple)
        if preview is None:
            return False
        # instLayout allocates an instance counter even for this options-only
        # preview; return it so F3 does not create a numbering gap.
        scene.itemCounter -= 1
        dlg = ldlg.layoutInstanceDialogue(self)
        dlg.instanceLibName.setText(preview.libraryName)
        dlg.instanceCellName.setText(preview.cellName)
        dlg.instanceViewName.setText(preview.viewName)
        dlg.arrayGroup.show()
        dlg.rowsEdit.setText("1")
        dlg.colsEdit.setText("1")
        dlg.rowPitchEdit.setText("0")
        dlg.colPitchEdit.setText("0")
        previous = scene.pendingInstanceOptions or {}
        previousArray = previous.get("arraySpec")
        if previousArray is not None:
            rows, cols, rowPitch, colPitch = previousArray
            dlg.rowsEdit.setText(str(rows))
            dlg.colsEdit.setText(str(cols))
            dlg.rowPitchEdit.setText(f"{rowPitch / fabproc.dbu:g}")
            dlg.colPitchEdit.setText(f"{colPitch / fabproc.dbu:g}")
        pcellValues = None
        if isinstance(preview, lshp.layoutPcell):
            lineEditDict = scene.extractPcellInstanceParameters(preview)
            if lineEditDict:
                dlg.pcellParamsGroup.show()
                pcellValues = previous.get("pcellValues", {})
                for key, field in lineEditDict.items():
                    field.setText(str(pcellValues.get(key, field.text())))
                    dlg.pcellParamsLayout.addRow(key, field)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        arraySpec = dlg.arraySpec()
        if arraySpec is not None:
            rows, cols, rowPitch, colPitch = arraySpec
            arraySpec = (rows, cols, rowPitch * fabproc.dbu, colPitch * fabproc.dbu)
        scene.pendingInstanceOptions = {
            "pcellValues": (
                {key: field.text() for key, field in lineEditDict.items()}
                if isinstance(preview, lshp.layoutPcell) else None),
            "arraySpec": arraySpec,
        }
        return True

    def createPinClick(self):
        self._configureLayoutPinPlacement(activate=True)

    def _configureLayoutPinPlacement(self, activate: bool = False) -> bool:
        """Edit the pending layout pin and its associated label settings."""
        scene = self.centralW.scene
        dlg = ldlg.createLayoutPinDialog(self)
        pinLayers = list(laylyr.pdkPinLayers)
        labelLayers = list(getattr(laylyr, "pdkLabelLayers", laylyr.pdkTextLayers))
        dlg.pinLayerCB.addItems(
            [f"{item.name} [{item.purpose}]" for item in pinLayers])
        dlg.labelLayerCB.addItems(
            [f"{item.name} [{item.purpose}]" for item in labelLayers])
        if scene.newPinTuple is not None:
            pin = scene.newPinTuple
            dlg.pinName.setText(pin.pinName)
            dlg.pinDir.setCurrentText(pin.pinDir)
            dlg.pinType.setCurrentText(pin.pinType)
            dlg.pinLayerCB.setCurrentText(
                f"{pin.pinLayer.name} [{pin.pinLayer.purpose}]")
        if scene.newLabelTuple is not None:
            label = scene.newLabelTuple
            dlg.labelLayerCB.setCurrentText(
                f"{label.labelLayer.name} [{label.labelLayer.purpose}]")
            dlg.familyCB.setCurrentText(label.fontFamily)
            dlg.fontStyleCB.setCurrentText(label.fontStyle)
            dlg.labelHeightCB.setCurrentText(str(label.fontHeight))
            dlg.labelAlignCB.setCurrentText(label.labelAlign)
            dlg.labelOrientCB.setCurrentText(label.labelOrient)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        pinLayerName, pinLayerPurpose = dlg.pinLayerCB.currentText().split()
        labelLayerName, labelLayerPurpose = dlg.labelLayerCB.currentText().split()
        pinLayer = next(
            item for item in pinLayers
            if item.name == pinLayerName and item.purpose == pinLayerPurpose.strip("[]"))
        labelLayer = next(
            item for item in labelLayers
            if item.name == labelLayerName
            and item.purpose == labelLayerPurpose.strip("[]"))
        scene.newPinTuple = ddef.layoutPinTuple(
            dlg.pinName.text(), dlg.pinDir.currentText(), dlg.pinType.currentText(),
            pinLayer)
        scene.newLabelTuple = ddef.layoutLabelTuple(
            dlg.pinName.text(), dlg.familyCB.currentText(),
            dlg.fontStyleCB.currentText(), float(dlg.labelHeightCB.currentText()),
            dlg.labelAlignCB.currentText(), dlg.labelOrientCB.currentText(), labelLayer)
        if activate:
            scene.editModes.setMode("drawPin")
        return True

    def createLabelClick(self):
        self._configureLayoutLabelPlacement(activate=True)

    def _configureLayoutLabelPlacement(self, activate: bool = False) -> bool:
        """Edit the pending layout label settings without cancelling placement."""
        scene = self.centralW.scene
        dlg = ldlg.createLayoutLabelDialog(self)
        labelLayers = list(getattr(laylyr, "pdkLabelLayers", laylyr.pdkTextLayers))
        dlg.labelLayerCB.addItems(
            [f"{item.name} [{item.purpose}]" for item in labelLayers])
        if scene.newLabelTuple is not None:
            label = scene.newLabelTuple
            dlg.labelName.setText(label.labelText)
            dlg.labelLayerCB.setCurrentText(
                f"{label.labelLayer.name} [{label.labelLayer.purpose}]")
            dlg.familyCB.setCurrentText(label.fontFamily)
            dlg.fontStyleCB.setCurrentText(label.fontStyle)
            dlg.labelHeightCB.setCurrentText(str(label.fontHeight))
            dlg.labelAlignCB.setCurrentText(label.labelAlign)
            dlg.labelOrientCB.setCurrentText(label.labelOrient)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        layerName, layerPurpose = dlg.labelLayerCB.currentText().split()
        labelLayer = next(
            item for item in labelLayers
            if item.name == layerName and item.purpose == layerPurpose.strip("[]"))
        scene.newLabelTuple = ddef.layoutLabelTuple(
            dlg.labelName.text(), dlg.familyCB.currentText(),
            dlg.fontStyleCB.currentText(), dlg.labelHeightCB.currentText(),
            dlg.labelAlignCB.currentText(), dlg.labelOrientCB.currentText(), labelLayer)
        if activate:
            scene.editModes.setMode("addLabel")
        return True

    def createViaClick(self):
        self._configureViaPlacement(activate=True)

    def _configureViaPlacement(self, activate: bool = False) -> bool:
        """Edit the pending single/array via specification used by placement."""
        scene = self.centralW.scene
        dlg = ldlg.createLayoutViaDialog(self)
        viaNames = [item.name for item in fabproc.processVias]
        dlg.singleViaNamesCB.addItems(viaNames)
        dlg.arrayViaNamesCB.addItems(viaNames)
        current = scene.arrayViaTuple
        if current is None:
            selected = fabproc.processVias[0]
            dlg.singleViaWidthEdit.setText(str(selected.minWidth))
            dlg.singleViaHeightEdit.setText(str(selected.minHeight))
            dlg.arrayViaWidthEdit.setText(str(selected.minWidth))
            dlg.arrayViaHeightEdit.setText(str(selected.minHeight))
            dlg.arrayXspacingEdit.setText(str(selected.minSpacing))
            dlg.arrayYspacingEdit.setText(str(selected.minSpacing))
            dlg.singleBottomEncEdit.setText(str(getattr(selected, "bottomEnclosure", 0.0)))
            dlg.singleTopEncEdit.setText(str(getattr(selected, "topEnclosure", 0.0)))
            dlg.arrayBottomEncEdit.setText(str(getattr(selected, "bottomEnclosure", 0.0)))
            dlg.arrayTopEncEdit.setText(str(getattr(selected, "topEnclosure", 0.0)))
        else:
            via = current.singleViaTuple
            isArray = current.xnum > 1 or current.ynum > 1
            if isArray:
                dlg.arrayViaRB.click()
            else:
                dlg.singleViaRB.click()
            for combo in (dlg.singleViaNamesCB, dlg.arrayViaNamesCB):
                combo.setCurrentText(via.viaDefTuple.name)
            width = f"{via.width / fabproc.dbu:g}"
            height = f"{via.height / fabproc.dbu:g}"
            dlg.singleViaWidthEdit.setText(width)
            dlg.singleViaHeightEdit.setText(height)
            dlg.arrayViaWidthEdit.setText(width)
            dlg.arrayViaHeightEdit.setText(height)
            bottomEnc = (via.bottomEnclosure if via.bottomEnclosure is not None
                         else getattr(via.viaDefTuple, "bottomEnclosure", 0.0))
            topEnc = (via.topEnclosure if via.topEnclosure is not None
                      else getattr(via.viaDefTuple, "topEnclosure", 0.0))
            dlg.singleBottomEncEdit.setText(str(bottomEnc))
            dlg.singleTopEncEdit.setText(str(topEnc))
            dlg.arrayBottomEncEdit.setText(str(bottomEnc))
            dlg.arrayTopEncEdit.setText(str(topEnc))
            dlg.arrayXspacingEdit.setText(f"{current.xs / fabproc.dbu:g}")
            dlg.arrayYspacingEdit.setText(f"{current.ys / fabproc.dbu:g}")
            dlg.arrayXNumEdit.setText(str(current.xnum))
            dlg.arrayYNumEdit.setText(str(current.ynum))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        if dlg.singleViaRB.isChecked():
            viaDef = next(item for item in fabproc.processVias
                          if item.name == dlg.singleViaNamesCB.currentText())
            singleVia = ddef.singleViaTuple(
                viaDef, fabproc.dbu * float(dlg.singleViaWidthEdit.text()),
                fabproc.dbu * float(dlg.singleViaHeightEdit.text()),
                float(dlg.singleBottomEncEdit.text()),
                float(dlg.singleTopEncEdit.text()))
            scene.arrayViaTuple = ddef.arrayViaTuple(
                singleVia, fabproc.dbu * viaDef.minSpacing,
                fabproc.dbu * viaDef.minSpacing, 1, 1)
        else:
            viaDef = next(item for item in fabproc.processVias
                          if item.name == dlg.arrayViaNamesCB.currentText())
            singleVia = ddef.singleViaTuple(
                viaDef, fabproc.dbu * float(dlg.arrayViaWidthEdit.text()),
                fabproc.dbu * float(dlg.arrayViaHeightEdit.text()),
                float(dlg.arrayBottomEncEdit.text()),
                float(dlg.arrayTopEncEdit.text()))
            scene.arrayViaTuple = ddef.arrayViaTuple(
                singleVia, fabproc.dbu * float(dlg.arrayXspacingEdit.text()),
                fabproc.dbu * float(dlg.arrayYspacingEdit.text()),
                int(float(dlg.arrayXNumEdit.text())),
                int(float(dlg.arrayYNumEdit.text())))
        if activate:
            scene.editModes.setMode("addVia")
        return True

    def createMultipartClick(self, s):
        self._configureMultipartPlacement(activate=True)

    def _configureMultipartPlacement(self, activate: bool = False) -> bool:
        """Edit the pending multipart specification used by the two-click draw."""
        scene = self.centralW.scene
        dlg = ldlg.createMultipartDialogue(self, scene.newMultipartSpec)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        scene.newMultipartSpec = dlg.selectedSpec()
        if activate:
            scene.editModes.setMode("drawMultipart")
            self.messageLine.setText("Click the start point, then click again to finish.")
        return True

    def createPolygonClick(self):
        self.centralW.scene.editModes.setMode("drawPolygon")

    def objPropClick(self, s):
        self.centralW.scene.viewObjProperties()

    def goDownClick(self):
        self.centralW.scene.goDownHier()

    def checkSaveCell(self):
        # need to add checks
        if getattr(self, '_isPcellPreview', False):
            return
        self.centralW.scene.saveLayoutCell(self.file)
        self._clearAutosave()
        if self.parentEditor:
            self.parentEditor.centralW.scene.reloadScene()

    def saveCell(self):
        if getattr(self, '_isPcellPreview', False):
            return
        self.centralW.scene.saveLayoutCell(self.file)
        self._clearAutosave()

    def loadLayout(self):
        self.logger.info(f"Loading layout from {self.cellName} - {self.viewName}")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self.centralW.scene._safeLoadDesign(self._resolveLoadPath())
            viewNameTuple = ddef.viewNameTuple(
                self.libItem.libraryName, self.cellItem.cellName, self.viewName
            )
            self.appMainW.openViews[viewNameTuple] = self
        except Exception as e:
            self.logger.error(f"Error during loading layout for {self.cellName}: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def createInstClick(self, s):
        self._selectLayoutInstance(activate=True)

    def _selectLayoutInstance(self, activate: bool = False) -> bool:
        """Select the source cellview for the next layout instance placement."""
        libraryModel = lmview.layoutViewsModel(self.libraryDict, self.layoutViews)
        chooser = fd.selectCellViewDialog(self, libraryModel)
        if chooser.exec() != QDialog.DialogCode.Accepted:
            return False
        libItem = libm.getLibItem(libraryModel, chooser.libNamesCB.currentText())
        cellItem = libm.getCellItem(libItem, chooser.cellCB.currentText())
        viewItem = libm.getViewItem(cellItem, chooser.viewCB.currentText())
        self.layoutChooser = chooser
        self.centralW.scene.layoutInstanceTuple = ddef.viewItemTuple(
            libItem, cellItem, viewItem)
        self.centralW.scene.pendingInstanceOptions = None
        if activate:
            self.centralW.scene.editModes.setMode("addInstance")
        return True

    def _exportLayoutCell(self, export_format="GDS"):
        """Export layout cell in the specified format (GDS or OAS)."""
        # Use appropriate dialogue - both gdsExportDialogue and oasExportDialogue
        # now inherit from the same base class
        if export_format.upper() == "OAS":
            dlg = fd.oasExportDialogue(self)
        else:
            dlg = fd.gdsExportDialogue(self)

        dlg.setWindowTitle(
            f"Export {export_format.upper()} for {self.cellName}-{self.viewName}"
        )
        dlg.unitEdit.setText(fabproc.gdsUnit.render())
        dlg.precisionEdit.setText(fabproc.gdsPrecision.render())
        dlg.exportPathEdit.setText(str(self.gdsExportDirObj))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.gdsExportDir = pathlib.Path(dlg.exportPathEdit.text().strip())
            gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
            gdsPrecision = Quantity(dlg.precisionEdit.text().strip()).real

            layerMap = dlg.layerMap()
            cellNameMap = dlg.cellNameMap()
            flattenDepth = dlg.flattenDepth()

            # Call the appropriate export method
            if export_format.upper() == "OAS":
                self.centralW.scene.exportCellOAS(
                    self.gdsExportDir, gdsUnit, gdsPrecision, fabproc.dbu,
                    layerMap, cellNameMap, flattenDepth,
                )
            else:
                self.centralW.scene.exportCellGDS(
                    self.gdsExportDir, gdsUnit, gdsPrecision, fabproc.dbu,
                    layerMap, cellNameMap, flattenDepth,
                )

    def exportGDSClick(self):
        """Export layout cell as GDS format."""
        self._exportLayoutCell("GDS")

    def exportOASClick(self):
        """Export layout cell as OAS format."""
        self._exportLayoutCell("OAS")

    def handlePolygonSelection(self, polygons):
        # Remove previous polygons and reset their transforms
        for polygon in self._drcPolygons:
            try:
                polygon.setTransform(QTransform())
                self.centralW.scene.removeItem(polygon)
            except RuntimeError:
                # The scene or Qt has already destroyed the C++ object.
                pass

        # Add new polygons, applying instance transforms for sub-cell violations.
        # KLayout reports DRC violations in the cell's local coordinate system.
        # For the top cell, coordinates are already in scene space. For sub-cells
        # (pcell instances, regular instances), we need to apply the instance's
        # scene transform so the error polygon lines up with the layout.
        for polygon in polygons:
            polygonCell = polygon.cell
            if polygonCell and polygonCell != self.cellName:
                # Violation is in a sub-cell — find the matching instance and
                # apply its transform to position the polygon correctly.
                transform = self._findInstanceTransform(polygonCell)
                if transform is not None:
                    polygon.setTransform(transform)
            self.centralW.scene.addItem(polygon)

        # Remember current polygons (store reference)
        self._drcPolygons = polygons

    def _findInstanceTransform(self, gdsCellName: str):
        """Find the scene transform for an instance whose GDS cell name matches.

        GDS cell naming conventions (from exportGDS.py):
          - Regular instances: {libraryName}_{cellName}_{viewName}
          - Pcells: {libraryName}_{className}_{params}_{counter}

        Returns the QTransform of the first matching instance, or None.
        """
        from revedaEditor.common import layoutShapes as lshp

        for item in self.centralW.scene.items():
            if isinstance(item, lshp.layoutPcell):
                # Pcell GDS name starts with {libraryName}_{className}_
                prefix = f"{item.libraryName}_{type(item).__name__}_"
                if gdsCellName.startswith(prefix):
                    return item.sceneTransform()
            elif isinstance(item, lshp.layoutInstance):
                # Regular instance GDS name: {libraryName}_{cellName}_{viewName}
                instanceGDSName = f"{item.libraryName}_{item.cellName}_{item.viewName}"
                if gdsCellName == instanceGDSName:
                    return item.sceneTransform()
        return None

    def clearDRCPolygons(self):
        self.handlePolygonSelection([])

    def handleLVSRectSelection(self, rects: list[QGraphicsRectItem]):
        # Remove previous rectangles
        for rect in self._lvsRectangles:
            self.centralW.scene.removeItem(rect)

        # Add new rectangles
        for rect in rects:
            self.centralW.scene.addItem(rect)

        # Remember current rectangles (store reference)
        self._lvsRectangles = rects

    def renumberInstanceClick(self, s):
        self.centralW.scene.renumberInstances()

    def sdlLoadClick(self):
        """Open a schematic and replace the current layout from its instances."""
        libraryModel = lmview.schematicViewsModel(self.libraryDict)
        dialog = fd.selectCellViewDialog(self, libraryModel)
        dialog.libNamesCB.setCurrentText(self.libName)
        dialog.cellCB.setCurrentText(self.cellName)

        if dialog.exec() == QDialog.DialogCode.Accepted:

            libItem = libm.getLibItem(libraryModel, dialog.libNamesCB.currentText())
            cellItem = libm.getCellItem(libItem, dialog.cellCB.currentText())
            viewItem = libm.getViewItem(cellItem, dialog.viewCB.currentText())
            scene = self.centralW.scene
            if scene.items():
                reply = QMessageBox.question(
                    self,
                    "Replace Layout",
                    "Loading from a schematic removes ALL existing layout "
                    "items — not just instances — and cannot be undone.\n\n"
                    "Save the layout first if you may need its current "
                    "geometry.\n\nDo you want to proceed?",
                    QMessageBox.StandardButton.Ok
                    | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if reply != QMessageBox.StandardButton.Ok:
                    return
            scene.clear()
            scene.itemsRefSet.clear()
            # Stale undo commands hold references to the cleared items.
            scene.undoStack.clear()
            scene.loadSchematicInstances(
                ddef.viewItemTuple(libItem, cellItem, viewItem)
            )

    def dispConfigEdit(self):
        import revedaEditor.gui.propertyDialogues as pdlg

        dcd = pdlg.layoutDisplayConfigDialog(self)
        dcd.dbuEntry.setText(str(self.dbu))
        # Display grid values in layout units (e.g. µm).
        dcd.majorGridEntry.setText(str(self.majorGrid / self.dbu))
        dcd.snapGridEdit.setText(str(self.snapGrid / self.dbu))
        dcd.snapConnectEdit.setText(str(self.snapConnectDistance / self.dbu))
        dcd.lodThresholdEdit.setText(str(self.lodThreshold))
        if dcd.exec() == QDialog.DialogCode.Accepted:
            self.configureGridSettings(
                (
                    round(float(dcd.majorGridEntry.text()) * self.dbu),
                    round(float(dcd.snapGridEdit.text()) * self.dbu),
                )
            )
            self.snapConnectDistance = round(
                float(dcd.snapConnectEdit.text()) * self.dbu
            )
            if hasattr(self, 'centralW') and self.centralW:
                self.centralW.scene.snapConnectDistance = self.snapConnectDistance
            if dcd.dotType.isChecked():
                self.centralW.view.gridbackg = True
                self.centralW.view.linebackg = False
            elif dcd.lineType.isChecked():
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = True
            else:
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = False
            # Apply LOD threshold
            try:
                newThreshold = float(dcd.lodThresholdEdit.text())
                if newThreshold > 0:
                    self.lodThreshold = newThreshold
                    from revedaEditor.common.layoutShapes import layoutInstance
                    layoutInstance._lodThreshold = newThreshold
                    self.centralW.scene.update()
            except ValueError:
                pass

    def closeEvent(self, event):
        try:
            if not getattr(self, '_isPcellPreview', False) and self._lockHeld:
                self.centralW.scene.saveLayoutCell(self.file)
            if self.parentEditor is not None:
                self.parentEditor.centralW.scene.reloadScene()
            cellViewNameTuple = ddef.viewNameTuple(
                self.libName, self.cellName, self.viewName
            )
            self.appMainW.openViews.pop(cellViewNameTuple, None)
        except Exception as e:
            self.appMainW.logger.error(
                f"Error in closing layout editor window:{self.cellName}-{self.viewName}:{e}"
            )
        finally:
            event.accept()
            super().closeEvent(event)

    # def _createSignalConnections(self):
    #     super()._createSignalConnections()
    @property
    def lvsRectangles(self):
        return self._lvsRectangles
    
    @property
    def drcPolygons(self):
        return self._drcPolygons


class layoutContainer(edw.editorContainer):
    def __init__(self, parent: layoutEditor):
        super().__init__(parent=parent)
        self.editorWindow = parent
        self.scene = layoutScene(self)
        self.view = edv.layoutView(self.scene, self)
        self.lswModel = lsw.layerDataModel(laylyr.pdkAllLayers)
        layerViewTable = lsw.layerViewTable(self, self.lswModel)
        self.lswWidget = lswWindow(layerViewTable)
        self.lswWidget.setMinimumWidth(300)
        self.lswWidget.setMaximumWidth(360)
        self.lswWidget.lswTable.dataSelected.connect(self.selectLayer)
        self.lswWidget.lswTable.layerSelectable.connect(self.layerSelectableChange)
        self.lswWidget.lswTable.layerVisible.connect(self.layerVisibleChange)
        self.lswWidget.objectsTable.objectVisible.connect(self.objectVisibleChange)
        self.lswWidget.objectsTable.objectSelectable.connect(self.objectSelectableChange)
        self.init_UI()

    def init_UI(self):
        # there could be other widgets in the grid layout, such as edLayer
        # viewer/editor.
        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter()
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.insertWidget(0, self.lswWidget)
        splitter.insertWidget(1, self.view)
        # ratio of first column to second column is 5
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        vLayout.addWidget(splitter)
        self.setLayout(vLayout)

    def findSelectedLayer(self, layerName: str, layerPurpose: str) -> ddef.layLayer:
        for layer in laylyr.pdkAllLayers:
            if layer.name == layerName and layer.purpose == layerPurpose:
                return layer
        return laylyr.pdkAllLayers[0]

    def selectLayer(self, layerName: str, layerPurpose: str):
        selectedLayer = self.findSelectedLayer(layerName, layerPurpose)
        self.scene.selectEdLayer = selectedLayer

    def layerSelectableChange(
        self, layerName: str, layerPurpose: str, layerSelectable: bool
    ):
        selectedLayer = self.findSelectedLayer(layerName, layerPurpose)
        selectedLayer.selectable = layerSelectable

        pinLabels = self.scene.pinLabelItems()
        for item in self.scene.items():
            if (
                hasattr(item, "layer")
                and item.layer == selectedLayer
                and item.parentItem() is None
            ):
                item.setEnabled(
                    layerSelectable and self.scene.objectSelectable(item, pinLabels)
                )

    def layerVisibleChange(self, layerName: str, layerPurpose: str, layerVisible: bool):
        selectedLayer = self.findSelectedLayer(layerName, layerPurpose)
        selectedLayer.visible = layerVisible

        pinLabels = self.scene.pinLabelItems()
        for item in self.scene.items():
            # Vias/via arrays are composite: a single item draws its cut layer
            # plus the connecting-metal enclosure layers. Visibility is honoured
            # per layer inside paint(), so these items are only repainted (not
            # setVisible'd, which would hide the whole composite at once).
            if hasattr(item, "usesLayer"):
                if item.usesLayer(selectedLayer):
                    item.update()
            elif hasattr(item, "layer") and item.layer == selectedLayer:
                item.setVisible(
                    layerVisible and self.scene.objectVisible(item, pinLabels)
                )

    def objectVisibleChange(self, category: str, visible: bool):
        self.scene.setObjectClassVisible(category, visible)

    def objectSelectableChange(self, category: str, selectable: bool):
        self.scene.setObjectClassSelectable(category, selectable)


class LayerFilterProxyModel(QSortFilterProxyModel):
    """Proxy model that matches the search string against layer name OR purpose,
    and optionally restricts to only layers used in the layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._usedLayersOnly = False
        self._usedLayerRows: set = set()  # source-model row indices of used layers

    def setUsedLayersOnly(self, enabled: bool):
        """Enable/disable the 'show only used layers' filter."""
        self._usedLayersOnly = enabled
        self.invalidateFilter()

    def setUsedLayerRows(self, rows: set):
        """Set which source-model rows correspond to layers used in the scene."""
        self._usedLayerRows = rows
        if self._usedLayersOnly:
            self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        # Used-layers filter takes priority
        if self._usedLayersOnly and sourceRow not in self._usedLayerRows:
            return False
        pattern = self.filterRegularExpression()
        if pattern.pattern() == "":
            return True
        model = self.sourceModel()
        name_item = model.item(sourceRow, lsw.layerViewTable.columnName)
        purp_item = model.item(sourceRow, lsw.layerViewTable.columnPurpose)
        name = name_item.text() if name_item else ""
        purpose = purp_item.text() if purp_item else ""
        return pattern.match(name).hasMatch() or pattern.match(purpose).hasMatch()


class lswWindow(QWidget):
    def __init__(self, lswTable: lsw.layerViewTable):
        super().__init__()
        self.lswTable = lswTable

        # ensure widget has an opaque background so the underlying scene
        # doesn't show through in the top-left corner
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QLineEdit

        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, pal.color(QPalette.Window))
        self.setPalette(pal)

        layout = QVBoxLayout()
        toolBar = QToolBar()
        avIcon = QIcon(":/icons/eye.png")
        nvIcon = QIcon(":/icons/eye-close.png")
        avAction = QAction(avIcon, "Set Layers Visible", self)
        avAction.setToolTip("Set Layers visible")
        avAction.triggered.connect(self._allLayersVisible)
        nvAction = QAction(nvIcon, "Set Layers Invisible", self)
        nvAction.setToolTip("Set Layers invisible")
        nvAction.triggered.connect(self._noLayersVisible)
        asIcon = QIcon(":/icons/pencil.png")
        nsIcon = QIcon(":/icons/pencil-prohibition.png")
        nsAction = QAction(nsIcon, "Set Layers Selectable", self)
        nsAction.setToolTip("Set layers selectable")
        nsAction.triggered.connect(self._noLayersSelectable)
        asAction = QAction(asIcon, "Set Layers Unselectable", self)
        asAction.setToolTip("Set layers unselectable")
        asAction.triggered.connect(self._allLayersSelectable)

        # Filter used layers toggle
        fuIcon = QIcon(":/icons/layer-mask.png")
        self._filterUsedAction = QAction(fuIcon, "Show Used Layers Only", self)
        self._filterUsedAction.setToolTip("Show only layers used in the layout")
        self._filterUsedAction.setCheckable(True)
        self._filterUsedAction.toggled.connect(self._toggleUsedLayers)

        toolBar.addAction(avAction)
        toolBar.addAction(nvAction)
        toolBar.addAction(asAction)
        toolBar.addAction(nsAction)
        toolBar.addSeparator()
        toolBar.addAction(self._filterUsedAction)
        layout.addWidget(toolBar)

        # Search field
        from PySide6.QtWidgets import QLabel, QHBoxLayout

        searchLayout = QHBoxLayout()
        searchLabel = QLabel("Search:")
        searchLabel.setStyleSheet("font-weight: bold; font-size: 13px;")
        self._searchEdit = QLineEdit()
        self._searchEdit.setPlaceholderText("Filter layers by name...")
        self._searchEdit.setToolTip("Type to filter layers by name")
        self._searchEdit.setClearButtonEnabled(True)
        self._searchEdit.setMinimumHeight(24)
        self._searchEdit.setStyleSheet(
            "QLineEdit { color: palette(text); background: palette(base); }"
        )
        searchLayout.addWidget(searchLabel)
        searchLayout.addWidget(self._searchEdit)
        layout.addLayout(searchLayout)

        # Proxy model: filters layer name (col 1) OR purpose (col 2)
        self._proxyModel = LayerFilterProxyModel(self)
        self._proxyModel.setSourceModel(self.lswTable.model())
        self._proxyModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxyModel.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.lswTable.setModel(self._proxyModel)
        self._searchEdit.textChanged.connect(self._proxyModel.setFilterFixedString)

        layout.addWidget(self.lswTable)

        # Objects filter: per-category visibility/selectability below the LSW
        objectsLabel = QLabel("Objects")
        objectsLabel.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(objectsLabel)
        self.objectsModel = lsw.objectsFilterModel(
            list(self.lswTable.layoutScene.objectFilterClasses)
        )
        self.objectsTable = lsw.objectsFilterTable(self, self.objectsModel)
        layout.addWidget(self.objectsTable)
        self.setLayout(layout)

    def _updateFilteredLayers(self, visible=None, selectable=None):
        """Apply visibility/selectability only to rows currently shown by the filter."""
        sourceModel = self._proxyModel.sourceModel()
        if visible is not None:
            state = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
            col = lsw.layerViewTable.columnVisible
        else:
            state = Qt.CheckState.Checked if selectable else Qt.CheckState.Unchecked
            col = lsw.layerViewTable.columnSelectable
        # The currently selected layer is exempt from being switched off
        exemptLayer = None
        if state == Qt.CheckState.Unchecked:
            exemptLayer = self.lswTable.layoutScene.selectEdLayer
        for proxyRow in range(self._proxyModel.rowCount()):
            sourceIndex = self._proxyModel.mapToSource(
                self._proxyModel.index(proxyRow, col)
            )
            sourceRow = sourceIndex.row()
            if exemptLayer is not None:
                nameItem = sourceModel.item(sourceRow, lsw.layerViewTable.columnName)
                purpItem = sourceModel.item(sourceRow, lsw.layerViewTable.columnPurpose)
                if (
                    nameItem
                    and purpItem
                    and nameItem.text() == exemptLayer.name
                    and purpItem.text() == exemptLayer.purpose
                ):
                    continue
            item = sourceModel.item(sourceRow, col)
            if item is not None:
                item.setCheckState(state)

    def _allLayersVisible(self):
        self._updateFilteredLayers(visible=True)

    def _noLayersVisible(self):
        self._updateFilteredLayers(visible=False)

    def _allLayersSelectable(self):
        self._updateFilteredLayers(selectable=True)

    def _noLayersSelectable(self):
        self._updateFilteredLayers(selectable=False)

    def _toggleUsedLayers(self, checked: bool):
        """Toggle filtering to show only layers used in the current layout."""
        if checked:
            usedRows = self._getUsedLayerRows()
            self._proxyModel.setUsedLayerRows(usedRows)
        self._proxyModel.setUsedLayersOnly(checked)

    def _getUsedLayerRows(self) -> set:
        """Scan the layout scene and return source-model rows for layers that
        have at least one shape on them (including inside instances)."""
        scene = self.lswTable.layoutScene
        # Collect (name, purpose) tuples — always hashable
        usedLayerKeys: set = set()
        for item in scene.items():
            if hasattr(item, "layer"):
                layer = item.layer
                usedLayerKeys.add((layer.name, layer.purpose))

        # Map used layer keys back to source model row indices
        sourceModel = self._proxyModel.sourceModel()
        usedRows = set()
        for row in range(sourceModel.rowCount()):
            nameItem = sourceModel.item(row, lsw.layerViewTable.columnName)
            purpItem = sourceModel.item(row, lsw.layerViewTable.columnPurpose)
            if nameItem and purpItem:
                if (nameItem.text(), purpItem.text()) in usedLayerKeys:
                    usedRows.add(row)
        return usedRows
