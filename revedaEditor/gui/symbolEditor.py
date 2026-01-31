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

    def _symbolContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.stretchAction)

    def objPropClick(self):
        self.centralW.scene.itemProperties()

    def checkSaveCell(self):
        self.centralW.scene.saveSymbolCell(self.file)
        if self.parentEditor:
            self.parentEditor.centralW.scene.reloadScene()

    def saveCell(self):
        self.centralW.scene.saveSymbolCell(self.file)

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

    def createPinClick(self, s):
        createPinDlg = pdlg.createPinDialog(self)
        if createPinDlg.exec() == QDialog.DialogCode.Accepted:
            modeList = [False for _ in range(8)]
            modeList[0] = True
            self.centralW.scene.pinName = createPinDlg.pinName.text()
            self.centralW.scene.pinType = createPinDlg.pinType.currentText()
            self.centralW.scene.pinDir = createPinDlg.pinDir.currentText()
            self.centralW.scene.editModes.setMode("drawPin")
            self.messageLine.setText("Place pin on the symbol.")

    def rotateItemClick(self, s):
        self.centralW.scene.editModes.setMode("rotateItem")
        self.messageLine.setText("Click on an item to rotate CW 90 degrees.")

    def copyClick(self, s):
        self.centralW.scene.editModes.setMode("copyItem")
        self.centralW.scene.copySelectedItems()
        self.messageLine.setText("Copying selected items")

    def viewPropClick(self, s):
        self.centralW.scene.editModes.setMode("selectItem")
        self.centralW.scene.viewSymbolProperties()

    def loadSymbol(self):
        """
        symbol is loaded to the scene.
        """
        try:
            self.logger.info(f'Loading symbol from {self.cellName} - {self.viewName}')
            self.centralW.scene.loadDesign(self.file)
            viewNameTuple = ddef.viewTuple(self.libItem.libraryName, self.cellItem.cellName,
                                           self.viewName)
            self.appMainW.openViews[viewNameTuple] = self
        except Exception as e:
            self.logger.error(f"Error during loading symbol for {self.cellName}: {e}")

    def createLabelClick(self):
        createLabelDlg = pdlg.createSymbolLabelDialog(self)
        self.messageLine.setText("Place a label")
        createLabelDlg.labelHeightEdit.setText("12")
        if createLabelDlg.exec() == QDialog.DialogCode.Accepted:
            self.centralW.scene.editModes.setMode("addLabel")
            # directly setting scene class attributes here to pass the information.
            self.centralW.scene.labelDefinition = createLabelDlg.labelDefinition.text()
            self.centralW.scene.labelHeight = (
                createLabelDlg.labelHeightEdit.text().strip()
            )
            self.centralW.scene.labelAlignment = (
                createLabelDlg.labelAlignCombo.currentText()
            )
            self.centralW.scene.labelOrient = (
                createLabelDlg.labelOrientCombo.currentText()
            )
            self.centralW.scene.labelUse = createLabelDlg.labelUseCombo.currentText()
            self.centralW.scene.labelOpaque = (
                    createLabelDlg.labelVisiCombo.currentText() == "Yes"
            )
            self.centralW.scene.labelType = "Normal"  # default button
            if createLabelDlg.normalType.isChecked():
                self.centralW.scene.labelType = "Normal"
            elif createLabelDlg.NLPType.isChecked():
                self.centralW.scene.labelType = "NLPLabel"
            elif createLabelDlg.pyLType.isChecked():
                self.centralW.scene.labelType = "PyLabel"

    def closeEvent(self, event):
        """
        Closes the application.
        """
        try:
            self.centralW.scene.saveSymbolCell(self.file)
            cellViewNameTuple = ddef.viewTuple(self.libName, self.cellName,
                                               self.viewName)
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
