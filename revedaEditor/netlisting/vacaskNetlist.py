# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""VACASK netlist generation for schematic editors.

This module provides the vacaskNetlist class for generating VACASK-compatible
netlists from schematic designs. It supports hierarchical netlisting with config views,
array notation for buses, and various netlist formats including VACASK, Verilog-A, and
LVS modes.

VACASK format differences from Spectre:
- Uses ``ground`` directive instead of ``global`` for reference nodes
- Uses ``load`` directive for OSDI/Verilog-A devices instead of ``ahdl_include``
- Requires ``model`` statements for all device types
- Supports ``parameters`` block for parameter declarations
- Supports ``control``/``endc`` block for simulation setup
- Supports ``embed`` directive for embedded files
- Supports section-based includes with ``include "file" section=name``
- Subcircuit blocks use ``subckt`` / ``ends`` (same as Spectre)
- Include directives use ``include "file"`` (same as Spectre)
- Comments use ``//`` (same as Spectre)

Device loading categories:
- **Built-in** (vsource, isource, vcvs, vccs, ccvs, cccs, mutual):
  No ``load`` needed; ``VacaskModelLine`` provides the ``model`` statement.
- **Built-in OSDI** (resistor, capacitor, inductor, diode, opamp):
  ``VacaskLoadFile`` is a bare filename (e.g. ``resistor.osdi``);
  ``VacaskModelLine`` provides the ``model`` statement.
- **Custom Verilog-A/OSDI**: ``VacaskLoadFile`` is a full path, or if absent
  the path is auto-constructed as ``{cellPath}/{cellName}.va``;
  ``VacaskModelLine`` provides the ``model`` statement.
- **Library includes**: ``VacaskIncludeLib`` emits an ``include`` directive
  and suppresses that symbol's ``VacaskModelLine`` (the library provides it).
