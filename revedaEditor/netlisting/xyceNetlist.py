# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Xyce netlist generation for schematic editors.

This module provides the xyceNetlist class for generating SPICE-compatible
netlists from schematic designs. It supports hierarchical netlisting with
config views, array notation for buses, and various netlist formats including
Spice, Verilog-A, and LVS modes.
"""

from __future__ import annotations

import datetime
import pathlib
import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.shapes as shp
from revedaEditor.netlisting import exprSupport
from revedaEditor.netlisting.baseNetlist import NetlistBase
from revedaEditor.scenes.schematicScene import schematicScene

if TYPE_CHECKING:
    from revedaEditor.gui.schematicEditor import schematicEditor


class xyceNetlist(NetlistBase):
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
    # after token substitution, plus `key=@token` pairs whose label did not resolve
    # (e.g. `ps=@ps` on instances placed before the symbol gained that label).
    # Compiled once at class level avoids re.compile() on every
    # netlist line inside the hot loop.
    _PARAM_RE = re.compile(r'\s+\w+\s*=\s*@\w+|\s+\w+\s*=(?=\s|$)')

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
        # (lib, cell, view) -> {exprName: default} implicit-terminal defs.
        self._exprDefsCache: dict[tuple, dict] = {}
        # Global (!) nets resolved from net expressions; emitted as .GLOBAL.
        self.globalNets: set[str] = {"gnd!"}

    def __repr__(self):
        return f"xyceNetlist(filePathObj={self.filePathObj}, schematic={self.schematic}, useConfig={self._useConfig}, lvsMode={self._lvsMode})"

    # switch/stop/config view properties are inherited from NetlistBase.

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

            # Declare global nets resolved from net expressions / netSet
            # bindings during the run (gnd! is already in the header).
            for globalNet in sorted(self.globalNets - {"gnd!"}):
                cirFile.write(f".GLOBAL {globalNet}\n")

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
        # Terminal mode: this scene's net expressions resolve to their
        # expression names — each is an implicit subcircuit terminal.
        schematicScene.nameSceneNets(netSet=exprSupport.terminalNetSet(
            schematicScene.collectNetExprNames()))
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
                    exprDefs = self._exprDefsFor(elementSymbol, cellItem,
                                                 netlistView)
                    exprNets = exprSupport.exprNetsForInstance(
                        elementSymbol, exprDefs)
                    lines = self.createXyceSymbolLine(elementSymbol,
                                                      exprNets=exprNets)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    self.globalNets |= exprSupport.globalNets(
                        exprDefs, getattr(elementSymbol, "netSet", {}))
                    if not self._isStopView(netlistView):
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
                            schematicObj.loadSchematic(register=False)
                            expandedPinsString = self.expandPinNames(
                                list(elementSymbol.pinNetMap.keys()))
                            terminals = exprSupport.exprTerminals(exprDefs)
                            if terminals:
                                expandedPinsString += " " + " ".join(
                                    terminals)
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
                elif ("spectre" in netlistView or "spef" in netlistView
                      or "vacask" in netlistView):
                    lines = self.createTextViewLine(elementSymbol, cellItem,
                                                    netlistView)
                    content.extend(lines if isinstance(lines, list) else [lines])
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
            topExprDefs = schematicScene.collectNetExprNames()
            topTerminals = exprSupport.exprTerminals(topExprDefs)
            if topTerminals:
                expandedPinsString += " " + " ".join(topTerminals)
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
            # Global nets reached through net expressions on this sheet
            # (inherited connections resolving to '!' nets).
            for elementSymbol in sceneSymbolSet:
                self.globalNets |= {
                    netName for netName in elementSymbol.pinNetMap.values()
                    if netName.endswith("!")}
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

    def _exprDefsFor(self, elementSymbol, cellItem,
                     netlistView: str) -> dict:
        """{exprName: default} implicit-terminal defs of a subckt's view.

        Read from the child schematic's records (no editor needed) and
        cached per (lib, cell, view) so every instance of a cell shares
        the same terminal list."""
        key = (elementSymbol.libraryName, elementSymbol.cellName,
               netlistView)
        if key not in self._exprDefsCache:
            self._exprDefsCache[key] = (
                exprSupport.exprDefsForSchematicView(
                    cellItem, netlistView, self.libraryDict)
                if cellItem is not None else {})
        return self._exprDefsCache[key]

    # _getCellItem and determineNetlistView are inherited from NetlistBase.

    def _findViewFromSwitchList(self, viewItems: list) -> str:
        """Find the first matching view from switchViewList, respecting stopViewList.

        This overrides the base rule: Xyce consults ``stopViewList`` so a
        switch-list type that is also a stop view is selected (and synthesised
        if no concrete view of that type exists) rather than skipped.

        switchViewList and stopViewList hold view *types* (e.g. "schematic",
        "symbol"); they are matched against each view item's viewType, so
        views like "schematic2" are covered by the "schematic" type. The
        switch-list order defines priority.

        Args:
            viewItems: List of available view items for the cell.

        Returns:
            The name of the selected view, or "symbol" if none match.
        """
        viewNameByType = {}
        for viewItem in viewItems:
            if (viewItem.viewType not in viewNameByType
                    or viewItem.viewName == viewItem.viewType):
                viewNameByType[viewItem.viewType] = viewItem.viewName
        for viewType in self._switchViewList:
            # If this type is in stopViewList, use it and stop searching
            if viewType in self._stopViewList:
                return viewNameByType.get(viewType, viewType)
            # Otherwise, if a view of this type is available, use it and stop
            if viewType in viewNameByType:
                return viewNameByType[viewType]

        # If no match found in switchViewList, default to "symbol"
        return "symbol"

    # _isStopView is inherited from NetlistBase.

    def createItemLine(self, cirFile, elementSymbol: shp.schematicSymbol,
                       cellItem: libb.cellItem, netlistView: str, ):
        """Create the appropriate netlist line(s) for a symbol based on its view type."""
        if "schematic" in netlistView:
            exprDefs = self._exprDefsFor(elementSymbol, cellItem,
                                         netlistView)
            exprNets = exprSupport.exprNetsForInstance(elementSymbol,
                                                       exprDefs)
            elementLines = self.createXyceSymbolLine(elementSymbol,
                                                     exprNets=exprNets)
            for line in elementLines:
                cirFile.write(f"{line}\n")
            self.globalNets |= exprSupport.globalNets(
                exprDefs, getattr(elementSymbol, "netSet", {}))

            if not self._isStopView(netlistView):
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
                    schematicObj.loadSchematic(register=False)
                    expandedPinsString = self.expandPinNames(
                        list(elementSymbol.pinNetMap.keys()))
                    terminals = exprSupport.exprTerminals(exprDefs)
                    if terminals:
                        expandedPinsString += " " + " ".join(terminals)
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
        elif ("spectre" in netlistView or "spef" in netlistView
              or "vacask" in netlistView):
            textLines = self.createTextViewLine(elementSymbol, cellItem,
                                                netlistView)
            for line in textLines:
                cirFile.write(f"{line}\n")

    def _createNetlistLine(self, elementSymbol: shp.schematicSymbol, netlistLineKey: str,
                           exprNets: list = None) -> \
            list[str]:
        """Shared netlist line creation logic.

        Handles array notation, attribute substitution, and pin ordering.
        This is the core netlisting logic used by all netlist formats.

        Args:
            elementSymbol: The symbol instance to create netlist lines for.
            netlistLineKey: The attribute key for the netlist line template.
            exprNets: ordered nets for the child subcircuit's implicit
                net-expression terminals (inherited connections); appended
                after the pinOrder nets.

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

            # Single-pass token substitution over the template. Only whole
            # "@name"/"%name" tokens match, so "@w" never substitutes inside
            # "@wfeed"; unresolved tokens are left for _PARAM_RE cleanup.
            tokenMap = {f"%{attrName}": attrValue
                        for attrName, attrValue in elementSymbol.symattrs.items()}
            tokenMap.update(
                (lbl.labelName, lbl.labelValue)
                for lbl in elementSymbol.labels.values())
            tokenPattern = re.compile("(?:" + "|".join(sorted(
                (re.escape(token)
                 for token in (*tokenMap, instNameToken, "%pinOrder",
                               "%lvsPinOrder")),
                key=len, reverse=True)) + r")(?!\w)")

            def createInstanceLine(instanceName, netsList, lvsNetsList):
                def substituteToken(match):
                    token = match.group(0)
                    if token == instNameToken:
                        return instanceName
                    if token == "%pinOrder":
                        return netsList
                    if token == "%lvsPinOrder":
                        return lvsNetsList
                    return tokenMap.get(token, token)
                return tokenPattern.sub(substituteToken, baseNetlistLine)

            def processLine(line):
                return xyceNetlist._PARAM_RE.sub('', line)

            def expandNet(netName):
                baseName, netTuple = self.parseArrayNotation(netName)
                if netTuple[0] == netTuple[1] == -1:
                    return [baseName]
                netStep = 1 if netTuple[1] >= netTuple[0] else -1
                return [f"{baseName}<{i}>" for i in
                        range(netTuple[0], netTuple[1] + netStep, netStep)]

            # Expand nets per pin
            expandedPinNets = [expandNet(netName) for netName in elementSymbol.pinNetMap.values()]

            # 'lvsPinOrder' reorders the same pin nets for the LVS line when
            # the extracted terminal order differs from pinOrder (e.g.
            # inductor3's center tap extracts between the outer ports).
            expandedLvsPinNets = expandedPinNets
            lvsPinOrder = (elementSymbol.symattrs or {}).get("lvsPinOrder")
            if lvsPinOrder:
                expandedLvsPinNets = [
                    expandNet(elementSymbol.pinNetMap[pinName])
                    for pinName in (pin.strip() for pin in str(lvsPinOrder).split(","))
                    if pinName in elementSymbol.pinNetMap
                ]

            def selectNets(expandedNets, index):
                """Pick per-instance nets honoring array broadcast rules."""
                pickedNets = []
                for nets in expandedNets:
                    if len(nets) == arraySize:
                        pickedNets.append(nets[index])  # 1-to-1 matching across array width
                    elif len(nets) == 1:
                        pickedNets.append(nets[0])  # Scalar broadcasted to all array nodes
                    elif index < len(nets):
                        pickedNets.append(nets[index])  # Partial connection: connect available nets
                    else:
                        # Out of bounds for partial connection - use last available net
                        pickedNets.append(nets[-1])
                return pickedNets

            # Generate instance lines
            exprNets = list(exprNets or ())
            if arraySize == 1:
                # Scalar instance logic
                flatNetsList = " ".join([nets[0] for nets in expandedPinNets]
                                        + exprNets)
                flatLvsNetsList = " ".join(
                    [nets[0] for nets in expandedLvsPinNets] + exprNets)
                symbolLines.append(processLine(createInstanceLine(
                    baseInstName, flatNetsList, flatLvsNetsList)))
            else:
                # Array instance logic
                arrayIndices = list(range(arrayTuple[0], arrayTuple[1] + arrayStep, arrayStep))

                for j, i in enumerate(arrayIndices):
                    specificNetsList = " ".join(selectNets(expandedPinNets, j)
                                                + exprNets)
                    specificLvsNetsList = " ".join(
                        selectNets(expandedLvsPinNets, j) + exprNets)
                    symbolLines.append(
                        processLine(createInstanceLine(
                            f"{baseInstName}<{i}>", specificNetsList,
                            specificLvsNetsList)))

            return symbolLines


        except Exception as e:
            self._scene.logger.error(
                f"Error creating netlist line for {elementSymbol.instanceName}: {e}")
            return [
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n"]

    def createXyceSymbolLine(self, elementSymbol: shp.schematicSymbol,
                             exprNets: list = None) -> list[str]:
        """Create Xyce netlist lines for a symbol instance.

        In LVS mode, uses the 'lvsNetlistLine' attribute, otherwise 'SpiceNetlistLine'.
        ``exprNets`` carries the resolved implicit-terminal nets when the
        instance expands to a subcircuit with net expressions.
        """
        netlistLineKey = "lvsNetlistLine" if self._lvsMode else "SpiceNetlistLine"
        return self._createNetlistLine(elementSymbol, netlistLineKey,
                                       exprNets=exprNets)

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
                    incFileName = elementSymbol.symattrs.get(
                        "SpiceIncludeLine", ""
                    ).strip()
                    if incFileName:
                        incFilePath = pathlib.Path(cellPath) / incFileName
                    else:
                        netlistView = self.determineNetlistView(elementSymbol, cellItem)
                        incFilePath = libb.textViewFilePath(
                            cellItem, libm.getViewItem(cellItem, netlistView))
                        if incFilePath is None:
                            incFilePath = pathlib.Path(cellPath) / f"{elementSymbol.cellName}.sp"
                    self.includeLines.add(f'.INC "{incFilePath}"')
                else:
                    self._scene.logger.warning(f"Cell path not found for {elementSymbol.cellName}, skipping include file")
            else:
                self._scene.logger.warning(f"Cell item not found for {elementSymbol.cellName}, skipping include file")
            return spiceLines
        except Exception as e:
            self._scene.logger.error(f"Spice subckt netlist error for {elementSymbol.instanceName}: {e}")
            return [f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n"]

    def createTextViewLine(self, elementSymbol: shp.schematicSymbol,
                           cellItem: libb.cellItem, netlistView: str) -> list[str]:
        """Create netlist lines for an instance bound to a file-backed text view.

        Emits the instance line and pulls the view's netlist file in once via
        a ``.INC`` directive. Used for spectre/spef/vacask views selected
        through the switch list or a config view (e.g. PEX-extracted
        netlists, which are complete subcircuits named after the cell).
        """
        try:
            symbolLines = self.createXyceSymbolLine(elementSymbol)
            viewItem = libm.getViewItem(cellItem, netlistView)
            filePath = libb.textViewFilePath(cellItem, viewItem)
            if filePath is not None:
                self.includeLines.add(f'.INC "{filePath}"')
            else:
                self._scene.logger.warning(
                    f"View '{netlistView}' of {elementSymbol.cellName} has no "
                    f"netlist file")
            return symbolLines
        except Exception as e:
            self._scene.logger.error(
                f"Text view netlist error for {elementSymbol.instanceName}: {e}")
            return [
                f"*Netlist line is not defined for symbol of {elementSymbol.instanceName}\n"]

    # parseArrayNotation / expandPinNames are inherited from NetlistBase.
