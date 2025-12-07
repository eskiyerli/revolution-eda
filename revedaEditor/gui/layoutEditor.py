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
import pathlib

# import numpy as np
from PySide6.QtCore import (Qt, )
from PySide6.QtGui import (QAction, QIcon, )
from PySide6.QtWidgets import (QApplication, QDialog, QMenu, QSplitter, QToolBar,
                               QVBoxLayout, QWidget)
from quantiphy import Quantity

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview

# import revedaEditor.fileio.layoutEncoder as layenc
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.gui.editorViews as edv
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.layoutDialogues as ldlg
import revedaEditor.gui.lsw as lsw
from revedaEditor.backend.pdkPaths import importPDKModule
from revedaEditor.scenes.layoutScene import layoutScene

fabproc = importPDKModule('process')
laylyr = importPDKModule('layoutLayers')


class layoutEditor(edw.editorWindow):

    def __init__(self, viewItem: libb.viewItem, libraryDict: dict,
                 libraryView) -> None:
        super().__init__(viewItem, libraryDict, libraryView)
        self.setWindowTitle(f"Layout Editor - {self.cellName} - {self.viewName}")
        self.setWindowIcon(QIcon(":/icons/edLayer-shape.png"))
        self.layoutViews = ["layout", "pcell"]
        self.dbu = fabproc.dbu
        self.majorGrid = fabproc.majorGrid
        self.snapGrid = fabproc.snapGrid
        self.snapTuple = (self.snapGrid, self.snapGrid)
        self.layoutChooser = None
        self.gdsExportDirObj = (self.appMainW.runPath / 'gdsExport' /
                                self.libName / self.cellName)
        self.gdsExportDirObj.mkdir(parents=True, exist_ok=True)
        self._layoutContextMenu()
        # drc error polygons
        self._previousPolygons = []

    def init_UI(self):
        super().init_UI()
        # create container to position all widgets
        self.centralW = layoutContainer(self)
        self.setCentralWidget(self.centralW)

    def _createMenuBar(self):
        super()._createMenuBar()
        self.alignMenu = QMenu("Align", self)
        self.alignMenu.setIcon(QIcon("icons/layers-alignment-middle.png"))
        self.klayoutVerMenu = QMenu('KLayout DRC/LVS')
        self.menuTools.addMenu(self.klayoutVerMenu)
        self.propertyMenu = self.menuEdit.addMenu("Properties")

    def _createActions(self):
        super()._createActions()
        self.exportGDSAction = QAction("Export GDS", self)
        self.exportGDSAction.setToolTip("Export GDS from Layout")
        self.klayoutDRCAction = QAction("KLayout DRC...", self)
        self.klayoutDRCAction.setToolTip("DRC with KLayout")

    def _addActions(self):
        super()._addActions()
        self.menuEdit.addMenu(self.alignMenu)
        # self.menuUtilities.addMenu(self.selectMenu)
        self.selectMenu.addAction(self.selectDeviceAction)
        self.selectMenu.addAction(self.selectWireAction)
        self.selectMenu.addSeparator()
        self.selectMenu.addAction(self.removeSelectFilterAction)

        self.propertyMenu.addAction(self.objPropAction)
        self.menuEdit.addAction(self.stretchAction)
        self.menuCreate.addAction(self.createInstAction)
        self.menuCreate.addAction(self.createRectAction)
        self.menuCreate.addAction(self.createPathAction)
        self.menuCreate.addAction(self.createPinAction)
        self.menuCreate.addAction(self.createLabelAction)
        self.menuCreate.addAction(self.createViaAction)
        self.menuCreate.addAction(self.createPolygonAction)
        self.menuCreate.addSeparator()
        self.menuCreate.addAction(self.rulerAction)
        self.menuCreate.addAction(self.delRulerAction)
        self.menuTools.addAction(self.exportGDSAction)
        self.klayoutVerMenu.addAction(self.klayoutDRCAction)

        # hierarchy submenu
        self.hierMenu = self.menuEdit.addMenu("Hierarchy")
        self.hierMenu.addAction(self.goUpAction)
        self.hierMenu.addAction(self.goDownAction)

    def _layoutContextMenu(self):
        super()._editorContextMenu()
        self.centralW.scene.itemContextMenu.addAction(self.goDownAction)

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

        self.createPathAction.triggered.connect(self.createPathClick)
        self.createPinAction.triggered.connect(self.createPinClick)
        self.createLabelAction.triggered.connect(self.createLabelClick)
        self.createViaAction.triggered.connect(self.createViaClick)
        self.createPolygonAction.triggered.connect(self.createPolygonClick)
        self.rulerAction.triggered.connect(self.createRulerClick)
        self.delRulerAction.triggered.connect(self.delRulerClick)
        self.deleteAction.triggered.connect(self.deleteClick)
        self.objPropAction.triggered.connect(self.objPropClick)
        self.klayoutDRCAction.triggered.connect(self.klayoutDRCClick)
        self.goDownAction.triggered.connect(self.goDownClick)

    def _createShortcuts(self):
        super()._createShortcuts()
        self.createRectAction.setShortcut(Qt.Key_R)
        self.createPathAction.setShortcut(Qt.Key_W)
        self.createInstAction.setShortcut(Qt.Key_I)
        self.createPinAction.setShortcut(Qt.Key_P)
        self.createLabelAction.setShortcut(Qt.Key_L)
        self.createViaAction.setShortcut(Qt.Key_V)
        self.createPolygonAction.setShortcut(Qt.Key_G)
        self.stretchAction.setShortcut(Qt.Key_S)
        self.rulerAction.setShortcut(Qt.Key_K)
        self.delRulerAction.setShortcut("Shift+K")

    def createRectClick(self, s):
        self.centralW.scene.editModes.setMode("drawRect")

    def createRulerClick(self, s):
        self.centralW.scene.editModes.setMode("drawRuler")
        self.messageLine.setText("Click on the first point of the ruler.")

    def delRulerClick(self, s):
        self.messageLine.setText("Deleting all rulers")
        self.centralW.scene.deleteAllRulers()
        self.centralW.scene.editModes.setMode("selectItem")

    def createPathClick(self, s):
        def pathLayerChanged(dlg):
            pathTupleName = dlg.pathLayerCB.currentText()
            pathDefTuple = \
                [item for item in fabproc.processPaths if item.name == pathTupleName][
                    0]
            dlg.pathWidth.setText(pathDefTuple.minWidth.__str__())
            dlg.pathWidthValidator.setRange(pathDefTuple.minWidth,
                                            pathDefTuple.maxWidth)
            dlg.startExtendEdit.setText(str(pathDefTuple.minWidth / 2))
            dlg.endExtendEdit.setText(str(pathDefTuple.minWidth / 2))

        dlg = ldlg.createPathDialogue(self)
        # paths are created on path layers
        processPathNames = [f'{pathTuple.name}' for pathTuple in
                            fabproc.processPaths]
        dlg.pathLayerCB.addItems(processPathNames)
        dlg.pathLayerCB.setCurrentIndex(0)
        defaultPathTuple = fabproc.processPaths[0]
        dlg.pathLayerCB.currentIndexChanged.connect(lambda: pathLayerChanged(dlg))
        dlg.pathWidth.setText(fabproc.processPaths[0].minWidth.__str__())
        dlg.pathWidthValidator.setRange(defaultPathTuple.minWidth,
                                        defaultPathTuple.maxWidth)
        dlg.startExtendEdit.setText(str(fabproc.processPaths[0].minWidth / 2))
        dlg.endExtendEdit.setText(str(fabproc.processPaths[0].minWidth / 2))

        if dlg.exec() == QDialog.Accepted:
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
            pathTuple = \
                [item for item in fabproc.processPaths if item.name == pathTupleName][
                    0]
            pathLayer = pathTuple.layer
            startExtend = float(dlg.startExtendEdit.text().strip()) * fabproc.dbu
            endExtend = float(dlg.endExtendEdit.text().strip()) * fabproc.dbu
            self.centralW.scene.newPathTuple = ddef.layoutPathTuple(pathName,
                                                                    pathLayer,
                                                                    pathMode,
                                                                    pathWidth,
                                                                    startExtend,
                                                                    endExtend)

    def createPinClick(self):
        dlg = ldlg.createLayoutPinDialog(self)
        pinLayersNames = [f"{item.name} [{item.purpose}]" for item in
                          laylyr.pdkPinLayers]
        textLayersNames = [f"{item.name} [{item.purpose}]" for item in
                           laylyr.pdkTextLayers]
        dlg.pinLayerCB.addItems(pinLayersNames)
        dlg.labelLayerCB.addItems(textLayersNames)

        if self.centralW.scene.newPinTuple is not None:
            dlg.pinLayerCB.setCurrentText(
                f"{self.centralW.scene.newPinTuple.pinLayer.name} "
                f"[{self.centralW.scene.newPinTuple.pinLayer.purpose}]")
        if self.centralW.scene.newLabelTuple is not None:
            dlg.labelLayerCB.setCurrentText(
                f"{self.centralW.scene.newLabelTuple.labelLayer.name} ["
                f"{self.centralW.scene.newLabelTuple.labelLayer.purpose}]")
            dlg.familyCB.setCurrentText(
                self.centralW.scene.newLabelTuple.fontFamily)
            dlg.fontStyleCB.setCurrentText(
                self.centralW.scene.newLabelTuple.fontStyle)
            dlg.labelHeightCB.setCurrentText(
                str(self.centralW.scene.newLabelTuple.fontHeight))
            dlg.labelAlignCB.setCurrentText(
                self.centralW.scene.newLabelTuple.labelAlign)
            dlg.labelOrientCB.setCurrentText(
                self.centralW.scene.newLabelTuple.labelOrient)
        if dlg.exec() == QDialog.Accepted:
            self.centralW.scene.editModes.setMode("drawPin")
            pinName = dlg.pinName.text()
            pinDir = dlg.pinDir.currentText()
            pinType = dlg.pinType.currentText()
            pinLayerName = dlg.pinLayerCB.currentText().split()[0]
            pinLayer = \
                [item for item in laylyr.pdkPinLayers if item.name == pinLayerName][0]
            labelLayerName = dlg.labelLayerCB.currentText().split()[0]
            labelLayer = [item for item in laylyr.pdkTextLayers if
                          item.name == labelLayerName][0]
            fontFamily = dlg.familyCB.currentText()
            fontStyle = dlg.fontStyleCB.currentText()
            labelHeight = float(dlg.labelHeightCB.currentText())
            labelAlign = dlg.labelAlignCB.currentText()
            labelOrient = dlg.labelOrientCB.currentText()
            self.centralW.scene.newPinTuple = ddef.layoutPinTuple(pinName, pinDir,
                                                                  pinType, pinLayer)
            self.centralW.scene.newLabelTuple = ddef.layoutLabelTuple(pinName,
                                                                      fontFamily, fontStyle, labelHeight, labelAlign,
                                                                      labelOrient,
                                                                      labelLayer, )

    def createLabelClick(self):
        dlg = ldlg.createLayoutLabelDialog(self)
        textLayersNames = [f"{item.name} [{item.purpose}]" for item in
                           laylyr.pdkTextLayers]
        dlg.labelLayerCB.addItems(textLayersNames)
        if dlg.exec() == QDialog.Accepted:
            self.centralW.scene.editModes.setMode("addLabel")
            labelName = dlg.labelName.text()
            labelLayerName = dlg.labelLayerCB.currentText().split()[0]
            labelLayer = [item for item in laylyr.pdkTextLayers if
                          item.name == labelLayerName][0]
            fontFamily = dlg.familyCB.currentText()
            fontStyle = dlg.fontStyleCB.currentText()
            fontHeight = dlg.labelHeightCB.currentText()
            labelAlign = dlg.labelAlignCB.currentText()
            labelOrient = dlg.labelOrientCB.currentText()
            self.centralW.scene.newLabelTuple = ddef.layoutLabelTuple(labelName,
                                                                      fontFamily, fontStyle, fontHeight, labelAlign,
                                                                      labelOrient,
                                                                      labelLayer, )

    def createViaClick(self):
        dlg = ldlg.createLayoutViaDialog(self)
        viaLayerNames = [item.name for item in fabproc.processVias]
        dlg.singleViaNamesCB.addItems(viaLayerNames)
        dlg.arrayViaNamesCB.addItems(viaLayerNames)
        dlg.singleViaWidthEdit.setText(str(fabproc.processVias[0].minWidth))
        dlg.singleViaHeightEdit.setText(str(fabproc.processVias[0].minHeight))
        dlg.arrayViaWidthEdit.setText(str(fabproc.processVias[0].minWidth))
        dlg.arrayViaHeightEdit.setText(str(fabproc.processVias[0].minHeight))
        dlg.arrayXspacingEdit.setText(str(fabproc.processVias[0].minSpacing))
        dlg.arrayYspacingEdit.setText(str(fabproc.processVias[0].minSpacing))
        if dlg.exec() == QDialog.Accepted:
            self.centralW.scene.editModes.setMode("addVia")
            self.centralW.scene.addVia = True
            if dlg.singleViaRB.isChecked():
                selViaDefTuple = fabproc.processVias[
                    fabproc.processViaNames.index(
                        dlg.singleViaNamesCB.currentText())]

                singleViaTuple = ddef.singleViaTuple(selViaDefTuple,
                                                     fabproc.dbu * float(dlg.singleViaWidthEdit.text().strip()),
                                                     fabproc.dbu * float(dlg.singleViaHeightEdit.text().strip()), )
                self.centralW.scene.arrayViaTuple = ddef.arrayViaTuple(
                    singleViaTuple, fabproc.dbu * selViaDefTuple.minSpacing,
                                    fabproc.dbu * selViaDefTuple.minSpacing, 1,
                    1, )
            else:
                selViaDefTuple = \
                    [viaDefTuple for viaDefTuple in fabproc.processVias if
                     viaDefTuple.name == dlg.arrayViaNamesCB.currentText()][0]

                singleViaTuple = ddef.singleViaTuple(selViaDefTuple,
                                                     fabproc.dbu * float(dlg.arrayViaWidthEdit.text().strip()),
                                                     fabproc.dbu * float(dlg.arrayViaHeightEdit.text().strip()), )
                self.centralW.scene.arrayViaTuple = ddef.arrayViaTuple(
                    singleViaTuple,
                    fabproc.dbu * float(dlg.arrayXspacingEdit.text().strip()),
                    fabproc.dbu * float(dlg.arrayYspacingEdit.text().strip()),
                    int(float(dlg.arrayXNumEdit.text().strip())),
                    int(float(dlg.arrayYNumEdit.text().strip())), )
        else:
            self.centralW.scene.editModes.setMode("selectItem")

    def createPolygonClick(self):
        self.centralW.scene.editModes.setMode("drawPolygon")

    def objPropClick(self, s):
        self.centralW.scene.viewObjProperties()

    def goDownClick(self):
        self.centralW.scene.goDownHier()

    def checkSaveCell(self):
        self.centralW.scene.saveLayoutCell(
            self.file)  # if the parent editor is not None, emit the childEditorChanged signal  # and pass the parentObj as the argument  # if self.parentEditor:  #     self.parentEditor.childEditorChanged.emit(self.parentObj)

    def saveCell(self):
        self.centralW.scene.saveLayoutCell(self.file)

    def loadLayout(self):
        self.logger.info(f'Loading layout from {self.cellName} - {self.viewName}')

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:

            self.centralW.scene.loadDesign(self.file)
        finally:
            QApplication.restoreOverrideCursor()

    def createInstClick(self, s):
        # create a designLibrariesView
        libraryModel = lmview.layoutViewsModel(self.libraryDict, self.layoutViews)
        if self.layoutChooser is None:
            self.layoutChooser = fd.selectCellViewDialog(self, libraryModel)
            self.layoutChooser.show()
        else:
            self.layoutChooser.raise_()
        if self.layoutChooser.exec() == QDialog.Accepted:
            self.centralW.scene.editModes.setMode("addInstance")
            libItem = libm.getLibItem(libraryModel,
                                      self.layoutChooser.libNamesCB.currentText())
            cellItem = libm.getCellItem(libItem,
                                        self.layoutChooser.cellCB.currentText())
            viewItem = libm.getViewItem(cellItem,
                                        self.layoutChooser.viewCB.currentText())
            # libm.findViewItem(libraryModel, self.layoutChooser.libNamesCB.currentText())
            self.centralW.scene.layoutInstanceTuple = ddef.viewItemTuple(libItem,
                                                                         cellItem, viewItem)

    def exportGDSClick(self):
        dlg = fd.gdsExportDialogue(self)
        dlg.unitEdit.setText(fabproc.gdsUnit.render())
        dlg.precisionEdit.setText(fabproc.gdsPrecision.render())
        dlg.exportPathEdit.setText(str(self.gdsExportDirObj))

        if dlg.exec() == QDialog.Accepted:
            self.gdsExportDir = pathlib.Path(dlg.exportPathEdit.text().strip())
            gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
            gdsPrecision = Quantity(
                dlg.precisionEdit.text().strip()).real
            self.centralW.scene.exportCellGDS(self.gdsExportDir, gdsUnit, gdsPrecision, fabproc.dbu)

    def handlePolygonSelection(self, polygons):
        # Remove previous polygons
        for polygon in self._previousPolygons:
            self.centralW.scene.removeItem(polygon)

        # Add new polygons
        for polygon in polygons:
            self.centralW.scene.addItem(polygon)

        # Remember current polygons (store reference)
        self._previousPolygons = polygons

    def klayoutDRCClick(self):
        klayoutDRCModule = importPDKModule("klayoutDRC")
        if klayoutDRCModule is None:
            self.logger.error('PDK does not allow DRC verification with KLayout.')
            return

        def saveRunSet(dlg):
            klayoutPath = dlg.klayoutPathEdit.text().strip()
            cellName = dlg.cellNameEdit.text().strip()
            drcRunSetName = dlg.DRCRunSetCB.currentText().strip()
            drcRunLimit = dlg.DRCRunLimitEdit.text().strip()
            drcRunPath = dlg.DRCRunPathEdit.text().strip()
            gdsExport = 1 if dlg.gdsExportBox.isChecked() else 0
            gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
            gdsPrecision = Quantity(dlg.precisionEdit.text().strip()).real
            drcRunPathObj = pathlib.Path(drcRunPath)
            drcRunPathObj.mkdir(parents=True, exist_ok=True)
            settingsPathObj = drcRunPathObj / 'drcSettings.json'
            with settingsPathObj.open('w') as f:
                json.dump({'klayoutPath': klayoutPath, 'cellName': cellName,
                           'drcRunSetName': drcRunSetName, 'drcRunLimit':
                               drcRunLimit, 'drcRunPath': drcRunPath,
                           'gdsExport': gdsExport, 'gdsUnit': gdsUnit,
                           'gdsPrecision': gdsPrecision}, f, indent=4)

        def DRCProcessFinished(filePath: pathlib.Path):
            dlg = ldlg.drcErrorsDialogue(self, filePath.resolve())
            dlg.drcTable.polygonSelected.connect(self.handlePolygonSelection)
            dlg.show()

        def runKlayoutDRC(dlg):
            klayoutPath = dlg.klayoutPathEdit.text().strip()
            cellName = dlg.cellNameEdit.text().strip()
            drcRunSetName = dlg.DRCRunSetCB.currentText().strip()
            drcRunLimit = dlg.DRCRunLimitEdit.text().strip()
            drcRunPath = dlg.DRCRunPathEdit.text().strip()
            gdsExport = 1 if dlg.gdsExportBox.isChecked() else 0
            gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
            gdsPrecision = Quantity(dlg.precisionEdit.text().strip()).real
            drcRunPathObj = pathlib.Path(drcRunPath)
            drcRunPathObj.mkdir(parents=True, exist_ok=True)
            if gdsExport:
                self.centralW.scene.exportCellGDS(drcRunPathObj, gdsUnit, gdsPrecision, fabproc.dbu)
            if (drcRunPathObj / f'{cellName}.gds').exists():
                gdsPath = drcRunPathObj.joinpath(f'{cellName}.gds')
                drcPath = pathlib.Path(drc.__file__).parent.resolve()
                drcRuleFilePath = drcPath.joinpath(f'{drcRunSetName}.lydrc')
                drcReportFilePath = drcRunPathObj.joinpath(f'{cellName}.lyrdb')
                argumentsList = ['-b', '-r',
                                 f'{drcRuleFilePath}',
                                 '-rd',
                                 f'in_gds={gdsPath}',
                                 '-rd',
                                 f'report_file={drcReportFilePath}']
                self.processManager.maxProcesses = int(drcRunLimit)
                drcProcess = self.processManager.add_process(klayoutPath, argumentsList)
                drcProcess.process.finished.connect(lambda: DRCProcessFinished(drcReportFilePath))
            else:
                self.logger.error('GDS file can not be found')

        dlg = klayoutDRCModule.drcKLayoutDialogue(self)
        drc = importPDKModule("drc")
        if drc is None:
            self.logger.error('PDK does not have DRC module.')
            return
        drcPath = pathlib.Path(drc.__file__).parent.resolve()
        rulesFiles = [pathItem.stem for pathItem in list(drcPath.glob("*.lydrc"))]
        dlg.DRCRunSetCB.addItems(rulesFiles)
        dlg.saveButton.clicked.connect(lambda: saveRunSet(dlg))
        dlg.runButton.clicked.connect(lambda: runKlayoutDRC(dlg))
        settingsPathObj = (self.gdsExportDirObj / 'drcSettings.json')
        if settingsPathObj.exists():
            try:
                with settingsPathObj.open('r') as f:
                    settings = json.load(f)
                    dlg.klayoutPathEdit.setText(settings['klayoutPath'])
                    dlg.cellNameEdit.setText(settings['cellName'])
                    dlg.DRCRunSetCB.setCurrentText(settings['drcRunSetName'])
                    dlg.DRCRunLimitEdit.setText(settings['drcRunLimit'])
                    dlg.DRCRunPathEdit.setText(settings['drcRunPath'])
                    dlg.gdsExportBox.setChecked(bool(settings['gdsExport']))
                    dlg.unitEdit.setText(str(settings['gdsUnit']))
                    dlg.precisionEdit.setText(str(settings['gdsPrecision']))
            except Exception as e:
                self.logger.error(e)
        else:
            dlg.gdsExportBox.setChecked(False)
            dlg.cellNameEdit.setText(self.cellName)
            dlg.DRCRunSetCB.setCurrentIndex(0)
            dlg.DRCRunLimitEdit.setText('2')
            dlg.DRCRunPathEdit.setText(str(self.gdsExportDirObj))
            if hasattr(fabproc, "gdsUnit"):
                dlg.unitEdit.setText(fabproc.gdsUnit.render())
            if hasattr(fabproc, "gdsPrecision"):
                dlg.precisionEdit.setText(fabproc.gdsPrecision.render())

        dlg.show()

    def dispConfigEdit(self):
        import revedaEditor.gui.propertyDialogues as pdlg
        dcd = pdlg.layoutDisplayConfigDialog(self)
        dcd.dbuEntry.setText(str(self.dbu))
        dcd.majorGridEntry.setText(str(self.majorGrid))
        dcd.snapGridEdit.setText(str(self.snapGrid))
        if dcd.exec() == QDialog.Accepted:
            self.configureGridSettings(
                (int(dcd.majorGridEntry.text()), int(dcd.snapGridEdit.text())))
            if dcd.dotType.isChecked():
                self.centralW.view.gridbackg = True
                self.centralW.view.linebackg = False
            elif dcd.lineType.isChecked():
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = True
            else:
                self.centralW.view.gridbackg = False
                self.centralW.view.linebackg = False

    def _createSignalConnections(self):
        super()._createSignalConnections()  # if self.parentEditor is None:  #     self.childEditorChanged.connect(self.centralW.scene.reloadScene)


