# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""Xyce netlist generation for schematic editors.

This module provides the xyceNetlist class for generating SPICE-compatible
netlists from schematic designs. It supports hierarchical netlisting with
config views, array notation for buses, and various netlist formats including
Spice, Verilog-A, and LVS modes.
"""

from __future__ import annotations

import datetime
import functools
import pathlib
import re
from typing import TYPE_CHECKING, List

from PySide6.QtCore import Qt

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.shapes as shp
from revedaEditor.scenes.schematicScene import schematicScene

if TYPE_CHECKING:
    from revedaEditor.gui.schematicEditor import schematicEditor


class xyceNetlist:
    """Generate Xyce-compatible netlists from schematic designs.

    This class handles recursive netlisting of hierarchical designs, supports
    configuration views for view switching, and handles array notation for
    bussed signals. It caches cell lookups to avoid repeated Qt model traversals.

    Attributes:
        filePathObj: Path to write the netlist file.
        schematic: The schematic editor being netlisted.
        topSubckt: Whether to wrap the top level in a .SUBCKT block.
        configDict: Configuration dictionary for view switching (config views).
        subcircuitDefs: List of subcircuit definitions collected during netlisting.
    """

    # Pre-compiled regex to strip dangling parameter assignments (e.g. ` width =`) left
    # after token substitution.  Compiled once at class level avoids re.compile() on every
    # netlist line inside the hot loop.
    _PARAM_RE = re.compile(r'\s+\w+\s*=(?=\s|$)')

    def __init__(self, schematic: schematicEditor, filePathObj: pathlib.Path, useConfig: bool = False,
                 topSubckt: bool = False, lvsMode: bool = False):
        """Initialize the netlister.

        Args:
            schematic: The schematic editor to netlist.
            filePathObj: Destination path for the netlist file.
            useConfig: Whether to use configuration view for view switching.
            topSubckt: Whether to wrap top level in a .SUBCKT block.
            lvsMode: LVS mode - uses lvsIgnore attribute instead of NetlistIgnore.
        """
        self.filePathObj = filePathObj
        self.schematic = schematic
        self._useConfig = useConfig
        self._scene = self.schematic.centralW.scene
        self.libraryDict = self.schematic.libraryDict
        self.libraryView = self.schematic.libraryView
        self._configDict = {}
        self.topSubckt = topSubckt
        self._lvsMode = lvsMode
        self.libItem = libm.getLibItem(self.schematic.libraryView.libraryModel,
                                       self.schematic.libName, )
        self.cellItem = libm.getCellItem(self.libItem, self.schematic.cellName)
        self.subcircuitDefs = []
        self._switchViewList = schematic.switchViewList
        self._stopViewList = schematic.stopViewList
        self.netlistedViewsSet = set()  # keeps track of netlisted views.
        self.includeLines = set()  # keeps track of include lines.
        # Caches to avoid repeated Qt model traversals for the same cells.
        self._viewNameCache: dict[tuple, str] = {}  # (libName, cellName) -> netlist view name
        self._cellItemCache: dict[tuple, libb.cellItem | None] = {}  # (libName, cellName) -> cellItem

    def __repr__(self):
        return f"xyceNetlist(filePathObj={self.filePathObj}, schematic={self.schematic}, useConfig={self._useConfig}, lvsMode={self._lvsMode})"

    @property
    def switchViewList(self) -> List[str]:
        """List of view names to try when determining how to netlist a cell."""
        return self._switchViewList

    @switchViewList.setter
    def switchViewList(self, value: List[str]):
        self._switchViewList = value

    @property
    def stopViewList(self) -> List[str]:
        """List of view names that stop hierarchical expansion."""
        return self._stopViewList

    @stopViewList.setter
    def stopViewList(self, value: List[str]):
        self._stopViewList = value

    @property
    def configDict(self):
        """Configuration dictionary for view switching (used with config views)."""
        return self._configDict

    @configDict.setter
    def configDict(self, value: dict):
        self._configDict = value

    def writeNetlist(self):
        """Write the complete netlist to filePathObj.

        This method writes the header, performs recursive netlisting,
        and appends all subcircuit definitions at the end.
        """
        with self.filePathObj.open(mode="w") as cirFile:
            cirFile.write("*".join(["\n", 80 * "*", "\n", "* Revolution EDA CDL Netlist\n",
                                    f"* Library: {self.schematic.libName}\n",
                                    f"* Top Cell Name: {self.schematic.cellName}\n",
                                    f"* View Name: {self.schematic.viewName}\n",
                                    f"* Date: {datetime.datetime.now()}\n", 80 * "*", "\n",
                                    ".GLOBAL gnd!\n\n", ]))

            # Initialize subcircuit definitions list
            self.subcircuitDefs = []

            # now go down the rabbit hole to track all circuit elements.
            self.recursiveNetlisting(self.schematic, cirFile)

            # Write all subcircuit definitions at the end
            if self.subcircuitDefs:
                cirFile.write("\n* Subcircuit Definitions\n")
                for subcktDef in self.subcircuitDefs:
                    cirFile.write(subcktDef)

            # cirFile.write(".END\n")
            for line in self.includeLines:
                cirFile.write(f"{line}\n")

    def collectSubcircuitContent(self, schematic: schematicEditor, content):
        """Collect subcircuit content without writing to file.

        This is used when building subcircuit definitions for hierarchical cells.
        It traverses the schematic, netlists each element, and recursively
        processes nested schematics.

        Args:
            schematic: The schematic editor to collect content from.
            content: List to append netlist lines to.
        """
        schematicScene = schematic.centralW.scene
        schematicScene.nameSceneNets()
        sceneSymbolSet = schematicScene.findSceneSymbolSet()
        schematicScene.generatePinNetMap(sceneSymbolSet)
        for elementSymbol in sceneSymbolSet:
            # Check for ignore conditions based on mode (consistent with processElementSymbol)
            should_ignore = False
            if self._lvsMode:
                # In LVS mode, check lvsIgnore attribute
                if elementSymbol.symattrs.get("lvsIgnore") == "1":
                    should_ignore = True
            else:
                # In normal mode, check NetlistIgnore attribute and netlistIgnore flag
                if elementSymbol.symattrs.get("NetlistIgnore") == "1" or elementSymbol.netlistIgnore:
                    should_ignore = True
            
            if not should_ignore:
                cellItem = self._getCellItem(elementSymbol.libraryName,
                                             elementSymbol.cellName)
                netlistView = self.determineNetlistView(elementSymbol, cellItem)

                if "schematic" in netlistView:
                    lines = self.createXyceSymbolLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    if netlistView not in self._stopViewList:
                        # Check deduplication before loading the schematic to avoid
                        # creating a schematicEditor object for every repeated instance.
                        viewTuple = ddef.viewNameTuple(elementSymbol.libraryName,
                                                       elementSymbol.cellName, netlistView)
                        if viewTuple not in self.netlistedViewsSet:
                            self.netlistedViewsSet.add(viewTuple)
                            schematicItem = libm.getViewItem(cellItem, netlistView)
                            from revedaEditor.gui.schematicEditor import schematicEditor
                            schematicObj = schematicEditor(schematicItem, self.libraryDict,
                                                           self.libraryView)
                            schematicObj.loadSchematic()
                            expandedPinsString = self.expandPinNames(
                                list(elementSymbol.pinNetMap.keys()))
                            subcktContent = []
                            self.collectSubcircuitContent(schematicObj, subcktContent)
                            subcktDef = f".SUBCKT {schematicObj.cellName} {expandedPinsString}\n" + '\n'.join(
                                subcktContent) + "\n.ENDS\n"
                            self.subcircuitDefs.append(subcktDef)
                elif "symbol" in netlistView:
                    lines = self.createXyceSymbolLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                elif "spice" in netlistView:
                    lines = self.createSpiceLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                elif "veriloga" in netlistView:
                    raise ValueError(
                        f"Verilog-A view '{netlistView}' selected for "
                        f"{elementSymbol.libraryName}/{elementSymbol.cellName} "
                        f"({elementSymbol.instanceName}). Xyce netlister no "
                        f"longer supports Verilog-A. Use VACASK instead."
                    )
            elif elementSymbol.netlistIgnore:
                content.append(f"*{elementSymbol.instanceName} is marked to be ignored\n")
            else:
                # NetlistIgnore attribute == "1" but netlistIgnore flag is False
                content.append(
                    f"*{elementSymbol.instanceName} is excluded via NetlistIgnore attribute\n")

    def recursiveNetlisting(self, schematicEdObj: schematicEditor, cirFile):
        """Recursively traverse all sub-circuits and netlist them.

        Args:
            schematicEdObj: The schematic editor to netlist.
            cirFile: Open file handle to write netlist to.
        """
        if self.topSubckt:
            viewTuple = ddef.viewNameTuple(schematicEdObj.libName, schematicEdObj.cellName,
                                           schematicEdObj.viewName)
            self.netlistedViewsSet.add(viewTuple)

            # Name nets and generate pin-net map first
            schematicScene = schematicEdObj.centralW.scene
            schematicScene.nameSceneNets()
            sceneSymbolSet = schematicScene.findSceneSymbolSet()
            schematicScene.generatePinNetMap(sceneSymbolSet)

            # Then get schematic pins
            schematicPinsSet = schematicScene.findSceneSchemPinsSet()
            pinNames = [pin.pinName for pin in schematicPinsSet]
            self._scene.logger.info(f"Schematic pins found for {schematicEdObj.cellName}: {pinNames}")
            expandedPinsString = self.expandPinNames(pinNames)
            self._scene.logger.info(f"Expanded pins string for {schematicEdObj.cellName}: {expandedPinsString}")

            subcktContent = []
            self.collectSubcircuitContent(schematicEdObj, subcktContent)
            subcktDef = f"\n.SUBCKT {schematicEdObj.cellName} {expandedPinsString}\n" + '\n'.join(
                subcktContent) + "\n.ENDS\n"
            self.subcircuitDefs.append(subcktDef)
        else:
            schematicScene = schematicEdObj.centralW.scene
            schematicScene.nameSceneNets()  # name all nets in the schematic
            sceneSymbolSet = schematicScene.findSceneSymbolSet()
            schematicScene.generatePinNetMap(sceneSymbolSet)
            for elementSymbol in sceneSymbolSet:
                self.processElementSymbol(elementSymbol, schematicEdObj, cirFile)

    def processElementSymbol(self, elementSymbol, schematic, cirFile):
        """Process a single element symbol during netlisting.

        Checks ignore conditions based on mode (LVS or normal) and either
        writes an ignore comment or creates the appropriate netlist line.

        Args:
            elementSymbol: The schematic symbol to process.
            schematic: The schematic editor containing the symbol.
            cirFile: Open file handle to write to.
        """
        # Check for ignore conditions based on mode
        should_ignore = False
        ignore_reason = ""

        if self._lvsMode:
            # In LVS mode, check lvsIgnore attribute
            if elementSymbol.symattrs.get("lvsIgnore") == "1":
                should_ignore = True
                ignore_reason = f"*{elementSymbol.instanceName} is excluded via lvsIgnore attribute\n"
        else:
            # In normal mode, check NetlistIgnore attribute and netlistIgnore flag
            if elementSymbol.symattrs.get("NetlistIgnore") == "1" or elementSymbol.netlistIgnore:
                should_ignore = True
                if elementSymbol.netlistIgnore:
                    ignore_reason = f"*{elementSymbol.instanceName} is marked to be ignored\n"
                else:
                    ignore_reason = f"*{elementSymbol.instanceName} is excluded via NetlistIgnore attribute\n"

        if should_ignore:
            cirFile.write(ignore_reason)
        else:
            cellItem = self._getCellItem(elementSymbol.libraryName,
                                         elementSymbol.cellName)
            netlistView = self.determineNetlistView(elementSymbol, cellItem)

            # Create the netlist line for the item.
            self.createItemLine(cirFile, elementSymbol, cellItem, netlistView)

    def _getCellItem(self, libraryName: str, cellName: str) -> libb.cellItem | None:
        """Return the cellItem for (libraryName, cellName), cached to avoid repeated model traversals.

        Returns None if the cell is not found in the library.
        """
        key = (libraryName, cellName)
        if key not in self._cellItemCache:
            libItem = libm.getLibItem(self.libraryView.libraryModel, libraryName)
            self._cellItemCache[key] = libm.getCellItem(libItem, cellName)
        return self._cellItemCache[key]

    def determineNetlistView(self, elementSymbol, cellItem) -> str:
        """Determine which view to use for netlisting a symbol instance.

        Priority order:
        1. configDict (in config mode)
        2. switchViewList (fallback)

        Args:
            elementSymbol: The symbol instance being netlisted.
            cellItem: The cell item containing available views.

        Returns:
            The view name to use for netlisting.
        """
        cacheKey = (elementSymbol.libraryName, elementSymbol.cellName)
        if cacheKey in self._viewNameCache:
            return self._viewNameCache[cacheKey]

        viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]
        viewNames = [view.viewName for view in viewItems]

        # Priority 2: Use configDict if configured
        if self._useConfig and self.configDict:
            config_entry = self.configDict.get(elementSymbol.cellName)
            if config_entry:
                # Verify library name matches
                if config_entry[0] == elementSymbol.libraryName:
                    result = config_entry[1]
                else:
                    # Library mismatch, fall back to switchViewList
                    result = self._findViewFromSwitchList(viewNames)
            else:
                # Cell not in config, fall back to switchViewList
                result = self._findViewFromSwitchList(viewNames)
        else:
            # Not using config or config dict is empty
            result = self._findViewFromSwitchList(viewNames)

        self._viewNameCache[cacheKey] = result
        return result

    def _findViewFromSwitchList(self, viewNames: List[str]) -> str:
        """Find the first matching view from switchViewList, respecting stopViewList.
        
        Iterates through switchViewList in order:
        - If a view is in stopViewList, use it and stop
        - Else if a view is in viewNames (available), use it and stop
        - If no match found, default to "symbol"
        
        Args:
            viewNames: List of available view names for the cell.
            
        Returns:
            The selected view name from switchViewList, or "symbol" if none match.
        """
        
        for viewName in self._switchViewList:
            # If this view is in stopViewList, use it and stop searching
            if viewName in self._stopViewList:
                return viewName
            # Otherwise, if it's available, use it and stop searching
            if viewName in viewNames:
                return viewName
        
        # If no match found in switchViewList, default to "symbol"
        return "symbol"

    def createItemLine(self, cirFile, elementSymbol: shp.schematicSymbol,
                       cellItem: libb.cellItem, netlistView: str, ):
        """Create the appropriate netlist line(s) for a symbol based on its view type."""
        if "schematic" in netlistView:
            elementLines = self.createXyceSymbolLine(elementSymbol)
            for line in elementLines:
                cirFile.write(f"{line}\n")

            if netlistView not in self._stopViewList:
                # Build viewTuple from symbol attributes before touching the filesystem;
                # this avoids creating a heavy schematicEditor object for every instance
                # of an already-netlisted cell (the common case in large designs).
                viewTuple = ddef.viewNameTuple(elementSymbol.libraryName,
                                               elementSymbol.cellName, netlistView)
                if viewTuple not in self.netlistedViewsSet:
                    self.netlistedViewsSet.add(viewTuple)
                    schematicItem = libm.getViewItem(cellItem, netlistView)
                    if schematicItem is None:
                        self._scene.logger.warning(f"View {netlistView} not found for {elementSymbol.cellName}")
                        return
                    from revedaEditor.gui.schematicEditor import schematicEditor
                    schematicObj = schematicEditor(schematicItem, self.libraryDict,
                                                   self.libraryView)
                    schematicObj.loadSchematic()
                    expandedPinsString = self.expandPinNames(
                        list(elementSymbol.pinNetMap.keys()))
                    subcktContent = []
                    self.collectSubcircuitContent(schematicObj, subcktContent)
                    subcktDef = f"\n.SUBCKT {schematicObj.cellName} {expandedPinsString}\n" + '\n'.join(
                        subcktContent) + "\n.ENDS\n"
                    self.subcircuitDefs.append(subcktDef)
        elif "symbol" in netlistView:
            symbolLines = self.createXyceSymbolLine(elementSymbol)
            for line in symbolLines:
                cirFile.write(f"{line}\n")
        elif "spice" in netlistView:
            spiceLines = self.createSpiceLine(elementSymbol)
            for line in spiceLines:
                cirFile.write(f"{line}\n")
        elif "veriloga" in netlistView:
            raise ValueError(
                f"Verilog-A view '{netlistView}' selected for "
                f"{elementSymbol.libraryName}/{elementSymbol.cellName} "
                f"({elementSymbol.instanceName}). Xyce netlister no "
                f"longer supports Verilog-A. Use VACASK instead."
            )

    def _createNetlistLine(self, elementSymbol: shp.schematicSymbol, netlistLineKey: str) -> \
            list[str]:
        """Shared netlist line creation logic.

        Handles array notation, attribute substitution, and pin ordering.
        This is the core netlisting logic used by all netlist formats.

        Args:
            elementSymbol: The symbol instance to create netlist lines for.
            netlistLineKey: The attribute key for the netlist line template.

        Returns:
            List of netlist line strings (one per array element if arrayed).
        """
        try:
            instNameLabel = elementSymbol.labels.get('@instName')
            if not instNameLabel:
                return []

            baseInstName, arrayTuple = self.parseArrayNotation(
                instNameLabel.labelValue.strip())
            arrayStep = -1 if arrayTuple[0] > arrayTuple[1] else 1
            arraySize = abs(arrayTuple[0] - arrayTuple[1]) + 1

            baseNetlistLine = elementSymbol.symattrs[netlistLineKey].strip()
            instNameToken = instNameLabel.labelName
            symbolLines = []

            # Pre-compute substitution lists once; avoids repeated dict iteration
            # for every element in an arrayed instance (e.g. inst<0:99>).
            attr_replacements = [(f"%{a}", v) for a, v in elementSymbol.symattrs.items()]
            label_replacements = [(lbl.labelName, lbl.labelValue)
                                  for lbl in elementSymbol.labels.values()]

            def processLine(line, netsList):
                line = line.replace("%pinOrder", netsList)
                for token, value in attr_replacements:
                    line = line.replace(token, value)
                return xyceNetlist._PARAM_RE.sub('', line)

            def createInstanceLine(instanceName):
                line = baseNetlistLine.replace(instNameToken, instanceName)
                for labelName, labelValue in label_replacements:
                    line = line.replace(labelName, labelValue)
                return line

            def expandNet(netName):
                baseName, netTuple = self.parseArrayNotation(netName)
                if netTuple[0] == netTuple[1] == -1:
                    return [baseName]
                netStep = 1 if netTuple[1] >= netTuple[0] else -1
                return [f"{baseName}<{i}>" for i in
                        range(netTuple[0], netTuple[1] + netStep, netStep)]

            # Expand nets per pin
            expandedPinNets = [expandNet(netName) for netName in elementSymbol.pinNetMap.values()]

            # Generate instance lines
            if arraySize == 1:
                # Scalar instance logic
                flatNetsList = " ".join([nets[0] for nets in expandedPinNets])
                symbolLines.append(processLine(createInstanceLine(baseInstName), flatNetsList))
            else:
                # Array instance logic
                arrayIndices = list(range(arrayTuple[0], arrayTuple[1] + arrayStep, arrayStep))

                for j, i in enumerate(arrayIndices):
                    instanceNets = []
                    for nets in expandedPinNets:
                        if len(nets) == arraySize:
                            instanceNets.append(nets[j])  # 1-to-1 matching across array width
                        elif len(nets) == 1:
                            instanceNets.append(nets[0])  # Scalar broadcasted to all array nodes
                        elif j < len(nets):
                            instanceNets.append(nets[j])  # Partial connection: connect available nets
                        else:
                            # Out of bounds for partial connection - use last available net
                            instanceNets.append(nets[-1])

                    specificNetsList = " ".join(instanceNets)
                    symbolLines.append(
                        processLine(createInstanceLine(f"{baseInstName}<{i}>"), specificNetsList))

            return symbolLines


        except Exception as e:
            self._scene.logger.error(
                f"Error creating netlist line for {elementSymbol.instanceName}: {e}")
            return [
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n"]

    def createXyceSymbolLine(self, elementSymbol: shp.schematicSymbol) -> list[str]:
        """Create Xyce netlist lines for a symbol instance.

        In LVS mode, uses the 'lvsNetlistLine' attribute, otherwise 'SpiceNetlistLine'.
        """
        netlistLineKey = "lvsNetlistLine" if self._lvsMode else "SpiceNetlistLine"
        return self._createNetlistLine(elementSymbol, netlistLineKey)

    def createSpiceLine(self, elementSymbol: shp.schematicSymbol) -> list[str]:
        """Create Spice subcircuit netlist lines with include file handling.

        Generates the netlist line using createXyceSymbolLine and adds an .INC directive.
        The Spice subcircuit file path is automatically constructed as {cellPath}/{cellName}.sp.
        """
        try:
            spiceLines = self.createXyceSymbolLine(elementSymbol)
            # Automatically construct Spice subcircuit file path from cell directory and cell name
            cellItem = self._getCellItem(elementSymbol.libraryName, elementSymbol.cellName)
            if cellItem:
                cellPath = cellItem.data(Qt.ItemDataRole.UserRole + 2)
                if cellPath:
                    incFileName = f"{elementSymbol.cellName}.sp"
                    incFilePath = pathlib.Path(cellPath) / incFileName
                    self.includeLines.add(f'.INC "{incFilePath}"')
                else:
                    self._scene.logger.warning(f"Cell path not found for {elementSymbol.cellName}, skipping include file")
            else:
                self._scene.logger.warning(f"Cell item not found for {elementSymbol.cellName}, skipping include file")
            return spiceLines
        except Exception as e:
            self._scene.logger.error(f"Spice subckt netlist error for {elementSymbol.instanceName}: {e}")
            return [f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n"]

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
        """Parse net/instance array notation like 'name<0:5>' into base name and index range.

        Also handles single instance/net notation like 'name<0>' or 'name<1>'.

        Args:
            name: The net name with optional bus notation.

        Returns:
            A tuple containing the base name and a tuple of (start, end) indices.
            For scalar names, returns (name, (-1, -1)).

        Examples:
            >>> parseArrayNotation("net<0:3>")
            ("net", (0, 3))
            >>> parseArrayNotation("bus<5>")
            ("bus", (5, 5))
            >>> parseArrayNotation("scalar")
            ("scalar", (-1, -1))
        """
        # Check if the name does not contain bus notation
        if '<' not in name or '>' not in name:
            return name, (-1, -1)

        baseName = name.split('<')[0]  # Extract the base name before '<'
        indexRange = name.split('<')[1].split('>')[0]  # Extract the content inside '<>'

        # Check if it's a single index (e.g., 'name<0>')
        if ':' not in indexRange:
            singleIndex = int(indexRange)
            return baseName, (singleIndex, singleIndex)

        # Handle range notation (e.g., 'name<0:5>')
        start, end = map(int, indexRange.split(':'))
        return baseName, (start, end)

    @staticmethod
    def expandPinNames(pinNamesList: List[str]) -> str:
        """Expand a list of pin names, expanding array notation into individual pins.

        Args:
            pinNamesList: List of pin names, may contain array notation.

        Returns:
            Space-separated string of expanded pin names.

        Example:
            >>> expandPinNames(["a<0:1>", "b"])
            "a<0> a<1> b"
        """
        expandedPinNameList = []
        for pinName in pinNamesList:
            pinBaseName, pinTuple = xyceNetlist.parseArrayNotation(pinName)
            if pinTuple[0] == pinTuple[1] == -1:
                expandedPinNameList.append(pinBaseName)
            else:
                pinStep = 1 if pinTuple[1] >= pinTuple[0] else -1
                for i in range(pinTuple[0], pinTuple[1] + pinStep, pinStep):
                    expandedPinNameList.append(f'{pinBaseName}<{i}>')
        return ' '.join(expandedPinNameList)
