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

# import revedaEditor.fileio.symbolEncoder as se
# import revedaEditor.gui.propertyDialogues as pdlg
# import revedaEditor.gui.fileDialogues as fd
# import revedaEditor.gui.libraryBrowser as libw
# import revedaEditor.gui.symbolEditor as syed
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QMainWindow, QDialog

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.hdlBackEnd as hdl
# import revedaEditor.backend.libBackEnd as scb  # import the backend
import revedaEditor.common.shapes as shp
from revedaEditor.backend import dataDefinitions as ddef, hdlBackEnd as hdl, \
    libBackEnd as scb
from revedaEditor.fileio import symbolEncoder as se
from revedaEditor.gui import libraryBrowser as libw, fileDialogues as fd, \
    symbolEditor as syed, \
    propertyDialogues as pdlg


def drawBaseSymbol(symbolScene, dlg):
    leftPinNames = list(
        filter(
            None,
            [pinName.strip() for pinName in dlg.leftPinsEdit.text().split(",")],
        )
    )
    rightPinNames = list(
        filter(
            None,
            [pinName.strip() for pinName in dlg.rightPinsEdit.text().split(",")],
        )
    )
    topPinNames = list(
        filter(
            None,
            [pinName.strip() for pinName in dlg.topPinsEdit.text().split(",")],
        )
    )
    bottomPinNames = list(
        filter(
            None,
            [pinName.strip() for pinName in dlg.bottomPinsEdit.text().split(",")],
        )
    )
    stubLength = (
        int(float(dlg.stubLengthEdit.text().strip()))
        if dlg.stubLengthEdit.text()
        else 60
    )
    pinDistance = (
        int(float(dlg.pinDistanceEdit.text().strip()))
        if dlg.pinDistanceEdit.text()
        else 80
    )
    rectXDim = (max(len(topPinNames), len(bottomPinNames)) + 1) * pinDistance
    rectYDim = (max(len(leftPinNames), len(rightPinNames)) + 1) * pinDistance

    symbolScene.rectDraw(
        QPoint(0, 0),
        QPoint(rectXDim, rectYDim),
    )
    symbolScene.labelDraw(
        QPoint(int(0.25 * rectXDim), int(0.4 * rectYDim)),
        "[@cellName]",
        "NLPLabel",
        "12",
        "Center",
        "R0",
        "Instance",
    )
    symbolScene.labelDraw(
        QPoint(int(rectXDim), int(-0.1 * rectYDim)),
        "[@instName]",
        "NLPLabel",
        "12",
        "Center",
        "R0",
        "Instance",
    )

    leftPinLocs = [
        QPoint(-stubLength, (i + 1) * pinDistance) for i in range(len(leftPinNames))
    ]
    rightPinLocs = [
        QPoint(rectXDim + stubLength, (i + 1) * pinDistance)
        for i in range(len(rightPinNames))
    ]
    bottomPinLocs = [
        QPoint((i + 1) * pinDistance, rectYDim + stubLength)
        for i in range(len(bottomPinNames))
    ]
    topPinLocs = [
        QPoint((i + 1) * pinDistance, -stubLength) for i in range(len(topPinNames))
    ]
    for i, pinName in enumerate(leftPinNames):
        symbolScene.lineDraw(
            leftPinLocs[i],
            leftPinLocs[i] + QPoint(stubLength, 0),
        )
        symbolScene.addItem(
            shp.symbolPin(
                leftPinLocs[i],
                pinName,
                shp.symbolPin.pinDirs[0],
                shp.symbolPin.pinTypes[0],
            )
        )
    for i, pinName in enumerate(rightPinNames):
        symbolScene.lineDraw(
            rightPinLocs[i],
            rightPinLocs[i] + QPoint(-stubLength, 0),
        )
        symbolScene.addItem(
            shp.symbolPin(
                rightPinLocs[i],
                pinName,
                shp.symbolPin.pinDirs[1],
                shp.symbolPin.pinTypes[0],
            )
        )
    for i, pinName in enumerate(topPinNames):
        symbolScene.lineDraw(
            topPinLocs[i],
            topPinLocs[i] + QPoint(0, stubLength),
        )
        symbolScene.addItem(
            shp.symbolPin(
                topPinLocs[i],
                pinName,
                shp.symbolPin.pinDirs[2],
                shp.symbolPin.pinTypes[2],
            )
        )
    for i, pinName in enumerate(bottomPinNames):
        symbolScene.lineDraw(
            bottomPinLocs[i],
            bottomPinLocs[i] + QPoint(0, -stubLength),
        )
        symbolScene.addItem(
            shp.symbolPin(
                bottomPinLocs[i],
                pinName,
                shp.symbolPin.pinDirs[2],
                shp.symbolPin.pinTypes[1],
            )
        )

    return rectXDim, rectYDim