class layoutContainer(QWidget):
    def __init__(self, parent: layoutEditor):
        super().__init__(parent=parent)
        self.parent = parent
        self.scene = layoutScene(self)
        self.view = edv.layoutView(self.scene, self)
        self.lswModel = lsw.layerDataModel(laylyr.pdkAllLayers)
        layerViewTable = lsw.layerViewTable(self, self.lswModel)
        self.lswWidget = lswWindow(layerViewTable)
        self.lswWidget.setMinimumWidth(300)
        self.lswWidget.setMaximumWidth(360)
        self.lswWidget.lswTable.dataSelected.connect(self.selectLayer)
        self.lswWidget.lswTable.layerSelectable.connect(
            self.layerSelectableChange)
        self.lswWidget.lswTable.layerVisible.connect(self.layerVisibleChange)
        self.init_UI()

    def init_UI(self):
        # there could be other widgets in the grid layout, such as edLayer
        # viewer/editor.
        vLayout = QVBoxLayout(self)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.insertWidget(0, self.lswWidget)
        splitter.insertWidget(1, self.view)
        # ratio of first column to second column is 5
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        vLayout.addWidget(splitter)

        self.setLayout(vLayout)

    def selectLayer(self, layerName: str, layerPurpose: str):
        self.scene.selectEdLayer = self.findSelectedLayer(layerName, layerPurpose)

    def findSelectedLayer(self, layerName: str, layerPurpose: str):
        for layer in laylyr.pdkAllLayers:
            if layer.name == layerName and layer.purpose == layerPurpose:
                return layer
        return laylyr.pdkAllLayers[0]

    def layerSelectableChange(self, layerName: str, layerPurpose: str,
                              layerSelectable: bool):
        selectedLayer = self.findSelectedLayer(layerName, layerPurpose)
        if selectedLayer:
            selectedLayer.selectable = layerSelectable

        for item in self.scene.items():
            if (hasattr(item,
                        "layer") and item.layer == selectedLayer and item.parentItem() is None):
                item.setEnabled(layerSelectable)
                item.update()

    def layerVisibleChange(self, layerName: str, layerPurpose: str,
                           layerVisible: bool):
        selectedLayer = self.findSelectedLayer(layerName, layerPurpose)
        if selectedLayer:
            selectedLayer.visible = layerVisible

            for item in self.scene.items():
                if hasattr(item, "layer") and item.layer == selectedLayer:
                    item.setVisible(layerVisible)
                    item.update()


