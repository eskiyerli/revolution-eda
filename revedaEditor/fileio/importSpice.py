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
from revedaEditor.fileio.createSymbols import createSpiceSymbol
from revedaEditor.gui import fileDialogues as fd


#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#


def importSpiceSubckt(viewT: ddef.viewNameTuple, filePath: str):
    """
    Import a SPICE subcircuit and add it to a design library.
    
    Args:
        mainWindow: The main application window instance
        viewT: View tuple containing library, cell, and view names
        filePath: Path to the SPICE file to import
    """
    # Get the library model
    appMainW = QApplication.instance().appMainW
    libraryView = appMainW.libraryBrowser.designView
    libraryModel = libraryView.libraryModel
    # Open the import dialog
    importDlg = fd.importSpiceCellDialogue(libraryModel, appMainW)
    importDlg.spiceFileEdit.setText(filePath)
    # Set the default view name in the dialog
    if viewT.libraryName:
        importDlg.libNamesCB.setCurrentText(viewT.libraryName)
    if viewT.cellName:
        importDlg.cellNamesCB.setCurrentText(viewT.cellName)
    if viewT.viewName:
        importDlg.spiceViewName.setText(viewT.viewName)
    else:
        importDlg.spiceViewName.setText("spice")
    # Execute the import dialog and check if it was accepted
    if importDlg.exec() == QDialog.DialogCode.Accepted:
        # Create the SPICE object from the file path
        importedSpiceObj = hdl.spiceC(pathlib.Path(importDlg.spiceFileEdit.text()))

        # Create the SPICE view item tuple
        spiceViewItemTuple = createSpiceView(appMainW, importDlg, libraryModel,
                                             importedSpiceObj)
        viewsModel = libraryView.createViewsListModel(spiceViewItemTuple.cellItem)
        libraryView.viewsListView.setModel(viewsModel)
        # Check if the symbol checkbox is checked
        if importDlg.symbolCheckBox.isChecked():
            # Create the spice symbol
            createSpiceSymbol(appMainW, spiceViewItemTuple,
                              appMainW.libraryDict,
                              appMainW.libraryBrowser, importedSpiceObj)


def createSpiceView(
        parent: QMainWindow,
        importDlg: QDialog,
        libraryModel: lmview.designLibrariesModel,
        importedSpiceObj: hdl.spiceC,
) -> ddef.viewItemTuple:
    """
    Create a new Spice view.

    Args:
        parent (QMainWindow): The parentW window.
        importDlg (QDialog): The import dialog window.
        libraryModel (edw.designLibrariesModel): The model for the design libraries.
        importedSpiceObj (hdl.spiceC): The imported Spice object.

    Returns:
        tuple: A tuple containing the library item, cell item, and Spice item.
    """
    # Get the file path of the imported Spice file
    importedSpiceFilePathObj = pathlib.Path(importDlg.spiceFileEdit.text())
    # Get the selected library item
    libItem = libm.getLibItem(libraryModel, importDlg.libNamesCB.currentText())
    libItemRow = libItem.row()

    # Get the cell names in the selected library
    libCellNames = [
        libraryModel.item(libItemRow).child(i).cellName
        for i in range(libraryModel.item(libItemRow).rowCount())
    ]

    # Get the selected cell name
    cellName = importDlg.cellNamesCB.currentText().strip()

    # If the cell name is not in the library and is not empty, create a new cell
    if cellName not in libCellNames and cellName != "":
        scb.createCell(parent, libItem, cellName)

        # Get the cell item
    cellItem = libm.getCellItem(libItem, cellName)
    newSpiceFilePathObj = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
        importedSpiceFilePathObj.name
    )
    # Create the Spice item view
    spiceItem = scb.createCellView(parent, importDlg.spiceViewName.text(), cellItem)
    # Create a temporary copy of the imported Spice file
    tempSpiceFilePathObj = importedSpiceFilePathObj.with_suffix(".tmp")
    shutil.copy(importedSpiceFilePathObj, tempSpiceFilePathObj)

    shutil.copy(tempSpiceFilePathObj, newSpiceFilePathObj)
    # Remove the temporary file
    tempSpiceFilePathObj.unlink()

    # Create a list of items to be stored in the Spice item data
    items = list()
    items.insert(0, {"cellView": "spice"})
    items.insert(1, {"filePath": str(newSpiceFilePathObj.name)})
    items.insert(2, {"subcktParams": importedSpiceObj.subcktParams})

    # Write the items to the Verilog-A item data file
    with spiceItem.data(Qt.ItemDataRole.UserRole + 2).open(mode="w") as f:
        json.dump(items, f, indent=4)

    # Return the tuple of library item, cell item, and Verilog-A item
    return ddef.viewItemTuple(libItem, cellItem, spiceItem)