"""

from __future__ import annotations

import datetime
import functools
import io
import json
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


class vacaskNetlist:
    """Generate VACASK-compatible netlists from schematic designs.

    This class handles recursive netlisting of hierarchical designs, supports
    configuration views for view switching, and handles array notation for
    bussed signals.  It caches cell lookups to avoid repeated Qt model traversals.

    VACASK-specific formatting is used throughout: ``//`` comments, ``subckt``/``ends``
    blocks, ``ground`` declarations, ``include`` directives, and ``load`` for
    Verilog-A/OSDI files.

    Attributes:
        filePathObj: Path to write the netlist file.
        schematic: The schematic editor being netlisted.
        topSubckt: Whether to wrap the top level in a ``subckt`` block.
        configDict: Configuration dictionary for view switching (config views).
        subcircuitDefs: List of subcircuit definitions collected during netlisting.
    """

    # Pre-compiled regex to strip dangling parameter assignments (e.g. `` width =``) left
    # after token substitution.  Compiled once at class level avoids re.compile() on every
    # netlist line inside the hot loop.
    _PARAM_RE = re.compile(r'\s+\w+\s*=(?=\s|$)')

    def __init__(
        self,
        schematic: schematicEditor,
        filePathObj: pathlib.Path,
        useConfig: bool = False,
        topSubckt: bool = False,
        lvsMode: bool = False,
    ):
        """Initialize the VACASK netlister.

        Args:
            schematic: The schematic editor to netlist.
            filePathObj: Destination path for the netlist file.
            useConfig: Whether to use configuration view for view switching.
            topSubckt: Whether to wrap top level in a ``subckt`` block.
            lvsMode: LVS mode – uses ``lvsIgnore`` attribute instead of ``NetlistIgnore``.
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
        self.libItem = libm.getLibItem(
            self.schematic.libraryView.libraryModel,
            self.schematic.libName,
        )
        self.cellItem = libm.getCellItem(self.libItem, self.schematic.cellName)
        self.subcircuitDefs: list[str] = []
        self._switchViewList = schematic.switchViewList
        self._stopViewList = schematic.stopViewList
        self.netlistedViewsSet: set = set()
        self.includeLines: set[str] = set()
        self.vahdlLines: set[str] = set()
        self.loadLines: set[str] = set()
        self.groundNets: set[str] = set()
        self.globalNets: set[str] = set()
        self.modelLines: set[str] = set()
        self.osdiLoadLines: set[str] = set()
        self.includeLibLines: set[str] = set()
        # Caches to avoid repeated Qt model traversals for the same cells.
        self._viewNameCache: dict[tuple, str] = {}
        self._cellItemCache: dict[tuple, libb.cellItem | None] = {}

    def __repr__(self):
        return (
            f"vacaskNetlist(filePathObj={self.filePathObj}, "
            f"schematic={self.schematic}, "
            f"useConfig={self._useConfig}, lvsMode={self._lvsMode})"
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def writeNetlist(self):
        """Write the complete VACASK netlist to *filePathObj*.

        Writes the file header, performs recursive netlisting, and appends all
        subcircuit definitions at the end.
        """
        with self.filePathObj.open(mode="w") as cirFile:
            # VACASK header – the first line *must* start with "// " for VACASK to
            # recognise the file as VACASK format.
            cirFile.write(
                "// ".join([
                    "\n",
                    80 * "/" + "\n",
                    "// Revolution EDA VACASK Netlist\n",
                    f"// Library: {self.schematic.libName}\n",
                    f"// Top Cell Name: {self.schematic.cellName}\n",
                    f"// View Name: {self.schematic.viewName}\n",
                    f"// Date: {datetime.datetime.now()}\n",
                    80 * "/" + "\n",
                ])
            )

            self.subcircuitDefs = []

            # Buffer netlisting content so ground net names can be collected
            # before writing the ground directive.
            contentBuffer = io.StringIO()
            self.recursiveNetlisting(self.schematic, contentBuffer)

            # Write global directive with collected non-ground global net names.
            globalNets = " ".join(sorted(self.globalNets))
            if globalNets:
                cirFile.write(f"global {globalNets}\n\n")

            # Write ground directive with collected ground net names (once).
            groundNets = " ".join(sorted(self.groundNets))
            if groundNets:
                cirFile.write(f"ground 0 {groundNets}\n\n")
            else:
                cirFile.write("ground 0\n\n")

            # Write library includes (section-based model libraries).
            for line in sorted(self.includeLibLines):
                cirFile.write(f"{line}\n")
            if self.includeLibLines:
                cirFile.write("\n")

            # Write OSDI built-in loads (bare filenames) and custom loads (paths).
            for line in sorted(self.osdiLoadLines):
                cirFile.write(f"{line}\n")
            for line in sorted(self.loadLines):
                cirFile.write(f"{line}\n")
            if self.osdiLoadLines or self.loadLines:
                cirFile.write("\n")

            # Write model statements (deduplicated).
            for line in sorted(self.modelLines):
                cirFile.write(f"{line}\n")
            if self.modelLines:
                cirFile.write("\n")

            cirFile.write(contentBuffer.getvalue())
            contentBuffer.close()

            if self.subcircuitDefs:
                cirFile.write("\n// Subcircuit Definitions\n")
                for subcktDef in self.subcircuitDefs:
                    cirFile.write(subcktDef)

            for line in self.includeLines:
                cirFile.write(f"{line}\n")
            for line in self.vahdlLines:
                cirFile.write(f"{line}\n")

    def collectSubcircuitContent(self, schematic: schematicEditor, content: list):
        """Collect subcircuit content without writing to file.

        Traverses *schematic*, netlists each element, and recursively processes
        nested schematics.

        Args:
            schematic: The schematic editor to collect content from.
            content: List to append netlist lines to.
        """
        schematicScene = schematic.centralW.scene
        schematicScene.nameSceneNets()
        sceneSymbolSet = schematicScene.findSceneSymbolSet()
        schematicScene.generatePinNetMap(sceneSymbolSet)

        for elementSymbol in sceneSymbolSet:
            if elementSymbol.symattrs.get("NetlistIgnore") != "1" and (
                not elementSymbol.netlistIgnore
            ):
                cellItem = self._getCellItem(
                    elementSymbol.libraryName, elementSymbol.cellName
                )
                netlistView = self.determineNetlistView(elementSymbol, cellItem)

                if "schematic" in netlistView:
                    lines = self.createVacaskSymbolLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    if netlistView not in self._stopViewList:
                        viewTuple = ddef.viewNameTuple(
                            elementSymbol.libraryName,
                            elementSymbol.cellName,
                            netlistView,
                        )
                        if viewTuple not in self.netlistedViewsSet:
                            self.netlistedViewsSet.add(viewTuple)
                            schematicItem = libm.getViewItem(cellItem, netlistView)
                            from revedaEditor.gui.schematicEditor import schematicEditor
                            schematicObj = schematicEditor(
                                schematicItem, self.libraryDict, self.libraryView
                            )
                            schematicObj.loadSchematic()
                            expandedPinsString = self.expandPinNames(
                                list(elementSymbol.pinNetMap.keys())
                            )
                            subcktContent: list[str] = []
                            self.collectSubcircuitContent(schematicObj, subcktContent)
                            subcktDef = (
                                f"subckt {schematicObj.cellName} ( {expandedPinsString} ) \n"
                                + "\n".join(subcktContent)
                                + f"\nends {schematicObj.cellName}\n"
                            )
                            self.subcircuitDefs.append(subcktDef)
                elif "symbol" in netlistView:
                    lines = self.createVacaskSymbolLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    self._collectModelLoadInfo(elementSymbol)
                elif "spice" in netlistView:
                    lines = self.createSpiceLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    self._collectModelLoadInfo(elementSymbol)
                elif "veriloga" in netlistView:
                    lines = self.createVerilogaLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
            elif elementSymbol.netlistIgnore:
                content.append(
                    f"// {elementSymbol.instanceName} is marked to be ignored"
                )
            else:
                content.append(
                    f"// {elementSymbol.instanceName} is excluded via NetlistIgnore attribute"
                )

    def recursiveNetlisting(self, schematicEdObj: schematicEditor, cirFile):
        """Recursively traverse all sub-circuits and netlist them.

        Args:
            schematicEdObj: The schematic editor to netlist.
            cirFile: Open file handle to write netlist to.
        """
        if self.topSubckt:
            viewTuple = ddef.viewNameTuple(
                schematicEdObj.libName,
                schematicEdObj.cellName,
                schematicEdObj.viewName,
            )
            self.netlistedViewsSet.add(viewTuple)
            schematicPinsSet = schematicEdObj.centralW.scene.findSceneSchemPinsSet()
            pinNames = [pin.pinName for pin in schematicPinsSet]
            expandedPinsString = self.expandPinNames(pinNames)

            subcktContent: list[str] = []
            self.collectSubcircuitContent(schematicEdObj, subcktContent)
            subcktDef = (
                f"\nsubckt {schematicEdObj.cellName} ( {expandedPinsString} ) \n"
                + "\n".join(subcktContent)
                + f"\nends {schematicEdObj.cellName}\n"
            )
            self.subcircuitDefs.append(subcktDef)
        else:
            schScene = schematicEdObj.centralW.scene
            schScene.nameSceneNets()
            sceneSymbolSet = schScene.findSceneSymbolSet()
            schScene.generatePinNetMap(sceneSymbolSet)
            for elementSymbol in sceneSymbolSet:
                self.processElementSymbol(elementSymbol, schematicEdObj, cirFile)

    def _shouldIgnoreSymbol(self, elementSymbol) -> tuple[bool, str]:
        """Determine if a symbol should be ignored during netlisting.

        Checks ignore conditions based on mode (LVS or normal).

        Args:
            elementSymbol: The schematic symbol to check.

        Returns:
            Tuple of (should_ignore, ignore_reason).
        """
        if self._lvsMode:
            if elementSymbol.symattrs.get("lvsIgnore") == "1":
                return True, f"// {elementSymbol.instanceName} is excluded via lvsIgnore attribute\n"
        else:
            if (
                elementSymbol.symattrs.get("NetlistIgnore") == "1"
                or elementSymbol.netlistIgnore
            ):
                if elementSymbol.netlistIgnore:
                    return True, f"// {elementSymbol.instanceName} is marked to be ignored\n"
                else:
                    return True, f"// {elementSymbol.instanceName} is excluded via NetlistIgnore attribute\n"
        return False, ""

    def processElementSymbol(self, elementSymbol, schematic, cirFile):
        """Process a single element symbol during netlisting.

        Checks ignore conditions based on mode (LVS or normal) and either writes an
        ignore comment or creates the appropriate netlist line.

        Args:
            elementSymbol: The schematic symbol to process.
            schematic: The schematic editor containing the symbol.
            cirFile: Open file handle to write to.
        """
        should_ignore, ignore_reason = self._shouldIgnoreSymbol(elementSymbol)

        if should_ignore:
            cirFile.write(ignore_reason)
        else:
            cellItem = self._getCellItem(
                elementSymbol.libraryName, elementSymbol.cellName
            )
            netlistView = self.determineNetlistView(elementSymbol, cellItem)
            self.createItemLine(cirFile, elementSymbol, cellItem, netlistView)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _processGlobalNet(self, netName: str) -> str:
        """Strip trailing ``!`` from global net names and track them for directives.

        VACASK does not accept ``!`` in net names.  Global nets (those ending
        with ``!``) are handled as follows:

        - ``gnd!`` is converted to ``gnd`` and added to :attr:`groundNets`
          for the ``ground 0`` directive.
        - Any other global net (e.g. ``vdd!``) has the ``!`` stripped and is
          added to :attr:`globalNets` for the ``global`` directive.
        """
        if "gnd!" in netName:
            self.groundNets.add("gnd")
            return netName.replace("gnd!", "gnd")
        if netName.endswith("!"):
            globalName = netName[:-1]
            self.globalNets.add(globalName)
            return globalName
        return netName

    def _collectModelLoadInfo(
        self, elementSymbol: shp.schematicSymbol, skipLoadFile: bool = False
    ):
        """Collect model, load, and include-library directives from symbol attributes.

        Reads ``VacaskModelLine``, ``VacaskLoadFile``, and ``VacaskIncludeLib``
        from *elementSymbol.symattrs* and populates the corresponding sets on
        this netlister.  All directives are deduplicated via sets so they are
        written only once per netlist.

        - ``VacaskModelLine``: added to :attr:`modelLines` unless
          ``VacaskIncludeLib`` is present (the library file provides the model).
        - ``VacaskLoadFile``: bare filenames (no path separator) go to
          :attr:`osdiLoadLines`; paths go to :attr:`loadLines`.
          Skipped when *skipLoadFile* is ``True`` (e.g. when the load path
          is resolved from the veriloga view JSON instead).
        - ``VacaskIncludeLib``: added to :attr:`includeLibLines`.
        """
        includeLib = elementSymbol.symattrs.get("VacaskIncludeLib")
        if includeLib:
            includeLib = includeLib.strip().replace("\\", "/")
            self.includeLibLines.add(f'include "{includeLib}"')

        if not includeLib:
            modelLine = elementSymbol.symattrs.get("VacaskModelLine")
            if modelLine:
                self.modelLines.add(modelLine.strip())

        if not skipLoadFile:
            loadFile = elementSymbol.symattrs.get("VacaskLoadFile")
            if loadFile:
                loadFile = loadFile.strip().replace("\\", "/")
                if "/" in loadFile:
                    self.loadLines.add(f'load "{loadFile}"')
                else:
                    self.osdiLoadLines.add(f'load "{loadFile}"')

    def _getCellItem(self, libraryName: str, cellName: str) -> libb.cellItem | None:
        """Return the cellItem for *(libraryName, cellName)*, cached to avoid repeated model traversals.

        Returns ``None`` if the cell is not found in the library.
        """
        key = (libraryName, cellName)
        if key not in self._cellItemCache:
            libItem = libm.getLibItem(self.libraryView.libraryModel, libraryName)
            self._cellItemCache[key] = libm.getCellItem(libItem, cellName)
        return self._cellItemCache[key]

    def determineNetlistView(self, elementSymbol, cellItem) -> str:
        """Determine which view to use for netlisting a symbol instance.

        Uses *configDict* in config mode, otherwise iterates through *switchViewList*
        to find the first matching view.

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
        """Find the first matching view from switchViewList.
        
        Args:
            viewNames: List of available view names for the cell.
            
        Returns:
            The first matching view name from switchViewList, or "symbol" if none match.
        """
        for viewName in self._switchViewList:
            if viewName in viewNames:
                return viewName
        return "symbol"

    def createItemLine(
        self,
        cirFile,
        elementSymbol: shp.schematicSymbol,
        cellItem: libb.cellItem,
        netlistView: str,
    ):
        """Create the appropriate VACASK netlist line(s) for a symbol based on its view type."""
        if "schematic" in netlistView:
            elementLines = self.createVacaskSymbolLine(elementSymbol)
            for line in elementLines:
                cirFile.write(f"{line}\n")

            if netlistView not in self._stopViewList:
                viewTuple = ddef.viewNameTuple(
                    elementSymbol.libraryName,
                    elementSymbol.cellName,
                    netlistView,
                )
                if viewTuple not in self.netlistedViewsSet:
                    self.netlistedViewsSet.add(viewTuple)
                    schematicItem = libm.getViewItem(cellItem, netlistView)
                    if schematicItem is None:
                        self._scene.logger.warning(
                            f"View {netlistView} not found for {elementSymbol.cellName}"
                        )
                        return
                    from revedaEditor.gui.schematicEditor import schematicEditor
                    schematicObj = schematicEditor(
                        schematicItem, self.libraryDict, self.libraryView
                    )
                    schematicObj.loadSchematic()
                    expandedPinsString = self.expandPinNames(
                        list(elementSymbol.pinNetMap.keys())
                    )
                    subcktContent: list[str] = []
                    self.collectSubcircuitContent(schematicObj, subcktContent)
                    subcktDef = (
                        f"\nsubckt {schematicObj.cellName} ( {expandedPinsString} )\n"
                        + "\n".join(subcktContent)
                        + f"\nends {schematicObj.cellName}\n"
                    )
                    self.subcircuitDefs.append(subcktDef)

        elif "symbol" in netlistView:
            symbolLines = self.createVacaskSymbolLine(elementSymbol)
            for line in symbolLines:
                cirFile.write(f"{line}\n")
            self._collectModelLoadInfo(elementSymbol)
        elif "spice" in netlistView:
            spiceLines = self.createSpiceLine(elementSymbol)
            for line in spiceLines:
                cirFile.write(f"{line}\n")
            self._collectModelLoadInfo(elementSymbol)
        elif "veriloga" in netlistView:
            verilogaLines = self.createVerilogaLine(elementSymbol)
            for line in verilogaLines:
                cirFile.write(f"{line}\n")

    def _createNetlistLine(
        self,
        elementSymbol: shp.schematicSymbol,
        netlistLineKey: str,
    ) -> list[str]:
        """Shared netlist line creation logic.

        Handles array notation, attribute substitution, and pin ordering.
        This is the core netlisting logic used by all netlist formats.

        Args:
            elementSymbol: The symbol instance to create netlist lines for.
            netlistLineKey: The attribute key for the netlist line template
                (e.g. ``"VacaskNetlistLine"`` or ``"lvsNetlistLine"``).

        Returns:
            List of netlist line strings (one per array element if arrayed).
        """
        try:
            instNameLabel = elementSymbol.labels.get('@instName')
            if not instNameLabel:
                return []

            baseInstName, arrayTuple = self.parseArrayNotation(
                instNameLabel.labelValue.strip()
            )
            arrayStep = -1 if arrayTuple[0] > arrayTuple[1] else 1
            arraySize = abs(arrayTuple[0] - arrayTuple[1]) + 1

            baseNetlistLine = elementSymbol.symattrs[netlistLineKey].strip()
            instNameToken = instNameLabel.labelName
            symbolLines: list[str] = []

            attr_replacements = [
                (f"%{a}", v) for a, v in elementSymbol.symattrs.items()
            ]
            label_replacements = [
                (lbl.labelName, lbl.labelValue)
                for lbl in elementSymbol.labels.values()
            ]

            def processLine(line: str, netsList: str) -> str:
                line = line.replace("%pinOrder", netsList)
                for token, value in attr_replacements:
                    line = line.replace(token, value)
                line = vacaskNetlist._PARAM_RE.sub('', line)
                line = line.replace('{', '').replace('}', '')
                return line

            def createInstanceLine(instanceName: str) -> str:
                line = baseNetlistLine.replace(instNameToken, instanceName)
                for labelName, labelValue in label_replacements:
                    line = line.replace(labelName, labelValue)
                return line

            def expandNet(netName: str) -> list[str]:
                baseName, netTuple = self.parseArrayNotation(netName)
                if netTuple[0] == netTuple[1] == -1:
                    return [baseName]
                netStep = 1 if netTuple[1] >= netTuple[0] else -1
                return [
                    f"{baseName}<{i}>"
                    for i in range(netTuple[0], netTuple[1] + netStep, netStep)
                ]

            def getNetVectorInfo(netName: str) -> tuple[str, tuple[int, int] | None]:
                """Get base name and array tuple for a net, or (name, None) if scalar."""
                baseName, netTuple = self.parseArrayNotation(netName)
                if netTuple[0] == netTuple[1] == -1:
                    return baseName, None
                return baseName, netTuple

            # Process net names: strip ! from global nets and track them.
            pinNets = [self._processGlobalNet(n) for n in elementSymbol.pinNetMap.values()]

            # Collect net vector information
            netVectorInfos = [
                getNetVectorInfo(netName) for netName in pinNets
            ]

            # Check if we can preserve vector notation
            # All nets must be scalars or vectors of the same dimension as the instance
            canUseVectorNotation = arraySize > 1
            if canUseVectorNotation:
                for netBaseName, netTuple in netVectorInfos:
                    if netTuple is None:
                        # Scalar net connected to vector instance - need expansion
                        canUseVectorNotation = False
                        break
                    netSize = abs(netTuple[0] - netTuple[1]) + 1
                    if netSize != arraySize:
                        # Dimension mismatch - need expansion
                        canUseVectorNotation = False
                        break

            if canUseVectorNotation:
                # Preserve vector notation: I5<0:3> (OUT<0:3> INP<0:3>) resistor r=1k
                vectorNetsList = " ".join([
                    f"{baseName}<{netTuple[0]}:{netTuple[1]}>"
                    if netTuple else baseName
                    for baseName, netTuple in netVectorInfos
                ])
                vectorInstName = f"{baseInstName}<{arrayTuple[0]}:{arrayTuple[1]}>"
                symbolLines.append(
                    processLine(createInstanceLine(vectorInstName), vectorNetsList)
                )
            else:
                # Fall back to expansion
                expandedPinNets = [
                    expandNet(netName) for netName in pinNets
                ]

                if arraySize == 1:
                    flatNetsList = " ".join([nets[0] for nets in expandedPinNets])
                    symbolLines.append(
                        processLine(createInstanceLine(baseInstName), flatNetsList)
                    )
                else:
                    arrayIndices = list(
                        range(arrayTuple[0], arrayTuple[1] + arrayStep, arrayStep)
                    )
                    for j, i in enumerate(arrayIndices):
                        instanceNets: list[str] = []
                        for nets in expandedPinNets:
                            if len(nets) == arraySize:
                                instanceNets.append(nets[j])
                            elif len(nets) == 1:
                                instanceNets.append(nets[0])
                            else:
                                self._scene.logger.warning(
                                    f"Net connection width mismatch for "
                                    f"{elementSymbol.instanceName}: "
                                    f"expected 1 or {arraySize}, got {len(nets)}. "
                                    f"Falling back to element 0."
                                )
                                instanceNets.append(nets[0])

                        specificNetsList = " ".join(instanceNets)
                        symbolLines.append(
                            processLine(
                                createInstanceLine(f"{baseInstName}<{i}>"),
                                specificNetsList,
                            )
                        )

            return symbolLines

        except Exception as e:
            self._scene.logger.error(
                f"Error creating netlist line for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    def createVacaskSymbolLine(
        self, elementSymbol: shp.schematicSymbol
    ) -> list[str]:
        """Create VACASK netlist lines for a symbol instance.

        In LVS mode uses the ``lvsNetlistLine`` attribute, otherwise uses
        ``VacaskNetlistLine``.
        """
        netlistLineKey = "lvsNetlistLine" if self._lvsMode else "VacaskNetlistLine"
        return self._createNetlistLine(elementSymbol, netlistLineKey)

    def createSpiceLine(self, elementSymbol: shp.schematicSymbol) -> list[str]:
        """Create VACASK-wrapped SPICE subcircuit netlist lines with include file handling.

        Generates the instance line using :meth:`createVacaskSymbolLine` and adds an
        ``include`` directive. The Spice subcircuit file path is automatically constructed as
        {cellPath}/{cellName}.sp.
        """
        try:
            spiceLines = self.createVacaskSymbolLine(elementSymbol)
            # Automatically construct Spice subcircuit file path from cell directory and cell name
            cellItem = self._getCellItem(
                elementSymbol.libraryName, elementSymbol.cellName
            )
            # Use cellPath attribute if available, otherwise fall back to UserRole+2
            cellPath = getattr(cellItem, 'cellPath', None) or cellItem.data(Qt.ItemDataRole.UserRole + 2)
            if not cellPath:
                self._scene.logger.warning(
                    f"Could not determine cell path for {elementSymbol.cellName}"
                )
                return spiceLines
            incFileName = f"{elementSymbol.cellName}.sp"
            incFilePath = pathlib.Path(cellPath) / incFileName
            self.includeLines.add(f'include "{incFilePath.as_posix()}"')
            return spiceLines
        except Exception as e:
            self._scene.logger.error(
                f"Vacask subckt netlist error for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    def _resolveVerilogaViewPath(self, elementSymbol) -> pathlib.Path | None:
        """Resolve the ``.va`` file path from the veriloga view JSON.

        Reads the view JSON (``viewItem.viewPath``) and extracts the
        ``filePath`` key from the second element, joining it with the cell
        path.  Returns ``None`` if the view or file path cannot be found.
        """
        cellItem = self._getCellItem(
            elementSymbol.libraryName, elementSymbol.cellName
        )
        if cellItem is None:
            return None
        netlistView = self.determineNetlistView(elementSymbol, cellItem)
        viewItem = libm.getViewItem(cellItem, netlistView)
        if viewItem is None:
            return None
        try:
            with viewItem.viewPath.open("r") as f:
                viewData = json.load(f)
            if len(viewData) > 1 and viewData[1].get("filePath"):
                return pathlib.Path(cellItem.cellPath).joinpath(
                    viewData[1]["filePath"]
                )
        except (json.JSONDecodeError, OSError, IndexError, KeyError):
            pass
        return None

    def createVerilogaLine(self, elementSymbol) -> list[str]:
        """Create VACASK Verilog-A netlist lines with load and model handling.

        Generates the instance line and resolves the ``.va`` file path from the
        veriloga view JSON.  Falls back to ``VacaskLoadFile`` from symbol
        attributes, then to auto-constructed ``{cellPath}/{cellName}.va``.
        Model and include-library directives are always collected via
        :meth:`_collectModelLoadInfo`.
        """
        try:
            symbolLines = self._createNetlistLine(
                elementSymbol, "VacaskNetlistLine"
            )
            vaFilePath = self._resolveVerilogaViewPath(elementSymbol)
            if vaFilePath:
                self.loadLines.add(f'load "{vaFilePath.as_posix()}"')
                self._collectModelLoadInfo(elementSymbol, skipLoadFile=True)
            else:
                self._collectModelLoadInfo(elementSymbol)
                if not elementSymbol.symattrs.get("VacaskLoadFile"):
                    cellItem = self._getCellItem(
                        elementSymbol.libraryName, elementSymbol.cellName
                    )
                    cellPath = cellItem.cellPath
                    vaFileName = f"{elementSymbol.cellName}.va"
                    vaFilePath = pathlib.Path(cellPath) / vaFileName
                    self.loadLines.add(f'load "{vaFilePath.as_posix()}"')
            return symbolLines
        except Exception as e:
            self._scene.logger.error(
                f"Verilog-A netlist error for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    # ------------------------------------------------------------------
    # Static helpers (shared with xyceNetlist via same logic)
    # ------------------------------------------------------------------

    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
        """Parse net/instance array notation like ``'name<0:5>'`` into base name and index range.

        Also handles single instance/net notation like ``'name<0>'``.

        Args:
            name: The net name with optional bus notation.

        Returns:
            A tuple of *(base_name, (start, end))*.
            For scalar names, returns *(name, (-1, -1))*.

        Examples:
            >>> vacaskNetlist.parseArrayNotation("net<0:3>")
            ('net', (0, 3))
            >>> vacaskNetlist.parseArrayNotation("bus<5>")
            ('bus', (5, 5))
            >>> vacaskNetlist.parseArrayNotation("scalar")
            ('scalar', (-1, -1))
        """
        if '<' not in name or '>' not in name:
            return name, (-1, -1)

        baseName = name.split('<')[0]
        indexRange = name.split('<')[1].split('>')[0]

        if ':' not in indexRange:
            singleIndex = int(indexRange)
            return baseName, (singleIndex, singleIndex)

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
            >>> vacaskNetlist.expandPinNames(["a<0:1>", "b"])
            'a<0> a<1> b'
        """
        expandedPinNameList: list[str] = []
        for pinName in pinNamesList:
            pinBaseName, pinTuple = vacaskNetlist.parseArrayNotation(pinName)
            if pinTuple[0] == pinTuple[1] == -1:
                expandedPinNameList.append(pinBaseName)
            else:
                pinStep = 1 if pinTuple[1] >= pinTuple[0] else -1
                for i in range(pinTuple[0], pinTuple[1] + pinStep):
                    expandedPinNameList.append(f'{pinBaseName}<{i}>')
        return ' '.join(expandedPinNameList)