def createVaSymbol(
        parent: QMainWindow,
        vaItemTuple: ddef.viewItemTuple,
        libraryDict: dict,
        libraryBrowser: libw.libraryBrowser,
        importedVaObj: hdl.verilogaC,
) -> None:
    """
    Creates a symbol for a given view item in the library.

    Args:
        parent (QMainWindow): The parentW window.
        vaItemTuple (ddef.viewItemTuple): The view item tuple.
        libraryDict (dict): The library dictionary.
        libraryBrowser (edw.libraryBrowser): The library browser.
        importedVaObj (hdl.verilogaC): The imported Veriloga object.

    Returns:
        None

    Raises:
        None
    """
    symbolNameDlg = fd.createCellViewDialog(
        parent, libraryBrowser.libraryModel, vaItemTuple.cellItem
    )
    symbolNameDlg.viewComboBox.setCurrentText("symbol")
    symbolNameDlg.nameEdit.setText("symbol")
    if symbolNameDlg.exec() == QDialog.DialogCode.Accepted:
        symbolViewName = symbolNameDlg.nameEdit.text().strip()
        symbolViewItem = scb.createCellView(
            parent, symbolViewName, vaItemTuple.cellItem
        )
        newVaFilePathObj = vaItemTuple.cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
            importedVaObj.pathObj.name
        )
        symbolWindow = syed.symbolEditor(
            symbolViewItem,
            libraryDict,
            libraryBrowser.libBrowserCont.designView,
        )
        symbolScene = symbolWindow.centralW.scene
        dlg = pdlg.symbolCreateDialog(parent)

        dlg.leftPinsEdit.setText(",".join(importedVaObj.inPins))
        dlg.rightPinsEdit.setText(",".join(importedVaObj.outPins))
        dlg.topPinsEdit.setText(",".join(importedVaObj.inoutPins))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            rectXDim, rectYDim = drawBaseSymbol(symbolScene, dlg)
            # vaFileLabel = symbolScene.labelDraw(
            #     QPoint(int(0.25 * rectXDim), int(0.6 * rectYDim)),
            #     f"[@vaFile:vaFile=%:vaFile={str(newVaFilePathObj)}]",
            #     "NLPLabel",
            #     "12",
            #     "Center",
            #     "R0",
            #     "Instance",
            # )
            # vaFileLabel.labelVisible = False
            vaModuleLabel = symbolScene.labelDraw(
                QPoint(int(0.25 * rectXDim), int(0.8 * rectYDim)),
                f"[@vaModule:vaModule=%:vaModule={importedVaObj.vaModule}]",
                "NLPLabel",
                "12",
                "Center",
                "R0",
                "Instance",
            )
            vaModuleLabel.labelVisible = True
            # vaModelLabel = symbolScene.labelDraw(
            #     QPoint(int(0.25 * rectXDim), int(1 * rectYDim)),
            #     f"[@vaModel:vaModel=%:vaModel={importedVaObj.vaModule}Model]",
            #     "NLPLabel",
            #     "12",
            #     "Center",
            #     "R0",
            #     "Instance",
            # )
            # vaModelLabel.labelVisible = False

            instParamNum = len(importedVaObj.instanceParams)
            if instParamNum > 0:
                for index, (key, value) in enumerate(
                        importedVaObj.instanceParams.items()
                ):
                    symbolScene.labelDraw(
                        QPoint(
                            int(rectXDim),
                            int(index * 0.2 * rectYDim / instParamNum),
                        ),
                        f"[@{key}:{key}=%:{key}={value}]",
                        "NLPLabel",
                        "12",
                        "Center",
                        "R0",
                        "Instance",
                    )

            symbolScene.attributeList = list()  # empty attribute list
            if importedVaObj.modelParams:
                for key, value in importedVaObj.modelParams.items():
                    symbolScene.attributeList.append(se.symbolAttribute(key, value))
                symbolScene.attributeList.append(
                    se.symbolAttribute(
                        "XyceVerilogaNetlistLine", importedVaObj.netlistLine
                    )
                )

            modelParamsString = ", ".join(
                f"{key} = {value}" for key, value in importedVaObj.modelParams.items()
            )
            symbolScene.attributeList.append(
                se.symbolAttribute(
                    "vaModelLine",
                    f".MODEL {importedVaObj.vaModule}Model {importedVaObj.vaModule} {modelParamsString}",
                )
            )
            symbolScene.attributeList.append(
                se.symbolAttribute("vaHDLLine", f"*.HDL {str(importedVaObj.pathObj)}")
            )
            symbolScene.attributeList.append(
                se.symbolAttribute("pinOrder", importedVaObj.pinOrder)
            )
            symbolWindow.show()
            symbolViewTuple = ddef.viewTuple(
                vaItemTuple.libraryItem.libraryName,
                vaItemTuple.cellItem.cellName,
                "symbol",
            )
            symbolWindow.libraryView.openViews[symbolViewTuple] = symbolWindow


