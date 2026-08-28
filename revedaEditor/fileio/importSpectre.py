# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

import json
import pathlib
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QApplication, QMainWindow)

from revedaEditor.backend import dataDefinitions as ddef, hdlBackEnd as hdl, \
    libBackEnd as scb, \
    libraryMethods as libm, \
    libraryModelView as lmview
from revedaEditor.fileio.createSymbols import createSpectreSymbol
from revedaEditor.gui import fileDialogues as fd


def importSpectreSubckt(viewT: ddef.viewNameTuple, filePath: str):
    """
    Import a Spectre subcircuit and add it to a design library.

    Args:
        viewT: View tuple containing library, cell, and view names
        filePath: Path to the Spectre file to import
    """
    appMainW = QApplication.instance().appMainW
    libraryView = appMainW.libraryBrowser.designView
    libraryModel = libraryView.libraryModel

    importDlg = fd.importSpectreCellDialogue(libraryModel, appMainW)
    importDlg.spectreFileEdit.setText(filePath)

    if viewT.libraryName:
        importDlg.libNamesCB.setCurrentText(viewT.libraryName)
    if viewT.cellName:
        importDlg.cellNamesCB.setCurrentText(viewT.cellName)
    if viewT.viewName:
        importDlg.spectreViewName.setText(viewT.viewName)
    else:
        importDlg.spectreViewName.setText("spectre")

    if importDlg.exec() == QDialog.DialogCode.Accepted:
        importedSpectreObj = hdl.spectreC(pathlib.Path(importDlg.spectreFileEdit.text()))

        spectreViewItemTuple = createSpectreView(appMainW, importDlg, libraryModel,
                                                 importedSpectreObj)
        viewsModel = libraryView.createViewsListModel(spectreViewItemTuple.cellItem)
        libraryView.viewsListView.setModel(viewsModel)

        if importDlg.symbolCheckBox.isChecked():
            createSpectreSymbol(appMainW, spectreViewItemTuple,
                                appMainW.libraryDict,
                                appMainW.libraryBrowser, importedSpectreObj)


def createSpectreView(
        parent: QMainWindow,
        importDlg: QDialog,
        libraryModel: lmview.designLibrariesModel,
        importedSpectreObj: hdl.spectreC,
) -> ddef.viewItemTuple:
    """
    Create a new Spectre view.

    Args:
        parent: The parent window.
        importDlg: The import dialog window.
        libraryModel: The model for the design libraries.
        importedSpectreObj: The imported Spectre object.

    Returns:
        A viewItemTuple containing the library item, cell item, and spectre view item.
    """
    importedSpectreFilePathObj = pathlib.Path(importDlg.spectreFileEdit.text())
    libItem = libm.getLibItem(libraryModel, importDlg.libNamesCB.currentText())
    libItemRow = libItem.row()

    libCellNames = [
        libraryModel.item(libItemRow).child(i).cellName
        for i in range(libraryModel.item(libItemRow).rowCount())
    ]

    cellName = importDlg.cellNamesCB.currentText().strip()

    if cellName not in libCellNames and cellName != "":
        scb.createCell(parent, libItem, cellName)

    cellItem = libm.getCellItem(libItem, cellName)
    newSpectreFilePathObj = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
        importedSpectreFilePathObj.name
    )

    spectreItem = scb.createCellView(parent, importDlg.spectreViewName.text(), cellItem)

    tempSpectreFilePathObj = importedSpectreFilePathObj.with_suffix(".tmp")
    shutil.copy(importedSpectreFilePathObj, tempSpectreFilePathObj)
    shutil.copy(tempSpectreFilePathObj, newSpectreFilePathObj)
    tempSpectreFilePathObj.unlink()

    items = list()
    items.insert(0, {"cellView": "spectre"})
    items.insert(1, {"filePath": str(newSpectreFilePathObj.name)})
    items.insert(2, {"subcktParams": importedSpectreObj.subcktParams})

    with spectreItem.data(Qt.ItemDataRole.UserRole + 2).open(mode="w") as f:
        json.dump(items, f, indent=4)

    return ddef.viewItemTuple(libItem, cellItem, spectreItem)
