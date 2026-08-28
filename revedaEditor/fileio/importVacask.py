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
from revedaEditor.fileio.createSymbols import createVacaskSymbol
from revedaEditor.gui import fileDialogues as fd


def importVacaskSubckt(viewT: ddef.viewNameTuple, filePath: str):
    """
    Import a VACASK subcircuit and add it to a design library.

    Args:
        viewT: View tuple containing library, cell, and view names
        filePath: Path to the VACASK file to import
    """
    appMainW = QApplication.instance().appMainW
    libraryView = appMainW.libraryBrowser.designView
    libraryModel = libraryView.libraryModel

    importDlg = fd.importVacaskCellDialogue(libraryModel, appMainW)
    importDlg.vacaskFileEdit.setText(filePath)

    if viewT.libraryName:
        importDlg.libNamesCB.setCurrentText(viewT.libraryName)
    if viewT.cellName:
        importDlg.cellNamesCB.setCurrentText(viewT.cellName)
    if viewT.viewName:
        importDlg.vacaskViewName.setText(viewT.viewName)
    else:
        importDlg.vacaskViewName.setText("vacask")

    if importDlg.exec() == QDialog.DialogCode.Accepted:
        importedVacaskObj = hdl.vacaskC(pathlib.Path(importDlg.vacaskFileEdit.text()))

        vacaskViewItemTuple = createVacaskView(appMainW, importDlg, libraryModel,
                                               importedVacaskObj)
        viewsModel = libraryView.createViewsListModel(vacaskViewItemTuple.cellItem)
        libraryView.viewsListView.setModel(viewsModel)

        if importDlg.symbolCheckBox.isChecked():
            createVacaskSymbol(appMainW, vacaskViewItemTuple,
                               appMainW.libraryDict,
                               appMainW.libraryBrowser, importedVacaskObj)


def createVacaskView(
        parent: QMainWindow,
        importDlg: QDialog,
        libraryModel: lmview.designLibrariesModel,
        importedVacaskObj: hdl.vacaskC,
) -> ddef.viewItemTuple:
    """
    Create a new VACASK view.

    Args:
        parent: The parent window.
        importDlg: The import dialog window.
        libraryModel: The model for the design libraries.
        importedVacaskObj: The imported VACASK object.

    Returns:
        A viewItemTuple containing the library item, cell item, and vacask view item.
    """
    importedVacaskFilePathObj = pathlib.Path(importDlg.vacaskFileEdit.text())
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
    newVacaskFilePathObj = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
        importedVacaskFilePathObj.name
    )

    vacaskItem = scb.createCellView(parent, importDlg.vacaskViewName.text(), cellItem)

    tempVacaskFilePathObj = importedVacaskFilePathObj.with_suffix(".tmp")
    shutil.copy(importedVacaskFilePathObj, tempVacaskFilePathObj)
    shutil.copy(tempVacaskFilePathObj, newVacaskFilePathObj)
    tempVacaskFilePathObj.unlink()

    items = list()
    items.insert(0, {"cellView": "vacask"})
    items.insert(1, {"filePath": str(newVacaskFilePathObj.name)})
    items.insert(2, {"subcktParams": importedVacaskObj.subcktParams})

    with vacaskItem.data(Qt.ItemDataRole.UserRole + 2).open(mode="w") as f:
        json.dump(items, f, indent=4)

    return ddef.viewItemTuple(libItem, cellItem, vacaskItem)
