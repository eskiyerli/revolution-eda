# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Shared helpers for the schematic netlisters.

``NetlistBase`` collects the logic that is genuinely identical across the
Spectre, VACASK and Xyce netlisters so a fix lands in one place instead of
three (the descending-bus ``range()`` bug is exactly the kind of divergence
this prevents).

Simulator-specific formatting — ``writeNetlist``, ``_createNetlistLine``,
the ``create*Line`` family, and directive ordering — is intentionally *not*
here; it lives in each subclass. Two helpers that have legitimately diverged
expose override hooks rather than being forced into one shape:

* ``expandPinNames`` calls :meth:`_formatExpandedPin` per expanded pin so
  VACASK can quote bus identifiers while Spectre/Xyce pass them through.
* ``_findViewFromSwitchList`` here is the plain "first available matching
  view" rule used by Spectre and VACASK; Xyce overrides it to honour
  ``stopViewList``.

Subclasses are expected to initialise these instance attributes in their
own ``__init__``: ``_switchViewList``, ``_stopViewList``, ``_configDict``,
``_useConfig``, ``_lvsMode``, ``libraryView``, ``_cellItemCache`` and
``_viewNameCache``.
"""

from __future__ import annotations

import functools
from typing import List

import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm


class NetlistBase:
    """Mixin of netlister logic shared verbatim across simulators."""

    # ------------------------------------------------------------------
    # View-switch configuration
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
    # Array-notation helpers
    # ------------------------------------------------------------------
    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
        """Parse array notation like ``'name<0:5>'`` into base name and range.

        Also handles single-index notation like ``'name<0>'``.

        Returns:
            ``(base_name, (start, end))``. For scalar names, returns
            ``(name, (-1, -1))``.

        Examples:
            >>> NetlistBase.parseArrayNotation("net<0:3>")
            ('net', (0, 3))
            >>> NetlistBase.parseArrayNotation("bus<5>")
            ('bus', (5, 5))
            >>> NetlistBase.parseArrayNotation("scalar")
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
    def _formatExpandedPin(pinName: str) -> str:
        """Format a single expanded pin name for the target netlist syntax.

        Default is identity (Spectre/Xyce). VACASK overrides this to quote
        bus identifiers. Implemented as a classmethod dispatch target so
        ``expandPinNames`` works as both an instance and a class-level call.
        """
        return pinName

    @classmethod
    def expandPinNames(cls, pinNamesList: List[str]) -> str:
        """Expand a list of pin names, expanding array notation into pins.

        Ascending (``a<0:1>``) and descending (``a<1:0>``) ranges are both
        honoured via an explicit ``range`` step. ``cls._formatExpandedPin``
        dispatches to the subclass's per-simulator formatting.

        Example:
            >>> NetlistBase.expandPinNames(["a<0:1>", "b"])
            'a<0> a<1> b'
        """
        expandedPinNameList: list[str] = []
        for pinName in pinNamesList:
            pinBaseName, pinTuple = cls.parseArrayNotation(pinName)
            if pinTuple[0] == pinTuple[1] == -1:
                expandedPinNameList.append(cls._formatExpandedPin(pinBaseName))
            else:
                pinStep = 1 if pinTuple[1] >= pinTuple[0] else -1
                for i in range(pinTuple[0], pinTuple[1] + pinStep, pinStep):
                    expandedPinNameList.append(
                        cls._formatExpandedPin(f'{pinBaseName}<{i}>'))
        return ' '.join(expandedPinNameList)

    # ------------------------------------------------------------------
    # Cell/view resolution
    # ------------------------------------------------------------------
    def _getCellItem(self, libraryName: str,
                     cellName: str) -> "libb.cellItem | None":
        """Return the cellItem for *(libraryName, cellName)*, cached.

        Returns ``None`` if the cell is not found in the library.
        """
        key = (libraryName, cellName)
        if key not in self._cellItemCache:
            libItem = libm.getLibItem(self.libraryView.libraryModel, libraryName)
            self._cellItemCache[key] = libm.getCellItem(libItem, cellName)
        return self._cellItemCache[key]

    def determineNetlistView(self, elementSymbol, cellItem) -> str:
        """Determine which view to use for netlisting a symbol instance.

        Uses *configDict* in config mode, otherwise falls back to
        *switchViewList* via :meth:`_findViewFromSwitchList`.
        """
        cacheKey = (elementSymbol.libraryName, elementSymbol.cellName)
        if cacheKey in self._viewNameCache:
            return self._viewNameCache[cacheKey]

        viewItems = [cellItem.child(row) for row in range(cellItem.rowCount())]

        if self._useConfig and self.configDict:
            config_entry = self.configDict.get(elementSymbol.cellName)
            if config_entry:
                if config_entry[0] == elementSymbol.libraryName:
                    result = config_entry[1]
                else:
                    # Library mismatch, fall back to switchViewList
                    result = self._findViewFromSwitchList(viewItems)
            else:
                # Cell not in config, fall back to switchViewList
                result = self._findViewFromSwitchList(viewItems)
        else:
            # Not using config or config dict is empty
            result = self._findViewFromSwitchList(viewItems)

        self._viewNameCache[cacheKey] = result
        return result

    def _findViewFromSwitchList(self, viewItems: list) -> str:
        """Find the first available matching view from switchViewList.

        switchViewList holds view *types* (e.g. "schematic", "symbol")
        matched against each view item's viewType, so a view like
        "schematic2" is covered by the "schematic" type. The switch-list
        order defines priority. Returns "symbol" if none match.

        Note: this base rule does not consult ``stopViewList`` — Xyce
        overrides it to do so.
        """
        viewNameByType = {}
        for viewItem in viewItems:
            if (viewItem.viewType not in viewNameByType
                    or viewItem.viewName == viewItem.viewType):
                viewNameByType[viewItem.viewType] = viewItem.viewName
        for viewType in self._switchViewList:
            if viewType in viewNameByType:
                return viewNameByType[viewType]
        return "symbol"

    def _isStopView(self, viewName: str) -> bool:
        """Check whether a view name belongs to a stop view type.

        View types are matched as substrings of the view name, the same way
        viewItem.viewType is derived from the file stem.
        """
        return any(stopType in viewName for stopType in self._stopViewList)
