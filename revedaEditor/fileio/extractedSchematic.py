#     "Commons Clause" License Condition v1.0
#    #
#     The Software is provided to you by the Licensor under the License, as defined
#     below, subject to the following condition.
#  #
#     Without limiting other conditions in the License, the grant of rights under the
#     License will not include, and the License does not grant to you, the right to
#     Sell the Software.
#  #
#     For purposes of the foregoing, "Sell" means practicing any or all of the rights
#     granted to you under the License to provide to third parties, for a fee or other
#     consideration (including without limitation fees for hosting) a product or service whose value
#     derives, entirely or substantially, from the functionality of the Software. Any
#     license notice or attribution required by the License must also include this
#     Commons Clause License Condition notice.
#  #
#    Add-ons and extensions developed for this software may be distributed
#    under their own separate licenses.
#  #
#     Software: Revolution EDA
#     License: Mozilla Public License 2.0
#     Licensor: Revolution Semiconductor (Registered in the Netherlands)



import logging
import json
import pathlib
from typing import Any, Optional

from PySide6.QtCore import QPoint



import revedaEditor.common.shapes as shp
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.net as snet



SYMBOL_PIN_DISTANCE = 80
SYMBOL_STUB_LENGHT = 20


class klayoutSchematicGenerator:
    """Generates a temporary schematic from LVS extracted data."""

    def __init__(
        self,
        parser,
        layoutEditor,
        revedaMain,
        findSymbolViewNameTuple,
        logger: logging.Logger,
    ):
        self.parser = parser
        self.layoutEditor = layoutEditor
        self.revedaMain = revedaMain
        self.findSymbolViewNameTuple = findSymbolViewNameTuple
        self.logger = logger
        self.tempSchematicEditor = None
        self.schem_to_layout_pos = {}
        self._symbol_view_cache: dict[str, Optional[ddef.viewNameTuple]] = {}
        self._generated_hierarchy_cells: set[tuple[str, str]] = set()

    @staticmethod
    def _make_hashable(obj):
        return tuple(obj) if isinstance(obj, list) else obj

    @classmethod
    def _parse_source_netlist(
        cls, sourceNetlistPath: pathlib.Path | None
    ) -> dict[str, dict[str, Any]]:
        if sourceNetlistPath is None or not sourceNetlistPath.exists():
            return {}

        subckts: dict[str, dict[str, Any]] = {}
        current: dict[str, Any] | None = None

        with sourceNetlistPath.open("r", encoding="utf-8") as netlistFile:
            for rawLine in netlistFile:
                line = rawLine.strip()
                if not line or line.startswith("*"):
                    continue

                upperLine = line.upper()
                if upperLine.startswith(".SUBCKT"):
                    tokens = line.split()
                    if len(tokens) < 2:
                        current = None
                        continue
                    name = tokens[1]
                    current = {
                        "name": name,
                        "pins": tokens[2:],
                        "instances": {},
                    }
                    subckts[name.casefold()] = current
                    continue

                if upperLine.startswith(".ENDS"):
                    current = None
                    continue

                if current is None or not line[:1].upper() == "X":
                    continue

                tokens = line.split()
                if len(tokens) < 3:
                    continue

                instanceName = tokens[0][1:]
                callTokens = tokens[1:]
                cellIndex = next(
                    (
                        index
                        for index in range(len(callTokens) - 1, -1, -1)
                        if "=" not in callTokens[index]
                    ),
                    None,
                )
                if cellIndex is None:
                    continue

                cellName = callTokens[cellIndex]
                connections = callTokens[:cellIndex]
                current["instances"][instanceName] = {
                    "name": instanceName,
                    "cell_name": cellName,
                    "connections": connections,
                }

        return subckts

    @classmethod
    def _build_hierarchy_node(
        cls,
        cellName: str,
        groupedDevices: list[tuple[list[str], dict]],
        subcktMap: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        node = {
            "name": cellName,
            "instances": [],
            "primitive_devices": [],
            "source_device_ids": [],
        }

        nestedGroups: dict[str, list[tuple[list[str], dict]]] = {}
        for nameParts, device in groupedDevices:
            deviceId = device.get("id")
            if deviceId is not None:
                node["source_device_ids"].append(deviceId)

            if len(nameParts) <= 1:
                clonedDevice = dict(device)
                clonedDevice["name"] = (
                    nameParts[0] if nameParts else clonedDevice.get("name", "")
                )
                node["primitive_devices"].append(clonedDevice)
                continue

            prefix = nameParts[0]
            clonedDevice = dict(device)
            clonedDevice["name"] = ".".join(nameParts[1:])
            nestedGroups.setdefault(prefix, []).append((nameParts[1:], clonedDevice))

        subcktInfo = subcktMap.get(cellName.casefold(), {})
        subcktInstances = subcktInfo.get("instances", {})
        for instanceName, instanceInfo in subcktInstances.items():
            instanceDevices = nestedGroups.get(instanceName)
            if not instanceDevices:
                continue

            childCellName = instanceInfo.get("cell_name")
            childPins = subcktMap.get(childCellName.casefold(), {}).get("pins", [])
            connections = instanceInfo.get("connections", [])
            childNode = cls._build_hierarchy_node(childCellName, instanceDevices, subcktMap)
            node["instances"].append(
                {
                    "name": instanceName,
                    "cell_name": childCellName,
                    "terminals": dict(zip(childPins, connections)),
                    "source_device_ids": childNode["source_device_ids"],
                    "extracted": childNode,
                }
            )

        return node

    @classmethod
    def infer_hierarchical_extraction(
        cls,
        extracted: dict,
        sourceNetlistPath: pathlib.Path | None = None,
    ) -> dict:
        devices = extracted.get("devices", [])
        if not isinstance(devices, list) or not devices:
            return extracted

        if not any(
            isinstance(device.get("name"), str) and "." in device.get("name", "")
            for device in devices
            if isinstance(device, dict)
        ):
            return extracted

        subcktMap = cls._parse_source_netlist(sourceNetlistPath)
        topCellName = extracted.get("name", "")
        topSubckt = subcktMap.get(str(topCellName).casefold())
        if not topSubckt:
            return extracted

        topInstances = topSubckt.get("instances", {})
        groupedDevices: dict[str, list[tuple[list[str], dict]]] = {}
        primitiveDevices: list[dict] = []
        primitiveDeviceIds: list[Any] = []

        for device in devices:
            if not isinstance(device, dict):
                continue
            deviceName = device.get("name", "")
            if not isinstance(deviceName, str) or "." not in deviceName:
                primitiveDevices.append(device)
                if device.get("id") is not None:
                    primitiveDeviceIds.append(device.get("id"))
                continue

            nameParts = [part for part in deviceName.split(".") if part]
            if len(nameParts) < 2 or nameParts[0] not in topInstances:
                primitiveDevices.append(device)
                if device.get("id") is not None:
                    primitiveDeviceIds.append(device.get("id"))
                continue

            groupedDevices.setdefault(nameParts[0], []).append((nameParts[1:], device))

        if not groupedDevices:
            return extracted

        inferredInstances = []
        for instanceName, instanceInfo in topInstances.items():
            instanceDevices = groupedDevices.get(instanceName)
            if not instanceDevices:
                continue

            childCellName = instanceInfo.get("cell_name")
            childPins = subcktMap.get(childCellName.casefold(), {}).get("pins", [])
            connections = instanceInfo.get("connections", [])
            childNode = cls._build_hierarchy_node(childCellName, instanceDevices, subcktMap)
            inferredInstances.append(
                {
                    "name": instanceName,
                    "cell_name": childCellName,
                    "terminals": dict(zip(childPins, connections)),
                    "source_device_ids": childNode["source_device_ids"],
                    "extracted": childNode,
                }
            )

        if not inferredInstances:
            return extracted

        enrichedExtracted = dict(extracted)
        enrichedExtracted["primitive_devices"] = primitiveDevices
        enrichedExtracted["primitive_device_ids"] = primitiveDeviceIds
        enrichedExtracted["instances"] = inferredInstances
        return enrichedExtracted

    def buildPositionMapping(self) -> dict:
        """Build mapping from schematic device IDs to layout positions."""
        self.schem_to_layout_pos = {}
        layout_devices = self.parser.get_layout_devices(self.layoutEditor.cellName)
        xref = self.parser.get_crossref(self.layoutEditor.cellName)

        if xref and layout_devices:
            layout_pos_by_id = {
                self._make_hashable(d["id"]): d.get("position") for d in layout_devices
            }
            for mapping in xref.get("mapping", {}).get("devices", []):
                layout_dev = self._make_hashable(mapping.get("layout_dev"))
                schem_dev = self._make_hashable(mapping.get("schem_dev"))
                if layout_dev in layout_pos_by_id and schem_dev is not None:
                    self.schem_to_layout_pos[schem_dev] = layout_pos_by_id[layout_dev]
        return self.schem_to_layout_pos

    def _findCellItem(self, cellName: str):
        libItem = libm.getLibItem(self.revedaMain.libraryModel, self.layoutEditor.libName)
        cellItem = libm.getCellItem(libItem, cellName)
        if cellItem is not None:
            return libItem, cellItem

        normalizedCellName = cellName.casefold()
        if libItem is not None:
            for row in range(libItem.rowCount()):
                candidateCellItem = libItem.child(row)
                if (
                    candidateCellItem is not None
                    and hasattr(candidateCellItem, "cellName")
                    and str(candidateCellItem.cellName).casefold() == normalizedCellName
                ):
                    return libItem, candidateCellItem

        root = self.revedaMain.libraryModel.invisibleRootItem()
        for row in range(root.rowCount()):
            candidateLibItem = root.child(row)
            candidateCellItem = libm.getCellItem(candidateLibItem, cellName)
            if candidateCellItem is not None:
                return candidateLibItem, candidateCellItem
            for cellRow in range(candidateLibItem.rowCount()):
                candidateCellItem = candidateLibItem.child(cellRow)
                if (
                    candidateCellItem is not None
                    and hasattr(candidateCellItem, "cellName")
                    and str(candidateCellItem.cellName).casefold() == normalizedCellName
                ):
                    return candidateLibItem, candidateCellItem
        return None, None

    def createTempSchematicEditor(self, cellName: str | None = None):
        """Create and return a temporary schematic editor."""
        targetCellName = cellName or self.layoutEditor.cellName
        libItem, cellItem = self._findCellItem(targetCellName)
        if cellItem is None or libItem is None:
            self.logger.error(
                f"Could not find cell for extracted schematic generation: {targetCellName}"
            )
            return None

        tempViewFilePath = cellItem.cellPath.joinpath("lvs_schematic.json")
        tempViewItem = None
        for row in range(cellItem.rowCount()):
            childItem = cellItem.child(row)
            if childItem and childItem.viewName == "lvs_schematic":
                tempViewItem = childItem
                break

        if tempViewItem is None:
            tempViewItem = libb.viewItem(tempViewFilePath)
            cellItem.appendRow(tempViewItem)

        tempViewItemTuple = ddef.viewItemTuple(
            libItem, cellItem, tempViewItem
        )
        tempViewNameTuple = ddef.viewNameTuple(
            libItem.libraryName, cellItem.cellName, tempViewItem.viewName
        )
        existingEditor = self.revedaMain.openViews.get(tempViewNameTuple)
        if existingEditor:
            existingEditor.close()

        self._initializeTempSchematicFile(tempViewFilePath)

        self.revedaMain.libraryBrowser.designView.createNewCellView(tempViewItemTuple)

        self.tempSchematicEditor = self.revedaMain.openViews.get(tempViewNameTuple)
        if self.tempSchematicEditor is None:
            self.logger.error("Could not create temporary schematic editor.")
        return self.tempSchematicEditor

    def _initializeTempSchematicFile(self, filePath):
        """Initialize temp view file with an empty valid schematic payload."""
        emptySchematic = [
            {"viewType": "schematic"},
            {"snapGrid": (20, 10)},
        ]
        with filePath.open("w", encoding="utf-8") as f:
            json.dump(emptySchematic, f, indent=2)

    def _resolveSymbolView(self, deviceType: str) -> Optional[ddef.viewNameTuple]:
        if deviceType not in self._symbol_view_cache:
            self._symbol_view_cache[deviceType] = self.findSymbolViewNameTuple(
                deviceType, self.revedaMain.libraryModel
            )
        return self._symbol_view_cache[deviceType]

    def _getScene(self):
        if not self.tempSchematicEditor:
            return None
        return self.tempSchematicEditor.centralW.scene

    def _getMappedLayoutPosition(self, deviceId: Any):
        if deviceId is None:
            return None
        return self.schem_to_layout_pos.get(self._make_hashable(deviceId))

    def _getAggregateLayoutPosition(self, deviceIds: list[Any]) -> Any:
        if not deviceIds:
            return None

        positions = [self._getMappedLayoutPosition(deviceId) for deviceId in deviceIds]
        positions = [position for position in positions if position is not None]
        if not positions:
            return None

        xs = []
        ys = []
        for position in positions:
            if isinstance(position, dict):
                xValue = position.get("x")
                yValue = position.get("y")
            elif isinstance(position, (list, tuple)) and len(position) >= 2:
                xValue = position[0]
                yValue = position[1]
            else:
                continue

            try:
                xs.append(float(xValue))
                ys.append(float(yValue))
            except (TypeError, ValueError):
                continue

        if not xs or not ys:
            return positions[0]

        return {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}

    def _toScenePlacement(self, layout_pos, snapToGrid) -> Optional[QPoint]:
        """Convert parser position payload to schematic scene coordinates."""
        if layout_pos is None:
            return None

        try:
            if isinstance(layout_pos, dict):
                x_raw = layout_pos.get("x")
                y_raw = layout_pos.get("y")
            elif isinstance(layout_pos, (list, tuple)) and len(layout_pos) >= 2:
                x_raw = layout_pos[0]
                y_raw = layout_pos[1]
            else:
                return None

            x = int(round(float(x_raw) / 5))
            y = int(round(float(y_raw) / 5))
            return snapToGrid(QPoint(x, y))
        except (TypeError, ValueError):
            return None

    def addDeviceToSchematic(self, device: dict):
        """Add a single device (symbol instance) to the schematic."""
        scene = self._getScene()
        if scene is None:
            self.logger.error("Temporary schematic editor scene is not available.")
            return None

        deviceType = device.get("type")
        if not deviceType:
            self.logger.warning(f"Skipping device without type: {device}")
            return None

        symbolViewNameTuple = self._resolveSymbolView(deviceType)
        if symbolViewNameTuple is None:
            self.logger.warning(f"Could not find symbol for device: {device}")
            return None

        schem_dev_id = device.get("id")
        layout_pos = self._getMappedLayoutPosition(schem_dev_id)
        if layout_pos is None:
            layout_pos = self._getAggregateLayoutPosition(device.get("source_device_ids", []))
        snapToGrid = scene.snapToGrid
        targetPos = self._toScenePlacement(layout_pos, snapToGrid)

        if targetPos is None and layout_pos is not None:
            self.logger.warning(
                f"Invalid layout position for device {schem_dev_id}: {layout_pos}"
            )

        symbolItem = scene.instSymbol(symbolViewNameTuple, targetPos or QPoint(0, 0))

        if symbolItem is None:
            self.logger.warning(f"Could not instantiate symbol for device: {device}")
            return None

        symbolItem.instanceName = device.get("name", str(schem_dev_id or "I0"))
        if "@instName" in symbolItem.labels:
            symbolItem.labels["@instName"].labelDefs()
        if targetPos is not None:
            symbolItem.setPos(targetPos)
        scene.addItem(symbolItem)
        return symbolItem

    def _generateChildHierarchicalViews(self, instances: list[dict]):
        for instance in instances:
            childExtracted = instance.get("extracted")
            childCellName = instance.get("cell_name")
            if not isinstance(childExtracted, dict) or not childCellName:
                continue

            cacheKey = (self.layoutEditor.libName, childCellName)
            if cacheKey not in self._generated_hierarchy_cells:
                self._generated_hierarchy_cells.add(cacheKey)
                self.generateSchematic(childExtracted, _show=False)

    def createPinNet(
        self, pinItem, symbolItem: shp.schematicSymbol, device: dict
    ) -> "snet.schematicNet":
        """Create a schematic net for a device pin based on pin side."""
        localPos = pinItem.start
        pinScenePos = pinItem.mapToScene(localPos)
        br = symbolItem.boundingRect()
        center = br.center()
        dx = localPos.x() - center.x()
        dy = localPos.y() - center.y()

        if abs(dx) > abs(dy):
            side = "left" if dx < 0 else "right"
        else:
            side = "top" if dy < 0 else "bottom"

        if side == "left":
            pinNetItem = snet.schematicNet(pinScenePos, pinScenePos - QPoint(30, 0), 1, 0)
        elif side == "right":
            pinNetItem = snet.schematicNet(pinScenePos, pinScenePos + QPoint(30, 0), 1, 0)
        elif side == "top":
            pinNetItem = snet.schematicNet(pinScenePos, pinScenePos - QPoint(0, 30), 1, 0)
        else:  # bottom
            pinNetItem = snet.schematicNet(pinScenePos, pinScenePos + QPoint(0, 30), 1, 0)

        terminals = device.get("terminals", {})
        name = terminals.get(pinItem.pinName) if isinstance(terminals, dict) else None
        if name:
            pinNetItem.name = name
        return pinNetItem

    def addDeviceNets(self, symbolItem, device: dict):
        """Add nets for all pins of a device."""
        scene = self._getScene()
        if scene is None:
            self.logger.error("Temporary schematic editor scene is not available.")
            return

        for pinItem in symbolItem.pins.values():
            pinNetItem = self.createPinNet(pinItem, symbolItem, device)
            scene.addItem(pinNetItem)

    def generateSchematic(
        self,
        extracted: dict,
        sourceNetlistPath: pathlib.Path | None = None,
        _show: bool = True,
    ):
        """Generate the full schematic from extracted data."""
        extracted = self.infer_hierarchical_extraction(extracted, sourceNetlistPath)
        self.buildPositionMapping()
        targetCellName = extracted.get("name", self.layoutEditor.cellName)
        self.createTempSchematicEditor(targetCellName)
        if self.tempSchematicEditor is None:
            return None

        if not _show:
            self.tempSchematicEditor.hide()

        # Save reference to this cell's editor BEFORE recursive child calls,
        # because _generateChildHierarchicalViews() will overwrite self.tempSchematicEditor.
        currentEditor = self.tempSchematicEditor

        hierarchicalInstances: Any = extracted.get("instances", [])
        if not isinstance(hierarchicalInstances, list):
            hierarchicalInstances = []

        self._generateChildHierarchicalViews(hierarchicalInstances)

        # Restore this cell's editor after child views have been generated.
        self.tempSchematicEditor = currentEditor

        devices: Any = extracted.get("primitive_devices", extracted.get("devices", []))
        if not isinstance(devices, list):
            self.logger.error("Extracted data has invalid 'devices' format.")
            devices = []

        for instance in hierarchicalInstances:
            if not isinstance(instance, dict):
                continue
            hierarchicalDevice = {
                "id": None,
                "name": instance.get("name", ""),
                "type": instance.get("cell_name", ""),
                "terminals": instance.get("terminals", {}),
                "source_device_ids": instance.get("source_device_ids", []),
            }
            symbolItem = self.addDeviceToSchematic(hierarchicalDevice)
            if symbolItem:
                self.addDeviceNets(symbolItem, hierarchicalDevice)

        for device in devices:
            if not isinstance(device, dict):
                self.logger.warning(f"Skipping malformed device entry: {device}")
                continue
            symbolItem = self.addDeviceToSchematic(device)
            if symbolItem:
                self.addDeviceNets(symbolItem, device)

        if _show:
            self.tempSchematicEditor.show()
        return self.tempSchematicEditor
