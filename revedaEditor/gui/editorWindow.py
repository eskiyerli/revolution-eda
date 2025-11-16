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


import pathlib
from contextlib import contextmanager
import time
from logging import getLogger
from PySide6.QtCore import (Qt, QSize,)
from PySide6.QtGui import (QAction, QIcon, QImage, QKeySequence)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QGraphicsScene, QGraphicsView, QLabel, QMainWindow,
                               QMenu, QToolBar)
from numpy import lib

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.gui.helpBrowser as hlp
import revedaEditor.resources.resources # noqa: F401
from revedaEditor.gui.startThread import startThread
import revedaEditor.gui.propertyDialogues as pdlg


class editorWindow(QMainWindow):
    """
    Base class for editor windows.
    """
    MAIN_LOGGER = "reveda"
    MAJOR_GRID_DEFAULT = 20
    SNAP_GRID_DEFAULT = 10

    def __init__(self, viewItem: libb.viewItem, libraryDict: dict,
                 libraryView: lmview.BaseDesignLibrariesView, ):
        super().__init__()
        self.centralW = None
        self.viewItem = viewItem
        self.file: pathlib.Path = self.viewItem.data(Qt.UserRole + 2)  # pathlib Path object
        self.cellItem: libb.cellItem = self.viewItem.parent()
        self.cellName = self.cellItem.cellName
        self.libItem: libb.libraryItem = self.cellItem.parent()
        self.libName: str = self.libItem.libraryName
        self.viewName: str = self.viewItem.viewName
        self.libraryDict = libraryDict
        self.libraryView = libraryView
        self.parentEditor: editorWindow|None = None  # type: editorWindow
        self.parentObj = None  # type symbol or layoutInstance
        self._app = QApplication.instance()  # main application pointer
        # self.appMainW = self.libraryView.parent.parent.appMainW
        self.appMainW = self._app.mainW
        self.logger = getLogger(self.MAIN_LOGGER)
        self.switchViewList = self.appMainW.switchViewList
        self.stopViewList = self.appMainW.stopViewList
        self.statusLine = self.statusBar()
        self.messageLine = QLabel()  # message line
        self.statusLine.insertPermanentWidget(0,self.messageLine)
        self.majorGrid = self.MAJOR_GRID_DEFAULT  # dot/line grid spacing
        self.snapGrid = self.SNAP_GRID_DEFAULT  # snapping grid size
        self.snapTuple = (self.snapGrid, self.snapGrid)
        self.init_UI()
        self._createSignalConnections()

    def __repr__(self):
        return f'editorWindow({self.libName}-{self.cellName}-{self.viewName})'

    def init_UI(self):
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
        self.printPreviewAction = QAction(printPreviewIcon, "Print Preview...", self)
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

        alignTopIcon = QIcon(":/icons/layers-alignment.png")
        self.alignTopAction = QAction(alignTopIcon, "Top Align", self)
        self.alignTopAction.setToolTip("Align top of selected objects")

        alignVerticalIcon = QIcon(":/icons/layers-alignment-center.png")
        self.alignVerticalAction = QAction(alignVerticalIcon, "Vertical Align", self)
        self.alignVerticalAction.setToolTip(
            "Align selected objects vertically at the centre")

        alignRightIcon = QIcon(":/icons/layers-alignment-center.png")
        self.alignRightAction = QAction(alignRightIcon, "Right Align", self)
        self.alignRightAction.setToolTip("Align right of selected objects")

        alignLeftIcon = QIcon(":/icons/layers-alignment-left.png")
        self.alignLeftAction = QAction(alignLeftIcon, "Left Align", self)
        self.alignLeftAction.setToolTip("Align left of selected objects")

        # display options
        dispConfigIcon = QIcon(":/icons/grid-snap-dot.png")
        self.dispConfigAction = QAction(dispConfigIcon, "Display Config...", self)
        self.dispConfigAction.setToolTip("Configure the display options")

        selectConfigIcon = QIcon(":/icons/zone-select.png")
        self.selectConfigAction = QAction(selectConfigIcon, "Selection Config...", self)
        self.selectConfigAction.setToolTip("Configure the selection options")

        panZoomConfigIcon = QIcon(":/icons/selection-resize.png")
        self.panZoomConfigAction = QAction(panZoomConfigIcon, "Pan/Zoom Config...", self)
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
        self.horizontalFlipAction = QAction(horizontalFlipIcon, "Horizontal Flip", self)
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
        self.viewPropAction = QAction(viewPropIcon, "Cellview Properties...", self)
        self.viewPropAction.setToolTip("Configure Cellview Properties")

        viewCheckIcon = QIcon(":/icons/ui-check-box.png")
        self.viewCheckAction = QAction(viewCheckIcon, "Check CellView", self)
        self.viewCheckAction.setToolTip("Check Cellview")

        viewErrorsIcon = QIcon(":/icons/report--exclamation.png")
        self.viewErrorsAction = QAction(viewErrorsIcon, "View Errors...", self)
        self.viewErrorsAction.setToolTip("View Errros")

        deleteErrorsIcon = QIcon(":/icons/report--minus.png")
        self.deleteErrorsAction = QAction(deleteErrorsIcon, "Delete Errors...", self)
        self.deleteErrorsAction.setToolTip("Delete Errros")

        netlistIcon = QIcon(":/icons/script-text.png")
        self.netlistAction = QAction(netlistIcon, "Create Netlist...", self)
        self.netlistAction.setToolTip("Create Netlist")

        createLineIcon = QIcon(":/icons/layer-shape-line.png")
        self.createLineAction = QAction(createLineIcon, "Create Line...", self)
        self.createLineAction.setToolTip("Create Line")

        createRectIcon = QIcon(":/icons/layer-shape.png")
        self.createRectAction = QAction(createRectIcon, "Create Rectangle...", self)
        self.createRectAction.setToolTip("Create Rectangle")

        createPolyIcon = QIcon(":/icons/layer-shape-polygon.png")
        self.createPolygonAction = QAction(createPolyIcon, "Create Polygon...", self)
        self.createPolygonAction.setToolTip("Create Polygon")

        createCircleIcon = QIcon(":/icons/layer-shape-ellipse.png")
        self.createCircleAction = QAction(createCircleIcon, "Create Circle...", self)
        self.createCircleAction.setToolTip("Create Circle")

        createArcIcon = QIcon(":/icons/layer-shape-polyline.png")
        self.createArcAction = QAction(createArcIcon, "Create Arc...", self)
        self.createArcAction.setToolTip("Create Arc")

        createViaIcon = QIcon(":/icons/layer-mask.png")
        self.createViaAction = QAction(createViaIcon, "Create Via...", self)
        self.createViaAction.setToolTip("Create Via")

        createInstIcon = QIcon(":/icons/block--plus.png")
        self.createInstAction = QAction(createInstIcon, "Create Instance...", self)
        self.createInstAction.setToolTip("Create Instance")

        self.createNetAction = QAction(createLineIcon, "Create Net...", self)
        self.createNetAction.setToolTip("Create Net")

        self.createPathAction = QAction(createLineIcon, "Create Path...", self)
        self.createPathAction.setToolTip("Create Path")

        createBusIcon = QIcon(":/icons/node-select-all.png")
        self.createBusAction = QAction(createBusIcon, "Create Bus...", self)
        self.createBusAction.setToolTip("Create Bus")

        createSymbolIcon = QIcon(":/icons/application-block.png")
        self.createSymbolAction = QAction(createSymbolIcon, "Create Symbol...", self)
        self.createSymbolAction.setToolTip("Create Symbol from Cellview")

        createTextIcon = QIcon(":icons/sticky-note-text.png")
        self.createTextAction = QAction(createTextIcon, "Create Text...", self)
        self.createTextAction.setToolTip("Create Text")

        # selection Actions
        selectDeviceIcon = QIcon(":icons/target.png")
        self.selectDeviceAction = QAction(selectDeviceIcon, "Select Devices", self)
        self.selectDeviceAction.setToolTip("Select Devices Only")

        selectNetIcon = QIcon(":icons/pencil--plus.png")
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

        ignoreIcon = QIcon(":/icons/minus-circle.png")
        self.ignoreAction = QAction(ignoreIcon, "Ignore", self)
        self.ignoreAction.setToolTip("Ignore selected cell")

        helpIcon = QIcon(":/icons/document-arrow.png")
        self.helpAction = QAction(helpIcon, "Help...", self)
        self.helpAction.setToolTip("Help")

        self.aboutIcon = QIcon(":/icons/information.png")
        self.aboutAction = QAction(self.aboutIcon, "About", self)
        self.aboutAction.setToolTip("About Revolution EDA")

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
        self.menuView.addAction(self.panZoomConfigAction)
        # edit menu
        self.menuEdit.addAction(self.undoAction)
        self.menuEdit.addAction(self.redoAction)
        # self.menuEdit.addAction(self.yankAction)
        self.menuEdit.addAction(self.pasteAction)
        self.menuEdit.addAction(self.deleteAction)
        self.menuEdit.addAction(self.copyAction)
        self.menuEdit.addAction(self.moveAction)
        self.menuEdit.addAction(self.moveByAction)
        self.menuEdit.addAction(self.moveOriginAction)
        self.menuEdit.addAction(self.stretchAction)
        self.menuEdit.addAction(self.rotateAction)
        self.menuEdit.addAction(self.horizontalFlipAction)
        self.menuEdit.addAction(self.verticalFlipAction)
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
        self.moveByAction.triggered.connect(self.moveByClick)
        self.rotateAction.triggered.connect(self.rotateItemClick)
        self.verticalFlipAction.triggered.connect(self.verticalFlipClick)
        self.horizontalFlipAction.triggered.connect(self.horizontalFlipClick)
        self.goUpAction.triggered.connect(self.goUpHierarchy)
        self.helpAction.triggered.connect(self.helpClick)
        self.aboutAction.triggered.connect(self.aboutClick)

    def _createShortcuts(self):
        self.redoAction.setShortcut("Shift+U")
        self.undoAction.setShortcut(Qt.Key_U)
        self.objPropAction.setShortcut(Qt.Key_Q)
        self.copyAction.setShortcut(Qt.Key_C)
        self.rotateAction.setShortcut("Ctrl+R")
        self.createTextAction.setShortcut("Shift+L")
        self.fitAction.setShortcut(Qt.Key_F)
        self.deleteAction.setShortcut(QKeySequence.Delete)
        self.selectAllAction.setShortcut("Ctrl+A")
        self.stretchAction.setShortcut(Qt.Key_S)

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

    def dispConfigEdit(self):
        
        dcd = pdlg.displayConfigDialog(self)
        dcd.majorGridEntry.setText(str(self.majorGrid))
        dcd.snapGridEdit.setText(str(self.snapGrid))
        if dcd.exec() == QDialog.Accepted:
            self.configureGridSettings((int(dcd.majorGridEntry.text()), int(dcd.snapGridEdit.text())))
            if dcd.dotType.isChecked():
                self.centralW.view.gridbackg = True
                self.centralW.view.linebackg = False
            elif dcd.lineType.isChecked():
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = True
            else:
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = False
    

    def configureGridSettings(self, gridSettings: tuple[int,int]) -> None:
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
                self.centralW.scene.invalidate(self.centralW.scene.sceneRect(),
                                               QGraphicsScene.BackgroundLayer)
        except Exception as e:
            self.logger.info(f'Problem with grid settings: {e}')

    def selectConfigEdit(self):
        scd = pdlg.selectConfigDialogue(self)
        if self.centralW.scene.partialSelection:
            scd.partialSelection.setChecked(True)
        else:
            scd.fullSelection.setChecked(True)
        if scd.exec() == QDialog.Accepted:
            self.centralW.scene.partialSelection = scd.partialSelection.isChecked()


    def readOnlyCellClick(self):
        self.centralW.scene.readOnly = self.readOnlyCellAction.isChecked()

    def updateDesignScene(self):
        # reloadScene() is implemented editor scenes
        self.messageLine.setText("Reloading design.")
        self.centralW.scene.reloadScene()

    def printClick(self):
        dlg = QPrintDialog(self)
        if dlg.exec() == QDialog.Accepted:
            printer = dlg.printer()
            printRunner = startThread(self.centralW.view.printView(printer))
            self.appMainW.threadPool.start(printRunner)
            self.logger.info("Printing started")  # self.centralW.view.printView(printer)

    def printPreviewClick(self):
        printer = QPrinter(QPrinter.ScreenResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        ppdlg = QPrintPreviewDialog(self)
        ppdlg.paintRequested.connect(self.centralW.view.printView)
        ppdlg.exec()

    def imageExportClick(self):
        image = QImage(self.centralW.view.viewport().size(),
                       QImage.Format_ARGB32_Premultiplied)
        self.centralW.view.printView(image)
        fdlg = QFileDialog(self, caption="Select or create an image file")
        fdlg.setDefaultSuffix("png")
        fdlg.setFileMode(QFileDialog.AnyFile)
        fdlg.setViewMode(QFileDialog.Detail)
        fdlg.setNameFilter("Image Files (*.png *.jpg *.bmp *.gif *.jpeg)")
        if fdlg.exec() == QDialog.Accepted:
            imageFile = fdlg.selectedFiles()[0]
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

    def goUpHierarchy(self):
        self.saveCell()
        if self.parentEditor is not None:
            self.parentEditor.updateDesignScene()
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
        cellViewTuple = ddef.viewTuple(self.libName, self.cellName, self.viewName)
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
        self.centralW.view.update()

    def _findTopParent(self):
        current = self
        while current is not None and hasattr(current, 'parentObj'):
            if current.parentObj is None:
                return current
            current = current.parentObj
        return current

    def _createSignalConnections(self):
        self.centralW.scene.selectionChanged.connect(self.appMainW.selectionChangedScene)
        self.centralW.view.keyPressedSignal.connect(self.appMainW.viewKeyPressed)

    @contextmanager
    def measureDuration(self):
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            self.logger.info(f"Total processing time: {(end_time - start_time) * 1000:.3f} milliseconds")

