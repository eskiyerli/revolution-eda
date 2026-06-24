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

import os
import pathlib
import shutil
import subprocess
import tempfile
import time

import numpy as np
from contextlib import contextmanager
from logging import getLogger
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import (Qt, QSize, QSizeF, QMarginsF, QRectF)
from PySide6.QtGui import (QAction, QIcon, QImage, QKeySequence, QPageSize, QPainter)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QGraphicsScene,
                               QLabel, QMainWindow, QDialogButtonBox,
                               QMenu, QToolBar, QWidget, QMessageBox)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.backend.processManager as prm
import revedaEditor.gui.alignItems as alg
import revedaEditor.gui.helpBrowser as hlp
import revedaEditor.gui.propertyDialogues as pdlg
import revedaEditor.resources.resources  # noqa: F401
from revedaEditor.backend.startThread import startThread
from revedaEditor.gui.editorViews import editorView
from revedaEditor.scenes.editorScene import editorScene

if TYPE_CHECKING:
    from revedaEditor.gui.editorTypes import EditorContainer


class editorWindow(QMainWindow):
    """
    Base class for editor windows.
    """
    MAIN_LOGGER = "reveda"
    MAJOR_GRID_DEFAULT = 20
    SNAP_GRID_DEFAULT = 10
    SNAP_CONNECT_DISTANCE_DEFAULT = 20

    def __init__(self, viewItem: libb.viewItem, libraryDict: dict,
                 libraryView: lmview.BaseDesignLibrariesView) -> None:
        super().__init__()

        self.viewItem = viewItem
        self.file: pathlib.Path = self.viewItem.data(
            Qt.ItemDataRole.UserRole + 2)  # pathlib Path object
        self.cellItem: libb.cellItem = self.viewItem.parent()
        self.cellName = self.cellItem.cellName
        self.libItem: libb.libraryItem = self.cellItem.parent()
        self.libName: str = self.libItem.libraryName
        self.viewName: str = self.viewItem.viewName
        self.libraryDict = libraryDict
        self.libraryView = libraryView
        self.parentEditor: Optional[editorWindow] = None
        self.parentObj = None  # type symbol or layoutInstance
        self._app = QApplication.instance()  # main application pointer
        self.appMainW = self._app.appMainW  # main window pointer
        self.logger = getLogger(self.MAIN_LOGGER)
        self.switchViewList = self.appMainW.switchViewList
        self.stopViewList = self.appMainW.stopViewList
        self.statusLine = self.statusBar()
        self.messageLine = QLabel()  # message line
        self.statusLine.insertPermanentWidget(0, self.messageLine)
        self.majorGrid = self.MAJOR_GRID_DEFAULT  # dot/line grid spacing
        self.snapGrid = self.SNAP_GRID_DEFAULT  # snapping grid size
        self.snapTuple = (self.snapGrid, self.snapGrid)
        self.snapConnectDistance = self.SNAP_CONNECT_DISTANCE_DEFAULT
        self.processManager = prm.ProcessManager(3, self)
        self.init_UI()
        self._createSignalConnections()

    def __repr__(self):
        return f'editorWindow({self.libName}-{self.cellName}-{self.viewName})'

    def init_UI(self) -> None:
        self.centralW: EditorContainer = editorContainer(self)
        self.setCentralWidget(self.centralW)
        self.resize(1600, 800)
        self._createActions()
        self._createMenuBar()
        self._createToolBars()
        self._addActions()
        self._createTriggers()
        self._createShortcuts()

    def _createMenuBar(self):
        """
        Creates the menu bar for the editor.

        """
        self.editorMenuBar = self.menuBar()
        self.editorMenuBar.setNativeMenuBar(False)
        # Returns QMenu object.
        self.menuFile = self.editorMenuBar.addMenu("&File")
        self.menuView = self.editorMenuBar.addMenu("&View")
        self.menuEdit = self.editorMenuBar.addMenu("&Edit")
        self.menuCreate = self.editorMenuBar.addMenu("C&reate")
        self.menuOptions = self.editorMenuBar.addMenu("&Options")
        self.menuCheck = self.editorMenuBar.addMenu("&Check")
        self.menuTools = self.editorMenuBar.addMenu("&Tools")
        # self.menuWindow = self.editorMenuBar.addMenu("&Window")
        self.menuUtilities = self.editorMenuBar.addMenu("&Utilities")
        self.menuHelp = self.editorMenuBar.addMenu("&Help")

    def _createActions(self):
        checkCellIcon = QIcon(":/icons/document-task.png")
        self.checkCellAction = QAction(checkCellIcon, "Check-Save", self)

        saveCellIcon = QIcon(":/icons/document--plus.png")
        self.saveCellAction = QAction(saveCellIcon, "Save", self)

        self.readOnlyCellIcon = QIcon(":/icons/lock.png")
        self.readOnlyCellAction = QAction("Read Only", self)
        self.readOnlyCellAction.setCheckable(True)

        updateCellIcon = QIcon(":/icons/document-xaml.png")
        self.updateCellAction = QAction(updateCellIcon, "Update Design", self)
        self.updateCellAction.setToolTip("Reread all the cells in the design")

        printIcon = QIcon(":/icons/printer--arrow.png")
        self.printAction = QAction(printIcon, "Print...", self)
        self.printAction.setToolTip("Print the current design")

        printPreviewIcon = QIcon(":/icons/printer--arrow.png")
        self.printPreviewAction = QAction(printPreviewIcon, "Print Preview...",
                                          self)
        self.printPreviewAction.setToolTip("Preview the current design output")

        exportImageIcon = QIcon(":/icons/image-export.png")
        self.exportImageAction = QAction(exportImageIcon, "Export...", self)
        self.exportImageAction.setToolTip("Export the current design as an image")

        exitIcon = QIcon(":/icons/external.png")
        self.exitAction = QAction(exitIcon, "Close Window", self)
        self.exitAction.setShortcut("Ctrl+Q")
        self.exitAction.setToolTip("Close the current window")

        fitIcon = QIcon(":/icons/zone.png")
        self.fitAction = QAction(fitIcon, "Fit to Window", self)
        self.fitAction.setToolTip("Fit the design to the window")

        zoomInIcon = QIcon(":/icons/zone-resize.png")
        self.zoomInAction = QAction(zoomInIcon, "Zoom In", self)
        self.zoomInAction.setToolTip("Zoom in on the design")

        zoomOutIcon = QIcon(":/icons/zone-resize-actual.png")
        self.zoomOutAction = QAction(zoomOutIcon, "Zoom Out", self)
        self.zoomOutAction.setToolTip("Zoom out on the design")

        panIcon = QIcon(":/icons/zone--arrow.png")
        self.panAction = QAction(panIcon, "Pan View", self)
        self.panAction.setToolTip("Pan the design")

        redrawIcon = QIcon(":/icons/arrow-circle.png")
        self.redrawAction = QAction(redrawIcon, "Redraw", self)
        self.redrawAction.setToolTip("Redraw the design on the screen")

        rulerIcon = QIcon(":/icons/ruler.png")
        self.rulerAction = QAction(rulerIcon, "Add Ruler", self)
        self.rulerAction.setToolTip("Add a ruler to the layout")

        delRulerIcon = QIcon(":/icons/ruler--minus.png")
        self.delRulerAction = QAction(delRulerIcon, "Delete Rulers", self)
        self.delRulerAction.setToolTip("Delete all the rulers from the layout")

        alignIcon = QIcon(":/icons/layers-alignment-middle.png")
        self.alignItemsAction = QAction(alignIcon, "Align Items...", self)
        self.alignItemsAction.setToolTip("Align selected items")

        # display options
        dispConfigIcon = QIcon(":/icons/grid-snap-dot.png")
        self.dispConfigAction = QAction(dispConfigIcon, "Display Config...", self)
        self.dispConfigAction.setToolTip("Configure the display options")

        selectConfigIcon = QIcon(":/icons/zone-select.png")
        self.selectConfigAction = QAction(selectConfigIcon, "Selection Config...",
                                          self)
        self.selectConfigAction.setToolTip("Configure the selection options")

        panZoomConfigIcon = QIcon(":/icons/selection-resize.png")
        self.panZoomConfigAction = QAction(panZoomConfigIcon,
                                           "Pan/Zoom Config...", self)
        self.panZoomConfigAction.setToolTip("Configure the pan/zoom options")

        undoIcon = QIcon(":/icons/arrow-circle-315-left.png")
        self.undoAction = QAction(undoIcon, "Undo", self)
        self.undoAction.setToolTip("Undo the last action")

        redoIcon = QIcon(":/icons/arrow-circle-225.png")
        self.redoAction = QAction(redoIcon, "Redo", self)
        self.redoAction.setToolTip("Redo the last undone action")

        yankIcon = QIcon(":/icons/node-insert.png")
        self.yankAction = QAction(yankIcon, "Yank", self)

        pasteIcon = QIcon(":/icons/clipboard-paste.png")
        self.pasteAction = QAction(pasteIcon, "Paste", self)
        self.pasteAction.setToolTip("Paste the contents of the clipboard")

        deleteIcon = QIcon(":/icons/node-delete.png")
        self.deleteAction = QAction(deleteIcon, "Delete", self)
        self.deleteAction.setToolTip("Delete selected items")

        copyIcon = QIcon(":/icons/document-copy.png")
        self.copyAction = QAction(copyIcon, "Copy", self)
        self.copyAction.setToolTip("Copy selected items")

        moveIcon = QIcon(":/icons/arrow-move.png")
        self.moveAction = QAction(moveIcon, "Move", self)
        self.moveAction.setToolTip("Move selected items")

        constrainedMoveIcon = QIcon(":/icons/arrow-move.png")
        self.constrainedMoveAction = QAction(constrainedMoveIcon, "Constrained Move", self)
        self.constrainedMoveAction.setToolTip("Move with constraints (Shift+M: Shift=Ortho+Diagonal, Ctrl=Ortho)")

        moveByIcon = QIcon(":/icons/arrow-transition.png")
        self.moveByAction = QAction(moveByIcon, "Move By ...", self)
        self.moveAction.setToolTip("Move selected items by an offset")

        moveOriginIcon = QIcon(":/icons/arrow-skip.png")
        self.moveOriginAction = QAction(moveOriginIcon, "Move Origin", self)
        self.moveOriginAction.setToolTip("Move the origin of the design")

        stretchIcon = QIcon(":/icons/fill.png")
        self.stretchAction = QAction(stretchIcon, "Stretch", self)
        self.stretchAction.setToolTip("Stretch item")

        rotateIcon = QIcon(":/icons/arrow-circle.png")
        self.rotateAction = QAction(rotateIcon, "Rotate...", self)
        self.rotateAction.setToolTip("Rotate item")

        scaleIcon = QIcon(":/icons/selection-resize.png")
        self.scaleAction = QAction(scaleIcon, "Scale...", self)
        self.scaleAction.setToolTip("Scale item")

        verticalFlipIcon = QIcon(":/icons/layer-flip-vertical.png")
        self.verticalFlipAction = QAction(verticalFlipIcon, "Vertical Flip", self)
        self.verticalFlipAction.setToolTip("Vertical Flip")

        horizontalFlipIcon = QIcon(":/icons/layer-flip.png")
        self.horizontalFlipAction = QAction(horizontalFlipIcon, "Horizontal Flip",
                                            self)
        self.horizontalFlipAction.setToolTip("Horizontal Flip")

        netNameIcon = QIcon(":/icons/node-design.png")
        self.netNameAction = QAction(netNameIcon, "Net Name...", self)
        self.netNameAction.setToolTip("Set net name")

        # create label action but do not add to any menu.
        createLabelIcon = QIcon(":/icons/tag-label-yellow.png")
        self.createLabelAction = QAction(createLabelIcon, "Create Label...", self)
        self.createLabelAction.setToolTip("Create Label")

        createPinIcon = QIcon(":/icons/pin.png")
        self.createPinAction = QAction(createPinIcon, "Create Pin...", self)
        self.createPinAction.setToolTip("Create Pin")

        goUpIcon = QIcon(":/icons/arrow-step-out.png")
        self.goUpAction = QAction(goUpIcon, "Go Up", self)
        self.goUpAction.setToolTip("Go up a level in design hierarchy")

        goDownIcon = QIcon(":/icons/arrow-step.png")
        self.goDownAction = QAction(goDownIcon, "Go Down", self)
        self.goDownAction.setToolTip("Go down a level in design hierarchy")

        self.selectAllIcon = QIcon(":/icons/node-select-all.png")
        self.selectAllAction = QAction(self.selectAllIcon, "Select All", self)
        self.selectAllAction.setToolTip("Select all items in the design")

        deselectAllIcon = QIcon(":/icons/node.png")
        self.deselectAllAction = QAction(deselectAllIcon, "Unselect All", self)
        self.deselectAllAction.setToolTip("Unselect all items in the design")

        objPropIcon = QIcon(":/icons/property-blue.png")
        self.objPropAction = QAction(objPropIcon, "Object Properties...", self)
        self.objPropAction.setToolTip("Configure object properties")

        viewPropIcon = QIcon(":/icons/property.png")
        self.viewPropAction = QAction(viewPropIcon, "Cellview Properties...",
                                      self)
        self.viewPropAction.setToolTip("Configure Cellview Properties")

        viewCheckIcon = QIcon(":/icons/ui-check-box.png")
        self.viewCheckAction = QAction(viewCheckIcon, "Check CellView", self)
        self.viewCheckAction.setToolTip("Check Cellview")

        viewErrorsIcon = QIcon(":/icons/report--exclamation.png")
        self.viewErrorsAction = QAction(viewErrorsIcon, "View Errors...", self)
        self.viewErrorsAction.setToolTip("View Errros")

        deleteErrorsIcon = QIcon(":/icons/report--minus.png")
        self.deleteErrorsAction = QAction(deleteErrorsIcon, "Delete Errors...",
                                          self)
        self.deleteErrorsAction.setToolTip("Delete Errros")

        netlistIcon = QIcon(":/icons/script-text.png")
        self.netlistAction = QAction(netlistIcon, "Create Netlist...", self)
        self.netlistAction.setToolTip("Create Netlist")

        createLineIcon = QIcon(":/icons/layer-shape-line.png")
        self.createLineAction = QAction(createLineIcon, "Create Line...", self)
        self.createLineAction.setToolTip("Create Line")

        createRectIcon = QIcon(":/icons/layer-shape.png")
        self.createRectAction = QAction(createRectIcon, "Create Rectangle...",
                                        self)
        self.createRectAction.setToolTip("Create Rectangle")

        createPolyIcon = QIcon(":/icons/layer-shape-polygon.png")
        self.createPolygonAction = QAction(createPolyIcon, "Create Polygon...",
                                           self)
        self.createPolygonAction.setToolTip("Create Polygon")

        createCircleIcon = QIcon(":/icons/layer-shape-ellipse.png")
        self.createCircleAction = QAction(createCircleIcon, "Create Circle...",
                                          self)
        self.createCircleAction.setToolTip("Create Circle")

        createArcIcon = QIcon(":/icons/layer-shape-polyline.png")
        self.createArcAction = QAction(createArcIcon, "Create Arc...", self)
        self.createArcAction.setToolTip("Create Arc")

        createViaIcon = QIcon(":/icons/layer-mask.png")
        self.createViaAction = QAction(createViaIcon, "Create Via...", self)
        self.createViaAction.setToolTip("Create Via")

        createInstIcon = QIcon(":/icons/block--plus.png")
        self.createInstAction = QAction(createInstIcon, "Create Instance...",
                                        self)
        self.createInstAction.setToolTip("Create Instance")

        self.createNetAction = QAction(createLineIcon, "Create Net...", self)
        self.createNetAction.setToolTip("Create Net")

        self.createPathAction = QAction(createLineIcon, "Create Path...", self)
        self.createPathAction.setToolTip("Create Path")

        createBusIcon = QIcon(":/icons/node-select-all.png")
        self.createBusAction = QAction(createBusIcon, "Create Bus...", self)
        self.createBusAction.setToolTip("Create Bus")

        createSymbolIcon = QIcon(":/icons/application-block.png")
        self.createSymbolAction = QAction(createSymbolIcon, "Create Symbol...",
                                          self)
        self.createSymbolAction.setToolTip("Create Symbol from Cellview")

        createTextIcon = QIcon(":/icons/sticky-note-text.png")
        self.createTextAction = QAction(createTextIcon, "Create Text...", self)
        self.createTextAction.setToolTip("Create Text")

        # selection Actions
        selectDeviceIcon = QIcon(":/icons/target.png")
        self.selectDeviceAction = QAction(selectDeviceIcon, "Select Devices",
                                          self)
        self.selectDeviceAction.setToolTip("Select Devices Only")

        selectNetIcon = QIcon(":/icons/pencil--plus.png")
        self.selectNetAction = QAction(selectNetIcon, "Select Nets", self)
        self.selectNetAction.setToolTip("Select Nets Only")

        self.selectWireAction = QAction(selectNetIcon, "Select Wires", self)
        self.selectWireAction.setToolTip("Select Wires Only")

        selectPinIcon = QIcon(":/icons/pin--plus.png")
        self.selectPinAction = QAction(selectPinIcon, "Select Pins", self)
        self.selectPinAction.setToolTip("Select Pins Only")

        removeSelectFilterIcon = QIcon(":icons/eraser.png")
        self.removeSelectFilterAction = QAction(removeSelectFilterIcon,
                                                "Remove Select Filters", self)
        self.removeSelectFilterAction.setToolTip("Remove Selection Filters")

        selectShapeIcon = QIcon(":icons/layer-shape.png")
        self.selectShapeAction = QAction(selectShapeIcon, "Select Shapes", self)
        self.selectShapeAction.setToolTip("Select Shapes Only")

        self.selectLabelAction = QAction("Select Labels", self)
        self.selectLabelAction.setToolTip("Select Labels Only")

        selectTextIcon = QIcon(":/icons/cheque--plus.png")
        self.selectTextAction = QAction(selectTextIcon, "Select Text", self)
        self.selectTextAction.setToolTip("Select Text Only")

        ignoreIcon = QIcon(":/icons/minus-circle.png")
        self.ignoreAction = QAction(ignoreIcon, "Ignore", self)
        self.ignoreAction.setToolTip("Ignore selected cell")

        helpIcon = QIcon(":/icons/document-arrow.png")
        self.helpAction = QAction(helpIcon, "Help...", self)
        self.helpAction.setToolTip("Help")

        self.aboutIcon = QIcon(":/icons/information.png")
        self.aboutAction = QAction(self.aboutIcon, "About", self)

    def _createToolBars(self):
        # Create tools bar called "main toolbar"
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setIconSize(QSize(32, 32))
        # place toolbar at top
        self.addToolBar(self.toolbar)
        self.toolbar.addAction(self.saveCellAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.printAction)
        self.toolbar.addAction(self.exportImageAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.undoAction)
        self.toolbar.addAction(self.redoAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.deleteAction)
        self.toolbar.addAction(self.moveAction)
        self.toolbar.addAction(self.copyAction)
        self.toolbar.addAction(self.stretchAction)
        self.toolbar.addAction(self.rotateAction)
        self.toolbar.addAction(self.horizontalFlipAction)
        self.toolbar.addAction(self.verticalFlipAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.fitAction)
        self.toolbar.addAction(self.zoomInAction)
        self.toolbar.addAction(self.zoomOutAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.objPropAction)

    def _addActions(self):
        # file menu
        self.menuFile.addAction(self.checkCellAction)
        self.menuFile.addAction(self.saveCellAction)
        self.menuFile.addAction(self.updateCellAction)
        self.menuFile.addAction(self.printAction)
        self.menuFile.addAction(self.printPreviewAction)
        self.menuFile.addAction(self.exportImageAction)
        self.menuFile.addAction(self.exitAction)
        # view menu
        self.menuView.addAction(self.fitAction)
        self.menuView.addAction(self.zoomInAction)
        self.menuView.addAction(self.zoomOutAction)
        self.menuView.addAction(self.panAction)
        self.menuView.addAction(self.redrawAction)
        # self.menuView.addAction(self.panZoomConfigAction)
        # edit menu
        self.menuEdit.addAction(self.undoAction)
        self.menuEdit.addAction(self.redoAction)
        # self.menuEdit.addAction(self.yankAction)
        self.menuEdit.addAction(self.pasteAction)
        self.menuEdit.addAction(self.deleteAction)
        self.menuEdit.addAction(self.copyAction)
        self.menuEdit.addAction(self.moveAction)
        self.menuEdit.addAction(self.constrainedMoveAction)
        self.menuEdit.addAction(self.moveByAction)
        self.menuEdit.addAction(self.moveOriginAction)
        self.menuEdit.addAction(self.stretchAction)
        self.menuEdit.addAction(self.rotateAction)
        self.menuEdit.addAction(self.horizontalFlipAction)
        self.menuEdit.addAction(self.verticalFlipAction)
        self.menuEdit.addAction(self.alignItemsAction)
        self.selectMenu = QMenu('Selection', self)
        self.selectMenu.setIcon(QIcon('icons/node-select.png'))
        self.menuEdit.addMenu(self.selectMenu)
        self.selectMenu.addAction(self.selectAllAction)
        self.selectMenu.addAction(self.deselectAllAction)
        self.menuTools.addAction(self.readOnlyCellAction)
        # self.menuCheck.addAction(self.viewCheckAction)
        self.menuOptions.addAction(self.dispConfigAction)
        self.menuOptions.addAction(self.selectConfigAction)
        self.menuHelp.addAction(self.helpAction)
        self.menuHelp.addAction(self.aboutAction)

    def helpClick(self):
        helpBrowser = hlp.helpBrowser(self)
        helpBrowser.show()

    def aboutClick(self):
        abtDlg = hlp.aboutDialog(self)
        abtDlg.show()

    def _createTriggers(self):
        self.checkCellAction.triggered.connect(self.checkSaveCell)
        self.saveCellAction.triggered.connect(self.saveCell)
        self.readOnlyCellAction.triggered.connect(self.readOnlyCellClick)
        self.updateCellAction.triggered.connect(self.updateDesignScene)
        self.printAction.triggered.connect(self.printClick)
        self.printPreviewAction.triggered.connect(self.printPreviewClick)
        self.exportImageAction.triggered.connect(self.imageExportClick)
        self.exitAction.triggered.connect(self.closeWindow)
        self.fitAction.triggered.connect(self.fitToWindow)
        self.redrawAction.triggered.connect(self.redraw)
        self.zoomInAction.triggered.connect(self.zoomIn)
        self.zoomOutAction.triggered.connect(self.zoomOut)
        self.panAction.triggered.connect(self.panView)
        self.dispConfigAction.triggered.connect(self.dispConfigEdit)
        self.selectConfigAction.triggered.connect(self.selectConfigEdit)
        self.stretchAction.triggered.connect(self.stretchClick)
        self.moveOriginAction.triggered.connect(self.moveOrigin)
        self.selectAllAction.triggered.connect(self.selectAllClick)
        self.deselectAllAction.triggered.connect(self.deselectAllClick)
        self.deleteAction.triggered.connect(self.deleteClick)
        self.copyAction.triggered.connect(self.copyClick)
        self.undoAction.triggered.connect(self.undoClick)
        self.redoAction.triggered.connect(self.redoClick)
        self.moveAction.triggered.connect(self.moveClick)
        self.constrainedMoveAction.triggered.connect(self.constrainedMoveClick)
        self.moveByAction.triggered.connect(self.moveByClick)
        self.rotateAction.triggered.connect(self.rotateItemClick)
        self.verticalFlipAction.triggered.connect(self.verticalFlipClick)
        self.horizontalFlipAction.triggered.connect(self.horizontalFlipClick)
        self.alignItemsAction.triggered.connect(self.alignItemsClick)
        self.goUpAction.triggered.connect(self.goUpHierarchy)
        self.helpAction.triggered.connect(self.helpClick)
        self.aboutAction.triggered.connect(self.aboutClick)

    def _createShortcuts(self):
        self.redoAction.setShortcut("Shift+U")
        self.undoAction.setShortcut(Qt.Key.Key_U)
        self.objPropAction.setShortcut(Qt.Key.Key_Q)
        self.constrainedMoveAction.setShortcut("Shift+M")
        self.copyAction.setShortcut(Qt.Key.Key_C)
        self.rotateAction.setShortcut("Ctrl+R")
        self.createTextAction.setShortcut("Shift+L")
        self.fitAction.setShortcut(Qt.Key.Key_F)
        self.deleteAction.setShortcut(QKeySequence.StandardKey.Delete)
        self.selectAllAction.setShortcut("Ctrl+A")
        self.stretchAction.setShortcut(Qt.Key.Key_S)
        self.alignItemsAction.setShortcut("Shift+A")

    def _editorContextMenu(self):
        self.centralW.scene.itemContextMenu.addAction(self.copyAction)
        self.centralW.scene.itemContextMenu.addAction(self.moveAction)
        self.centralW.scene.itemContextMenu.addAction(self.moveByAction)
        self.centralW.scene.itemContextMenu.addAction(self.verticalFlipAction)
        self.centralW.scene.itemContextMenu.addAction(self.horizontalFlipAction)
        self.centralW.scene.itemContextMenu.addAction(self.rotateAction)
        self.centralW.scene.itemContextMenu.addAction(self.deleteAction)
        self.centralW.scene.itemContextMenu.addAction(self.objPropAction)
        self.centralW.scene.itemContextMenu.addAction(self.selectAllAction)
        self.centralW.scene.itemContextMenu.addAction(self.deselectAllAction)

    def checkSaveCell(self):
        pass

    def saveCell(self):
        pass

    def dispConfigEdit(self):

        dcd = pdlg.displayConfigDialog(self)
        dcd.majorGridEntry.setText(str(self.majorGrid))
        dcd.snapGridEdit.setText(str(self.snapGrid))
        dcd.snapConnectEdit.setText(str(self.snapConnectDistance))
        if dcd.exec() == QDialog.DialogCode.Accepted:
            self.configureGridSettings(
                (int(dcd.majorGridEntry.text()), int(dcd.snapGridEdit.text())))
            self.snapConnectDistance = int(dcd.snapConnectEdit.text())
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

    def configureGridSettings(self, gridSettings: tuple[int, int]) -> None:
        """Configure grid settings from decoded data."""
        try:

            # Update editor window
            self.majorGrid, self.snapGrid = gridSettings
            # majorG, snapG = gridSettings
            # print(majorG, snapG)
            self.snapTuple = (self.snapGrid, self.snapGrid)

            # Update scene and view if they exist and have these attributes
            if hasattr(self, 'centralW') and self.centralW:
                for obj in (self.centralW.scene, self.centralW.view):
                    if hasattr(obj, 'majorGrid'):
                        obj.majorGrid = self.majorGrid
                    if hasattr(obj, 'snapGrid'):
                        obj.snapGrid = self.snapGrid
                    if hasattr(obj, 'snapTuple'):
                        obj.snapTuple = (self.snapGrid, self.snapGrid)
                    if hasattr(obj, 'snapConnectDistance'):
                        obj.snapConnectDistance = self.snapConnectDistance
                self.centralW.scene.invalidate(self.centralW.scene.sceneRect(),
                                               QGraphicsScene.SceneLayer.BackgroundLayer)
        except Exception as e:
            self.logger.info(f'Problem with grid settings: {e}')

    def selectConfigEdit(self):
        scd = pdlg.selectConfigDialogue(self)
        if self.centralW.scene.partialSelection:
            scd.partialSelection.setChecked(True)
        else:
            scd.fullSelection.setChecked(True)
        if scd.exec() == QDialog.DialogCode.Accepted:
            self.centralW.scene.partialSelection = scd.partialSelection.isChecked()

    def readOnlyCellClick(self):
        self.centralW.scene.readOnly = self.readOnlyCellAction.isChecked()

    def updateDesignScene(self):
        # reloadScene() is implemented editor scenes
        self.messageLine.setText("Reloading design.")
        self.centralW.scene.reloadScene()

    def printClick(self):
        dlg = QPrintDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            printer = dlg.printer()
            printRunner = startThread(self.centralW.view.printView(printer))
            self.appMainW.threadPool.start(printRunner)
            self.logger.info(
                "Printing started")  # self.centralW.view.printView(printer)

    def printPreviewClick(self):
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        ppdlg = QPrintPreviewDialog(self)
        ppdlg.paintRequested.connect(self.centralW.view.printView)
        ppdlg.exec()

    def imageExportClick(self):
        fdlg = QFileDialog(self, caption="Select or create an image file")
        fdlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        fdlg.setDefaultSuffix("png")
        fdlg.setFileMode(QFileDialog.FileMode.AnyFile)
        fdlg.setViewMode(QFileDialog.ViewMode.Detail)
        fdlg.setNameFilter("PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp);;GIF Image (*.gif);;SVG Vector Graphic (*.svg);;EPS Vector Graphic (*.eps)")
        if fdlg.exec() == QDialog.DialogCode.Accepted:
            imageFile = fdlg.selectedFiles()[0]
            ext = pathlib.Path(imageFile).suffix.lower()
            if ext == ".svg":
                items_rect = self.centralW.view.scene().itemsBoundingRect()
                if items_rect.isEmpty():
                    items_rect = self.centralW.view.sceneRect()
                margin = max(20.0, min(items_rect.width(), items_rect.height()) * 0.05)
                sourceRect = items_rect.adjusted(-margin, -margin, margin, margin)
                # Normalize to a reasonable pixel size instead of using raw scene
                # units (which can be 100k+ for layout scenes using dbu=1000).
                maxDim = 4000
                srcW = sourceRect.width()
                srcH = sourceRect.height()
                if srcW <= 0:
                    srcW = 800
                if srcH <= 0:
                    srcH = 600
                aspect = srcW / srcH
                if srcW >= srcH:
                    width = maxDim
                    height = int(maxDim / aspect)
                else:
                    height = maxDim
                    width = int(maxDim * aspect)
                generator = QSvgGenerator()
                generator.setFileName(imageFile)
                generator.setResolution(72)
                generator.setSize(QSize(width, height))
                generator.setViewBox(sourceRect)
                generator.setTitle("Revolution EDA Export")
                self.centralW.view.printView(generator, sourceRect)
            elif ext == ".eps":
                if not shutil.which("pdftops"):
                    QMessageBox.critical(self, "Export Error", "pdftops tool is required for EPS export but was not found in the system PATH.")
                    return
                monoChoice = QMessageBox.question(
                    self,
                    "EPS Export Mode",
                    "Export as black and white?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                monochrome = monoChoice == QMessageBox.StandardButton.Yes
                temp_pdf_fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
                os.close(temp_pdf_fd)
                try:
                    items_rect = self.centralW.view.scene().itemsBoundingRect()
                    if items_rect.isEmpty():
                        items_rect = self.centralW.view.sceneRect()
                    margin = max(20.0, min(items_rect.width(), items_rect.height()) * 0.05)
                    sourceRect = items_rect.adjusted(-margin, -margin, margin, margin)
                    srcW = sourceRect.width()
                    srcH = sourceRect.height()
                    if srcW <= 0:
                        srcW = 800
                    if srcH <= 0:
                        srcH = 600
                    aspect = srcW / srcH
                    maxPoints = 720.0
                    if srcW >= srcH:
                        width_points = maxPoints
                        height_points = maxPoints / aspect
                    else:
                        height_points = maxPoints
                        width_points = maxPoints * aspect
                    page_size = QPageSize(QSizeF(width_points, height_points), QPageSize.Unit.Point)
                    if monochrome:
                        # Render to high-res QImage, threshold to B&W, then paint to PDF
                        maxDim = 4000
                        if srcW >= srcH:
                            imgW = maxDim
                            imgH = int(maxDim / aspect)
                        else:
                            imgH = maxDim
                            imgW = int(maxDim * aspect)
                        image = QImage(QSize(imgW, imgH), QImage.Format_ARGB32_Premultiplied)
                        image.fill(Qt.GlobalColor.white)
                        self.centralW.view.printView(image, sourceRect)
                        # Threshold: any non-white pixel becomes black
                        ptr = image.bits()
                        ptr.setsize(image.sizeInBytes())
                        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(imgH, imgW, 4)
                        mask = (arr[:, :, :3] < 255).any(axis=2)
                        arr[mask] = [0, 0, 0, 255]
                        arr[~mask] = [255, 255, 255, 255]
                        # Paint monochrome image to PDF
                        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
                        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                        printer.setOutputFileName(temp_pdf_path)
                        printer.setPageSize(page_size)
                        printer.setPageMargins(QMarginsF(0, 0, 0, 0))
                        painter = QPainter(printer)
                        painter.drawImage(QRectF(0, 0, width_points, height_points), image)
                        painter.end()
                    else:
                        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
                        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                        printer.setOutputFileName(temp_pdf_path)
                        printer.setPageSize(page_size)
                        printer.setPageMargins(QMarginsF(0, 0, 0, 0))
                        self.centralW.view.printView(printer, sourceRect)
                    subprocess.run(["pdftops", "-eps", temp_pdf_path, imageFile], check=True)
                except Exception as e:
                    QMessageBox.critical(self, "Export Error", f"Failed to export to EPS: {str(e)}")
                finally:
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
            else:
                items_rect = self.centralW.view.scene().itemsBoundingRect()
                if items_rect.isEmpty():
                    items_rect = self.centralW.view.sceneRect()
                aspect_ratio = items_rect.width() / items_rect.height() if items_rect.height() > 0 else 1.0
                target_width = max(2000, self.centralW.view.viewport().width())
                target_height = int(target_width / aspect_ratio)
                if target_height > 10000:
                    target_height = 10000
                    target_width = int(target_height * aspect_ratio)
                elif target_width > 10000:
                    target_width = 10000
                    target_height = int(target_width / aspect_ratio)
                image = QImage(QSize(target_width, target_height), QImage.Format_ARGB32_Premultiplied)
                image.fill(Qt.GlobalColor.white)
                self.centralW.view.printView(image)
                image.save(imageFile)

    def deleteClick(self, s):
        self.centralW.scene.editModes.setMode("deleteItem")
        self.centralW.scene.deleteSelectedItems()
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])

    def selectAllClick(self):
        self.centralW.scene.selectAll()

    def deselectAllClick(self):
        self.centralW.scene.deselectAll()

    def stretchClick(self, s):
        self.centralW.scene.editModes.setMode("stretchItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])
        self.centralW.scene.stretchSelectedItems()

    def moveClick(self):
        self.centralW.scene.editModes.setMode("moveItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])

    def constrainedMoveClick(self):
        self.centralW.scene.editModes.setMode("constrainedMoveItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])

    def moveByClick(self):
        self.centralW.scene.editModes.setMode("moveItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])
        self.centralW.scene.moveBySelectedItems()

    def rotateClick(self):
        self.centralW.scene.editModes.setMode("rotateItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])

    def panView(self):
        self.centralW.scene.editModes.setMode("panView")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])

    def alignItemsClick(self):
        self.messageLine.setText("Select Items will be aligned.")
        dlg = alg.alignItemsDialogue(self)
        dlg.buttonBox.button(
            QDialogButtonBox.StandardButton.Apply).clicked.connect(
            lambda: alg.handleAlignAction(dlg, False))
        dlg.buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(
            lambda: alg.handleAlignAction(dlg, True))
        dlg.alignLineButton.pressed.connect(
            lambda: alg.startLineAlign(self.centralW.scene, dlg))
        dlg.alignEdgesButton.pressed.connect(
            lambda: alg.startEdgeAlign(self.centralW.scene, dlg))
        dlg.show()

    def goUpHierarchy(self):
        self.saveCell()
        if self.parentEditor is not None:
            self.parentEditor.raise_()
        self.close()

    def fitToWindow(self):
        self.centralW.scene.fitItemsInView()
        self.messageLine.setText("Fitting to window")

    def copyClick(self, s):
        self.centralW.scene.editModes.setMode("copyItem")
        self.messageLine.setText(self.centralW.scene.messages[
                                     self.centralW.scene.editModes.mode()])
        self.centralW.scene.copySelectedItems()

    def horizontalFlipClick(self):
        self.messageLine.setText('Flipping Selected Items Horizontally')
        self.centralW.scene.flipHorizontal()

    def verticalFlipClick(self):
        self.messageLine.setText('Flipping Selected Items Vertically')
        self.centralW.scene.flipVertical()

    def zoomIn(self):
        self.messageLine.setText("Zooming in")
        self.centralW.view.scale(1.25, 1.25)
        self.centralW.view.viewRect = self.centralW.view.mapToScene(
            self.rect()).boundingRect().toRect()

    def zoomOut(self):
        self.messageLine.setText("Zooming out")
        self.centralW.view.scale(0.8, 0.8)
        self.centralW.view.viewRect = self.centralW.view.mapToScene(
            self.rect()).boundingRect().toRect()

    def closeWindow(self):
        self.close()

    def closeEvent(self, event):
        cellViewTuple = ddef.viewNameTuple(self.libName, self.cellName, self.viewName)
        self.appMainW.openViews.pop(cellViewTuple, None)
        event.accept()
        super().closeEvent(event)

    def moveOrigin(self):
        self.centralW.scene.editModes.setMode("changeOrigin")

    def undoClick(self, s):

        self.messageLine.setText(self.centralW.scene.undoStack.undoText())
        self.centralW.scene.undoStack.undo()

    def redoClick(self, s):
        self.centralW.scene.undoStack.redo()

    def rotateItemClick(self, s):
        self.centralW.scene.editModes.setMode("rotateItem")

    def redraw(self):
        self.messageLine.setText("Redrawing...")
        self.centralW.view.updateSceneRect(self.centralW.view.sceneRect())

    def _findTopParent(self):
        current = self
        while current is not None and hasattr(current, 'parentObj'):
            if current.parentObj is None:
                return current
            current = current.parentObj
        return current

    def _createSignalConnections(self):
        self.centralW.scene.selectionChanged.connect(
            self.appMainW.selectionChangedScene)
        self.centralW.view.keyPressedSignal.connect(self.appMainW.viewKeyPressed)

    def addPluginAction(self, menu_name: str, action_name: str, callback, shortcut=None):
        """Add plugin action to specified menu"""
        menu = None
        for action in self.menuBar().actions():
            if action.text() == menu_name:
                menu = action.menu()
                break

        if not menu:
            menu = self.menuBar().addMenu(menu_name)

        action = QAction(action_name, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)

        menu.addAction(action)
        return action

    @contextmanager
    def measureDuration(self):
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            self.logger.info(
                f"Total processing time: {(end_time - start_time) * 1000:.3f} milliseconds")


class editorContainer(QWidget):
    def __init__(self, parent: editorWindow):
        super().__init__(parent=parent)
        self.editorWindow = parent
        self.scene = editorScene(self)
        self.view = editorView(self.scene, self)