class lswWindow(QWidget):
    def __init__(self, lswTable: lsw.layerViewTable):
        super().__init__()
        self.lswTable = lswTable
        layout = QVBoxLayout()
        toolBar = QToolBar()
        avIcon = QIcon("icons/eye.png")
        nvIcon = QIcon("icons/eye-close.png")
        avAction = QAction(avIcon, "All Visible", self)
        avAction.setToolTip("All layers visible")
        avAction.triggered.connect(self.lswTable.allLayersVisible)
        nvAction = QAction(nvIcon, "None Visible", self)
        nvAction.setToolTip("No layer visible")
        nvAction.triggered.connect(self.lswTable.noLayersVisible)
        asIcon = QIcon("icons/pencil.png")
        nsIcon = QIcon("icons/pencil-prohibition.png")
        nsAction = QAction(nsIcon, "All Selectable", self)
        nsAction.setToolTip("No layers selectable")
        nsAction.triggered.connect(self.lswTable.noLayersSelectable)
        asAction = QAction(asIcon, "None Selectable", self)
        asAction.setToolTip("All layers selectable")
        asAction.triggered.connect(self.lswTable.allLayersSelectable)

        toolBar.addAction(avAction)
        toolBar.addAction(nvAction)
        toolBar.addAction(asAction)
        toolBar.addAction(nsAction)
        layout.addWidget(toolBar)
        layout.addWidget(self.lswTable)
        self.setLayout(layout)
