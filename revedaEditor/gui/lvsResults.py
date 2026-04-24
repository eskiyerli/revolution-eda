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

from collections import Counter, defaultdict
import re
from typing import Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPen,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import revedaEditor.backend.LVSModelView as lvsmv
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.fileio.importlvsdb import LVSDBParser, LVSErrorRect

# from dotenv import load_dotenv

process = importPDKModule("process")


class lvsResultsDialogue(QDialog):
    _DEVICE_HIGHLIGHT_SIZE = 600  # half-width/height in layout units for device highlight rect

    def __init__(self, parent, nets: list, devices: list, cells: Optional[list] = None, parser=None,
                 crossrefs: Optional[list] = None, schem_nets: Optional[list] = None,
                 schem_devices: Optional[list] = None, schematic_editor=None):
        super().__init__(parent)
        self.layoutEditor = parent
        self.parser = parser
        self.schematicEditor = schematic_editor
        self._lvs_transform: tuple[float, float, int] | None = None
        self._schematic_highlight_rects: list = []
        self._schematic_highlighted_nets: set = set()
        self.mismatchSummaryLabel: QLabel | None = None
        self.mismatchDetailsBox: QPlainTextEdit | None = None
        self._current_layout_cell: str | None = None
        self._current_schem_cell: str | None = None
        self._highlight_colors = [
            QColor("#e11d48"),  # Red
            QColor("#0ea5e9"),  # Blue
            QColor("#10b981"),  # Green
            QColor("#f59e0b"),  # Amber
            QColor("#8b5cf6"),  # Purple
            QColor("#ec4899"),  # Pink
            QColor("#06b6d4"),  # Cyan
            QColor("#f97316"),  # Orange
            QColor("#6366f1"),  # Indigo
            QColor("#14b8a6"),  # Teal
            QColor("#d946ef"),  # Fuchsia
            QColor("#3b82f6"),  # Deep Blue
            QColor("#eab308"),  # Yellow
            QColor("#84cc16"),  # Lime
            QColor("#a855f7"),  # Violet
            QColor("#0891b2"),  # Cyan Dark
        ]
        self._highlight_color_index = 0
        self._net_color_by_signature: dict[tuple, QColor] = {}

        self.setWindowTitle("Revolution EDA LVS Results Dialogue")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        layout = QVBoxLayout()

        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(*self._build_summary_tab(crossrefs))
        self.tabWidget.addTab(*self._build_nets_tab(nets))
        self.tabWidget.addTab(*self._build_devices_tab(devices))
        self.tabWidget.addTab(*self._build_schem_nets_tab(schem_nets))
        self.tabWidget.addTab(*self._build_schem_devices_tab(schem_devices))
        self.tabWidget.addTab(*self._build_cells_tab(cells))
        self.tabWidget.addTab(*self._build_mismatches_tab(crossrefs))
        layout.addWidget(self.tabWidget)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def closeEvent(self, event):
        """Clean up highlight shapes when dialog is closed."""
        self._clear_layout_highlights()
        self._clear_schematic_highlights()

        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Tab builder helpers — each returns (QWidget, tab_label: str)
    # ------------------------------------------------------------------

    def _build_summary_tab(self, crossrefs: Optional[list]) -> tuple[QWidget, str]:
        lvsStatus = self._determine_lvs_status(crossrefs)
        tab = QWidget()
        layout = QVBoxLayout()

        summaryLabel = QLabel()
        summaryLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summaryLabel.setFont(QFont("Courier New", 14))
        summaryLabel.setStyleSheet("padding: 40px; line-height: 1.5;")

        if lvsStatus["passed"]:
            asciiArt = r"""
    ╔════════════════════╗
    ║   LVS PASSED ✓     ║
    ║                    ║
    ║   Layout & Schem   ║
    ║    are MATCHED!    ║
    ║                    ║
    ║      ^_^  ♫        ║
    ║     (◕‿◕)~~        ║
    ║      \ /           ║
    ║      / \           ║
    ╚════════════════════╝

    🎉 Congratulations! 🎉

    All layout vs schematic checks passed.
    Excellent work!
            """
            summaryLabel.setStyleSheet(summaryLabel.styleSheet() + "color: #10b981; background-color: #f0fdf4;")
        else:
            asciiArt = r"""
    ╔════════════════════╗
    ║   LVS FAILED ✗     ║
    ║                    ║
    ║   Mismatches       ║
    ║    detected!       ║
    ║                    ║
    ║      ._. ≈         ║
    ║     (•_•)~~        ║
    ║      | |           ║
    ║      | |           ║
    ╚════════════════════╝

    Don't worry, you've got this! 💪

    Review the mismatches in detail tabs:
    - Check Nets, Devices, and Cells tabs
    - Compare with schematic in Mismatches tab
    - Make corrections and re-run LVS
            """
            summaryLabel.setStyleSheet(summaryLabel.styleSheet() + "color: #e11d48; background-color: #fef2f2;")

        summaryLabel.setText(asciiArt)
        layout.addWidget(summaryLabel)
        layout.addStretch()

        statsLabel = QLabel()
        total = len(crossrefs) if crossrefs else 0
        stats_text = f"Total Cells: {total}\nMatched: {lvsStatus['matched']}\nMismatched: {lvsStatus['mismatched']}"
        statsLabel.setText(stats_text)
        statsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(statsLabel)

        tab.setLayout(layout)
        return tab, "Summary"

    def _build_nets_tab(self, nets: list) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        self.lvsTable = lvsmv.LVSNetsTableView(nets)
        self.lvsTable.netSelected.connect(self.onNetSelected)
        layout.addWidget(self.lvsTable)
        tab.setLayout(layout)
        return tab, "Nets"

    def _build_devices_tab(self, devices: list) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        self.devicesTable = lvsmv.LVSDevicesTableView(devices)
        self.devicesTable.deviceSelected.connect(self.onDeviceSelected)
        layout.addWidget(self.devicesTable)
        tab.setLayout(layout)
        return tab, "Devices"

    def _build_schem_nets_tab(self, schem_nets: Optional[list]) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        if schem_nets:
            self.schemNetsTable = lvsmv.LVSNetsTableView(schem_nets)
            self.schemNetsTable.netDataSelected.connect(self.onSchemNetSelected)
            layout.addWidget(self.schemNetsTable)
        else:
            layout.addWidget(QLabel("No schematic net data available."))
        tab.setLayout(layout)
        return tab, "Schem Nets"

    def _build_schem_devices_tab(self, schem_devices: Optional[list]) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        if schem_devices:
            self.schemDevicesTable = lvsmv.LVSDevicesTableView(schem_devices)
            self.schemDevicesTable.deviceSelected.connect(self.onSchemDeviceSelected)
            layout.addWidget(self.schemDevicesTable)
        else:
            layout.addWidget(QLabel("No schematic device data available."))
        tab.setLayout(layout)
        return tab, "Schem Devices"

    def _build_cells_tab(self, cells: Optional[list]) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        if cells:
            self.cellsTable = lvsmv.LVSCellsTableView(cells)
            self.cellsTable.cellSelected.connect(self.onCellSelected)
            layout.addWidget(self.cellsTable)
        else:
            layout.addWidget(QLabel("No cell data available."))
        tab.setLayout(layout)
        return tab, "Cells"

    def _build_mismatches_tab(self, crossrefs: Optional[list]) -> tuple[QWidget, str]:
        tab = QWidget()
        layout = QVBoxLayout()
        total_mismatches = self._determine_lvs_status(crossrefs).get("total_mismatches", 0)

        if crossrefs and total_mismatches > 0:
            self.crossrefsTable = lvsmv.LVSCrossrefsTableView(crossrefs)
            self.crossrefsTable.crossrefSelected.connect(self.onCrossrefSelected)
            layout.addWidget(self.crossrefsTable)

            self.mismatchSummaryLabel = QLabel(
                "Select a mismatch count cell to see details and highlight corresponding items."
            )
            self.mismatchSummaryLabel.setWordWrap(True)
            self.mismatchSummaryLabel.setStyleSheet("font-weight: 600; color: #334155; padding-top: 8px;")
            layout.addWidget(self.mismatchSummaryLabel)

            self.mismatchDetailsBox = QPlainTextEdit()
            self.mismatchDetailsBox.setReadOnly(True)
            self.mismatchDetailsBox.setMinimumHeight(150)
            self.mismatchDetailsBox.setPlainText("Mismatch details will appear here.")
            layout.addWidget(self.mismatchDetailsBox)
        elif crossrefs:
            noMismatchesLabel = QLabel(
                "✓ No mismatches found!\n\n"
                "All layout vs schematic cross-references match correctly.\n"
                "The schematic and layout are fully equivalent."
            )
            noMismatchesLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            noMismatchesLabel.setStyleSheet("color: #10b981; font-size: 14px; padding: 40px;")
            layout.addStretch()
            layout.addWidget(noMismatchesLabel)
            layout.addStretch()
        else:
            noDataLabel = QLabel("No cross-reference data available.")
            noDataLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(noDataLabel)

        tab.setLayout(layout)
        label = f"Mismatches ({total_mismatches})" if total_mismatches > 0 else "Mismatches"
        return tab, label

    def _clear_layout_highlights(self):
        if hasattr(self.layoutEditor, 'centralW') and hasattr(self.layoutEditor.centralW, 'scene'):
            scene = self.layoutEditor.centralW.scene
            items_to_remove = [item for item in scene.items() if item.__class__.__name__ == 'LVSErrorRect']
            for item in items_to_remove:
                scene.removeItem(item)

    def _schematic_scene(self):
        if self.schematicEditor and hasattr(self.schematicEditor, 'centralW'):
            return self.schematicEditor.centralW.scene
        return None

    def _clear_schematic_highlights(self):
        scene = self._schematic_scene()
        if scene is None:
            return

        for net_item in self._schematic_highlighted_nets:
            try:
                net_item.highlighted = False
            except RuntimeError:
                pass
        self._schematic_highlighted_nets.clear()

        for rect_item in self._schematic_highlight_rects:
            try:
                if rect_item.scene() is scene:
                    scene.removeItem(rect_item)
            except RuntimeError:
                pass
        self._schematic_highlight_rects.clear()

        for item in scene.selectedItems():
            try:
                item.setSelected(False)
            except RuntimeError:
                pass

        scene.highlightNets = False

    def _highlight_schematic_device(self, device: dict):
        scene = self._schematic_scene()
        if scene is None:
            return

        self._clear_schematic_highlights()

        candidate_refs = {
            self._normalize_ref(device.get("name")),
            self._normalize_ref(device.get("id")),
        }
        candidate_refs.discard("")
        if not candidate_refs:
            return
        candidate_tokens = set().union(*(self._ref_tokens(ref) for ref in candidate_refs))

        color = self._next_highlight_color()
        matched_items = []
        for item in scene.items():
            if isinstance(item, shp.schematicSymbol) and self._symbol_matches_device_ref(
                    item, candidate_refs, candidate_tokens):
                item.setSelected(True)
                scene_rect = item.sceneBoundingRect().adjusted(-8, -8, 8, 8)
                rect_item = self._make_lvs_rect(
                    scene_rect.toRect(), color, alpha=80,
                    pen_style=Qt.PenStyle.DashLine,
                    z_offset=item.zValue() + 100,
                )
                scene.addItem(rect_item)
                self._schematic_highlight_rects.append(rect_item)
                matched_items.append(item)

        if matched_items and self.schematicEditor:
            bounds = matched_items[0].sceneBoundingRect()
            for matched_item in matched_items[1:]:
                bounds = bounds.united(matched_item.sceneBoundingRect())
            self.schematicEditor.centralW.view.fitInView(
                bounds.adjusted(-40, -40, 40, 40),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def _highlight_schematic_nets(self, net_data: dict):
        scene = self._schematic_scene()
        if scene is None:
            return

        self._clear_schematic_highlights()

        net_name = net_data.get("name")
        if not net_name:
            return

        scene.highlightNets = True
        matched = []
        for item in scene.items():
            if isinstance(item, snet.schematicNet) and item.name == net_name:
                item.highlighted = True
                self._schematic_highlighted_nets.add(item)
                matched.append(item)

        if matched and self.schematicEditor:
            bounds = matched[0].sceneBoundingRect()
            for net_item in matched[1:]:
                bounds = bounds.united(net_item.sceneBoundingRect())
            self.schematicEditor.centralW.view.fitInView(bounds.adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)

    @staticmethod
    def _shape_to_bbox(shape: dict) -> tuple[float, float, float, float] | None:
        if shape.get("type") == "rect":
            box = shape.get("bbox")
            if isinstance(box, list) and len(box) == 2:
                try:
                    x1 = float(box[0][0])
                    y1 = float(box[0][1])
                    x2 = float(box[1][0])
                    y2 = float(box[1][1])
                    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
                except (TypeError, ValueError, IndexError):
                    return None
        elif shape.get("type") == "polygon":
            points = shape.get("points", [])
            xs = [pt[0] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2]
            ys = [pt[1] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2]
            if xs and ys:
                return float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))
        return None

    @staticmethod
    def _determine_lvs_status(crossrefs: Optional[list]) -> dict:
        """
        Determine overall LVS pass/fail status from crossref data.

        Returns a dict with keys:
        - 'passed': bool — True when all cells are equivalent
        - 'matched': int — count of equivalent cells
        - 'mismatched': int — count of non-equivalent cells
        - 'total_mismatches': int — sum of net/pin/device mismatches across all cells
        """
        if not crossrefs:
            return {"passed": True, "matched": 0, "mismatched": 0, "total_mismatches": 0}

        matched = sum(1 for c in crossrefs if c.get('equivalent', False))
        mismatched = len(crossrefs) - matched
        total_mismatches = sum(
            c.get('net_mismatches', 0) + c.get('pin_mismatches', 0) + c.get('device_mismatches', 0)
            for c in crossrefs if not c.get('equivalent', False)
        )

        return {
            "passed": mismatched == 0 and total_mismatches == 0,
            "matched": matched,
            "mismatched": mismatched,
            "total_mismatches": total_mismatches,
        }

    def _infer_lvs_transform(self, shapes: list[dict]) -> tuple[float, float, int]:
        if self._lvs_transform is not None:
            return self._lvs_transform

        scene = self.layoutEditor.centralW.scene
        lvs_rects = []
        for shape in shapes:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            w = int(round(x2 - x1))
            h = int(round(y2 - y1))
            if w <= 0 or h <= 0:
                continue
            lvs_rects.append((int(round(x1)), int(round(y1)), w, h))

        if not lvs_rects:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        scene_by_size: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        scene_rect_set: set[tuple[int, int, int, int]] = set()

        for item in scene.items():
            if isinstance(item, LVSErrorRect):
                continue
            if not item.isVisible() or item.zValue() >= 100:
                continue
            rect = item.sceneBoundingRect().normalized()
            w = int(round(rect.width()))
            h = int(round(rect.height()))
            if w <= 0 or h <= 0:
                continue
            x = int(round(rect.left()))
            y = int(round(rect.top()))
            key = (w, h)
            if len(scene_by_size[key]) < 80:
                scene_by_size[key].append((x, y))
            scene_rect_set.add((x, y, w, h))

        if not scene_rect_set:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        votes: Counter[tuple[int, int, int]] = Counter()
        for x, y, w, h in lvs_rects[:700]:
            candidates = scene_by_size.get((w, h), [])
            if not candidates:
                continue
            for sign in (1, -1):
                for X, Y in candidates:
                    votes[(sign, X - x, Y - sign * y)] += 1

        if not votes:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        best = None
        best_matches = -1
        for (sign, dx, dy), _score in votes.most_common(20):
            matches = 0
            for x, y, w, h in lvs_rects:
                if (x + dx, sign * y + dy, w, h) in scene_rect_set:
                    matches += 1
            if matches > best_matches:
                best_matches = matches
                best = (float(dx), float(dy), int(sign))

        self._lvs_transform = best if best is not None else (0.0, 0.0, 1)
        return self._lvs_transform

    def _next_highlight_color(self) -> QColor:
        color = self._highlight_colors[
            self._highlight_color_index % len(self._highlight_colors)
        ]
        self._highlight_color_index += 1
        return color

    @staticmethod
    def _apply_transform(bbox: tuple[float, float, float, float], dx: float, dy: float,
                         y_sign: int) -> QRect:
        """Convert a (x1,y1,x2,y2) layout bbox to a scene QRect using dx/dy/y_sign transform."""
        x1, y1, x2, y2 = bbox
        tx1, tx2 = x1 + dx, x2 + dx
        ty1, ty2 = y_sign * y1 + dy, y_sign * y2 + dy
        left = int(round(min(tx1, tx2)))
        top = int(round(min(ty1, ty2)))
        width = max(1, int(round(abs(tx2 - tx1))))
        height = max(1, int(round(abs(ty2 - ty1))))
        return QRect(left, top, width, height)

    @staticmethod
    def _make_lvs_rect(rect: QRect, color: QColor, alpha: int = 150,
                       pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine,
                       pen_width: int = 4, z_offset: float = 0.0) -> LVSErrorRect:
        """Create a styled LVSErrorRect ready to add to a scene."""
        fill = QColor(color)
        fill.setAlpha(alpha)
        rect_item = LVSErrorRect(rect)
        rect_item.setBrush(QBrush(fill))
        rect_item.setPen(QPen(color, pen_width, pen_style))
        rect_item.setOpacity(0.9)
        if z_offset:
            rect_item.setZValue(z_offset)
        return rect_item

    @staticmethod
    def _normalize_ref(value) -> str:
        if value is None:
            return ""
        text = str(value).strip().strip('"\'')
        text = re.sub(r"\s+", "", text)
        return text.upper()

    def _ref_tokens(self, value) -> set[str]:
        norm = self._normalize_ref(value)
        return {token for token in re.findall(r"[A-Z0-9_]+", norm) if len(token) > 1}

    def _symbol_matches_device_ref(self, symbol_item: shp.schematicSymbol, refs: set[str],
                                   ref_tokens: set[str]) -> bool:
        symbol_ref = self._normalize_ref(symbol_item.instanceName)
        if not symbol_ref:
            return False
        if symbol_ref in refs:
            return True

        symbol_tokens = self._ref_tokens(symbol_ref)
        return bool(ref_tokens and symbol_tokens and ref_tokens.intersection(symbol_tokens))

    def _update_mismatch_details(self, title: str, details: str, severity: str = "warning"):
        if self.mismatchSummaryLabel is None or self.mismatchDetailsBox is None:
            return

        color = {
            "info": "#0ea5e9",
            "warning": "#d97706",
            "error": "#dc2626",
        }.get(severity, "#334155")
        self.mismatchSummaryLabel.setText(title)
        self.mismatchSummaryLabel.setStyleSheet(
            f"font-weight: 600; color: {color}; padding-top: 8px;"
        )
        self.mismatchDetailsBox.setPlainText(details.strip())

    def _color_for_shapes(self, shapes: list[dict]) -> QColor:
        # Build a lightweight, stable signature from first few shape bounding boxes.
        signature_parts = []
        for shape in shapes[:8]:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            signature_parts.append(
                (
                    shape.get("type", ""),
                    int(round(x1)),
                    int(round(y1)),
                    int(round(x2 - x1)),
                    int(round(y2 - y1)),
                )
            )
        signature = tuple(signature_parts)
        if signature not in self._net_color_by_signature:
            self._net_color_by_signature[signature] = self._next_highlight_color()
        return self._net_color_by_signature[signature]

    def onNetSelected(self, shapes):
        dx, dy, y_sign = self._infer_lvs_transform(shapes)
        color = self._color_for_shapes(shapes)
        lvsShapes = [
            self._make_lvs_rect(self._apply_transform(bbox, dx, dy, y_sign), color)
            for shape in shapes
            if (bbox := self._shape_to_bbox(shape)) is not None
        ]
        self.layoutEditor.handleLVSRectSelection(lvsShapes)

    def onDeviceSelected(self, device):
        """Handle device selection from devices table."""
        position = device.get("position")
        if not position:
            return

        if isinstance(position, (list, tuple)) and len(position) >= 2:
            x, y = position[0], position[1]
        elif isinstance(position, dict):
            x = position.get("x")
            y = position.get("y")
            if x is None or y is None:
                return
        else:
            return

        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            return

        half = self._DEVICE_HIGHLIGHT_SIZE / 2
        shape_bbox = [[x - half, y - half], [x + half, y + half]]
        shapes = [{"type": "rect", "bbox": shape_bbox}]
        dx, dy, y_sign = self._infer_lvs_transform(shapes)
        color = self._next_highlight_color()
        bbox = (x - half, y - half, x + half, y + half)
        rect_item = self._make_lvs_rect(self._apply_transform(bbox, dx, dy, y_sign), color)
        rect_item._cell = (
            f"{device.get('type', '?')} ({device.get('id', '?')}) - {device.get('name', '?')}"
        )
        self.layoutEditor.handleLVSRectSelection([rect_item])

    def onCellSelected(self, cell):
        """Handle cell selection from cells table."""
        raw_bbox = cell.get("bbox")
        if not raw_bbox or not (isinstance(raw_bbox, list) and len(raw_bbox) == 2):
            return

        try:
            x1, y1 = float(raw_bbox[0][0]), float(raw_bbox[0][1])
            x2, y2 = float(raw_bbox[1][0]), float(raw_bbox[1][1])
        except (TypeError, ValueError, IndexError):
            return

        shapes = [{"type": "rect", "bbox": raw_bbox}]
        dx, dy, y_sign = self._infer_lvs_transform(shapes)
        color = self._next_highlight_color()
        rect_item = self._make_lvs_rect(
            self._apply_transform((x1, y1, x2, y2), dx, dy, y_sign), color
        )
        rect_item._cell = (
            f"Cell: {cell.get('name', '?')}"
            f" ({cell.get('net_count', 0)} nets, {cell.get('device_count', 0)} devices)"
        )
        self.layoutEditor.handleLVSRectSelection([rect_item])

    def onCrossrefSelected(self, crossref, mismatch_type='all'):
        """Handle crossref selection from crossrefs table.

        Args:
            crossref: The crossref dictionary containing mismatch data
            mismatch_type: Type of mismatch clicked - 'nets', 'pins', 'devices', or 'all'
        """
        # Extract crossref data
        layout_cell = crossref.get("layout_cell", "")
        schem_cell = crossref.get("schem_cell", "")
        self._current_layout_cell = layout_cell
        self._current_schem_cell = schem_cell
        equivalent = crossref.get("equivalent", False)
        xref_data = crossref.get("crossref", {})
        mapping = xref_data.get("mapping", {})

        # Get all nets, pins, and devices, then filter to actual mismatches
        all_nets = mapping.get("nets", [])
        all_pins = mapping.get("pins", [])
        all_devices = mapping.get("devices", [])

        mismatched_nets = [n for n in all_nets if LVSDBParser._is_mismatch(n)]
        mismatched_pins = [p for p in all_pins if LVSDBParser._is_mismatch(p)]
        mismatched_devices = [d for d in all_devices if LVSDBParser._is_mismatch(d)]

        # Determine which mismatches to show and highlight based on the clicked column
        show_nets = mismatch_type in ('nets', 'all') and mismatched_nets
        show_pins = mismatch_type in ('pins', 'all') and mismatched_pins
        show_devices = mismatch_type in ('devices', 'all') and mismatched_devices

        # Build title based on what was clicked
        type_labels = {'nets': 'Net', 'pins': 'Pin', 'devices': 'Device', 'all': 'All'}
        title = f"{type_labels.get(mismatch_type, 'All')} Mismatches: {layout_cell} ↔ {schem_cell}"

        # Build detailed message - only show the relevant mismatch type(s)
        details = f"Cell Equivalence: {'✓ Equivalent' if equivalent else '✗ Not Equivalent'}\n\n"

        if show_nets:
            details += f"❌ Net Mismatches ({len(mismatched_nets)}):\n"
            for net in mismatched_nets:
                layout_net = net.get('layout_net', '?')
                schem_net = net.get('schem_net', '?')
                status = net.get('status', '?')
                details += f"  Layout Net {layout_net} ↔ Schematic Net {schem_net} [status={status}]\n"
            details += "\n"

        if show_pins:
            details += f"❌ Pin Mismatches ({len(mismatched_pins)}):\n"
            for pin in mismatched_pins:
                layout_pin = pin.get('layout_pin', '?')
                schem_pin = pin.get('schem_pin', '?')
                status = pin.get('status', '?')
                details += f"  Layout Pin {layout_pin} ↔ Schematic Pin {schem_pin} [status={status}]\n"
            details += "\n"

        if show_devices:
            details += f"❌ Device Mismatches ({len(mismatched_devices)}):\n"
            for device in mismatched_devices:
                layout_dev = device.get('layout_dev', '?')
                schem_dev = device.get('schem_dev', '?')
                status = device.get('status', '?')
                details += f"  Layout Device {layout_dev} ↔ Schematic Device {schem_dev} [status={status}]\n"
            details += "\n"

        # Highlight mismatched items on both views
        self._highlight_mismatches(mismatched_nets if show_nets else [],
                                   mismatched_pins if show_pins else [],
                                   mismatched_devices if show_devices else [])

        if show_nets or show_pins or show_devices:
            self._update_mismatch_details(title, details, severity="warning")
        else:
            self._update_mismatch_details(
                title,
                f"{details}"
                "✓ No mismatches of this type found!\n"
                "All items matched correctly between layout and schematic.",
                severity="info",
            )

    def _highlight_mismatches(self, nets: list, pins: list, devices: list):
        """Highlight mismatched nets, pins, and devices on both schematic and layout views.

        Args:
            nets: List of mismatched net dictionaries
            pins: List of mismatched pin dictionaries
            devices: List of mismatched device dictionaries
        """
        # Clear existing highlights
        self._clear_layout_highlights()
        self._clear_schematic_highlights()

        # Highlight mismatched nets on both views
        for net in nets:
            self._highlight_mismatched_net(net)

        # Highlight mismatched pins on both views
        for pin in pins:
            self._highlight_mismatched_pin(pin)

        # Highlight mismatched devices on both views
        for device in devices:
            self._highlight_mismatched_device(device)

    def _highlight_mismatched_net(self, net: dict):
        """Highlight a mismatched net on both schematic and layout views."""
        # Get net info
        layout_net_id = net.get('layout_net', '')
        schem_net_id = net.get('schem_net', '')

        # Highlight on layout view using net shapes from parser
        if self.parser and layout_net_id and hasattr(self.layoutEditor, 'centralW'):
            layout_cell = None
            # Find the layout cell name from current context
            if hasattr(self, '_current_layout_cell'):
                layout_cell = self._current_layout_cell
            else:
                # Try to get from the first crossref
                for cell_name in self.parser.crossrefs.keys():
                    layout_cell = cell_name
                    break

            if layout_cell:
                nets_data = self.parser.get_nets_with_schematic_names(layout_cell)
                for net_data in nets_data:
                    if net_data.get('net_id') == layout_net_id:
                        self._highlight_layout_net_shapes(net_data.get('shapes', []))
                        break

        # Highlight on schematic view using net name lookup
        scene = self._schematic_scene()
        if scene and schem_net_id:
            # Get schematic net name from mapping if available
            schem_net_name = None
            for item in scene.items():
                if isinstance(item, snet.schematicNet):
                    # Match by net ID or name
                    if hasattr(item, 'netID') and item.netID == schem_net_id:
                        schem_net_name = item.name
                        break
                    elif item.name == schem_net_id:
                        schem_net_name = item.name
                        break

            if schem_net_name:
                self._highlight_schematic_nets({'name': schem_net_name})

    def _highlight_layout_net_shapes(self, shapes: list):
        """Highlight net shapes on the layout view."""
        if not shapes or not hasattr(self.layoutEditor, 'centralW'):
            return

        scene = self.layoutEditor.centralW.scene
        color = self._next_highlight_color()
        dx, dy, y_sign = self._infer_lvs_transform(shapes)

        for shape in shapes:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            scene.addItem(self._make_lvs_rect(self._apply_transform(bbox, dx, dy, y_sign), color))

    def _highlight_mismatched_pin(self, pin: dict):
        """Highlight a mismatched pin on both schematic and layout views.

        TODO: Pin-specific highlighting is not yet implemented.
              Pins typically share nets; add pin-shape lookup via parser when available.
        """

    def _highlight_mismatched_device(self, device: dict):
        """Highlight a mismatched device on both schematic and layout views."""
        layout_dev_id = device.get('layout_dev', '')
        schem_dev_id = device.get('schem_dev', '')

        # Schematic side — reuse _highlight_schematic_device with a minimal device dict
        if schem_dev_id and self.schematicEditor:
            # Resolve additional candidate refs from parser if available
            name = schem_dev_id
            if self.parser and self._current_schem_cell:
                for schem_dev in self.parser.get_schematic_devices(self._current_schem_cell):
                    dev_id = self._normalize_ref(schem_dev.get('id'))
                    dev_name = self._normalize_ref(schem_dev.get('name'))
                    if self._normalize_ref(schem_dev_id) in {dev_id, dev_name}:
                        name = schem_dev.get('name', schem_dev_id)
                        break
            self._highlight_schematic_device({"name": name, "id": schem_dev_id})

        # Layout side — look up device position via parser and delegate to onDeviceSelected
        if layout_dev_id and self.parser and hasattr(self.layoutEditor, 'centralW'):
            layout_cell = next(iter(self.parser.crossrefs), None)
            if layout_cell:
                for dev in self.parser.get_layout_devices(layout_cell):
                    if dev.get('id') == layout_dev_id:
                        self.onDeviceSelected(dev)
                        break

    def onSchemNetSelected(self, net_data):
        """Handle extracted schematic net selection in the lvs_schematic editor."""
        self._highlight_schematic_nets(net_data)

    def onSchemDeviceSelected(self, device):
        """Handle extracted schematic device selection in the lvs_schematic editor."""
        self._highlight_schematic_device(device)

