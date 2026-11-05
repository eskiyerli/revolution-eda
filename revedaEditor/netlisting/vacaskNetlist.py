# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

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
import io
import json
import os
import pathlib
import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.shapes as shp
from revedaEditor.netlisting import exprSupport, vacaskFormat
from revedaEditor.netlisting.baseNetlist import NetlistBase
from revedaEditor.scenes.schematicScene import schematicScene

if TYPE_CHECKING:
    from revedaEditor.gui.schematicEditor import schematicEditor


class vacaskNetlist(NetlistBase):
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
    # netlist line inside the hot loop.  ``$`` is allowed as a parameter-name prefix so
    # VACASK system parameters such as ``$mfactor`` are cleaned up as well.
    # The Qt-free formatting implementation lives in ``vacaskFormat``;
    # the constants are kept here as aliases for backwards compatibility.
    _PARAM_RE = vacaskFormat.PARAM_RE
    _MODEL_STMT_RE = vacaskFormat.MODEL_STMT_RE
    _INCLUDE_STMT_RE = vacaskFormat.INCLUDE_STMT_RE
    _INCLUDE_SECTION_RE = vacaskFormat.INCLUDE_SECTION_RE
    _FOREIGN_INCLUDE_RE = vacaskFormat.FOREIGN_INCLUDE_RE
    _SECTION_RE = vacaskFormat.SECTION_RE
    _ENDSECTION_RE = vacaskFormat.ENDSECTION_RE
    _MAX_INCLUDE_DEPTH = vacaskFormat.MAX_INCLUDE_DEPTH

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
        # Directive collection (ground/global nets, includes, loads,
        # models) is owned by the Qt-free DeckCollector; the familiar
        # attribute names alias its members so existing readers keep
        # working unchanged.
        self._deck = vacaskFormat.DeckCollector()
        self.includeLines = self._deck.includeLines
        self.vahdlLines = self._deck.vahdlLines
        self.loadLines = self._deck.loadLines
        self.groundNets = self._deck.globals.groundNets
        self.globalNets = self._deck.globals.globalNets
        # (lib, cell, view) -> {exprName: default} implicit-terminal defs.
        self._exprDefsCache: dict[tuple, dict] = {}
        self.modelLines = self._deck.modelLines
        self._modelDefs = self._deck._model_defs
        self._includeFilePaths = self._deck._include_file_paths
        self.osdiLoadLines = self._deck.osdiLoadLines
        self.includeLibLines = self._deck.includeLibLines
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

            # Included files may already define models collected from
            # symbol attributes — drop the redundant local definitions.
            self._suppressIncludeDefinedModels()

            # Write global directive with collected non-ground global net names.
            globalNets = " ".join(
                sorted(vacaskNetlist._quoteId(n) for n in self.globalNets)
            )
            if globalNets:
                cirFile.write(f"global {globalNets}\n\n")

            # Write ground directive with collected ground net names (once).
            groundNets = " ".join(
                sorted(vacaskNetlist._quoteId(n) for n in self.groundNets)
            )
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
        # Terminal mode: this scene's net expressions resolve to their
        # expression names — each is an implicit subcircuit terminal.
        schematicScene.nameSceneNets(netSet=exprSupport.terminalNetSet(
            schematicScene.collectNetExprNames()))
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
                    exprDefs = self._exprDefsFor(elementSymbol, cellItem,
                                                 netlistView)
                    exprNets = exprSupport.exprNetsForInstance(
                        elementSymbol, exprDefs)
                    lines = self.createVacaskSymbolLine(elementSymbol,
                                                        exprNets=exprNets)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    if not self._isStopView(netlistView):
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
                            schematicObj.loadSchematic(register=False)
                            expandedPinsString = self.expandPinNames(
                                list(elementSymbol.pinNetMap.keys())
                            )
                            terminals = exprSupport.exprTerminals(exprDefs)
                            if terminals:
                                expandedPinsString += " " + " ".join(
                                    terminals)
                            subcktContent: list[str] = []
                            self.collectSubcircuitContent(schematicObj, subcktContent)
                            # Build parameters line from NLP labels using default values
                            subcktParams = self._getSubcktParams(elementSymbol)
                            paramsLine = ""
                            if subcktParams:
                                paramsLine = "parameters " + " ".join(
                                    f"{name}={defVal}" for name, _, defVal in subcktParams
                                ) + "\n"
                            subcktDef = (
                                f"subckt {schematicObj.cellName} ( {expandedPinsString} )\n"
                                + paramsLine
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
                elif ("vacask" in netlistView or "spectre" in netlistView
                      or "spef" in netlistView):
                    lines = self.createTextViewLine(elementSymbol, cellItem,
                                                    netlistView)
                    content.extend(lines if isinstance(lines, list) else [lines])
                    self._collectModelLoadInfo(elementSymbol)
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
            topExprDefs = schematicEdObj.centralW.scene.collectNetExprNames()
            topTerminals = exprSupport.exprTerminals(topExprDefs)
            if topTerminals:
                expandedPinsString += " " + " ".join(topTerminals)

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

    def _processGlobalNet(self, netName: str) -> str:
        """Strip trailing ``!`` from global nets and register directives.

        ``gnd!`` becomes ``gnd`` and lands in :attr:`groundNets` for the
        ``ground 0`` directive; other ``x!`` nets drop the ``!`` and join
        :attr:`globalNets` for the ``global`` directive.
        """
        return self._deck.process_global_net(netName)

    def _collectModelLoadInfo(
        self, elementSymbol: shp.schematicSymbol, skipLoadFile: bool = False
    ):
        """Collect model, load, and include-library directives from attributes.

        Reads ``VacaskModelLine``, ``VacaskLoadFile``, ``VacaskIncludeLib``
        and ``VacaskIncludeFile`` from *elementSymbol.symattrs* into the
        deck collector.  ``VacaskIncludeFile`` is resolved relative to the
        cell directory; everything else delegates to
        :meth:`DeckCollector.collect_symbol_directives`.
        """
        cell_dir = None
        if elementSymbol.symattrs.get("VacaskIncludeFile"):
            cellItem = self._getCellItem(
                elementSymbol.libraryName, elementSymbol.cellName
            )
            if cellItem is not None:
                cell_dir = pathlib.Path(cellItem.cellPath)
        self._deck.collect_symbol_directives(
            elementSymbol.symattrs, cell_dir=cell_dir,
            skip_load_file=skipLoadFile,
            base_dirs=(self.filePathObj.parent,))

    def _addModelLine(self, modelLine: str):
        """Register a ``model`` statement, deduplicating on the model name."""
        self._deck.add_model_line(modelLine,
                                  warn=self._scene.logger.warning)

    @staticmethod
    def _modelName(modelLine: str) -> str:
        """Model name declared by a ``model`` statement line."""
        return vacaskFormat.model_name(modelLine)

    def _resolveIncludePath(
        self, includeName: str, *extraBases: pathlib.Path
    ) -> pathlib.Path | None:
        """Resolve an ``include`` file name to a readable local path."""
        return vacaskFormat.resolve_include_file(
            includeName, *extraBases, self.filePathObj.parent)

    def _addIncludeFile(self, filePath: pathlib.Path) -> None:
        """Register an ``include`` directive for a local file."""
        self._deck.add_include_file(filePath)

    def _suppressIncludeDefinedModels(self):
        """Drop model lines already defined inside an included file."""
        self._deck.suppress_include_defined_models(
            info=self._scene.logger.info,
            base_dirs=(self.filePathObj.parent,))

    @staticmethod
    def _getSubcktParams(elementSymbol: shp.schematicSymbol) -> list[tuple[str, str, str]]:
        """Extract NLP label parameters suitable for subcircuit parameter declaration.

        Returns a list of (paramName, instanceValue, defaultValue) tuples for all
        NLP labels that are NOT predefined (instName, cellName, etc.).

        These are used to build the ``parameters`` line inside the subcircuit
        definition (with default values).  The instance line is fully handled by
        the VacaskNetlistLine template — no extra appending is done here.

        If a value is wrapped in ``{...}``, the braces are stripped for output.

        Args:
            elementSymbol: The symbol instance to extract parameters from.

        Returns:
            List of (name, instanceValue, defaultValue) tuples for subcircuit parameters.
        """
        predefinedNames = {
            "@instName", "@cellName", "@libName",
            "@viewName", "@modelName", "@elementNum",
        }
        params: list[tuple[str, str, str]] = []
        for label in elementSymbol.labels.values():
            if label.labelType != "NLPLabel":
                continue
            if label.labelName in predefinedNames:
                continue
            paramName = label.labelName.lstrip("@")
            if not paramName:
                continue
            # Strip braces if present (expression marker)
            value = label.labelValue.strip() if label.labelValue else ""
            if value.startswith("{") and value.endswith("}"):
                instanceValue = value[1:-1].strip()
            else:
                instanceValue = value
            # Extract default value from the label definition
            defaultValue = (
                vacaskFormat.nlp_label_default(label.labelDefinition)
                or instanceValue)
            params.append((paramName, instanceValue, defaultValue))
        return params

    def createItemLine(
        self,
        cirFile,
        elementSymbol: shp.schematicSymbol,
        cellItem: libb.cellItem,
        netlistView: str,
    ):
        """Create the appropriate VACASK netlist line(s) for a symbol based on its view type."""
        if "schematic" in netlistView:
            exprDefs = self._exprDefsFor(elementSymbol, cellItem,
                                         netlistView)
            exprNets = exprSupport.exprNetsForInstance(elementSymbol,
                                                       exprDefs)
            elementLines = self.createVacaskSymbolLine(elementSymbol,
                                                       exprNets=exprNets)
            for line in elementLines:
                cirFile.write(f"{line}\n")

            if not self._isStopView(netlistView):
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
                    schematicObj.loadSchematic(register=False)
                    expandedPinsString = self.expandPinNames(
                        list(elementSymbol.pinNetMap.keys())
                    )
                    terminals = exprSupport.exprTerminals(exprDefs)
                    if terminals:
                        expandedPinsString += " " + " ".join(terminals)
                    subcktContent: list[str] = []
                    self.collectSubcircuitContent(schematicObj, subcktContent)
                    # Build parameters line from NLP labels using default values
                    subcktParams = self._getSubcktParams(elementSymbol)
                    paramsLine = ""
                    if subcktParams:
                        paramsLine = "parameters " + " ".join(
                            f"{name}={defVal}" for name, _, defVal in subcktParams
                        ) + "\n"
                    subcktDef = (
                        f"\nsubckt {schematicObj.cellName} ( {expandedPinsString} )\n"
                        + paramsLine
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
        elif ("vacask" in netlistView or "spectre" in netlistView
              or "spef" in netlistView):
            textLines = self.createTextViewLine(elementSymbol, cellItem,
                                                netlistView)
            for line in textLines:
                cirFile.write(f"{line}\n")
            self._collectModelLoadInfo(elementSymbol)

    def _createNetlistLine(
        self,
        elementSymbol: shp.schematicSymbol,
        netlistLineKey: str,
        exprNets: list = None,
    ) -> list[str]:
        """Shared netlist line creation logic.

        Handles array notation, attribute substitution, and pin ordering.
        This is the core netlisting logic used by all netlist formats.

        Args:
            elementSymbol: The symbol instance to create netlist lines for.
            netlistLineKey: The attribute key for the netlist line template
                (e.g. ``"VacaskNetlistLine"`` or ``"lvsNetlistLine"``).
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
            if netlistLineKey not in (elementSymbol.symattrs or {}):
                raise KeyError(netlistLineKey)

            ir = vacaskFormat.InstanceIR(
                name=instNameLabel.labelValue.strip(),
                attrs=dict(elementSymbol.symattrs or {}),
                labels={
                    lbl.labelName: lbl.labelValue
                    for lbl in elementSymbol.labels.values()
                },
                pinNets=list(elementSymbol.pinNetMap.items()),
                exprNets=list(exprNets or ()),
            )
            return vacaskFormat.format_instance_lines(
                ir, netlistLineKey,
                globals_tracker=self._deck.globals,
                warn=self._scene.logger.warning)

        except Exception as e:
            self._scene.logger.error(
                f"Error creating netlist line for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    def createVacaskSymbolLine(
        self, elementSymbol: shp.schematicSymbol, exprNets: list = None
    ) -> list[str]:
        """Create VACASK netlist lines for a symbol instance.

        In LVS mode uses the ``lvsNetlistLine`` attribute, otherwise uses
        ``VacaskNetlistLine``.  ``exprNets`` carries the resolved
        implicit-terminal nets when the instance expands to a subcircuit
        with net expressions.
        """
        netlistLineKey = "lvsNetlistLine" if self._lvsMode else "VacaskNetlistLine"
        return self._createNetlistLine(elementSymbol, netlistLineKey,
                                       exprNets=exprNets)

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
            netlistView = self.determineNetlistView(elementSymbol, cellItem)
            incFilePath = libb.textViewFilePath(
                cellItem, libm.getViewItem(cellItem, netlistView))
            if incFilePath is None:
                incFilePath = pathlib.Path(cellPath) / f"{elementSymbol.cellName}.sp"
            self._addIncludeFile(incFilePath)
            return spiceLines
        except Exception as e:
            self._scene.logger.error(
                f"Vacask subckt netlist error for {elementSymbol.instanceName}: {e}"
            )
            return [
                f"// Netlist line is not defined for symbol of {elementSymbol.instanceName}"
            ]

    def createTextViewLine(self, elementSymbol: shp.schematicSymbol,
                           cellItem: libb.cellItem, netlistView: str) -> list[str]:
        """Create netlist lines for an instance bound to a file-backed text view.

        Emits the instance line and pulls the view's netlist file in once via
        an ``include`` directive. Used for vacask/spectre/spef views selected
        through the switch list or a config view (e.g. PEX-extracted
        netlists, which are complete subcircuits named after the cell).
        """
        try:
            symbolLines = self.createVacaskSymbolLine(elementSymbol)
            viewItem = libm.getViewItem(cellItem, netlistView)
            filePath = libb.textViewFilePath(cellItem, viewItem)
            if filePath is not None:
                self._addIncludeFile(filePath)
            else:
                self._scene.logger.warning(
                    f"View '{netlistView}' of {elementSymbol.cellName} has no "
                    f"netlist file"
                )
            return symbolLines
        except Exception as e:
            self._scene.logger.error(
                f"Text view netlist error for {elementSymbol.instanceName}: {e}"
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
    def _quoteId(name: str) -> str:
        """Quote a bus-tap identifier with single quotes (see vacaskFormat)."""
        return vacaskFormat.quote_id(name)

    @staticmethod
    def _formatExpandedPin(pinName: str) -> str:
        """VACASK quotes bus identifiers; see :meth:`_quoteId`.

        Overrides the identity hook used by
        :meth:`NetlistBase.expandPinNames`.
        """
        return vacaskNetlist._quoteId(pinName)

    # parseArrayNotation / expandPinNames / _getCellItem /
    # determineNetlistView / _findViewFromSwitchList / _isStopView and the
    # switch/stop/config view properties are inherited from NetlistBase.
