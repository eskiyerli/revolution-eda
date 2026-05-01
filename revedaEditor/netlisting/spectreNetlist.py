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
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

"""Spectre netlist generation for schematic editors.

Untested code.

This module provides the spectreNetlist class for generating Cadence Spectre-compatible
netlists from schematic designs. It supports hierarchical netlisting with config views,
array notation for buses, and various netlist formats including Spectre, Verilog-A, and
LVS modes.

Spectre format differences from SPICE/Xyce:
- Comments use ``//`` instead of ``*``
- Global declarations use ``global gnd!`` instead of ``.GLOBAL gnd!``
- Subcircuit blocks use ``subckt`` / ``ends`` instead of ``.SUBCKT`` / ``.ENDS``
- Include directives use ``include "file"`` instead of ``.INC "file"``
- Verilog-A includes use ``ahdl_include "file"`` instead of ``*.HDL``
- Instance netlist lines are expected in Spectre syntax
  (``instName (n1 n2) modelName param=value``)
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


class spectreNetlist:
    """Generate Cadence Spectre-compatible netlists from schematic designs.

    This class handles recursive netlisting of hierarchical designs, supports
    configuration views for view switching, and handles array notation for
    bussed signals.  It caches cell lookups to avoid repeated Qt model traversals.

    Spectre-specific formatting is used throughout: ``//`` comments, ``subckt``/``ends``
    blocks, ``global`` declarations, ``include`` directives, and ``ahdl_include`` for
    Verilog-A files.

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
        """Initialize the Spectre netlister.

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
        self.vamodelLines: set[str] = set()
        self.vahdlLines: set[str] = set()
        # Caches to avoid repeated Qt model traversals for the same cells.
        self._viewNameCache: dict[tuple, str] = {}
        self._cellItemCache: dict[tuple, libb.cellItem | None] = {}

    def __repr__(self):
        return (
            f"spectreNetlist(filePathObj={self.filePathObj}, "
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
        """Write the complete Spectre netlist to *filePathObj*.

        Writes the file header, performs recursive netlisting, and appends all
        subcircuit definitions at the end.
        """
        with self.filePathObj.open(mode="w") as cirFile:
            # Spectre header – the first line *must* start with "// " for Spectre to
            # recognise the file as Spectre format.
            cirFile.write(
                "// ".join([
                    "\n",
                    80 * "/" + "\n",
                    "// Revolution EDA Spectre Netlist\n",
                    f"// Library: {self.schematic.libName}\n",
                    f"// Top Cell Name: {self.schematic.cellName}\n",
                    f"// View Name: {self.schematic.viewName}\n",
                    f"// Date: {datetime.datetime.now()}\n",
                    80 * "/" + "\n",
                    "global gnd!\n\n",
                ])
            )

            self.subcircuitDefs = []

            self.recursiveNetlisting(self.schematic, cirFile)

            if self.subcircuitDefs:
                cirFile.write("\n// Subcircuit Definitions\n")
                for subcktDef in self.subcircuitDefs:
                    cirFile.write(subcktDef)

            for line in self.includeLines:
                cirFile.write(f"{line}\n")
            for line in self.vamodelLines:
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
                    lines = self.createSpectreSymbolLine(elementSymbol)
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
                                f"subckt {schematicObj.cellName} {expandedPinsString}\n"
                                + "\n".join(subcktContent)
                                + f"\nends {schematicObj.cellName}\n"
                            )
                            self.subcircuitDefs.append(subcktDef)
                elif "symbol" in netlistView:
                    lines = self.createSpectreSymbolLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
                elif "spice" in netlistView:
                    lines = self.createSpiceLine(elementSymbol)
                    content.extend(lines if isinstance(lines, list) else [lines])
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
                f"\nsubckt {schematicEdObj.cellName} {expandedPinsString}\n"
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

    def processElementSymbol(self, elementSymbol, schematic, cirFile):
        """Process a single element symbol during netlisting.

        Checks ignore conditions based on mode (LVS or normal) and either writes an
        ignore comment or creates the appropriate netlist line.

        Args:
            elementSymbol: The schematic symbol to process.
            schematic: The schematic editor containing the symbol.
            cirFile: Open file handle to write to.
        """
        should_ignore = False
        ignore_reason = ""

        if self._lvsMode:
            if elementSymbol.symattrs.get("lvsIgnore") == "1":
                should_ignore = True
                ignore_reason = (
                    f"// {elementSymbol.instanceName} is excluded via lvsIgnore attribute\n"
                )
        else:
            if (
                elementSymbol.symattrs.get("NetlistIgnore") == "1"
                or elementSymbol.netlistIgnore
            ):
                should_ignore = True
                if elementSymbol.netlistIgnore:
                    ignore_reason = (
                        f"// {elementSymbol.instanceName} is marked to be ignored\n"
                    )
                else:
                    ignore_reason = (
                        f"// {elementSymbol.instanceName} is excluded via NetlistIgnore attribute\n"
                    )

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

        if self._useConfig:
            config_entry = self.configDict.get(elementSymbol.cellName)
            result = config_entry[1] if config_entry else "symbol"
        else:
            for viewName in self._switchViewList:
                if viewName in viewNames:
                    result = viewName
                    break
            else:
                result = "symbol"

        self._viewNameCache[cacheKey] = result
        return result

    def createItemLine(
        self,
        cirFile,
        elementSymbol: shp.schematicSymbol,
        cellItem: libb.cellItem,
        netlistView: str,
    ):
        """Create the appropriate Spectre netlist line(s) for a symbol based on its view type."""
        if "schematic" in netlistView:
            elementLines = self.createSpectreSymbolLine(elementSymbol)
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
                        f"\nsubckt {schematicObj.cellName} {expandedPinsString}\n"
                        + "\n".join(subcktContent)
                        + f"\nends {schematicObj.cellName}\n"
                    )
                    self.subcircuitDefs.append(subcktDef)

        elif "symbol" in netlistView:
            symbolLines = self.createSpectreSymbolLine(elementSymbol)
            for line in symbolLines:
                cirFile.write(f"{line}\n")
        elif "spice" in netlistView:
            spiceLines = self.createSpiceLine(elementSymbol)
            for line in spiceLines:
                cirFile.write(f"{line}\n")
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
                (e.g. ``"SpectreNetlistLine"`` or ``"lvsNetlistLine"``).

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
                return spectreNetlist._PARAM_RE.sub('', line)

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

            expandedPinNets = [
                expandNet(netName) for netName in elementSymbol.pinNetMap.values()
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

    def createSpectreSymbolLine(
        self, elementSymbol: shp.schematicSymbol
    ) -> list[str]:
        """Create Spectre netlist lines for a symbol instance.

        In LVS mode uses the ``lvsNetlistLine`` attribute, otherwise uses
        ``SpectreNetlistLine``.
        """
        netlistLineKey = "lvsNetlistLine" if self._lvsMode else "SpectreNetlistLine"
        return self._createNetlistLine(elementSymbol, netlistLineKey)

    def createSpiceLine(self, elementSymbol: shp.schematicSymbol) -> list[str]:
        """Create Spectre-wrapped SPICE subcircuit netlist lines with include file handling.

        Generates the instance line using :meth:`createSpectreSymbolLine` and adds an
        ``include`` directive if the symbol has an ``incLine`` attribute.
        """
        try:
            spiceLines = self.createSpectreSymbolLine(elementSymbol)
            incFileName = elementSymbol.symattrs.get("incLine", "").strip()
            if incFileName:
                cellItem = self._getCellItem(
                    elementSymbol.libraryName, elementSymbol.cellName
                )
                cellPath = cellItem.data(Qt.ItemDataRole.UserRole + 2)
                incFilePath = pathlib.Path(cellPath) / incFileName
                self.includeLines.add(f'include "{incFilePath}"')
            else:
                self.includeLines.add(
                    f"// no include line found for {elementSymbol.cellName}"
                )
            return spiceLines
        except Exception as e:
            self._scene.logger.error(
                f"Spice subckt netlist error for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    def createVerilogaLine(self, elementSymbol) -> list[str]:
        """Create Spectre Verilog-A netlist lines with model and HDL file handling.

        Generates the instance line and adds ``vaModelLine`` and ``ahdl_include``
        directives if the symbol has the corresponding attributes.
        """
        try:
            symbolLines = self._createNetlistLine(
                elementSymbol, "SpectreVerilogaNetlistLine"
            )
            self.vamodelLines.add(
                elementSymbol.symattrs.get(
                    "vaModelLine",
                    f"// no model line is found for {elementSymbol.cellName}",
                ).strip()
            )
            vaFileName = elementSymbol.symattrs.get("vaFileName", "").strip()
            self._scene.logger.debug(
                f"Verilog-A file for {elementSymbol.cellName}: {vaFileName}"
            )
            if vaFileName:
                cellItem = self._getCellItem(
                    elementSymbol.libraryName, elementSymbol.cellName
                )
                cellPath = cellItem.cellPath
                vaFilePath = pathlib.Path(cellPath) / vaFileName
                self.vahdlLines.add(f'ahdl_include "{vaFilePath}"')
            else:
                self.vahdlLines.add(
                    f"// no Verilog-A file found for {elementSymbol.cellName}"
                )
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
    @functools.lru_cache(maxsize=None)
    def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
        """Parse net/instance array notation like ``'name<0:5>'`` into base name and index range.

        Also handles single instance/net notation like ``'name<0>'``.

        Args:
            name: The net name with optional bus notation.

        Returns:
            A tuple of *(base_name, (start, end))*.
            For scalar names, returns *(name, (-1, -1))*.

        Examples:
            >>> spectreNetlist.parseArrayNotation("net<0:3>")
            ('net', (0, 3))
            >>> spectreNetlist.parseArrayNotation("bus<5>")
            ('bus', (5, 5))
            >>> spectreNetlist.parseArrayNotation("scalar")
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
            >>> spectreNetlist.expandPinNames(["a<0:1>", "b"])
            'a<0> a<1> b'
        """
        expandedPinNameList: list[str] = []
        for pinName in pinNamesList:
            pinBaseName, pinTuple = spectreNetlist.parseArrayNotation(pinName)
            if pinTuple[0] == pinTuple[1] == -1:
                expandedPinNameList.append(pinBaseName)
            else:
                pinStep = 1 if pinTuple[1] >= pinTuple[0] else -1
                for i in range(pinTuple[0], pinTuple[1] + pinStep):
                    expandedPinNameList.append(f'{pinBaseName}<{i}>')
        return ' '.join(expandedPinNameList)
