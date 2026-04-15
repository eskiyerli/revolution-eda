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
from typing import Any, Optional

from PySide6.QtCore import QPoint



import revedaEditor.common.shapes as shp
import revedaEditor.backend.dataDefinitions as ddef
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

    def buildPositionMapping(self) -> dict:
        """Build mapping from schematic device IDs to layout positions."""
        self.schem_to_layout_pos = {}
        layout_devices = self.parser.get_layout_devices(self.layoutEditor.cellName)
        xref = self.parser.get_crossref(self.layoutEditor.cellName)

        if xref and layout_devices:
            layout_pos_by_id = {d["id"]: d.get("position") for d in layout_devices}
            for mapping in xref.get("mapping", {}).get("devices", []):
                layout_dev = mapping.get("layout_dev")
                schem_dev = mapping.get("schem_dev")
                if layout_dev in layout_pos_by_id and schem_dev is not None:
                    self.schem_to_layout_pos[schem_dev] = layout_pos_by_id[layout_dev]
        return self.schem_to_layout_pos

    def createTempSchematicEditor(self):
        """Create and return a temporary schematic editor."""
        import revedaEditor.backend.libBackEnd as libb

        tempViewFilePath = self.layoutEditor.cellItem.cellPath.joinpath(
            "lvs_schematic.json"
        )
        tempViewItem = None
        for row in range(self.layoutEditor.cellItem.rowCount()):
            childItem = self.layoutEditor.cellItem.child(row)
            if childItem and childItem.viewName == "lvs_schematic":
                tempViewItem = childItem
                break

        if tempViewItem is None:
            tempViewItem = libb.viewItem(tempViewFilePath)
            self.layoutEditor.cellItem.appendRow(tempViewItem)

        tempViewItemTuple = ddef.viewItemTuple(
            self.layoutEditor.libItem, self.layoutEditor.cellItem, tempViewItem
        )
        tempViewNameTuple = ddef.viewNameTuple(
            self.layoutEditor.libName, self.layoutEditor.cellName, tempViewItem.viewName
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
        layout_pos = self.schem_to_layout_pos.get(schem_dev_id)
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

    def generateSchematic(self, extracted: dict):
        """Generate the full schematic from extracted data."""
        self.buildPositionMapping()
        self.createTempSchematicEditor()
        if self.tempSchematicEditor is None:
            return None

        devices: Any = extracted.get("devices", [])
        if not isinstance(devices, list):
            self.logger.error("Extracted data has invalid 'devices' format.")
            devices = []

        for device in devices:
            if not isinstance(device, dict):
                self.logger.warning(f"Skipping malformed device entry: {device}")
                continue
            symbolItem = self.addDeviceToSchematic(device)
            if symbolItem:
                self.addDeviceNets(symbolItem, device)

        self.tempSchematicEditor.show()
        return self.tempSchematicEditor