def createSpiceSymbol(
        parent: QMainWindow,
        spiceItemTuple: ddef.viewItemTuple,
        libraryDict: dict,
        libraryBrowser: libw.libraryBrowser,
        importedSpiceObj: hdl.spiceC,
):
    symbolNameDlg = fd.newCellViewDialog(
        parent, libraryBrowser.designView.libraryModel
    )
    symbolNameDlg.libNamesCB.setCurrentText(spiceItemTuple.libraryItem.libraryName)
    symbolNameDlg.cellCB.setCurrentText(spiceItemTuple.cellItem.cellName)
    symbolNameDlg.viewType.addItems(["symbol"])
    symbolNameDlg.viewName.setText("symbol")
    if symbolNameDlg.exec() == QDialog.DialogCode.Accepted:
        symbolViewName = symbolNameDlg.viewName.text().strip()
        symbolViewItem = scb.createCellView(
            parent, symbolViewName, spiceItemTuple.cellItem
        )
        newSpiceFilePathObj = spiceItemTuple.cellItem.data(
            Qt.ItemDataRole.UserRole + 2).joinpath(
            importedSpiceObj.pathObj.name
        )
        symbolWindow = syed.symbolEditor(
            symbolViewItem,
            libraryDict,
            libraryBrowser.libBrowserCont.designView,
        )
        symbolScene = symbolWindow.centralW.scene
        dlg = pdlg.symbolCreateDialog(parent)
        dlg.leftPinsEdit.setText(", ".join(importedSpiceObj.subcktParams["pins"]))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            rectXDim, rectYDim = drawBaseSymbol(symbolScene, dlg)
            symbolFileLabel = symbolScene.labelDraw(
                QPoint(int(0.25 * rectXDim), int(-0.2 * rectYDim)),
                f"[@subcktName:subcktName=%:subcktName={importedSpiceObj.subcktParams['name']}]",
                "NLPLabel",
                "12",
                "Center",
                "R0",
                "Instance",
            )
            symbolFileLabel.labelVisible = False
            instParamNum = len(importedSpiceObj.subcktParams["params"])
            for index, (key, value) in enumerate(
                    importedSpiceObj.subcktParams["params"].items()
            ):
                symbolScene.labelDraw(
                    QPoint(
                        int(rectXDim),
                        int(index * 0.2 * rectYDim / instParamNum),
                    ),
                    f"[@{key}:{key}=%:{key}={value}]",
                    "NLPLabel",
                    "12",
                    "Center",
                    "R0",
                    "Instance",
                )
            symbolScene.attributeList = list()
            symbolScene.attributeList.append(
                se.symbolAttribute("pinOrder", importedSpiceObj.pinOrder)
            )
            symbolScene.attributeList.append(
                se.symbolAttribute("incLine", f".INC {str(newSpiceFilePathObj)}\n")
            )

            symbolScene.attributeList.append(
                se.symbolAttribute("SpiceNetlistLine",
                                   importedSpiceObj.netlistLine)
            )

            symbolWindow.show()
            symbolViewTuple = ddef.viewTuple(
                spiceItemTuple.libraryItem.libraryName,
                spiceItemTuple.cellItem.cellName,
                symbolViewItem.viewName,
            )
            symbolWindow.libraryView.openViews[symbolViewTuple] = symbolWindow
