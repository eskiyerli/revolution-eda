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

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QMainWindow, QDialog

import revedaEditor.backend.data_definitions as ddef
import revedaEditor.backend.hdl_back_end as hdl
# import revedaEditor.backend.lib_back_end as scb  # import the backend
import revedaEditor.common.shapes as shp
from revedaEditor.backend import data_definitions as ddef, hdl_back_end as hdl, \
    lib_back_end as scb
from revedaEditor.fileio import symbol_encoder as se
from revedaEditor.gui import library_browser as libw, file_dialogues as fd, \
    symbol_editor as syed, \
    property_dialogues as pdlg


def drawBaseSymbol(SymbolScene, dlg):
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

    SymbolScene.rectDraw(
        QPoint(0, 0),
        QPoint(rectXDim, rectYDim),
    )
    SymbolScene.labelDraw(
        QPoint(int(0.25 * rectXDim), int(0.4 * rectYDim)),
        "[@cellName]",
        "NLPLabel",
        "12",
        "Center",
        "R0",
        "Instance",
    )
    SymbolScene.labelDraw(
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
        SymbolScene.lineDraw(
            leftPinLocs[i],
            leftPinLocs[i] + QPoint(stubLength, 0),
        )
        SymbolScene.addItem(
            shp.SymbolPin(
                leftPinLocs[i],
                pinName,
                shp.SymbolPin.pinDirs[0],
                shp.SymbolPin.pinTypes[0],
            )
        )
    for i, pinName in enumerate(rightPinNames):
        SymbolScene.lineDraw(
            rightPinLocs[i],
            rightPinLocs[i] + QPoint(-stubLength, 0),
        )
        SymbolScene.addItem(
            shp.SymbolPin(
                rightPinLocs[i],
                pinName,
                shp.SymbolPin.pinDirs[1],
                shp.SymbolPin.pinTypes[0],
            )
        )
    for i, pinName in enumerate(topPinNames):
        SymbolScene.lineDraw(
            topPinLocs[i],
            topPinLocs[i] + QPoint(0, stubLength),
        )
        SymbolScene.addItem(
            shp.SymbolPin(
                topPinLocs[i],
                pinName,
                shp.SymbolPin.pinDirs[2],
                shp.SymbolPin.pinTypes[2],
            )
        )
    for i, pinName in enumerate(bottomPinNames):
        SymbolScene.lineDraw(
            bottomPinLocs[i],
            bottomPinLocs[i] + QPoint(0, -stubLength),
        )
        SymbolScene.addItem(
            shp.SymbolPin(
                bottomPinLocs[i],
                pinName,
                shp.SymbolPin.pinDirs[2],
                shp.SymbolPin.pinTypes[1],
            )
        )

    return rectXDim, rectYDim


def createVaSymbol(
        parent: QMainWindow,
        vaItemTuple: ddef.ViewItemTuple,
        libraryDict: dict,
        LibraryBrowser: libw.LibraryBrowser,
        importedVaObj: hdl.VerilogaC,
) -> None:
    """
    Creates a symbol for a given view item in the library.

    Args:
        parent (QMainWindow): The parentW window.
        vaItemTuple (ddef.ViewItemTuple): The view item tuple.
        libraryDict (dict): The library dictionary.
        LibraryBrowser (edw.LibraryBrowser): The library browser.
        importedVaObj (hdl.VerilogaC): The imported Veriloga object.

    Returns:
        None

    Raises:
        None
    """
    # symbolNameDlg = fd.createCellViewDialog(
    #     parent, LibraryBrowser.libraryModel, vaItemTuple.CellItem
    # )
    # symbolNameDlg.viewComboBox.setCurrentText("symbol")
    # symbolNameDlg.nameEdit.setText("symbol")
    symbolNameDlg = fd.NewCellViewDialog(
        parent, LibraryBrowser.designView.libraryModel
    )
    symbolNameDlg.libNamesCB.setCurrentText(vaItemTuple.LibraryItem.libraryName)
    symbolNameDlg.cellCB.setCurrentText(vaItemTuple.CellItem.cellName)
    symbolNameDlg.viewType.addItems(["symbol"])
    symbolNameDlg.viewName.setText("symbol")
    if symbolNameDlg.exec() == QDialog.DialogCode.Accepted:
        symbolViewName = symbolNameDlg.viewName.text().strip()
        symbolViewItem = scb.createCellView(
            parent, symbolViewName, vaItemTuple.CellItem
        )
        importedVaObjPath = vaItemTuple.CellItem.data(
            Qt.ItemDataRole.UserRole + 2).joinpath(
            importedVaObj.pathObj.name
        )
        symbolWindow = syed.SymbolEditor(
            symbolViewItem,
            libraryDict,
            LibraryBrowser.libBrowserCont.designView,
        )
        SymbolScene = symbolWindow.centralW.scene
        dlg = pdlg.SymbolCreateDialog(parent)

        dlg.leftPinsEdit.setText(",".join(importedVaObj.inPins))
        dlg.rightPinsEdit.setText(",".join(importedVaObj.outPins))
        dlg.topPinsEdit.setText(",".join(importedVaObj.inoutPins))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            rectXDim, rectYDim = drawBaseSymbol(SymbolScene, dlg)
            vaModuleLabel = SymbolScene.labelDraw(
                QPoint(int(0.25 * rectXDim), int(0.8 * rectYDim)),
                f"[@vaModule:vaModule=%:vaModule={importedVaObj.vaModule}]",
                "NLPLabel",
                "12",
                "Center",
                "R0",
                "Instance",
            )
            vaModuleLabel.labelVisible = True

            instParamNum = len(importedVaObj.instanceParams)
            if instParamNum > 0:
                for index, (key, value) in enumerate(
                        importedVaObj.instanceParams.items()
                ):
                    SymbolScene.labelDraw(
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

            SymbolScene.attributeList = list()  # empty attribute list
            # Because Xyce changes the netlist line,
            # we need to define a separate attribute for Xyce
            # TODO: What about NgSpice and/or VACASK
            if importedVaObj.modelParams:
                for key, value in importedVaObj.modelParams.items():
                    SymbolScene.attributeList.append(se.SymbolAttribute(key, value))
                SymbolScene.attributeList.append(
                    se.SymbolAttribute(
                        "XyceVerilogaNetlistLine", importedVaObj.netlistLine
                    )
                )

            modelParamsString = ", ".join(
                f"{key} = {value}" for key, value in importedVaObj.modelParams.items()
            )
            SymbolScene.attributeList.append(
                se.SymbolAttribute(
                    "vaModelLine",
                    f".MODEL {importedVaObj.vaModule}Model {importedVaObj.vaModule} {modelParamsString}",
                )
            )
            SymbolScene.attributeList.append(
                se.SymbolAttribute("vaFileName", f"{str(importedVaObjPath.name)}")
            )
            SymbolScene.attributeList.append(
                se.SymbolAttribute("pinOrder", importedVaObj.pinOrder)
            )
            symbolWindow.show()
            symbolViewTuple = ddef.ViewNameTuple(
                vaItemTuple.LibraryItem.libraryName,
                vaItemTuple.CellItem.cellName,
                "symbol",
            )
            symbolWindow.libraryView.openViews[symbolViewTuple] = symbolWindow


def createSpiceSymbol(
        parent: QMainWindow,
        spiceItemTuple: ddef.ViewItemTuple,
        libraryDict: dict,
        LibraryBrowser: libw.LibraryBrowser,
        importedSpiceObj: hdl.SpiceC,
):
    symbolNameDlg = fd.NewCellViewDialog(
        parent, LibraryBrowser.designView.libraryModel
    )
    symbolNameDlg.libNamesCB.setCurrentText(spiceItemTuple.LibraryItem.libraryName)
    symbolNameDlg.cellCB.setCurrentText(spiceItemTuple.CellItem.cellName)
    symbolNameDlg.viewType.addItems(["symbol"])
    symbolNameDlg.viewName.setText("symbol")
    if symbolNameDlg.exec() == QDialog.DialogCode.Accepted:
        symbolViewName = symbolNameDlg.viewName.text().strip()
        symbolViewItem = scb.createCellView(
            parent, symbolViewName, spiceItemTuple.CellItem
        )
        newSpiceFilePathObj = spiceItemTuple.CellItem.data(
            Qt.ItemDataRole.UserRole + 2).joinpath(
            importedSpiceObj.pathObj.name
        )
        symbolWindow = syed.SymbolEditor(
            symbolViewItem,
            libraryDict,
            LibraryBrowser.libBrowserCont.designView,
        )
        SymbolScene = symbolWindow.centralW.scene
        dlg = pdlg.SymbolCreateDialog(parent)
        dlg.leftPinsEdit.setText(", ".join(importedSpiceObj.subcktParams["pins"]))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            rectXDim, rectYDim = drawBaseSymbol(SymbolScene, dlg)
            symbolFileLabel = SymbolScene.labelDraw(
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
                SymbolScene.labelDraw(
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
            SymbolScene.attributeList = list()
            SymbolScene.attributeList.append(
                se.SymbolAttribute("pinOrder", importedSpiceObj.pinOrder)
            )
            SymbolScene.attributeList.append(
                se.SymbolAttribute("incLine", importedSpiceObj.pathObj.name)
            )

            SymbolScene.attributeList.append(
                se.SymbolAttribute("SpiceNetlistLine",
                                   importedSpiceObj.netlistLine)
            )

            symbolWindow.show()
            symbolViewTuple = ddef.ViewNameTuple(
                spiceItemTuple.LibraryItem.libraryName,
                spiceItemTuple.CellItem.cellName,
                symbolViewItem.viewName,
            )
            symbolWindow.libraryView.openViews[symbolViewTuple] = symbolWindow
