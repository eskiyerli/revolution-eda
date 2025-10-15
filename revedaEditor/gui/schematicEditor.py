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
from typing import List
import pathlib
import datetime
from copy import deepcopy
import re

from PySide6.QtCore import (QPoint, Qt, QThreadPool, )
from PySide6.QtGui import (QAction, QIcon, )
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QMenu, QToolBar, QWidget, )

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.common.shapes as shp  # import the shapes
import revedaEditor.fileio.symbolEncoder as symenc
import revedaEditor.gui.editorViews as edv
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.propertyDialogues as pdlg
import revedaEditor.gui.toolsDialogues as tdlg
import revedaEditor.scenes.schematicScene as schscn
from revedaEditor.gui.startThread import startThread



class schematicEditor(edw.editorWindow):
    MAJOR_GRID_DEFAULT = 20
    SNAP_GRID_DEFAULT = 10
    def __init__(self, viewItem: libb.viewItem, libraryDict: dict, libraryView) -> None:
        super().__init__(viewItem, libraryDict, libraryView)
        self.setWindowTitle(f"Schematic Editor - {self.cellName} - {self.viewName}")
        self.setWindowIcon(QIcon(":/icons/edLayer-shape.png"))
        self.configDict = dict()
        self.processedCells = set()  # cells included in config view
        self.symbolChooser = None
        self.majorGrid = self.MAJOR_GRID_DEFAULT  # dot/line grid spacing
        self.snapGrid = self.SNAP_GRID_DEFAULT  # snapping grid size
        self.snapTuple = (self.snapGrid, self.snapGrid)
        self.symbolViews = [
            "symbol"]  # only symbol can be instantiated in the schematic window.
        self._schematicContextMenu()

    def init_UI(self):
        super().init_UI()
        self.resize(1600, 800)
        # create container to position all widgets
        self.centralW = schematicContainer(self)
        self.setCentralWidget(self.centralW)

    def __repr__(self):
        return f'schematicEditor({self.libName}-{self.cellName}-{self.viewName})'

    def _createActions(self):
        super()._createActions()
        self.netNameAction = QAction("Net Name", self)
        self.netNameAction.setToolTip("Set Net Name")
        self.netNameAction.setShortcut(Qt.Key_L)
        self.hilightNetAction = QAction("Highlight Net", self)
        self.hilightNetAction.setToolTip("Highlight Selected Net Connections")
        self.hilightNetAction.setCheckable(True)
        self.renumberInstanceAction = QAction("Renumber Instances", self)
        self.renumberInstanceAction.setToolTip("Renumber Instances")
        simulationIcon = QIcon("icons/application-run.png")
        self.simulateAction = QAction(simulationIcon, "Revolution EDA SAE...", self)
        self.findRelatedEditors = QAction("Find Related Editors", self) 

    def _addActions(self):
        super()._addActions()
        # edit menu
        self.menuEdit.addAction(self.netNameAction)

        self.propertyMenu = self.menuEdit.addMenu("Properties")
        self.propertyMenu.addAction(self.objPropAction)

        # hierarchy submenu
        self.hierMenu = self.menuEdit.addMenu("Hierarchy")
        self.hierMenu.addAction(self.goUpAction)
        self.hierMenu.addAction(self.goDownAction)

        # create menu
        self.menuCreate.addAction(self.createInstAction)
        self.menuCreate.addAction(self.createNetAction)
        self.menuCreate.addAction(self.createBusAction)
        self.menuCreate.addAction(self.createPinAction)
        self.menuCreate.addAction(self.createTextAction)
        self.menuCreate.addAction(self.createSymbolAction)

        # check menu
        self.menuCheck.addAction(self.viewErrorsAction)
        self.menuCheck.addAction(self.deleteErrorsAction)

        # tools menu
        self.menuTools.addAction(self.hilightNetAction)
        self.menuTools.addAction(self.renumberInstanceAction)
        self.menuTools.addAction(self.findRelatedEditors)
        # utilities Menu
        self.selectMenu = self.menuUtilities.addMenu("Selection")
        self.selectMenu.addAction(self.selectDeviceAction)
        self.selectMenu.addAction(self.selectNetAction)
        self.selectMenu.addAction(self.selectPinAction)
        self.selectMenu.addSeparator()
        self.selectMenu.addAction(self.removeSelectFilterAction)
        self.simulationMenu = QMenu("&Simulation")
        # help menu
        self.simulationMenu.addAction(self.netlistAction)
        self.editorMenuBar.insertMenu(self.menuHelp.menuAction(), self.simulationMenu)
        # self.menuHelp = self.editorMenuBar.addMenu("&Help")
        if self._app.plugins.get('revedasim'):
            self.simulationMenu.addAction(self.simulateAction)

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
        self.simulateAction.triggered.connect(self.startSimClick)
        self.ignoreAction.triggered.connect(self.ignoreClick)
        self.goDownAction.triggered.connect(self.goDownClick)
        self.viewErrorsAction.triggered.connect(self.checkErrorsClick)
        self.deleteErrorsAction.triggered.connect(self.deleteErrorsClick)

        self.hilightNetAction.triggered.connect(self.hilightNetClick)
        self.netNameAction.triggered.connect(self.createNetNameClick)
        self.selectDeviceAction.triggered.connect(self.selectDeviceClick)
        self.selectNetAction.triggered.connect(self.selectNetClick)
        self.selectPinAction.triggered.connect(self.selectPinClick)
        self.removeSelectFilterAction.triggered.connect(self.removeSelectFilterClick)
        self.renumberInstanceAction.triggered.connect(self.renumberInstanceClick)
        self.findRelatedEditors.triggered.connect(self.findRelatedEditorsClick)

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
        self.schematicToolbar.addAction(self.removeSelectFilterAction)

    def _schematicContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.ignoreAction)
        self.centralW.scene.itemContextMenu.addAction(self.goDownAction)

    def _createShortcuts(self):
        super()._createShortcuts()
        self.createInstAction.setShortcut(Qt.Key_I)
        self.createNetAction.setShortcut(Qt.Key_W)
        self.createPinAction.setShortcut(Qt.Key_P)
        self.goDownAction.setShortcut("Shift+E")

    def createNetClick(self, s):
        self.centralW.scene.editModes.setMode("drawWire")

    def createBusClick(self, s):
        self.centralW.scene.editModes.setMode("drawBus")

    def createInstClick(self, s):
        # create a designLibrariesView
        libraryModel = lmview.symbolViewsModel(self.libraryDict, self.symbolViews)
        if self.symbolChooser is None:
            self.symbolChooser = fd.selectCellViewDialog(self, libraryModel)
            self.symbolChooser.show()
        else:
            self.symbolChooser.raise_()
        if self.symbolChooser.exec() == QDialog.Accepted:
            instanceTuple = ddef.viewTuple(self.symbolChooser.libNamesCB.currentText(),
                                           self.symbolChooser.cellCB.currentText(),
                                           self.symbolChooser.viewCB.currentText(), )

            self.centralW.scene.newInstanceTuple = instanceTuple

            self.centralW.scene.editModes.setMode("addInstance")

    def createPinClick(self, s):
        createPinDlg = pdlg.createSchematicPinDialog(self)
        if createPinDlg.exec() == QDialog.Accepted:
            self.centralW.scene.pinName = createPinDlg.pinName.text()
            self.centralW.scene.pinType = createPinDlg.pinType.currentText()
            self.centralW.scene.pinDir = createPinDlg.pinDir.currentText()
            self.centralW.scene.editModes.setMode("drawPin")

    def createNoteClick(self, s):
        textDlg = pdlg.noteTextEdit(self)
        if textDlg.exec() == QDialog.Accepted:
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

    def startSimClick(self, s):
        try:
            simdlg = self._app.plugins.get('revedasim').dialogueWindows
            revbenchdlg = simdlg.createRevbenchDialogue(self, self.libraryView.libraryModel,
                                                        self.cellItem)
            revbenchdlg.libNamesCB.setCurrentText(self.libName)
            revbenchdlg.cellCB.setCurrentText(self.cellName)
            revbenchdlg.viewCB.setCurrentText(self.viewName)
            # now first create the revbenchview item and populate it
            if revbenchdlg.exec() == QDialog.Accepted:
                try:
                    libItem = libm.getLibItem(self.libraryView.libraryModel,
                                              revbenchdlg.libNamesCB.currentText())
                    cellItem = libm.getCellItem(libItem, revbenchdlg.cellCB.currentText())
                    revbenchName = revbenchdlg.benchCB.currentText()
                    if not (libItem and cellItem):
                        raise ValueError(
                            f"library={libItem} or cell={cellItem} is not found")
                    revbenchItem = libm.findViewItem(self.libraryView.libraryModel,
                                                     libItem.libraryName, cellItem.cellName,
                                                     revbenchName, )
                    if not revbenchItem:  # if not found, create a new one
                        revbenchItem = libb.createCellView(self,
                                                           revbenchdlg.benchCB.currentText(),
                                                           cellItem)
                        items = []
                        libraryName = self.libItem.data(Qt.UserRole + 2).name
                        cellName = self.cellItem.data(Qt.UserRole + 2).name
                        items.append({"viewType": "revbench"})
                        items.append({"lib": libraryName})
                        items.append({"cell": cellName})
                        items.append({"view": revbenchdlg.viewCB.currentText()})
                        items.append({"settings": []})
                        with revbenchItem.data(Qt.UserRole + 2).open(mode="w") as benchFile:
                            json.dump(items, benchFile, indent=4)
                except Exception as e:
                    self.logger.error(f"Error during simulation setup: {e}")
                
                    # simmwModule = importlib.import_module("revedasim.simMainWindow",
                    #                                       str(self._app.revedasim_pathObj))
            
                simmwModule = self._app.plugins.get('revedasim')
                if simmwModule:
                    cellViewTuple = ddef.viewTuple(self.libItem.libraryName,
                                                   self.cellItem.cellName,
                                                   revbenchItem.viewName)
                    if self.appMainW.openViews.get(cellViewTuple):
                        simmw = self.appMainW.openViews[cellViewTuple]
                    else:
                        simmw = simmwModule.SimMainWindow(revbenchItem,
                                                          self.libraryView.libraryModel,
                                                          self.libraryView)
                        self.appMainW.openViews[cellViewTuple] = simmw
                    simmw.show()
                else:
                    self.logger.error('Revedasim plugin is not installed.')


        except ImportError or NameError:
            self.logger.error("Reveda SAE is not installed.")

    def renumberInstanceClick(self, s):
        self.centralW.scene.renumberInstances()

    def checkSaveCell(self):
        self.centralW.scene.nameSceneNets()
        self.centralW.scene.saveSchematic(self.file)
        if self.parentEditor:
            self.parentEditor.centralW.scene.reloadScene()

    def saveCell(self):
        self.centralW.scene.saveSchematic(self.file)

    def loadSchematic(self):
        self.centralW.scene.loadDesign(self.file)

    def createConfigView(self, configItem: libb.viewItem, configDict: dict,
                         newConfigDict: dict, processedCells: set, ):
        sceneSymbolSet = self.centralW.scene.findSceneSymbolSet()
        for item in sceneSymbolSet:
            libItem = libm.getLibItem(self.libraryView.libraryModel, item.libraryName)
            cellItem = libm.getCellItem(libItem, item.cellName)
            viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]
            viewNames = [viewItem.viewName for viewItem in viewItems]
            netlistableViews = [viewItemName for viewItemName in self.switchViewList if
                                viewItemName in viewNames]
            itemSwitchViewList = deepcopy(netlistableViews)
            viewDict = dict(zip(viewNames, viewItems))
            itemCellTuple = ddef.cellTuple(libItem.libraryName, cellItem.cellName)
            if itemCellTuple not in processedCells:
                if cellLine := configDict.get(cellItem.cellName):
                    netlistableViews = [cellLine[1]]
                for viewName in netlistableViews:
                    match viewDict[viewName].viewType:
                        case "schematic":
                            newConfigDict[cellItem.cellName] = [libItem.libraryName,
                                                                viewName,
                                                                itemSwitchViewList, ]
                            schematicObj = schematicEditor(viewDict[viewName],
                                                           self.libraryDict,
                                                           self.libraryView, )
                            schematicObj.loadSchematic()
                            schematicObj.createConfigView(configItem, configDict,
                                                          newConfigDict, processedCells, )
                            break
                        case _:
                            newConfigDict[cellItem.cellName] = [libItem.libraryName,
                                                                viewName,
                                                                itemSwitchViewList, ]
                            break
                processedCells.add(itemCellTuple)

    def closeEvent(self, event):
        self.centralW.scene.saveSchematic(self.file)
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

        if dlg.exec() == QDialog.Accepted:
            self._startNetlisting(dlg)

    def _getNetlistableViews(self):
        views = [self.viewItem.viewName]
        config_items = [self.cellItem.child(row) for row in range(self.cellItem.rowCount())
                        if self.cellItem.child(row).viewType == "config"]

        for item in config_items:
            with item.data(Qt.UserRole + 2).open(mode="r") as f:
                config = json.load(f)
                if config[1]["reference"] == self.viewItem.viewName:
                    views.append(item.viewName)

        return views

    def _startNetlisting(self, dlg: fd.netlistExportDialogue):
        try:
            self.appMainW.simulationOutputPath = pathlib.Path(dlg.netlistDirEdit.text())
            selectedViewName = dlg.viewNameCombo.currentText()

            self.switchViewList = [item.strip() for item in
                                   dlg.switchViewEdit.text().split(",")]
            self.stopViewList = [dlg.stopViewEdit.text().strip()]

            subDirPath = self.appMainW.simulationOutputPath / self.cellName / selectedViewName
            subDirPath.mkdir(parents=True, exist_ok=True)

            netlistFilePath = subDirPath / f"{self.cellName}_{selectedViewName}.cir"

            netlistObj = self.createNetlistObject(selectedViewName, netlistFilePath)

            if netlistObj:
                # self.runNetlisting(netlistObj, self.appMainW.threadPool)
                with self.measureDuration():
                    netlistObj.writeNetlist() 
        except Exception as e:
            self.logger.error(f"Error in creating netlist start: {e}")

    def createNetlistObject(self, view_name: str, filePath: pathlib.Path):
        if "schematic" in view_name:
            return xyceNetlist(self, filePath)
        elif "config" in view_name:
            netlist_obj = xyceNetlist(self, filePath, True)
            config_item = libm.findViewItem(self.libraryView.libraryModel, self.libName,
                                            self.cellName, view_name)
            with config_item.data(Qt.UserRole + 2).open(mode="r") as f:
                netlist_obj.configDict = json.load(f)[2]
            return netlist_obj
        return None

    # def runNetlisting(self, netlist_obj, threadPool: QThreadPool = None):
    #     with self.measureDuration():
    #         xyceNetlRunner = startThread(fn=netlist_obj.writeNetlist)
    #         xyceNetlRunner.signals.finished.connect(self.netListingFinished)
    #         xyceNetlRunner.signals.error.connect(self.netlistingError)
    #         xyceNetlRunner.setAutoDelete(False)
    #         threadPool.start(xyceNetlRunner)

    def runNetlisting(self, netlist_obj, threadPool: QThreadPool = None):
        if threadPool is None:
            threadPool = QThreadPool.globalInstance()

        with self.measureDuration():
            xyceNetlRunner = startThread(fn=netlist_obj.writeNetlist)
            xyceNetlRunner.signals.finished.connect(self.netListingFinished, Qt.QueuedConnection)
            xyceNetlRunner.signals.error.connect(self.netlistingError, Qt.QueuedConnection)
            xyceNetlRunner.setAutoDelete(False)
            threadPool.start(xyceNetlRunner)

    def netListingFinished(self, result):
        self.logger.info(f"Netlisting finished: {result}")

    def netlistingError(self, error):
        self.logger.error(f"Error in netlisting: {error}")

    def goDownClick(self, s):
        self.centralW.scene.goDownHier()

    def ignoreClick(self, s):
        self.centralW.scene.ignoreSymbol()

    def createNetNameClick(self, s):
        dlg = pdlg.netNameDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.centralW.scene.netNameString = dlg.netNameEdit.text().strip()
            self.centralW.scene.editModes.setMode('nameNet')
        self.messageLine.setText("Select a net to attach the name")

    def hilightNetClick(self, s):
        self.centralW.scene.hilightNets()

    def selectDeviceClick(self):
        self.centralW.scene.selectModes.setMode("selectDevice")
        self.messageLine.setText("Select Only Instances")

    def selectNetClick(self):
        self.centralW.scene.selectModes.setMode("selectNet")
        self.messageLine.setText("Select Only Nets")

    def selectPinClick(self):
        self.centralW.scene.selectModes.setMode("selectPin")
        self.messageLine.setText("Select Only Pins")

    def removeSelectFilterClick(self):
        self.centralW.scene.selectModes.setMode("selectAll")
        self.messageLine.setText("Select All Objects")

    def createSymbol(self) -> None:
        """
        Create a symbol view for a schematic.
        """
        oldSymbolItem = False

        askViewNameDlg = pdlg.symbolNameDialog(self.file.parent, self.cellName, self, )
        if askViewNameDlg.exec() == QDialog.Accepted:
            symbolViewName = askViewNameDlg.symbolViewsCB.currentText()
            if symbolViewName in askViewNameDlg.symbolViewNames:
                oldSymbolItem = True
            if oldSymbolItem:
                deleteSymViewDlg = fd.deleteSymbolDialog(self.cellName, symbolViewName,
                                                         self)
                if deleteSymViewDlg.exec() == QDialog.Accepted:
                    self.generateSymbol(symbolViewName)
            else:
                self.generateSymbol(symbolViewName)

    def generateSymbol(self, symbolViewName: str) -> None:
        symbolWindow = None
        libName = self.libName
        cellName = self.cellName
        libItem = libm.getLibItem(self.libraryView.libraryModel, libName)
        cellItem = libm.getCellItem(libItem, cellName)
        # libraryView = self.libraryView
        schematicPins: list[shp.schematicPin] = list(
            self.centralW.scene.findSceneSchemPinsSet())
        schematicPinNames: list[str] = [pinItem.pinName for pinItem in schematicPins]
        rectXDim: int = 0
        rectYDim: int = 0

        inputPins = [pinItem.pinName for pinItem in schematicPins if
                     pinItem.pinDir == shp.schematicPin.pinDirs[0]]

        outputPins = [pinItem.pinName for pinItem in schematicPins if
                      pinItem.pinDir == shp.schematicPin.pinDirs[1]]

        inoutPins = [pinItem.pinName for pinItem in schematicPins if
                     pinItem.pinDir == shp.schematicPin.pinDirs[2]]

        dlg = pdlg.symbolCreateDialog(self)
        dlg.leftPinsEdit.setText(", ".join(inputPins))
        dlg.rightPinsEdit.setText(", ".join(outputPins))
        dlg.topPinsEdit.setText(", ".join(inoutPins))
        if dlg.exec() == QDialog.Accepted:
            symbolViewItem = libb.createCellView(self, symbolViewName, cellItem)
            libraryDict = self.libraryDict
            # create symbol editor window with an empty items list
            from revedaEditor.gui.symbolEditor import symbolEditor

            symbolWindow = symbolEditor(symbolViewItem, libraryDict, self.libraryView)
            try:
                leftPinNames = list(filter(None, [pinName.strip() for pinName in
                                                  dlg.leftPinsEdit.text().split(",")], ))
                rightPinNames = list(filter(None, [pinName.strip() for pinName in
                                                   dlg.rightPinsEdit.text().split(",")], ))
                topPinNames = list(filter(None, [pinName.strip() for pinName in
                                                 dlg.topPinsEdit.text().split(",")], ))
                bottomPinNames = list(filter(None, [pinName.strip() for pinName in
                                                    dlg.bottomPinsEdit.text().split(
                                                        ",")], ))
                stubLength = int(float(dlg.stubLengthEdit.text().strip()))
                pinDistance = int(float(dlg.pinDistanceEdit.text().strip()))
                rectXDim = (max(len(topPinNames), len(bottomPinNames)) + 1) * pinDistance
                rectYDim = (max(len(leftPinNames), len(rightPinNames)) + 1) * pinDistance
            except ValueError:
                self.logger.error("Enter valid value")

        # add window to open windows list
        # libraryView.openViews[f"{libName}_{cellName}_{symbolViewName}"] = symbolWindow
        if symbolWindow is not None:
            symbolScene = symbolWindow.centralW.scene
            symbolScene.rectDraw(QPoint(0, 0), QPoint(rectXDim, rectYDim))
            symbolScene.labelDraw(QPoint(int(0.25 * rectXDim), int(0.4 * rectYDim)),
                                  "[@cellName]", "NLPLabel", "12", "Center", "R0",
                                  "Instance", )
            symbolScene.labelDraw(QPoint(int(rectXDim), int(-0.2 * rectYDim)),
                                  "[@instName]", "NLPLabel", "12", "Center", "R0",
                                  "Instance", )
            leftPinLocs = [QPoint(-stubLength, (i + 1) * pinDistance) for i in
                           range(len(leftPinNames))]
            rightPinLocs = [QPoint(rectXDim + stubLength, (i + 1) * pinDistance) for i in
                            range(len(rightPinNames))]
            bottomPinLocs = [QPoint((i + 1) * pinDistance, rectYDim + stubLength) for i in
                             range(len(bottomPinNames))]
            topPinLocs = [QPoint((i + 1) * pinDistance, -stubLength) for i in
                          range(len(topPinNames))]
            for i in range(len(leftPinNames)):
                symbolScene.lineDraw(leftPinLocs[i], leftPinLocs[i] + QPoint(stubLength, 0))
                symbolScene.addItem(
                    schematicPins[schematicPinNames.index(leftPinNames[i])].toSymbolPin(
                        leftPinLocs[i]))
            for i in range(len(rightPinNames)):
                symbolScene.lineDraw(rightPinLocs[i],
                                     rightPinLocs[i] + QPoint(-stubLength, 0))
                symbolScene.addItem(
                    schematicPins[schematicPinNames.index(rightPinNames[i])].toSymbolPin(
                        rightPinLocs[i]))
            for i in range(len(topPinNames)):
                symbolScene.lineDraw(topPinLocs[i], topPinLocs[i] + QPoint(0, stubLength))
                symbolScene.addItem(
                    schematicPins[schematicPinNames.index(topPinNames[i])].toSymbolPin(
                        topPinLocs[i]))
            for i in range(len(bottomPinNames)):
                symbolScene.lineDraw(bottomPinLocs[i],
                                     bottomPinLocs[i] + QPoint(0, -stubLength))
                symbolScene.addItem(
                    schematicPins[schematicPinNames.index(bottomPinNames[i])].toSymbolPin(
                        bottomPinLocs[i]))  # symbol attribute generation for netlisting.
            symbolScene.attributeList = list()  # empty attribute list

            symbolScene.attributeList.append(symenc.symbolAttribute(
                "XyceSymbolNetlistLine","X@instName %pinOrder @cellName"))
            symbolScene.attributeList.append(
                symenc.symbolAttribute("VacaskSymbolNetlistLine",
                                    "X@instName  ( %pinOrder ) @cellName"))
            symbolScene.attributeList.append(
                symenc.symbolAttribute("pinOrder", ", ".join(schematicPinNames)))

            symbolWindow.checkSaveCell()
            self.libraryView.reworkDesignLibrariesView(self.appMainW.libraryDict)

            openCellViewTuple = ddef.viewTuple(libName, cellName, symbolViewName)
            self.appMainW.openViews[openCellViewTuple] = symbolWindow
            symbolWindow.show()

    def checkErrorsClick(self):
        self.centralW.scene.checkErrors()
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
        openWindows = {w for w in QApplication.instance().topLevelWidgets()
                       if isinstance(w, schematicEditor)}
        relatedEditors = set()
        self.findRelated(self, relatedEditors, openWindows)
        dlg = tdlg.findProjectEditors(self)
        relatedEditorNameList = [editor.cellName for editor in relatedEditors]
        dlg.relatedEditorsCB.addItems(relatedEditorNameList)
        dlg.relatedEditorsCB.setCurrentIndex(0)
        if dlg.exec() == QDialog.Accepted:
            relatedEditorName = dlg.relatedEditorsCB.currentText()
            relatedEditor = next(
                (editor for editor in relatedEditors
                 if editor.cellName == relatedEditorName), None)
            if relatedEditor:
                relatedEditor.show()
                relatedEditor.raise_()
                relatedEditor.activateWindow()


