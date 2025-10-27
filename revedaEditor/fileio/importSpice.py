#    "Commons Clause" License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, "Sell" means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
import json
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

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


def importSpiceSubckt(viewT: ddef.viewTuple, filePath: str):
    """
    Import a SPICE subcircuit and add it to a design library.
    
    Args:
        mainWindow: The main application window instance
        viewT: View tuple containing library, cell, and view names
        filePath: Path to the SPICE file to import
    """
    # Get the library model
    mainWindow = QApplication.instance().mainW
    libraryModel = mainWindow.libraryBrowser.designView.libraryModel
    # Open the import dialog
    importDlg = fd.importSpiceCellDialogue(libraryModel, mainWindow)
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
    if importDlg.exec() == QDialog.Accepted:
        # Create the SPICE object from the file path
        importedSpiceObj = hdl.spiceC(pathlib.Path(importDlg.spiceFileEdit.text()))

        # Create the SPICE view item tuple
        spiceViewItemTuple = createSpiceView(mainWindow, importDlg, libraryModel, importedSpiceObj)

        # Check if the symbol checkbox is checked
        if importDlg.symbolCheckBox.isChecked():
            # Create the spice symbol
            createSpiceSymbol(mainWindow, spiceViewItemTuple, mainWindow.libraryDict,
                              mainWindow.libraryBrowser, importedSpiceObj)


def createSpiceView(
    parent: QMainWindow,
    importDlg: QDialog,
    libraryModel: lmview.designLibrariesModel,
    importedSpiceObj: hdl.spiceC,
):
    """
    Create a new Spice view.

    Args:
        parent (QMainWindow): The parent window.
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
    newSpiceFilePathObj = cellItem.data(Qt.UserRole + 2).joinpath(
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
    with spiceItem.data(Qt.UserRole + 2).open(mode="w") as f:
        json.dump(items, f, indent=4)

    # Return the tuple of library item, cell item, and Verilog-A item
    return ddef.viewItemTuple(libItem, cellItem, spiceItem)


