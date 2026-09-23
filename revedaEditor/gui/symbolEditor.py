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

# import numpy as np
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QToolBar,
)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.gui.editorViews as edv
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.propertyDialogues as pdlg
import revedaEditor.scenes.symbolScene as symscn


# from hashlib import new


class symbolEditor(edw.editorWindow):
    def __init__(
            self,
            viewItem: libb.viewItem,
            libraryDict: dict,
            libraryView: lmview.BaseDesignLibrariesView,
    ):
        super().__init__(viewItem, libraryDict, libraryView)
        self.setWindowTitle(f"Symbol Editor - {self.cellName} - {self.viewName}")
        self._symbolContextMenu()

    def init_UI(self):
        super().init_UI()
        # create container to position all widgets
        self.centralW = symbolContainer(self)
        self.setCentralWidget(self.centralW)

    # def _createActions(self):
    #     super()._createActions()

    def _createShortcuts(self):
        super()._createShortcuts()
        self.stretchAction.setShortcut(Qt.Key.Key_S)
        self.createRectAction.setShortcut(Qt.Key.Key_R)
        self.createLineAction.setShortcut(Qt.Key.Key_W)
        self.createLabelAction.setShortcut(Qt.Key.Key_L)
        self.createPinAction.setShortcut(Qt.Key.Key_P)

    def _createToolBars(self):  # redefine the toolbar in the editorWindow class
        super()._createToolBars()
        self.symbolToolbar = QToolBar("Symbol Toolbar", self)
        self.addToolBar(self.symbolToolbar)
        self.symbolToolbar.addAction(self.createLineAction)
        self.symbolToolbar.addAction(self.createRectAction)
        self.symbolToolbar.addAction(self.createPolygonAction)
        self.symbolToolbar.addAction(self.createCircleAction)
        self.symbolToolbar.addAction(self.createArcAction)
        self.symbolToolbar.addAction(self.createLabelAction)
        self.symbolToolbar.addAction(self.createPinAction)
        self.symbolToolbar.addSeparator()
        self.symbolToolbar.addAction(self.selectPinAction)
        self.symbolToolbar.addAction(self.selectShapeAction)
        self.symbolToolbar.addAction(self.selectLabelAction)
        self.symbolToolbar.addAction(self.removeSelectFilterAction)

    def _addActions(self):
        super()._addActions()
        self.menuEdit.addAction(self.stretchAction)
        self.menuEdit.addAction(self.viewPropAction)
        self.menuCreate.addAction(self.createLineAction)
        self.menuCreate.addAction(self.createRectAction)
        self.menuCreate.addAction(self.createPolygonAction)
        self.menuCreate.addAction(self.createCircleAction)
        self.menuCreate.addAction(self.createArcAction)
        self.menuCreate.addAction(self.createLabelAction)
        self.menuCreate.addAction(self.createPinAction)

        # Selection filter submenu
        self.selectMenu = self.menuUtilities.addMenu("Selection")
        self.selectMenu.addAction(self.selectPinAction)
        self.selectMenu.addAction(self.selectShapeAction)
        self.selectMenu.addAction(self.selectLabelAction)
        self.selectMenu.addAction(self.selectTextAction)
        self.selectMenu.addSeparator()
        self.selectMenu.addAction(self.removeSelectFilterAction)

        if hasattr(self._app, 'pluginsObj') and hasattr(self._app.pluginsObj, 'applyPluginMenus'):
            self._app.pluginsObj.applyPluginMenus(self)

    def _createTriggers(self):
        super()._createTriggers()
        self.createLineAction.triggered.connect(self.createLineClick)
        self.createRectAction.triggered.connect(self.createRectClick)
        self.createPolygonAction.triggered.connect(self.createPolyClick)
        self.createArcAction.triggered.connect(self.createArcClick)
        self.createCircleAction.triggered.connect(self.createCircleClick)
        self.createLabelAction.triggered.connect(self.createLabelClick)
        self.createPinAction.triggered.connect(self.createPinClick)
        self.objPropAction.triggered.connect(self.objPropClick)
        self.deleteAction.triggered.connect(self.deleteClick)
        self.viewPropAction.triggered.connect(self.viewPropClick)
        # Selection filter triggers
        self.selectPinAction.triggered.connect(self.selectPinClick)
        self.selectShapeAction.triggered.connect(self.selectShapeClick)
        self.selectLabelAction.triggered.connect(self.selectLabelClick)
        self.selectTextAction.triggered.connect(self.selectTextClick)
        self.removeSelectFilterAction.triggered.connect(self.removeSelectFilterClick)

    def _symbolContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.stretchAction)

    def objPropClick(self):
        self.centralW.scene.itemProperties()

    def selectPinClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectPin")
        self.messageLine.setText("Select Only Pins")

    def selectShapeClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectShape")
        self.messageLine.setText("Select Only Shapes")

    def selectLabelClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectLabel")
        self.messageLine.setText("Select Only Labels")

    def selectTextClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectText")
        self.messageLine.setText("Select Only Text")

    def removeSelectFilterClick(self, s=None):
        self.centralW.scene.selectModes.setMode("selectAll")
        self.messageLine.setText("Select All Objects")

    def checkSaveCell(self):
        self.centralW.scene.saveSymbolCell(self.file)
        self._clearAutosave()
        if self.parentEditor:
            self.parentEditor.centralW.scene.reloadScene()

    def saveCell(self):
        self.centralW.scene.saveSymbolCell(self.file)
        self._clearAutosave()

    def createRectClick(self, s):
        self.centralW.scene.editModes.setMode("drawRect")
        self.messageLine.setText("Press left mouse button for the first point.")

    def createLineClick(self, s):
        self.centralW.scene.editModes.setMode("drawLine")
        self.messageLine.setText("Press left mouse button for the first point.")

    def createPolyClick(self, s):
        self.centralW.scene.editModes.setMode("drawPolygon")
        self.messageLine.setText("Press left mouse button for the first point.")

    def createArcClick(self, s):
        self.centralW.scene.editModes.setMode("drawArc")
        self.messageLine.setText("Press left mouse button for the first point.")

    def createCircleClick(self, s):
        self.centralW.scene.editModes.setMode("drawCircle")
        self.messageLine.setText("Press left mouse button for the centre point.")

    def editActivePlacementOptions(self) -> bool:
        """Open the F3 form for the active symbol placement command."""
        scene = self.centralW.scene
        if scene.editModes.drawPin:
            self._configureSymbolPin(activate=False)
        elif scene.editModes.addLabel:
            self._configureSymbolLabel(activate=False)
        else:
            return False
        return True

    def createPinClick(self, s):
        self._configureSymbolPin(activate=True)

    def _configureSymbolPin(self, activate: bool = False) -> bool:
        """Edit pending symbol-pin values without leaving draw mode."""
        scene = self.centralW.scene
        dlg = pdlg.createPinDialog(self)
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
            self.messageLine.setText("Place pin on the symbol.")
        return True

    def rotateItemClick(self, s):
        self.centralW.scene.editModes.setMode("rotateItem")
        self.messageLine.setText("Click on an item to rotate CW 90 degrees.")

    def viewPropClick(self, s):
        self.centralW.scene.editModes.setMode("selectItem")
        self.centralW.scene.viewSymbolProperties()

    def loadSymbol(self):
        """
        symbol is loaded to the scene.
        """
        try:
            self.logger.info(f'Loading symbol from {self.cellName} - {self.viewName}')
            self.centralW.scene.loadDesign(self._resolveLoadPath())
            viewNameTuple = ddef.viewNameTuple(self.libItem.libraryName, self.cellItem.cellName,
                                               self.viewName)
            self.appMainW.openViews[viewNameTuple] = self
        except Exception as e:
            self.logger.error(f"Error during loading symbol for {self.cellName}: {e}")

    def createLabelClick(self):
        self._configureSymbolLabel(activate=True)

    def _configureSymbolLabel(self, activate: bool = False) -> bool:
        """Edit pending symbol-label values without leaving draw mode."""
        scene = self.centralW.scene
        dlg = pdlg.createSymbolLabelDialog(self)
        dlg.labelDefinition.setText(scene.labelDefinition or "")
        dlg.labelHeightEdit.setText(str(scene.labelHeight or "12"))
        dlg.labelAlignCombo.setCurrentText(scene.labelAlignment or "")
        dlg.labelOrientCombo.setCurrentText(scene.labelOrient or "")
        dlg.labelUseCombo.setCurrentText(scene.labelUse or "")
        dlg.labelVisiCombo.setCurrentText("Yes" if scene.labelOpaque else "No")
        if scene.labelType == "NLPLabel":
            dlg.NLPType.setChecked(True)
        elif scene.labelType == "PyLabel":
            dlg.pyLType.setChecked(True)
        else:
            dlg.normalType.setChecked(True)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        scene.labelDefinition = dlg.labelDefinition.text()
        scene.labelHeight = dlg.labelHeightEdit.text().strip()
        scene.labelAlignment = dlg.labelAlignCombo.currentText()
        scene.labelOrient = dlg.labelOrientCombo.currentText()
        scene.labelUse = dlg.labelUseCombo.currentText()
        scene.labelOpaque = dlg.labelVisiCombo.currentText() == "Yes"
        scene.labelType = (
            "NLPLabel" if dlg.NLPType.isChecked() else
            "PyLabel" if dlg.pyLType.isChecked() else "Normal")
        if activate:
            scene.editModes.setMode("addLabel")
            self.messageLine.setText("Place a label")
        return True

    def closeEvent(self, event):
        """
        Closes the application.
        """
        try:
            if self._lockHeld:
                self.centralW.scene.saveSymbolCell(self.file)
            if self.parentEditor is not None:
                self.parentEditor.centralW.scene.reloadScene()
            cellViewNameTuple = ddef.viewNameTuple(self.libName, self.cellName,
                                                   self.viewName)
            self.appMainW.symbolChanged.emit(self.libName, self.cellName, self.viewName)
            self.appMainW.openViews.pop(cellViewNameTuple, None)
        except Exception as e:
            self.appMainW.logger.error(
                f"Error in closing symbol window for {self.cellName}: {e}")
        finally:
            event.accept()
            super().closeEvent(event)


class symbolContainer(edw.editorContainer):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.editorWindow = parent
        self.scene = symscn.symbolScene(self)
        self.view = edv.symbolView(self.scene, self)
        self.init_UI()

    def init_UI(self):
        # layout statements, using a grid layout
        gLayout = QGridLayout()
        gLayout.setSpacing(10)
        gLayout.addWidget(self.view, 0, 0)
        gLayout.setColumnStretch(0, 5)
        gLayout.setRowStretch(0, 6)
        self.setLayout(gLayout)