class schematicContainer(QWidget):
    def __init__(self, parent: schematicEditor):
        super().__init__(parent=parent)
        assert isinstance(parent, schematicEditor)
        self.parent = parent
        self.scene = schscn.schematicScene(self)
        self.view = edv.schematicView(self.scene, self)

        self.init_UI()

    def init_UI(self):
        # layout statements, using a grid layout
        gLayout = QGridLayout()
        gLayout.setSpacing(10)
        gLayout.addWidget(self.view, 0, 0)
        # ratio of first column to second column is 5
        gLayout.setColumnStretch(0, 5)
        gLayout.setRowStretch(0, 6)
        self.setLayout(gLayout)


class xyceNetlist:
    def __init__(self, schematic, filePathObj: pathlib.Path, useConfig: bool = False, ):
        self.filePathObj = filePathObj
        self.schematic = schematic
        self._use_config = useConfig
        self._scene = self.schematic.centralW.scene
        self.libraryDict = self.schematic.libraryDict
        self.libraryView = self.schematic.libraryView
        self._configDict = None
        self.libItem = libm.getLibItem(self.schematic.libraryView.libraryModel,
                                       self.schematic.libName, )
        self.cellItem = libm.getCellItem(self.libItem, self.schematic.cellName)

        self._switchViewList = schematic.switchViewList
        self._stopViewList = schematic.stopViewList
        self.netlistedViewsSet = set()  # keeps track of netlisted views.
        self.includeLines = set()  # keeps track of include lines.
        self.vamodelLines = set()  # keeps track of vamodel lines.
        self.vahdlLines = set()  # keeps track of *.HDL lines.

    def __repr__(self):
        return f"xyceNetlist(filePathObj={self.filePathObj}, schematic={self.schematic}, useConfig={self._use_config})"

    @property
    def switchViewList(self) -> List[str]:
        return self._switchViewList

    @switchViewList.setter
    def switchViewList(self, value: List[str]):
        self._switchViewList = value

    @property
    def stopViewList(self) -> List[str]:
        return self._stopViewList

    @stopViewList.setter
    def stopViewList(self, value: List[str]):
        self._stopViewList = value

    def writeNetlist(self):
        with self.filePathObj.open(mode="w") as cirFile:
            cirFile.write("*".join(["\n", 80 * "*", "\n", "* Revolution EDA CDL Netlist\n",
                                    f"* Library: {self.schematic.libName}\n",
                                    f"* Top Cell Name: {self.schematic.cellName}\n",
                                    f"* View Name: {self.schematic.viewName}\n",
                                    f"* Date: {datetime.datetime.now()}\n", 80 * "*", "\n",
                                    ".GLOBAL gnd!\n\n", ]))

            # now go down the rabbit hole to track all circuit elements.
            self.recursiveNetlisting(self.schematic, cirFile)

            # cirFile.write(".END\n")
            for line in self.includeLines:
                cirFile.write(f"{line}\n")
            for line in self.vamodelLines:
                cirFile.write(f"{line}\n")
            for line in self.vahdlLines:
                cirFile.write(f"{line}\n")

    @property
    def configDict(self):
        return self._configDict

    @configDict.setter
    def configDict(self, value: dict):
        self._configDict = value

    def recursiveNetlisting(self, schematic: schematicEditor, cirFile):
        """
        Recursively traverse all sub-circuits and netlist them.
        """
        schematicScene = schematic.centralW.scene
        schematicScene.nameSceneNets()  # name all nets in the schematic
        sceneSymbolSet = schematicScene.findSceneSymbolSet()
        schematicScene.generatePinNetMap(sceneSymbolSet)
        for elementSymbol in sceneSymbolSet:
            self.processElementSymbol(elementSymbol, schematic, cirFile)

    def processElementSymbol(self, elementSymbol, schematic, cirFile):
        if elementSymbol.symattrs.get("XyceNetlistPass") != "1" and (
                not elementSymbol.netlistIgnore):
            libItem = libm.getLibItem(schematic.libraryView.libraryModel,
                                      elementSymbol.libraryName)
            cellItem = libm.getCellItem(libItem, elementSymbol.cellName)
            netlistView = self.determineNetlistView(elementSymbol, cellItem)

            # Create the netlist line for the item.
            self.createItemLine(cirFile, elementSymbol, cellItem, netlistView)
        elif elementSymbol.netlistIgnore:
            cirFile.write(f"*{elementSymbol.instanceName} is marked to be ignored\n")
        elif not elementSymbol.symattrs.get("XyceNetlistPass", False):
            cirFile.write(
                f"*{elementSymbol.instanceName} has no XyceNetlistLine attribute\n")

    def determineNetlistView(self, elementSymbol, cellItem):
        viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]
        viewNames = [view.viewName for view in viewItems]

        if self._use_config:
            return self.configDict.get(elementSymbol.cellName)[1]
        else:
            # Iterate over the switch view list to determine the appropriate netlist view.
            for viewName in self._switchViewList:
                if viewName in viewNames:
                    return viewName
            return "symbol"

    def createItemLine(self, cirFile, elementSymbol: shp.schematicSymbol,
                       cellItem: libb.cellItem, netlistView: str, ):
        if "schematic" in netlistView:
            # First write subckt call in the netlist.
            cirFile.write(self.createXyceSymbolLine(elementSymbol))
            schematicItem = libm.getViewItem(cellItem, netlistView)
            if netlistView not in self._stopViewList:
                # now load the schematic
                schematicObj = schematicEditor(schematicItem, self.libraryDict,
                                               self.libraryView)
                schematicObj.loadSchematic()

                viewTuple = ddef.viewTuple(schematicObj.libName, schematicObj.cellName,
                                           schematicObj.viewName)

                if viewTuple not in self.netlistedViewsSet:
                    self.netlistedViewsSet.add(viewTuple)
                    pinList = elementSymbol.symattrs.get("pinOrder", ", ").replace(",", " ")
                    cirFile.write(f".SUBCKT {schematicObj.cellName} {pinList}\n")
                    self.recursiveNetlisting(schematicObj, cirFile)
                    cirFile.write(".ENDS\n")
        elif "symbol" in netlistView:
            cirFile.write(self.createXyceSymbolLine(elementSymbol))
        elif "spice" in netlistView:
            cirFile.write(self.createSpiceLine(elementSymbol))
        elif "veriloga" in netlistView:
            cirFile.write(self.createVerilogaLine(elementSymbol))

    def createXyceSymbolLine(self, elementSymbol: shp.schematicSymbol):
        """
        Create a netlist line from a nlp device format line.
        """
        try:
            xyceNetlistFormatLine = elementSymbol.symattrs["XyceSymbolNetlistLine"].strip()

            # Process labels
            for labelItem in elementSymbol.labels.values():
                xyceNetlistFormatLine = xyceNetlistFormatLine.replace(labelItem.labelName,
                                                                      labelItem.labelValue)

            # Add pin list
            pinList = " ".join(elementSymbol.pinNetMap.values())
            xyceNetlistFormatLine = (
                    xyceNetlistFormatLine.replace("%pinOrder", pinList) + "\n")
            # Process other attributes
            for attrb, value in elementSymbol.symattrs.items():
                xyceNetlistFormatLine = xyceNetlistFormatLine.replace(f"%{attrb}", value)
            xyceNetlistFormatLine = re.sub(r'\s+\w+\s*=(?=\s|$)', '', xyceNetlistFormatLine)
            return xyceNetlistFormatLine

        except Exception as e:
            self._scene.logger.error(
                f"Error creating netlist line for {elementSymbol.instanceName}: {e}")
            return (
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n")

    def createSpiceLine(self, elementSymbol: shp.schematicSymbol):
        """
        Create a netlist line from a nlp device format line.
        """
        try:
            spiceNetlistFormatLine = elementSymbol.symattrs["VacaskSpiceNetlistLine"].strip()
            for labelItem in elementSymbol.labels.values():
                if labelItem.labelName in spiceNetlistFormatLine:
                    spiceNetlistFormatLine = spiceNetlistFormatLine.replace(
                        labelItem.labelName, labelItem.labelValue)

            for attrb, value in elementSymbol.symattrs.items():
                if f"%{attrb}" in spiceNetlistFormatLine:
                    spiceNetlistFormatLine = spiceNetlistFormatLine.replace(f"%{attrb}",
                                                                            value)
            pinList = elementSymbol.symattrs.get("pinOrder", ", ").replace(",", " ")
            spiceNetlistFormatLine = (
                    spiceNetlistFormatLine.replace("@pinList", pinList) + "\n")
            self.includeLines.add(elementSymbol.symattrs.get("incLine",
                                                             "* no include line is found for {item.cellName}").strip())
            return spiceNetlistFormatLine
        except Exception as e:
            self._scene.logger.error(f"Spice subckt netlist error: {e}")
            self._scene.logger.error(
                f"Netlist line is not defined for {elementSymbol.instanceName}")
            # if there is no NLPDeviceFormat line, create a warning line
            return (
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n")

    def createVerilogaLine(self, elementSymbol):
        """
        Create a netlist line from a nlp device format line.
        """
        try:
            verilogaNetlistFormatLine = elementSymbol.symattrs[
                "XyceVerilogaNetlistLine"].strip()
            for labelItem in elementSymbol.labels.values():
                if labelItem.labelName in verilogaNetlistFormatLine:
                    verilogaNetlistFormatLine = verilogaNetlistFormatLine.replace(
                        labelItem.labelName, labelItem.labelValue)

            for attrb, value in elementSymbol.symattrs.items():
                if f"%{attrb}" in verilogaNetlistFormatLine:
                    verilogaNetlistFormatLine = verilogaNetlistFormatLine.replace(
                        f"%{attrb}", value)
            pinList = " ".join(elementSymbol.pinNetMap.values())
            verilogaNetlistFormatLine = (
                    verilogaNetlistFormatLine.replace("@pinList", pinList) + "\n")
            self.vamodelLines.add(elementSymbol.symattrs.get("vaModelLine",
                                                             "* no model line is found for {item.cellName}").strip())
            self.vahdlLines.add(elementSymbol.symattrs.get("vaHDLLine",
                                                           "* no hdl line is found for {item.cellName}").strip())
            return verilogaNetlistFormatLine
        except Exception as e:
            self._scene.logger.error(e)
            self._scene.logger.error(
                f"Netlist line is not defined for {elementSymbol.instanceName}")
            # if there is no NLPDeviceFormat line, create a warning line
            return (
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n")


class vacaskNetlist():
    def __init__(self, schematic: schematicEditor, filePathObj: pathlib.Path,
                 useConfig: bool = False, ):
        self.filePathObj = filePathObj
        self.schematic = schematic
        self._use_config = useConfig
        self._scene = self.schematic.centralW.scene
        self.libraryDict = self.schematic.libraryDict
        self.libraryView = self.schematic.libraryView
        self._configDict = None
        self.libItem = libm.getLibItem(self.schematic.libraryView.libraryModel,
                                       self.schematic.libName, )
        self.cellItem = libm.getCellItem(self.libItem, self.schematic.cellName)

        self._switchViewList = schematic.switchViewList
        self._stopViewList = schematic.stopViewList
        self.netlistedViewsSet = set()  # keeps track of netlisted views.

    def __repr__(self):
        return f"xyceNetlist(filePathObj={self.filePathObj}, schematic={self.schematic}, useConfig={self._use_config})"

    @property
    def switchViewList(self) -> List[str]:
        return self._switchViewList

    @switchViewList.setter
    def switchViewList(self, value: List[str]):
        self._switchViewList = value

    @property
    def stopViewList(self) -> List[str]:
        return self._stopViewList

    @stopViewList.setter
    def stopViewList(self, value: List[str]):
        self._stopViewList = value

    def writeNetlist(self):
        with self.filePathObj.open(mode="w") as cirFile:
            cirFile.write("*".join(
                ["\n", 80 * "/", "\n", "// Revolution EDA VACASK Netlist\n",
                 f"// Library: {self.schematic.libName}\n",
                 f"// Top Cell Name: {self.schematic.cellName}\n",
                 f"// View Name: {self.schematic.viewName}\n",
                 f"// Date: {datetime.datetime.now()}\n", 80 * "/", "\n",
                 "ground 0\n\n", ]))

            # now go down the rabbit hole to track all circuit elements.
            self.recursiveNetlisting(self.schematic, cirFile)

            for line in self.includeLines:
                cirFile.write(f"{line}\n")
            for line in self.vamodelLines:
                cirFile.write(f"{line}\n")
            for line in self.vahdlLines:
                cirFile.write(f"{line}\n")

    @property
    def configDict(self):
        return self._configDict

    @configDict.setter
    def configDict(self, value: dict):
        self._configDict = value

    def recursiveNetlisting(self, schematic: schematicEditor, cirFile):
        """
        Recursively traverse all sub-circuits and netlist them.
        """
        schematicScene = schematic.centralW.scene
        schematicScene.nameSceneNets()  # name all nets in the schematic
        sceneSymbolSet = schematicScene.findSceneSymbolSet()
        schematicScene.generatePinNetMap(sceneSymbolSet)
        for elementSymbol in sceneSymbolSet:
            self.processElementSymbol(elementSymbol, schematic, cirFile)

    def processElementSymbol(self, elementSymbol, schematic, cirFile):
        if elementSymbol.symattrs.get("vacaskNetlistPass") != "1" and (
                not elementSymbol.netlistIgnore):
            libItem = libm.getLibItem(schematic.libraryView.libraryModel,
                                      elementSymbol.libraryName)
            cellItem = libm.getCellItem(libItem, elementSymbol.cellName)
            netlistView = self.determineNetlistView(elementSymbol, cellItem)

            # Create the netlist line for the item.
            self.createItemLine(cirFile, elementSymbol, cellItem, netlistView)
        elif elementSymbol.netlistIgnore:
            cirFile.write(f"//{elementSymbol.instanceName} is marked to be ignored\n")
        elif not elementSymbol.symattrs.get("vacaskNetlistPass", False):
            cirFile.write(
                f"*{elementSymbol.instanceName} has no VacaskNetlistLine attribute\n")

    def determineNetlistView(self, elementSymbol, cellItem):
        viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]
        viewNames = [view.viewName for view in viewItems]

        if self._use_config:
            return self.configDict.get(elementSymbol.cellName)[1]
        else:
            # Iterate over the switch view list to determine the appropriate netlist view.
            for viewName in self._switchViewList:
                if viewName in viewNames:
                    return viewName
            return "symbol"

    def createItemLine(self, cirFile, elementSymbol: shp.schematicSymbol,
                       cellItem: libb.cellItem, netlistView: str, ):
        if "schematic" in netlistView:
            # First write subckt call in the netlist.
            cirFile.write(self.createXyceSymbolLine(elementSymbol))
            schematicItem = libm.getViewItem(cellItem, netlistView)
            if netlistView not in self._stopViewList:
                # now load the schematic
                schematicObj = schematicEditor(schematicItem, self.libraryDict,
                                               self.libraryView)
                schematicObj.loadSchematic()

                viewTuple = ddef.viewTuple(schematicObj.libName, schematicObj.cellName,
                                           schematicObj.viewName)

                if viewTuple not in self.netlistedViewsSet:
                    self.netlistedViewsSet.add(viewTuple)
                    pinList = elementSymbol.symattrs.get("pinOrder", ", ").replace(",", " ")
                    cirFile.write(f"subckt {schematicObj.cellName} {pinList}\n")
                    self.recursiveNetlisting(schematicObj, cirFile)
                    cirFile.write("ends\n")
        elif "symbol" in netlistView:
            cirFile.write(self.createVacaskSymbolLine(elementSymbol))
        elif "spice" in netlistView:
            cirFile.write("Cannot import spice to Vacask netlists yet\n")
        elif "veriloga" in netlistView:
            cirFile.write(self.createVerilogaLine(elementSymbol))

    def createVacaskSymbolLine(self, elementSymbol: shp.schematicSymbol) -> str:
        """
        Create a netlist line from a Vacask device format line.

        Args:
            elementSymbol (shp.schematicSymbol): The schematic symbol containing netlist information

        Returns:
            str: The formatted netlist line

        Raises:
            KeyError: If required VacaskSymbolNetlistLine attribute is missing
        """
        try:
            # Get the base netlist format line
            try:
                netlist_line = elementSymbol.symattrs["VacaskSymbolNetlistLine"].strip()
            except KeyError:
                raise KeyError("Missing required VacaskSymbolNetlistLine attribute")

            # Create a mapping for all replacements at once
            replacements = {}

            # Add label replacements
            replacements.update({label.labelName: label.labelValue for label in
                                 elementSymbol.labels.values()})

            # Add attribute replacements
            replacements.update(
                {f"%{attr}": value for attr, value in elementSymbol.symattrs.items()})

            # Add pin list replacement
            pin_list = f'({" ".join(elementSymbol.pinNetMap.values())})'
            replacements["@pinList"] = pin_list

            # Perform all replacements in one pass
            for old, new in replacements.items():
                netlist_line = netlist_line.replace(old, new)

            return netlist_line + "\n"

        except Exception as e:
            raise Exception(f"Error creating Vacask netlist line: {str(e)}")

    # def createVacaskSymbolLine(self, elementSymbol: shp.schematicSymbol):
    #     """
    #     Create a netlist line from a nlp device format line.
    #     """
    #     try:
    #         vacaskNetlistFormatLine = elementSymbol.symattrs[
    #             "VacaskSymbolNetlistLine"].strip()
    #
    #         # Process labels
    #         for labelItem in elementSymbol.labels.values():
    #             vacaskNetlistFormatLine = vacaskNetlistFormatLine.replace(labelItem.labelName,
    #                                                                   labelItem.labelValue)
    #
    #         # Process attributes
    #         for attrb, value in elementSymbol.symattrs.items():
    #             vacaskNetlistFormatLine = vacaskNetlistFormatLine.replace(f"%{attrb}", value)
    #         # Add pin list with parantheses
    #         pinList = f'({" ".join(elementSymbol.pinNetMap.values())})'
    #         xyceNetlistFormatLine = (
    #                     vacaskNetlistFormatLine.replace("@pinList", pinList) + "\n")
    #
    #         return vacaskNetlistFormatLine
    #
    #     except Exception as e:
    #         self._scene.logger.error(
    #             f"Error creating netlist line for {elementSymbol.instanceName}: {e}")
    #         return (
    #             f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n")


    def createVerilogaLine(self, elementSymbol):
        """
        Create a netlist line from a nlp device format line.
        """
        try:
            verilogaNetlistFormatLine = elementSymbol.symattrs[
                "XyceVerilogaNetlistLine"].strip()
            for labelItem in elementSymbol.labels.values():
                if labelItem.labelName in verilogaNetlistFormatLine:
                    verilogaNetlistFormatLine = verilogaNetlistFormatLine.replace(
                        labelItem.labelName, labelItem.labelValue)

            for attrb, value in elementSymbol.symattrs.items():
                if f"%{attrb}" in verilogaNetlistFormatLine:
                    verilogaNetlistFormatLine = verilogaNetlistFormatLine.replace(
                        f"%{attrb}", value)
            pinList = " ".join(elementSymbol.pinNetMap.values())
            verilogaNetlistFormatLine = (
                    verilogaNetlistFormatLine.replace("@pinList", pinList) + "\n")
            self.vamodelLines.add(elementSymbol.symattrs.get("vaModelLine",
                                                             "* no model line is found for {item.cellName}").strip())
            self.vahdlLines.add(elementSymbol.symattrs.get("vaHDLLine",
                                                           "* no hdl line is found for {item.cellName}").strip())
            return verilogaNetlistFormatLine
        except Exception as e:
            self._scene.logger.error(e)
            self._scene.logger.error(
                f"Netlist line is not defined for {elementSymbol.instanceName}")
            # if there is no NLPDeviceFormat line, create a warning line
            return (
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n")
