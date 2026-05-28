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
#    consideration (including without limitation fees for hosting) a product or service
#    whose value derives, entirely or substantially, from the functionality of the Software.
#    Any license notice or attribution required by the License must also include this
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
import logging
import pathlib
import shutil
from typing import List

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (QAction, QStandardItemModel, QStandardItem, )
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QMenu, QMessageBox, QTreeView,
                               QWidget, QApplication, QListView, QHBoxLayout, QVBoxLayout,
                               QLabel, )

import revedaEditor.backend.data_definitions as ddef
import revedaEditor.backend.lib_back_end as libb
import revedaEditor.backend.library_methods as libm
import revedaEditor.gui.file_dialogues as fd
import revedaEditor.gui.layout_dialogues as ldlg
import revedaEditor.gui.text_editor as ted
from revedaEditor.gui.config_editor import ConfigEditor


class BaseDesignLibrariesView(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self._app = QApplication.instance()
        self.libBrowsW = self.parentWidget().parentWidget()
        self.appMainW = self.libBrowsW.appMainW
        self.libraryDict = self.appMainW.libraryDict  # type: dict
        self.cellViews = self.libBrowsW.cellViews  # type: list
        self.openViews = self.appMainW.openViews  # type: dict
        self.logger = logging.getLogger("reveda")

        # Common selection tracking
        self.selectedLib = None
        self.selectedCell = None
        self.selectedView = None

        # Initialize the model (to be implemented by child classes)
        self.libraryModel = DesignLibrariesModel(self.libraryDict)

    def removeLibrary(self, selectedLib: libb.LibraryItem):
        try:
            button = QMessageBox.question(self, "Library Deletion",
                                          "Are you sure to delete this library? This action cannot be undone.", )
            if button == QMessageBox.Yes:
                self.libraryModel.removeLibraryFromModel(selectedLib)
                self.libraryDict.pop(selectedLib.libraryName, None)
                self.reworkDesignLibrariesView(self.libraryDict)
                self.libBrowsW.writeLibDefFile(self.libraryDict, self.libBrowsW.libFilePath)
        except Exception as e:
            self.logger.error(f"Error removing library: {e}")

    def renameLib(self, selectedLib: libb.LibraryItem):
        try:
            oldLibraryName = selectedLib.libraryName
            dlg = fd.RenameLibDialog(self, oldLibraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newLibraryName = dlg.newLibraryName.text().strip()
                LibraryItem = libm.getLibItem(self.libraryModel, oldLibraryName)
                oldLibraryPath = LibraryItem.data(Qt.ItemDataRole.UserRole + 2)
                self.libraryModel.removeRow(LibraryItem.row())
                newLibraryPath = oldLibraryPath.parent.joinpath(newLibraryName)
                oldLibraryPath.rename(newLibraryPath)
                self.libraryDict.pop(oldLibraryName)
                self.libraryDict[newLibraryName] = pathlib.Path(newLibraryPath)
                self.reworkDesignLibrariesView(self.libraryDict)
                self.libBrowsW.writeLibDefFile(self.libraryDict, self.libBrowsW.libFilePath)
        except Exception as e:
            self.logger.error(f"Error renaming library: {e}")

    def openView(self, selectedViewItem: libb.ViewItem):
        try:
            CellItem = selectedViewItem.parent()
            libItem = CellItem.parent()
            viewItemT = ddef.ViewItemTuple(libItem, CellItem, selectedViewItem)
            self.openCellView(viewItemT)
        except Exception as e:
            self.logger.error(f"Error opening view: {e}")

    def createNewCellView(self, itemTuple: ddef.ViewItemTuple):
        """
            this method is used to open the editor after a viewitem is created.
        """
        viewNameT = itemTuple.convertToViewNameTuple()
        if itemTuple.ViewItem.viewType in ["schematic", "symbol", "layout"]:
            from revedaEditor.gui.editor_factory import EditorFactory
            editor = EditorFactory.createEditor(itemTuple.ViewItem.viewType, itemTuple.ViewItem,
                                                self.libraryDict,
                                                self)
            self.appMainW.openViews[viewNameT] = editor
            if hasattr(editor, "loadSchematic"):
                editor.loadSchematic()
            elif hasattr(editor, "loadSymbol"):
                editor.loadSymbol()
            elif hasattr(editor, "loadLayout"):
                editor.loadLayout()
            editor.show()
        elif itemTuple.ViewItem.viewType == "veriloga":
            self._handle_veriloga_view(itemTuple)
        elif itemTuple.ViewItem.viewType == "spice":
            self._handle_spice_view(itemTuple)
        elif itemTuple.ViewItem.viewType == "config":
            schViewsList = [itemTuple.CellItem.child(row).viewName for row in
                            range(itemTuple.CellItem.rowCount()) if
                            itemTuple.CellItem.child(row).viewType == "schematic"]
            dlg = fd.CreateConfigViewDialogue(self.appMainW)
            dlg.libraryNameEdit.setText(itemTuple.LibraryItem.libraryName)
            dlg.cellNameEdit.setText(itemTuple.CellItem.cellName)
            dlg.viewNameCB.addItems(schViewsList)
            dlg.switchViews.setText(", ".join(self.appMainW.switchViewList))
            dlg.stopViews.setText(", ".join(self.appMainW.stopViewList))
            if dlg.exec() == QDialog.DialogCode.Accepted:
                from revedaEditor.gui.config_editor import createNewConfigView
                configWindow = createNewConfigView(itemTuple.CellItem, itemTuple.ViewItem, dlg,
                                                   self.libraryDict,
                                                   self)
                self.appMainW.openViews[viewNameT] = configWindow
                configWindow.show()
        elif itemTuple.ViewItem.viewType == "pcell":
            dlg = ldlg.PcellLinkDialogue(self.appMainW, itemTuple.ViewItem)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                items = [{"cellView": "pcell"}, {"reference": dlg.pcellCB.currentText()}]
                with itemTuple.ViewItem.data(Qt.ItemDataRole.UserRole + 2).open(
                        mode="w+") as pcellFile:
                    json.dump(items, pcellFile, indent=4)
            else:
                try:
                    itemTuple.ViewItem.data(Qt.ItemDataRole.UserRole + 2).unlink()
                    itemTuple.ViewItem.parent().removeRow(itemTuple.ViewItem.row())
                except OSError as e:
                    self.logger.warning(f"Error:{e.strerror}")
        else:
            if hasattr(self._app, 'pluginsObj'):
                self._app.pluginsObj.createCellView(itemTuple)

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        To be implemented by child classes.
        """
        pass

    def _handle_text_view(self, viewItemT: ddef.ViewItemTuple, editor_class, finished_callback):
        """Handle text-based view opening (spice/veriloga)."""
        viewNameT = viewItemT.convertToViewNameTuple()
        filePath = None
        with open(viewItemT.ViewItem.viewPath) as f:
            try:
                filePath = pathlib.Path(viewItemT.CellItem.cellPath.joinpath(json.load(f)[1].get("filePath")))
            except IndexError:
                if viewItemT.ViewItem.viewType == 'spice':
                    filePath = pathlib.Path(viewItemT.CellItem.cellPath.joinpath(
                        viewNameT.cellName).with_suffix(".sp"))
                    filePath.touch(exist_ok=True)
                elif viewItemT.ViewItem.viewType == 'veriloga':
                    filePath = pathlib.Path(viewItemT.CellItem.cellPath.joinpath(
                        viewNameT.cellName).with_suffix(".va"))
                    filePath.touch(exist_ok=True)
        
        if filePath:
            filePath = filePath.resolve()
            editor = editor_class(filePath)
            editor.cellViewTuple = viewNameT
            editor.closedSignal.connect(finished_callback)
            self.appMainW.openViews[viewNameT] = editor
            editor.show()
        else:
            self.logger.warning(f"File {filePath} does not exist")


    def _handle_spice_view(self, viewItemT: ddef.ViewItemTuple):
        """Handle spice view opening."""
        self._handle_text_view(viewItemT, ted.SpiceEditor, self.spiceEditFinished)

    def _handle_veriloga_view(self, viewItemT: ddef.ViewItemTuple):
        """Handle veriloga view opening."""
        self._handle_text_view(viewItemT, ted.VerilogaEditor, self.verilogaEditFinished)

    def openCellView(self, viewItemT: ddef.ViewItemTuple):
        from revedaEditor.gui.editor_factory import EditorFactory
        viewNameT = viewItemT.convertToViewNameTuple()

        if viewNameT in self.appMainW.openViews.keys():
            self.appMainW.openViews[viewNameT].show()
            return viewNameT

        view_type = viewItemT.ViewItem.viewType

        # Handle standard editor types using factory
        if view_type in EditorFactory.getSupportedViewTypes():
            editor = EditorFactory.createEditor(view_type, viewItemT.ViewItem,
                                                self.libraryDict,
                                                self)

            # Load content based on editor type - use view_type instead of hasattr
            if view_type == 'layout':
                editor.loadLayout()  # type: ignore[attr-defined]
            elif view_type == 'schematic':
                editor.loadSchematic()  # type: ignore[attr-defined]
            elif view_type == 'symbol':
                editor.loadSymbol()  # type: ignore[attr-defined]

            editor.show()

            # Fit items in view if available
            if hasattr(editor, 'centralW') and hasattr(editor.centralW, 'scene'):
                editor.centralW.scene.fitItemsInView()
            self.appMainW.openViews[viewNameT] = editor

        # Handle special cases that require custom logic
        elif view_type == "config":
            editor = ConfigEditor(viewItemT.ViewItem, self.libraryDict,
                                  self)
            editor.loadConfig()
        elif view_type == "spice":
            self._handle_spice_view(viewItemT)
        elif view_type == "veriloga":
            self._handle_veriloga_view(viewItemT)
        else:
            if hasattr(self._app, 'pluginsObj'):
                result = self._app.pluginsObj.openCellView(viewItemT)
                if not result:
                    self.logger.warning(f"No handler for view type: {view_type}")

        return viewNameT

    def verilogaEditFinished(self, editor: ted.VerilogaEditor):
        import revedaEditor.fileio.import_veriloga as imva
        imva.importVerilogaModule(editor.cellViewTuple, str(editor.filePathObj))
        # self.appMainW.openViews.pop(editor.cellViewTuple)

    def spiceEditFinished(self, editor: ted.SpiceEditor):
        import revedaEditor.fileio.import_spice as imsp
        imsp.importSpiceSubckt(editor.cellViewTuple, str(editor.filePathObj))
        # self.appMainW.openViews.pop(editor.cellViewTuple)


class DesignLibrariesColumnView(BaseDesignLibrariesView):
    def __init__(self, parent):
        super().__init__(parent=parent)  # QTreeView

        # Create three list views with labels
        self.libsListView = QListView()

        self.libsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.libsListView.customContextMenuRequested.connect(self.libsListContextMenuEvent)
        self.cellsListView = QListView()
        self.cellsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cellsListView.customContextMenuRequested.connect(
            self.cellsListContextMenuEvent)
        self.viewsListView = QListView()
        self.viewsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.viewsListView.customContextMenuRequested.connect(
            self.viewsListContextMenuEvent)

        libsLabel = QLabel("**Libraries**")
        libsLabel.setTextFormat(Qt.MarkdownText)
        cellsLabel = QLabel("**Cells**")
        cellsLabel.setTextFormat(Qt.MarkdownText)
        viewsLabel = QLabel("**Cell Views**")
        viewsLabel.setTextFormat(Qt.MarkdownText)
        # Create a horizontal layout and add the list views to it
        layout = QHBoxLayout()

        # Create vertical layouts for each list with its label
        libsLayout = QVBoxLayout()
        libsLayout.addWidget(libsLabel)
        libsLayout.addWidget(self.libsListView)

        cellsLayout = QVBoxLayout()
        cellsLayout.addWidget(cellsLabel)
        cellsLayout.addWidget(self.cellsListView)

        viewsLayout = QVBoxLayout()
        viewsLayout.addWidget(viewsLabel)
        viewsLayout.addWidget(self.viewsListView)

        # Add layouts to main layout
        layout.addLayout(libsLayout)
        layout.addLayout(cellsLayout)
        layout.addLayout(viewsLayout)
        self.setLayout(layout)

        self.libsListView.setModel(self.libraryModel)
        # Connect selection signals
        self.libsListView.selectionModel().selectionChanged.connect(
            self.onLibsListSelection)

    def onLibsListSelection(self, selected, deselected):
        # Clear second and third lists
        self.cellsListView.setModel(None)
        self.viewsListView.setModel(None)

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            return

        # Create new model for second list
        cellsModel = QStandardItemModel()
        cellsModel.setHorizontalHeaderLabels(["Cells"])
        cellsModel.setSortRole(Qt.ItemDataRole.UserRole + 3)

        # Get the selected item and its children
        self.selectedLib = self.libraryModel.itemFromIndex(indexes[0])

        children = [self.selectedLib.child(i) for i in range(self.selectedLib.rowCount())]
        if self.selectedLib and self.selectedLib.hasChildren():
            for CellItem in children:
                clonedCellItem = CellItem.clone()
                cellsModel.appendRow(clonedCellItem)

        self.cellsListView.setModel(cellsModel)
        # Connect second list selection after setting its model
        self.cellsListView.selectionModel().selectionChanged.connect(
            self.onCellsListSelection)

    def recursive_clone(self, item):
        """Recursively clone an item and all its children."""
        clonedItem = item.clone()
        # Store reference to original item
        clonedItem.setData(item,
                           Qt.ItemDataRole.UserRole + 10)  # Use a custom role to store the original item

        if item.hasChildren():
            for i in range(item.rowCount()):
                child = item.child(i)
                clonedChild = self.recursive_clone(child)
                clonedItem.appendRow(clonedChild)
        return clonedItem

    def onCellsListSelection(self, selected, deselected):
        # Clear third list
        self.viewsListView.setModel(None)

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            return
        CellItem = (
            self.cellsListView.model().itemFromIndex(indexes[0]).data(
                Qt.ItemDataRole.UserRole + 10))
        # Create new model for third list
        viewsModel = self.createViewsListModel(CellItem=CellItem)
        self.viewsListView.setModel(viewsModel)
        # Connect third list selection after setting its model
        self.viewsListView.selectionModel().selectionChanged.connect(
            self.onViewsListSelection)

    def createViewsListModel(self, CellItem: libb.CellItem) -> QStandardItemModel:
        """
        Create a new model for the views list based on the selected cell item.
        """
        viewsModel = QStandardItemModel()
        viewsModel.setHorizontalHeaderLabels(["Cell Views"])
        viewsModel.setSortRole(Qt.ItemDataRole.UserRole + 3)

        if CellItem and CellItem.hasChildren():
            for i in range(CellItem.rowCount()):
                child = CellItem.child(i)
                cloned_child = child.clone()
                cloned_child.setData(child, Qt.ItemDataRole.UserRole + 10)
                viewsModel.appendRow(cloned_child)
        return viewsModel

    def onViewsListSelection(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            self.selectedView = self.viewsListView.model().itemFromIndex(indexes[0])

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        Recreate library model from libraryDict.
        """
        # Disconnect existing selection signals
        try:
            self.libsListView.selectionModel().selectionChanged.disconnect()
        except:
            pass

        # Create new model and set it
        self.libraryModel = DesignLibrariesModel(libraryDict)
        self.libsListView.setModel(self.libraryModel)

        # Reconnect selection signals
        self.libsListView.selectionModel().selectionChanged.connect(
            self.onLibsListSelection)

        # Clear other views
        self.cellsListView.setModel(None)
        self.viewsListView.setModel(None)

        # Update library model reference in parent
        self.libBrowsW.libraryModel = self.libraryModel

    def libsListContextMenuEvent(self, pos: QPoint):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedLibItem = self.libsListView.model().itemFromIndex(index)
            menu.addAction(QAction("Rename Library", self,
                                   triggered=lambda: self.renameLib(selectedLibItem), ))
            menu.addAction(QAction("Remove Library", self,
                                   triggered=lambda: self.removeLibrary(selectedLibItem), ))
            menu.addAction(QAction("Create Cell", self,
                                   triggered=lambda: self.createCell(selectedLibItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showItemFileInfo(
                                       selectedLibItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def cellsListContextMenuEvent(self, pos):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedCloneCellItem = self.cellsListView.model().itemFromIndex(index)
            selectedCellItem = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            menu.addAction(QAction("Create CellView...", self,
                                   triggered=lambda: self.createCellView(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("Copy Cell...", self,
                                   triggered=lambda: self.copyCell(selectedCellItem), ))
            menu.addAction(QAction("Rename Cell...", self,
                                   triggered=lambda: self.renameCell(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("Delete Cell...", self,
                                   triggered=lambda: self.deleteCell(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showClonedItemFileInfo(
                                       selectedCloneCellItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def viewsListContextMenuEvent(self, pos):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedCloneViewItem = self.viewsListView.model().itemFromIndex(index)
            selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
            menu.addAction(QAction("Open View", self,
                                   triggered=lambda: self.openView(selectedViewItem)))
            menu.addAction(QAction("Copy View...", self, triggered=lambda: self.copyView(
                selectedCloneViewItem), ))
            menu.addAction(QAction("Rename View...", self,
                                   triggered=lambda: self.renameView(
                                       selectedCloneViewItem), ))
            menu.addAction(QAction("Delete View...", self,
                                   triggered=lambda: self.deleteView(
                                       selectedCloneViewItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showClonedItemFileInfo(
                                       selectedCloneViewItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def createCell(self, selectedLib: libb.LibraryItem):
        try:
            dlg = fd.CreateCellDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedLib.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cellName = dlg.cellCB.currentText()
                if cellName.strip() != "":
                    selectedLib = libm.getLibItem(self.libraryModel,
                                                  dlg.libNamesCB.currentText())
                    newCellItem = libb.createCell(self, selectedLib, cellName)
                    if newCellItem:
                        # add now a clone of newCellItem to temporary cellListModel
                        cloneItem = newCellItem.clone()
                        self.cellsListView.model().appendRow(cloneItem)
                else:
                    self.logger.error("Please enter a cell name.")
        except OSError as e:
            self.logger.warning(f"Error creating cell: {e}")

    def copyCell(self, selectedCellItem: libb.CellItem):
        try:
            parentLib: libb.LibraryItem = selectedCellItem.parent()
            dlg = fd.CopyCellDialog(self)
            dlg.libraryCB.setModel(self.libraryModel)
            dlg.libraryCB.setCurrentText(parentLib.libraryName)
            pass
            if dlg.exec() == QDialog.DialogCode.Accepted:
                success, newCellItem = libb.copyCell(self, self.libraryModel,
                                                     selectedCellItem, dlg.copyName.text(),
                                                     dlg.selectedLibPath, )
                if success:
                    cloneItem = newCellItem.clone()
                    if selectedCellItem.hasChildren():
                        for i in range(selectedCellItem.rowCount()):
                            child = selectedCellItem.child(i)
                            clonedChild = child.clone()
                            cloneItem.appendRow(clonedChild)
                    self.cellsListView.model().appendRow(cloneItem)
                else:
                    self.logger.error("Failed to copy cell.")
        except OSError as e:
            self.logger.warning(f"Error copying cell: {e}")

    def renameCell(self, cloneCellItem: libb.CellItem):
        try:
            oldName = cloneCellItem.cellName
            CellItem = cloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            dlg = fd.RenameCellDialog(self, CellItem)
            libName = CellItem.parent().libraryName
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newName = dlg.nameEdit.text().strip()
                libb.renameCell(self, cloneCellItem, newName)
                # update the original cell item
                libb.renameCell(self, CellItem, dlg.nameEdit.text().strip(), )
                updateJSONFieldInCell(self.libraryModel, libName, 'cell', oldName, newName)
                self.logger.info(f"Renamed {oldName} to {newName}")
        except OSError as e:
            self.logger.warning(f"Error renaming cell: {e}")

    def deleteCell(self, selectedCloneCellItem: libb.CellItem):
        try:
            originalCell = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            shutil.rmtree(selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 2))
            self.libraryModel.removeRow(originalCell.row())
            if self.cellsListView.model():
                self.cellsListView.model().removeRow(selectedCloneCellItem.row())
            self.logger.info(f"Cell {originalCell.cellName} deleted.")
            self.reworkDesignLibrariesView(self.libraryModel.libraryDict)

        except OSError as e:
            self.logger.warning(f"Error deleting cell: {e}")

    def copyView(self, selectedCloneViewItem: libb.ViewItem):
        selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
        dlg = fd.CopyViewDialog(self, self.libraryModel)
        dlg.libNamesCB.setCurrentText(selectedViewItem.parent().parent().libraryName)
        dlg.cellCB.setCurrentText(selectedViewItem.parent().cellName)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if selectedViewItem.data(Qt.ItemDataRole.UserRole + 1) != "view":
            self.logger.error("Selected item is not a view.")
            return

        viewPath = selectedViewItem.data(Qt.ItemDataRole.UserRole + 2)
        libName = dlg.libNamesCB.currentText()
        cellName = dlg.cellCB.currentText()
        newViewName = dlg.viewName.text().strip()

        selectedLibItem = libm.getLibItem(self.libraryModel, libName)
        if not selectedLibItem:
            self.logger.error("Selected library not found.")
            return

        # Find or create cell
        CellItem = libm.getCellItem(selectedLibItem, cellName)  # noqa: F811
        if not CellItem:
            CellItem = libb.createCell(self.libBrowsW,  selectedLibItem,
                                       cellName)

        # Check if view already exists
        if any(child.viewName == newViewName for child in
               (CellItem.child(row) for row in range(CellItem.rowCount()))):
            self.logger.warning("View already exists. Delete cellview and try again.")
            return

        newViewPath = CellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
            f"{newViewName}.json")
        try:
            newViewPath.parent.mkdir(parents=True, exist_ok=True)
            newViewItem = libb.ViewItem(newViewPath)
            shutil.copy(viewPath, newViewPath)
            CellItem.appendRow(newViewItem)
            viewsModel = self.createViewsListModel(CellItem)
            self.viewsListView.setModel(viewsModel)
            self.logger.info(f"View {newViewName} copied successfully.")
        except Exception as e:
            self.logger.error(f"Failed to copy view: {e}")

    def createCellView(self, selectedCloneCellItem: libb.CellItem):
        CellItem = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
        dlg = fd.NewCellViewDialog(self, self.libraryModel)
        dlg.libNamesCB.setCurrentText(CellItem.parent().libraryName)
        dlg.cellCB.setCurrentText(CellItem.cellName)
        dlg.viewType.addItems(self.libBrowsW.cellViews)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.handleNewCellView(CellItem, dlg)

    def handleNewCellView(self, CellItem, dlg):
        viewName = dlg.viewName.text().strip()
        libItem = libm.getLibItem(self.libraryModel, dlg.libNamesCB.currentText())
        ViewItem = libm.findViewItem(self.libraryModel, libItem.libraryName,
                                     CellItem.cellName, viewName)

        if ViewItem:
            itemTuple = ddef.ViewItemTuple(libItem, CellItem, ViewItem)
            messagebox = QMessageBox(self)
            messagebox.setText("Cell view already exists.")
            messagebox.setIcon(QMessageBox.Warning)
            messagebox.setWindowTitle(f"{ViewItem.viewName} already exists")
            messagebox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            messagebox.setDefaultButton(QMessageBox.Discard)
            result = messagebox.exec()
            if result == QMessageBox.Save:
                self.viewsListView.model().removeRow(ViewItem.row())
                ViewItem = libb.createCellView(self.appMainW, viewName, CellItem)
                self.createNewCellView(itemTuple)
                # Add the new view item to the views list
                cloneViewItem = ViewItem.clone()
                self.viewsListView.model().appendRow(cloneViewItem)
        else:
            ViewItem = libb.createCellView(self.appMainW, viewName, CellItem)
            itemTuple = ddef.ViewItemTuple(libItem, CellItem, ViewItem)
            # CellItem.appendRow(ViewItem)
            self.createNewCellView(itemTuple)
            # Add the new view item to the views list
            cloneViewItem = ViewItem.clone()
            self.viewsListView.model().appendRow(cloneViewItem)

    def renameView(self, selectedCloneViewItem: libb.ViewItem):
        selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
        oldViewName = selectedViewItem.viewName
        CellItem = selectedViewItem.parent()  # noqa: F811
        dlg = fd.RenameViewDialog(self.libBrowsW, oldViewName)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newName = dlg.newViewNameEdit.text()
            try:
                viewPathObj = selectedViewItem.data(Qt.ItemDataRole.UserRole + 2)
                newPathObj = viewPathObj.parent.joinpath(f"{newName}.json")
                if newPathObj.exists():
                    raise FileExistsError
                viewPathObj.rename(newPathObj)
                # Update the view item with the new path and name

                newViewItem = libb.ViewItem(newPathObj)
                CellItem.appendRow(newViewItem)
                CellItem.removeRow(selectedViewItem.row())
                viewsModel = self.createViewsListModel(CellItem)
                self.viewsListView.setModel(viewsModel)
                self.logger.info(f"View {oldViewName} renamed to {newName}.")
            except FileExistsError:
                self.logger.error("Cellview exists.")

    def deleteView(self, selectedCloneViewItem: libb.ViewItem):
        try:
            selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 2).unlink()
            selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
            # Remove the original item from the model
            itemRow = selectedViewItem.row()
            CellItem = selectedViewItem.parent()
            CellItem.removeRow(itemRow)
            # Remove the cloned item from the view
            viewsModel = self.createViewsListModel(CellItem)
            self.viewsListView.setModel(viewsModel)
            self.logger.info(f"View {selectedViewItem.viewName} deleted.")
            # self.reworkDesignLibrariesView(self.libraryModel.libraryDict)
        except FileNotFoundError:
            self.logger.warning("View file not found.")
        except PermissionError:
            self.logger.warning("Permission denied while deleting view.")

        except Exception as e:
            self.logger.warning(f"Error:{e}")

    def showClonedItemFileInfo(self, selectedCloneItem: libb.ViewItem):
        selectedItem = selectedCloneItem.data(Qt.ItemDataRole.UserRole + 10)
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.FileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()

    def showItemFileInfo(self, selectedItem: libb.ViewItem):
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.FileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()


class DesignLibrariesTreeView(BaseDesignLibrariesView):
    """
    Deprecated for the moment. 4/3/2026.
    """
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.libraryModel.setSortRole(Qt.ItemDataRole.UserRole + 3)
        self.treeView = QTreeView()
        self.treeView.setModel(self.libraryModel)
        self.treeView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.treeView.setUniformRowHeights(True)
        # self.treeView.expandAll()
        layout = QVBoxLayout()
        layout.addWidget(self.treeView)
        self.setLayout(layout)

    def createCell(self, selectedLib: libb.LibraryItem):
        try:
            dlg = fd.CreateCellDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedLib.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cellName = dlg.cellCB.currentText()
                if cellName.strip() != "":
                    libb.createCell(self, selectedLib, cellName)
                else:
                    self.logger.error("Please enter a cell name.")
        except OSError as e:
            self.logger.warning(f"Error in creating cell:{e}")

    def copyCell(self, selectedCellItem: libb.CellItem):
        try:
            parentLibrary = selectedCellItem.parent()
            dlg = fd.CopyCellDialog(self)
            dlg.libraryCB.setCurrentText(parentLibrary.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                success, newCellItem = libb.copyCell(self, self.libraryModel,
                                                     selectedCellItem, dlg.copyName.text(),
                                                     dlg.selectedLibPath, )
                if success:
                    self.logger.info("Cell copied successfully.")

        except OSError as e:
            self.logger.warning(f"Error in copying cell:{e}")

    def renameCell(self, selectedCell: libb.CellItem):
        try:
            dlg = fd.RenameCellDialog(self, selectedCell)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                oldName = selectedCell.cellName
                libName = selectedCell.parent().libraryName
                success = libb.renameCell(self, dlg.CellItem, dlg.nameEdit.text())
                if success:
                    newName = selectedCell.cellName
                    self.logger.info(f"Cell {oldName} renamed to {dlg.nameEdit.text()}.")
                    updateJSONFieldInCell(self.libraryModel, libName, 'cell', oldName,
                                          newName)
        except OSError as e:
            self.logger.warning(f"Error in renaming cell:{e}")

    def deleteCell(self, selectedCell: libb.CellItem):
        try:
            shutil.rmtree(selectedCell.data(Qt.ItemDataRole.UserRole + 2))
            self.libraryModel.removeRow(selectedCell.row())
            self.logger.info(f"Cell {selectedCell.cellName} deleted.")
        except OSError as e:
            self.logger.warning(f"Error in deleting cell:{e}")

    def createCellView(self, selectedCell: libb.CellItem):
        try:
            dlg = fd.NewCellViewDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedCell.parent().libraryName)
            dlg.cellCB.setCurrentText(selectedCell.cellName)
            dlg.viewType.addItems(self.libBrowsW.cellViews)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.handleNewCellView(selectedCell, dlg)
        except OSError as e:
            self.logger.warning(f"Error in creating cell view:{e}")

    def handleNewCellView(self, CellItem:libb.CellItem, dlg):
        libItem:libb.LibraryItem = CellItem.parent()
        viewName = dlg.viewName.text().strip()
        ViewItem = libm.findViewItem(self.libraryModel, libItem.libraryName,
                                     CellItem.cellName, viewName)
        itemTuple = ddef.ViewItemTuple(libItem, CellItem, ViewItem)
        if ViewItem:
            messagebox = QMessageBox(self)
            messagebox.setText("Cell view already exists.")
            messagebox.setIcon(QMessageBox.Warning)
            messagebox.setWindowTitle(f"{ViewItem.viewName} already exists")
            messagebox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            messagebox.setDefaultButton(QMessageBox.Discard)
            result = messagebox.exec()
            if result == QMessageBox.Save:
                CellItem.removeRow(ViewItem.row())
                ViewItem = libb.createCellView(self.libBrowsW, viewName, CellItem)
                CellItem.appendRow(ViewItem)
                self.createNewCellView(itemTuple)

        else:
            ViewItem = libb.createCellView(self.appMainW, viewName.strip(), CellItem)
            CellItem.appendRow(ViewItem)
            self.createNewCellView(itemTuple)

    def copyView(self, selectedView: libb.ViewItem):
        try:
            dlg = fd.CopyViewDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedView.parent().parent().libraryName)
            dlg.cellCB.setCurrentText(selectedView.parent().cellName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                if selectedView.data(Qt.ItemDataRole.UserRole + 1) == "view":
                    viewPath = self.selectedItem.data(Qt.ItemDataRole.UserRole + 2)
                    selectedLibItem = libm.getLibItem(self.libraryModel,
                                                      dlg.libNamesCB.currentText())
                    cellName = dlg.cellCB.currentText()
                    libCellNames = [selectedLibItem.child(row).cellName for row in
                                    range(selectedLibItem.rowCount())]
                    if (
                            cellName in libCellNames):  # check if there is the cell in the library
                        CellItem = libm.getCellItem(selectedLibItem,
                                                    dlg.cellCB.currentText())
                    else:
                        CellItem = libb.createCell(self.libBrowsW, self.libraryModel,
                                                   selectedLibItem,
                                                   dlg.cellCB.currentText(), )
                    cellViewNames = [CellItem.child(row).viewName for row in
                                     range(CellItem.rowCount())]
                    newViewName = dlg.viewName.text()
                    if newViewName in cellViewNames:
                        self.logger.warning(
                            "View already exists. Delete cellview and try again.")
                    else:
                        newViewPath = CellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
                            f"{newViewName}.json")
                        shutil.copy(viewPath, newViewPath)
                        CellItem.appendRow(libb.ViewItem(newViewPath))
        except OSError as e:
            self.logger.warning(f"Error in copying view:{e}")

    def renameView(self, selectedView: libb.ViewItem):
        try:
            oldViewName = selectedView.viewName
            dlg = fd.RenameViewDialog(self.libBrowsW, oldViewName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newName = dlg.newViewNameEdit.text()
                try:
                    viewPathObj = selectedView.data(Qt.ItemDataRole.UserRole + 2)
                    newPathObj = selectedView.data(Qt.ItemDataRole.UserRole + 2).rename(
                        viewPathObj.parent.joinpath(f"{newName}.json"))
                    selectedView.parent().appendRow(libb.ViewItem(newPathObj))
                    selectedView.parent().removeRow(selectedView.row())
                except FileExistsError:
                    self.logger.error("Cellview exists.")
        except OSError as e:
            self.logger.warning(f"Error in renaming view:{e}")

    def deleteView(self, selectedView: libb.ViewItem):
        try:
            selectedView.data(Qt.ItemDataRole.UserRole + 2).unlink()
            itemRow = selectedView.row()
            parent = selectedView.parent()
            parent.removeRow(itemRow)
        except OSError as e:
            self.logger.warning(
                f"Error in removing item: {selectedView.viewName}:{e.strerror}")

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        Recreate library model from libraryDict.
        """
        self.libraryModel = DesignLibrariesModel(libraryDict)
        self.setModel(self.libraryModel)
        self.libBrowsW.libraryModel = self.libraryModel

    def showFileInfo(self, selectedItem: libb.ViewItem):
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.FileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()

    # context menu
    # def contextMenuEvent(self, event):
    #     menu = QMenu(self)
    #     pos = event.pos()
    #     # Use self directly instead of self.sender()
    #     index = self.treeView.indexAt(pos)
    #     if index.isValid():
    #         selectedItem = self.libraryModel.itemFromIndex(index)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        pos = self.treeView.mapFromGlobal(event.globalPos())
        index = self.treeView.indexAt(pos)
        if index.isValid():
            selectedItem = self.libraryModel.itemFromIndex(index)
            if selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "library":
                menu.addAction(QAction("Rename Library", self.treeView,
                                       triggered=lambda: self.renameLib(selectedItem), ))
                menu.addAction(QAction("Remove Library", self.treeView,
                                       triggered=lambda: self.removeLibrary(
                                           selectedItem), ))
                menu.addAction(QAction("Create Cell", self.treeView,
                                       triggered=lambda: self.createCell(selectedItem), ))
            elif selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "cell":
                menu.addAction(QAction("Create CellView...", self,
                                       triggered=lambda: self.createCellView(
                                           selectedItem), ))
                menu.addAction(QAction("Copy Cell...", self.treeView, triggered=lambda: (
                    self.copyCell(selectedItem.parent())), ))
                menu.addAction(QAction("Rename Cell...", self.treeView,
                                       triggered=lambda: self.renameCell(selectedItem), ))
                menu.addAction(QAction("Delete Cell...", self.treeView,
                                       triggered=lambda: self.deleteCell(selectedItem), ))
            elif selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "view":
                menu.addAction(QAction("Open View", self.treeView,
                                       triggered=lambda: self.openView(selectedItem), ))
                menu.addAction(QAction("Copy View...", self,
                                       triggered=lambda: self.copyView(selectedItem), ))
                menu.addAction(QAction("Rename View...", self.treeView,
                                       triggered=lambda: self.renameView(selectedItem), ))
                menu.addAction(QAction("Delete View...", self.treeView,
                                       triggered=lambda: self.deleteView(selectedItem), ))
            menu.addAction(QAction("File Information...", self.treeView,
                                   triggered=lambda: self.showFileInfo(selectedItem), ))
            # Use global position for context menu
            menu.exec(event.globalPos())


class DesignLibrariesModel(QStandardItemModel):
    def __init__(self, libraryDict):
        self.libraryDict = libraryDict
        super().__init__()

        self.setHorizontalHeaderLabels(["Libraries"])
        self.initModel()
        self.logger = logging.getLogger("reveda")

    def initModel(self):
        for designPath in self.libraryDict.values():
            self.populateLibrary(designPath)

    def populateLibrary(self, designPath: pathlib.Path) -> None:  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            LibraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                CellItem = self.addCellToModel(designPath.joinpath(cell), LibraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json"]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), CellItem)
                CellItem.sortChildren(0)
            LibraryItem.sortChildren(0)

    def addLibraryToModel(self, designPath: pathlib.Path) -> libb.LibraryItem:
        libraryEntry = libb.LibraryItem(designPath)
        for row in range(self.invisibleRootItem().rowCount()):
            existingItem = self.invisibleRootItem().child(row)
            if existingItem.data(Qt.ItemDataRole.UserRole + 2) == designPath:
                self.logger.warning(f"Library {designPath} already exists in the model.")
                break
        else:
            self.invisibleRootItem().appendRow(libraryEntry)
        return libraryEntry

    def removeLibraryFromModel(self, LibraryItem: libb.LibraryItem) -> None:
        shutil.rmtree(LibraryItem.data(Qt.ItemDataRole.UserRole + 2), ignore_errors=True)
        self.invisibleRootItem().removeRow(LibraryItem.row())

    def addCellToModel(self, cellPath: pathlib.Path,
                       parentItem: libb.LibraryItem) -> libb.CellItem:
        cellEntry = libb.CellItem(cellPath)
        parentItem.appendRow(cellEntry)
        return cellEntry

    def addViewToModel(self, viewPath: pathlib.Path,
                       parentItem: libb.CellItem) -> libb.ViewItem:
        viewEntry = libb.ViewItem(viewPath)
        parentItem.appendRow(viewEntry)
        return viewEntry

    def listLibraries(self) -> List[str]:
        librariesList = []
        for row in range(self.rowCount()):
            itemText = self.item(row, 0).text()
            if itemText:
                librariesList.append(itemText)
        return librariesList

    def listLibraryCells(self, libraryName: str) -> List[str]:
        cellsList = []
        LibraryItem = libm.getLibItem(self, libraryName)
        if LibraryItem:
            for row in range(LibraryItem.rowCount()):
                itemText = LibraryItem.child(row, 0).text()
                if itemText:
                    cellsList.append(itemText)
        return cellsList

    def listCellViews(self, libraryName: str, cellName: str, viewTypes: List[str]) -> List[
        str]:
        viewsList = []
        LibraryItem = libm.getLibItem(self, libraryName)
        CellItem = libm.getCellItem(LibraryItem, cellName)
        if CellItem:
            for row in range(CellItem.rowCount()):
                if CellItem.child(row, 0).viewType in viewTypes:
                    viewsList.append(CellItem.child(row, 0).text())
        return viewsList


class SymbolViewsModel(DesignLibrariesModel):
    """
    Initializes the object with the given `libraryDict` and `symbolViews`.

    Parameters:
        libraryDict (dict): A dictionary containing the library information.
        symbolViews (list): A list of symbol views.

    Returns:
        None
    """

    def __init__(self, libraryDict: dict, symbolViews: list):
        self.symbolViews = symbolViews
        super().__init__(libraryDict)

    def populateLibrary(self, designPath):  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            LibraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                CellItem = self.addCellToModel(designPath.joinpath(cell), LibraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json" and any(
                                x in view.name for x in self.symbolViews)]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), CellItem)


class LayoutViewsModel(DesignLibrariesModel):
    def __init__(self, libraryDict: dict, layoutViews: list):
        self.layoutViews = layoutViews
        super().__init__(libraryDict)

    def populateLibrary(self, designPath):  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            LibraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                CellItem = self.addCellToModel(designPath.joinpath(cell), LibraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json" and any(
                                x in view.name for x in self.layoutViews)]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), CellItem)


class SchematicViewsModel(DesignLibrariesModel):
    """Model for selecting schematic views in Schematic-Driven Layout (SDL)."""
    def __init__(self, libraryDict: dict):
        self.schematicViews = ["schematic"]
        super().__init__(libraryDict)

    def populateLibrary(self, designPath):  # designPath: Path
        """
        Populate library with schematic views.
        """
        if designPath.joinpath("reveda.lib").exists():
            LibraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                CellItem = self.addCellToModel(designPath.joinpath(cell), LibraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json" and any(
                                x in view.name for x in self.schematicViews)]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), CellItem)


class LibraryCheckListView(QListView):
    def __init__(self, parent, model: DesignLibrariesModel):
        super().__init__(parent)
        self.DesignLibrariesModel = model
        self.setWindowTitle("Library Check List")
        self.setGeometry(100, 100, 400, 600)
        self.model = QStandardItemModel(self)
        self.setModel(self.model)

        libraries = self.DesignLibrariesModel.listLibraries()
        for library in libraries:
            item = QStandardItem(library)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            self.model.appendRow(item)

    def getCheckedLibraries(self):
        checkedLibraries = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item.checkState() == Qt.Checked:
                checkedLibraries.append(item.text())
        return checkedLibraries


def updateJSONFieldInLibrary(model: "DesignLibrariesModel", libraryName: str, key: str,
                             oldValue: str, newValue: str) -> None:
    """
    Update a specific JSON field in all view files within a single library.

    Args:
        model: The DesignLibrariesModel instance
        libraryName: Name of the library to process
        key: The JSON key to search for
        oldValue: The old value to match
        newValue: The new value to set for the key
    """
    import json
    libItem = libm.getLibItem(model, libraryName)
    if libItem.hasChildren():
        for row in range(libItem.rowCount()):
            CellItem = libItem.child(row)
            if CellItem.hasChildren():
                for row in range(CellItem.rowCount()):
                    ViewItem = CellItem.child(row)
                    try:
                        with open(ViewItem.viewPath, "r") as f:
                            data = json.load(f)
                            updated = False
                            for item in data:
                                if item.get(key) == oldValue:
                                    updated = True
                                    item[key] = newValue

                        if updated:
                            with open(ViewItem.viewPath, "w") as f:
                                json.dump(data, f, indent=4)
                    except Exception as e:
                        print(f"Error updating {ViewItem.viewPath}: {str(e)}")


def updateJSONFieldInCell(model: "DesignLibrariesModel", libraryName: str, cellName: str,
                          key: str, oldValue: str, newValue: str) -> None:
    """
    Update a specific JSON field in all view files within a single cell.

    Args:
        model: The DesignLibrariesModel instance
        libraryName: Name of the library to process
        cellName: Name of the cell to process
        key: The JSON key to search for
        oldValue: The old value to match
        newValue: The new value to set for the key
    """
    import json
    libItem = libm.getLibItem(model, libraryName)
    CellItem = libm.getCellItem(libItem, cellName)

    if CellItem.hasChildren():
        for row in range(CellItem.rowCount()):
            ViewItem = CellItem.child(row)
            try:
                with open(ViewItem.viewPath, "r") as f:
                    data = json.load(f)
                    updated = False
                    for item in data:
                        if item.get(key) == oldValue:
                            updated = True
                            item[key] = newValue

                if updated:
                    with open(ViewItem.viewPath, "w") as f:
                        json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error updating {ViewItem.viewPath}: {str(e)}")
