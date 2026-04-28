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
import functools
import logging
import re
from typing import Optional, cast

from PySide6.QtCore import QEvent, QRect, QRectF, Qt
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
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.fileio.importlvsdb import LVSDBParser, LVSErrorRect

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
        self._schematic_highlight_scenes: list = []
        self.mismatchSummaryLabel: QLabel | None = None
        self.mismatchDetailsBox: QPlainTextEdit | None = None
        self._current_layout_cell: str | None = None
        self._current_schem_cell: str | None = None
        self._pending_schematic_device_highlights: list[dict] | None = None
        self._schematic_hierarchy_path: tuple[str, ...] = ()
        self._schematic_view_contexts: dict[tuple[str, str, str], tuple[dict | None, tuple[str, ...]]] = {}
        self._schematic_highlight_replay_by_view: dict[tuple[str, str, str], tuple[str, object]] = {}
        self._lvs_session_library_view = None
        self._tracked_schematic_editors: list = []
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
        self._uninstall_lvs_schematic_open_hook()
        self._schematic_highlight_replay_by_view.clear()

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
        """Clear all schematic highlights: nets, rects, selections, and scene states.

        Safely removes highlight items from their owning scenes and resets highlighted
        net tracking. Handles cases where scenes or editors may have been deleted.
        """
        # Clear highlighted net flags
        for net_item in self._schematic_highlighted_nets:
            try:
                net_item.highlighted = False
            except RuntimeError:
                # Item may have been deleted from scene; ignore
                pass
        self._schematic_highlighted_nets.clear()

        # Remove highlight rectangles from their owning scenes (not necessarily the active scene)
        for rect_item in self._schematic_highlight_rects:
            try:
                owner_scene = rect_item.scene()
                if owner_scene is not None:
                    owner_scene.removeItem(rect_item)
            except RuntimeError:
                # Scene may have been destroyed; ignore
                pass
        self._schematic_highlight_rects.clear()

        # Deselect all items and disable net highlighting in all tracked scenes
        for scene in list(self._schematic_highlight_scenes):
            try:
                for item in scene.selectedItems():
                    try:
                        item.setSelected(False)
                    except RuntimeError:
                        pass
                scene.highlightNets = False
            except RuntimeError:
                # Scene may have been destroyed; ignore
                pass
        self._schematic_highlight_scenes.clear()

    def _track_schematic_scene(self, scene):
        if scene is None:
            return
        if any(existing_scene is scene for existing_scene in self._schematic_highlight_scenes):
            return
        self._schematic_highlight_scenes.append(scene)

    def _highlight_schematic_device(self, device: dict):
        scene = self._schematic_scene()
        if scene is None:
            return

        self._remember_schematic_highlight_request('device', dict(device))
        self._clear_schematic_highlights()
        self._track_schematic_scene(scene)

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

        self._remember_schematic_highlight_request('net', dict(net_data))
        self._clear_schematic_highlights()
        self._track_schematic_scene(scene)

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

    def _find_layout_instance_at(self, scene_x: float, scene_y: float) -> "lshp.layoutInstance | None":
        """Return the smallest layout instance whose scene bounding rect contains the point.

        Using the smallest (innermost) instance ensures we highlight the specific device
        (e.g. a single PMOS transistor) rather than a large parent cell that contains it.
        """
        if not hasattr(self.layoutEditor, 'centralW'):
            return None
        scene = self.layoutEditor.centralW.scene
        point_rect = QRectF(scene_x - 1, scene_y - 1, 2, 2)
        best: "lshp.layoutInstance | None" = None
        best_area: float = float('inf')
        for item in scene.items(point_rect):
            if isinstance(item, lshp.layoutInstance):
                sbr = item.sceneBoundingRect()
                area = sbr.width() * sbr.height()
                if area < best_area:
                    best_area = area
                    best = item
        return best

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

    def _ref_variants(self, value) -> set[str]:
        norm = self._normalize_ref(value)
        if not norm:
            return set()

        parts = [part for part in norm.split('.') if part]
        variants = {norm, *parts}
        variants.update(self._ref_tokens(norm))
        return {variant for variant in variants if variant}

    def _symbol_matches_device_ref(self, symbol_item: shp.schematicSymbol, refs: set[str],
                                   ref_tokens: set[str]) -> bool:
        symbol_variants = set()
        symbol_variants.update(self._ref_variants(symbol_item.instanceName))
        symbol_variants.update(self._ref_variants(getattr(symbol_item, 'cellName', '')))

        instance_label = None
        if hasattr(symbol_item, 'labels') and isinstance(symbol_item.labels, dict):
            instance_label = symbol_item.labels.get('instanceName') or symbol_item.labels.get('@instName')
        if instance_label is not None:
            symbol_variants.update(self._ref_variants(getattr(instance_label, 'labelValue', '')))

        if not symbol_variants:
            return False
        if refs.intersection(symbol_variants):
            return True

        symbol_tokens = set().union(*(self._ref_tokens(variant) for variant in symbol_variants))
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
        # Try to find the actual layout instance and use its bounding rect
        sx = x + dx
        sy = y_sign * y + dy
        instance = self._find_layout_instance_at(sx, sy)
        if instance is not None:
            sbr = instance.sceneBoundingRect().normalized()
            scene_rect = QRect(
                int(round(sbr.left())),
                int(round(sbr.top())),
                max(1, int(round(sbr.width()))),
                max(1, int(round(sbr.height()))),
            )
        else:
            bbox = (x - half, y - half, x + half, y + half)
            scene_rect = self._apply_transform(bbox, dx, dy, y_sign)
        rect_item = self._make_lvs_rect(scene_rect, color)
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
        device_mismatch_summaries = crossref.get("device_mismatch_summaries", [])
        device_mismatch_details = crossref.get("device_mismatch_details", [])

        # Get all nets, pins, and devices, then filter to actual mismatches
        all_nets = mapping.get("nets", [])
        all_pins = mapping.get("pins", [])
        all_devices = mapping.get("devices", [])

        mismatched_nets = [n for n in all_nets if LVSDBParser._is_mismatch(n)]
        mismatched_pins = [p for p in all_pins if LVSDBParser._is_mismatch(p)]
        mismatched_devices = [d for d in all_devices if LVSDBParser._is_mismatch(d)]

        # Use pre-computed mismatch counts from the crossref dict (consistent with table display).
        # net_mismatches uses diagnostics-based counting which filters out device-property fallout.
        net_mismatch_count = crossref.get('net_mismatches', len(mismatched_nets))
        pin_mismatch_count = crossref.get('pin_mismatches', len(mismatched_pins))

        # Prefer human-readable diagnostic messages over raw mapping IDs for net mismatches.
        net_mismatch_messages = xref_data.get('diagnostics', {}).get('net_mismatch_messages', [])

        # Determine which mismatches to show and highlight based on the clicked column.
        # For nets, rely on the authoritative count (same source as the table column).
        show_nets = mismatch_type in ('nets', 'all') and net_mismatch_count > 0
        show_pins = mismatch_type in ('pins', 'all') and mismatched_pins
        show_devices = mismatch_type in ('devices', 'all') and mismatched_devices

        # Build title based on what was clicked
        type_labels = {'nets': 'Net', 'pins': 'Pin', 'devices': 'Device', 'all': 'All'}
        title = f"{type_labels.get(mismatch_type, 'All')} Mismatches: {layout_cell} ↔ {schem_cell}"

        # Build detailed message - only show the relevant mismatch type(s)
        details = f"Cell Equivalence: {'✓ Equivalent' if equivalent else '✗ Not Equivalent'}\n\n"

        if show_nets:
            details += f"❌ Net Mismatches ({net_mismatch_count}):\n"
            if net_mismatch_messages:
                # Use human-readable diagnostic messages (contain actual net names)
                for message in net_mismatch_messages:
                    details += f"  {message}\n"
            else:
                # Fall back to raw mapping entries (may show internal IDs)
                for net in mismatched_nets:
                    layout_net = net.get('layout_net', '?')
                    schem_net = net.get('schem_net', '?')
                    status = net.get('status', '?')
                    details += f"  Layout Net {layout_net} ↔ Schematic Net {schem_net} [status={status}]\n"
            details += "\n"

        if show_pins:
            details += f"❌ Pin Mismatches ({pin_mismatch_count}):\n"
            for pin in mismatched_pins:
                layout_pin = pin.get('layout_pin', '?')
                schem_pin = pin.get('schem_pin', '?')
                status = pin.get('status', '?')
                details += f"  Layout Pin {layout_pin} ↔ Schematic Pin {schem_pin} [status={status}]\n"
            details += "\n"

        if show_devices:
            if device_mismatch_summaries:
                details += f"❌ Device Property Mismatches ({len(device_mismatch_summaries)}):\n"
                for summary in device_mismatch_summaries:
                    details += f"  {summary}\n"
                if mismatched_devices:
                    details += (
                        f"\n  Raw cross-reference fallout rows: {len(mismatched_devices)}"
                        " (suppressed from the summary count).\n"
                    )
            else:
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
                                   mismatched_devices if show_devices else [],
                                   device_mismatch_details if show_devices else [])

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

    def _highlight_mismatches(self, nets: list, pins: list, devices: list,
                              device_details: Optional[list] = None):
        """Highlight mismatched nets, pins, and devices on both schematic and layout views.

        Args:
            nets: List of mismatched net dictionaries
            pins: List of mismatched pin dictionaries
            devices: List of mismatched device dictionaries
            device_details: Optional parser-derived device property mismatch details
        """
        # Clear existing highlights
        self._remember_schematic_highlight_request(
            'mismatches',
            {
                'nets': list(nets),
                'pins': list(pins),
                'devices': list(devices),
                'device_details': list(device_details) if device_details else None,
            },
        )
        self._clear_layout_highlights()
        self._clear_schematic_highlights()

        # Highlight mismatched nets on both views
        for net in nets:
            self._highlight_mismatched_net(net)

        # Highlight mismatched pins on both views
        for pin in pins:
            self._highlight_mismatched_pin(pin)

        # Highlight mismatched devices on both views
        if device_details:
            self._highlight_device_property_mismatches(device_details)
        else:
            for device in devices:
                self._highlight_mismatched_device(device)

    def _highlight_device_property_mismatches(self, device_details: list[dict]):
        """Highlight specific layout and schematic devices identified by property mismatch analysis."""
        layout_devices = []
        schematic_devices = []
        for detail in device_details:
            layout_devices.extend(detail.get('layout_devices', []))
            schematic_devices.extend(detail.get('schematic_devices', []))

        self._pending_schematic_device_highlights = list(device_details)
        self._highlight_layout_devices(layout_devices)
        self._highlight_schematic_devices(schematic_devices)

    def _highlight_layout_devices(self, devices: list[dict]):
        if not devices or not hasattr(self.layoutEditor, 'centralW'):
            return

        # Pre-compute the transform using the first valid device position as a reference
        _transform_shapes = []
        for device in devices:
            pos = device.get('position')
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                try:
                    x, y = float(pos[0]), float(pos[1])
                    half = self._DEVICE_HIGHLIGHT_SIZE / 2
                    _transform_shapes.append({"type": "rect", "bbox": [[x - half, y - half], [x + half, y + half]]})
                    break
                except (TypeError, ValueError):
                    pass
        dx, dy, y_sign = self._infer_lvs_transform(_transform_shapes) if _transform_shapes else (0.0, 0.0, 1)

        rects = []
        for device in devices:
            position = device.get('position')
            if not isinstance(position, (list, tuple)) or len(position) < 2:
                continue
            try:
                x, y = float(position[0]), float(position[1])
            except (TypeError, ValueError):
                continue

            color = self._next_highlight_color()
            # Convert LVS position to scene coordinates
            sx = x + dx
            sy = y_sign * y + dy
            instance = self._find_layout_instance_at(sx, sy)
            if instance is not None:
                sbr = instance.sceneBoundingRect().normalized()
                scene_rect = QRect(
                    int(round(sbr.left())),
                    int(round(sbr.top())),
                    max(1, int(round(sbr.width()))),
                    max(1, int(round(sbr.height()))),
                )
            else:
                half = self._DEVICE_HIGHLIGHT_SIZE / 2
                scene_rect = self._apply_transform(
                    (x - half, y - half, x + half, y + half), dx, dy, y_sign
                )
            rect_item = self._make_lvs_rect(scene_rect, color)
            rect_item._cell = (
                f"{device.get('type', '?')} ({device.get('id', '?')})"
            )
            rects.append(rect_item)

        if rects:
            self.layoutEditor.handleLVSRectSelection(rects)

    def register_schematic_view(self, schematic_editor, extracted: dict | None = None,
                                hierarchy_path: tuple[str, ...] = ()): 
        """Register an extracted schematic editor view and restore its per-view highlight state.

        This method is the main entry point for tracking schematic views. When a user opens
        an lvs_schematic view (by drilling down in the hierarchy browser), this method is
        called to:
        1. Store the view's extracted device data and hierarchy context
        2. Install event filters for tracking window show/activate events
        3. Apply any stored highlight state specific to this view

        Args:
            schematic_editor: The schematic editor widget that was opened.
            extracted: Dictionary containing 'primitive_device_ids' and 'primitive_devices' for
                      this hierarchy level, or None if not an extracted lvs_schematic.
            hierarchy_path: Tuple of cell names from root to this cell, e.g., ('opamp', 'opamp_core').
                          Used to filter device references when matching against parser results.
        """
        self._remember_schematic_view_context(schematic_editor, extracted, hierarchy_path)
        self.schematicEditor = schematic_editor
        self._schematic_hierarchy_path = tuple(part for part in hierarchy_path if part)
        self.apply_pending_highlights(extracted)

    def _remember_schematic_view_context(self, schematic_editor, extracted: dict | None,
                                         hierarchy_path: tuple[str, ...]):
        view_key = self._editor_view_key(schematic_editor)
        if view_key is None:
            return

        normalized_path = tuple(part for part in hierarchy_path if part)
        self._schematic_view_contexts[view_key] = (
            extracted if isinstance(extracted, dict) else None,
            normalized_path,
        )
        self._track_schematic_editor(schematic_editor)
        self._install_lvs_schematic_open_hook()

    def _track_schematic_editor(self, schematic_editor):
        if schematic_editor is None:
            return
        if any(existing_editor is schematic_editor for existing_editor in self._tracked_schematic_editors):
            return
        schematic_editor.installEventFilter(self)
        self._tracked_schematic_editors.append(schematic_editor)

    @staticmethod
    def _editor_view_key(editor) -> tuple[str, str, str] | None:
        if editor is None:
            return None

        lib_name = getattr(editor, 'libName', None)
        cell_name = getattr(editor, 'cellName', None)
        view_name = getattr(editor, 'viewName', None)
        if not all((lib_name, cell_name, view_name)):
            return None
        return str(lib_name), str(cell_name), str(view_name)

    def _install_lvs_schematic_open_hook(self):
        """Monkey-patch libraryView.openCellView() to intercept lvs_schematic opening.

        When a user clicks on an lvs_schematic cell in the library browser, the standard
        openCellView() is called. We wrap it to detect lvs_schematic openings and call
        register_schematic_view() with the correct context.

        This allows us to automatically restore per-view highlight state when drilling down.
        """
        library_view = getattr(self.layoutEditor, 'libraryView', None)
        if library_view is None:
            return
        if self._lvs_session_library_view is library_view:
            return
        if getattr(library_view, '_lvs_results_dialog_hook', None) not in (None, self):
            return

        original_open_cell_view = getattr(library_view, 'openCellView', None)
        if not callable(original_open_cell_view):
            return

        @functools.wraps(original_open_cell_view)
        def open_cell_view_with_lvs_context(viewItemT):
            view_name_tuple = original_open_cell_view(viewItemT)

            view_item = getattr(viewItemT, 'viewItem', None)
            view_name = getattr(view_item, 'viewName', None)
            if view_name != 'lvs_schematic':
                return view_name_tuple

            context = self._schematic_view_contexts.get(view_name_tuple)
            if context is None:
                return view_name_tuple

            editor = self.layoutEditor.appMainW.openViews.get(view_name_tuple)
            if editor is None:
                return view_name_tuple

            extracted, hierarchy_path = context
            self.register_schematic_view(editor, extracted, hierarchy_path)
            return view_name_tuple

        library_view.openCellView = open_cell_view_with_lvs_context
        library_view._lvs_results_dialog_hook = self
        library_view._lvs_results_dialog_original_open = original_open_cell_view
        self._lvs_session_library_view = library_view

    def _uninstall_lvs_schematic_open_hook(self):
        """Restore libraryView.openCellView() to original behavior.

        Called when the LVS dialog is closed. Removes the monkey-patched wrapper and
        restores the original method. Also removes event filters from all tracked editors.
        """
        library_view = self._lvs_session_library_view
        if library_view is None:
            pass
        elif getattr(library_view, '_lvs_results_dialog_hook', None) is self:
            original_open_cell_view = getattr(
                library_view,
                '_lvs_results_dialog_original_open',
                None,
            )
            if callable(original_open_cell_view):
                library_view.openCellView = original_open_cell_view
            if hasattr(library_view, '_lvs_results_dialog_hook'):
                delattr(library_view, '_lvs_results_dialog_hook')
            if hasattr(library_view, '_lvs_results_dialog_original_open'):
                delattr(library_view, '_lvs_results_dialog_original_open')
        self._lvs_session_library_view = None

        for editor in list(self._tracked_schematic_editors):
            try:
                editor.removeEventFilter(self)
            except RuntimeError:
                # Editor may have been deleted; ignore
                pass
        self._tracked_schematic_editors.clear()

    def eventFilter(self, watched, event):
        """Watch schematic editors for Show/WindowActivate events and restore highlight state.

        When a schematic editor window is raised/shown, this filter detects it and calls
        register_schematic_view() to restore the per-view highlight state that was stored
        when the view was first registered.

        Args:
            watched: The editor widget that received the event.
            event: The QEvent (Show or WindowActivate).

        Returns:
            False to allow event to propagate normally.
        """
        if event.type() in {QEvent.Type.Show, QEvent.Type.WindowActivate}:
            view_key = self._editor_view_key(watched)
            if view_key is not None:
                context = self._schematic_view_contexts.get(view_key)
                if context is not None:
                    extracted, hierarchy_path = context
                    self.register_schematic_view(watched, extracted, hierarchy_path)
        return super().eventFilter(watched, event)

    def apply_pending_highlights(self, extracted: dict | None = None):
        """
        Apply pending schematic device highlights when the user opens an extracted schematic.

        This method should be called from the extracted schematic view's initialization
        (e.g., from extractedSchematic.py when the lvs_schematic view is opened) or
        from the schematic editor's scene setup to ensure items are loaded first.
        
        Call this method after the extracted schematic view is fully initialized and all
        instances/nets are added to the scene. For example:
        
        - In klayoutLVS.py after generateSchematic() returns and before showing the dialog
        - OR in extractedSchematic.py in createTempSchematicEditor() after the view is loaded
        - OR in the schematic editor class when the scene is fully populated
        
        The method will apply any stored device highlights to the currently active schematic editor.
        """
        if not self.schematicEditor:
            return

        replayed = self._replay_last_schematic_highlight(extracted)
        if replayed:
            return

        if self._pending_schematic_device_highlights:
            schematic_devices = []
            for detail in self._pending_schematic_device_highlights:
                schematic_devices.extend(detail.get('schematic_devices', []))

            if schematic_devices:
                self._highlight_schematic_devices(schematic_devices, extracted)

    def _remember_schematic_highlight_request(self, request_type: str, payload: object):
        """Store highlight request for all registered schematic views.

        This ensures that when any schematic view is reactivated (via WindowActivate
        event), the last highlight state will be restored for that view.
        """
        # Store for the current active editor
        view_key = self._editor_view_key(self.schematicEditor)
        if view_key is not None:
            self._schematic_highlight_replay_by_view[view_key] = (request_type, payload)

        # Also store for all tracked editors to ensure highlights survive window switches
        for editor in self._tracked_schematic_editors:
            editor_key = self._editor_view_key(editor)
            if editor_key is not None:
                self._schematic_highlight_replay_by_view[editor_key] = (request_type, payload)

    def _replay_last_schematic_highlight(self, extracted: dict | None = None) -> bool:
        if self.schematicEditor is None:
            return False

        view_key = self._editor_view_key(self.schematicEditor)
        if view_key is None:
            return False

        highlight_request = self._schematic_highlight_replay_by_view.get(view_key)
        if highlight_request is None:
            return False

        request_type, payload = highlight_request
        if request_type == 'device' and isinstance(payload, dict):
            self._highlight_schematic_device(cast(dict, payload))
            return True
        if request_type == 'net' and isinstance(payload, dict):
            self._highlight_schematic_nets(cast(dict, payload))
            return True
        if request_type == 'mismatches' and isinstance(payload, dict):
            payload_dict = cast(dict[str, object], payload)
            nets = payload_dict.get('nets', [])
            pins = payload_dict.get('pins', [])
            devices = payload_dict.get('devices', [])
            device_details = payload_dict.get('device_details')
            if not isinstance(nets, list) or not isinstance(pins, list) or not isinstance(devices, list):
                return False
            if device_details is not None and not isinstance(device_details, list):
                device_details = None
            self._highlight_mismatches(
                nets,
                pins,
                devices,
                device_details,
            )
            return True
        if request_type == 'device_group' and isinstance(payload, list) and all(
            isinstance(device, dict) for device in payload
        ):
            self._highlight_schematic_devices(cast(list[dict], payload), extracted)
            return True
        return False

    def _highlight_schematic_devices(self, devices: list[dict], extracted: dict | None = None):
        """Highlight multiple schematic devices by name/ID matching or type fallback.

        First attempts to match devices by name/ID against schematic symbols. If name matching
        fails, falls back to type-based matching (e.g., matching all 'nmos' type devices).

        Only highlights devices local to the current hierarchy level (if extracted data provided).

        Args:
            devices: List of device dicts from LVS parser, each with 'name', 'id', 'type' keys.
            extracted: Dictionary with 'primitive_device_ids'/'primitive_devices' keys for
                      filtering to current hierarchy level, or None to highlight all devices.
        """
        scene = self._schematic_scene()
        if scene is None or not devices:
            return

        self._remember_schematic_highlight_request('device_group', list(devices))
        self._clear_schematic_highlights()
        self._track_schematic_scene(scene)

        relevant_device_ids = self._extract_device_ids_for_view(extracted)
        matched_items = []
        seen_items = set()

        matched_by_name = set()
        for device in devices:
            if relevant_device_ids is not None and device.get("id") not in relevant_device_ids:
                continue

            candidate_refs = self._relative_device_refs(device)
            candidate_refs.discard("")
            if not candidate_refs:
                continue
            candidate_tokens = set().union(*(self._ref_tokens(ref) for ref in candidate_refs))
            color = self._next_highlight_color()

            for item in scene.items():
                if not isinstance(item, shp.schematicSymbol):
                    continue
                if not self._symbol_matches_device_ref(item, candidate_refs, candidate_tokens):
                    continue
                if item in seen_items:
                    continue
                seen_items.add(item)
                matched_by_name.add(item)
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

        if not matched_by_name and devices:
            self._highlight_schematic_devices_by_type_matching(
                devices,
                scene,
                seen_items,
                matched_items,
                relevant_device_ids,
            )

        # Highlight hierarchical instances containing mismatched devices
        self._highlight_hierarchical_instances(scene, devices, extracted, seen_items)

        if matched_items and self.schematicEditor:
            bounds = matched_items[0].sceneBoundingRect()
            for matched_item in matched_items[1:]:
                bounds = bounds.united(matched_item.sceneBoundingRect())
            self.schematicEditor.centralW.view.fitInView(
                bounds.adjusted(-40, -40, 40, 40),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def _highlight_schematic_devices_by_type_matching(self, devices: list[dict], scene,
                                                      seen_items: set, matched_items: list,
                                                      relevant_device_ids: set | None = None):
        """
        Fallback matching when name-based matching fails.

        Only devices local to the currently opened extracted hierarchy level are considered.
        """
        flat_devices = {}

        for device in devices:
            if relevant_device_ids is not None and device.get('id') not in relevant_device_ids:
                continue
            if not self._relative_device_refs(device):
                continue
            dev_type = device.get('type', '?')
            if dev_type not in flat_devices:
                flat_devices[dev_type] = []
            flat_devices[dev_type].append(device)

        if flat_devices:
            scene_symbols_by_type = {}
            for item in scene.items():
                if not isinstance(item, shp.schematicSymbol):
                    continue
                cell_type = getattr(item, 'cellName', '?')
                if cell_type not in scene_symbols_by_type:
                    scene_symbols_by_type[cell_type] = []
                scene_symbols_by_type[cell_type].append(item)

            for dev_type, dev_list in flat_devices.items():
                scene_symbols = scene_symbols_by_type.get(dev_type, [])
                if not scene_symbols or len(dev_list) > len(scene_symbols):
                    continue

                selected_count = 0
                for item in scene_symbols:
                    if item in seen_items or selected_count >= len(dev_list):
                        continue
                    seen_items.add(item)
                    selected_count += 1

                    color = self._next_highlight_color()
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

    def _highlight_hierarchical_instances(self, scene, devices: list[dict],
                                          extracted: dict | None, seen_items: set):
        """Highlight instance symbols that contain mismatched devices in their sub-cells.

        When viewing a parent schematic, if devices inside a hierarchical instance have
        LVS mismatches, this method highlights those instance symbols.

        Args:
            scene: The schematic scene to search for instance symbols.
            devices: List of mismatched device dicts from LVS parser.
            extracted: Extracted schematic data containing 'instances' with 'source_device_ids'.
            seen_items: Set of already highlighted items to avoid duplicates.
        """
        if not isinstance(extracted, dict) or not devices:
            return

        instances = extracted.get('instances', [])
        if not isinstance(instances, list) or not instances:
            return

        # Build set of mismatched device IDs
        mismatched_device_ids = {str(d.get('id')) for d in devices if d.get('id') is not None}
        if not mismatched_device_ids:
            return

        # Find instances that contain mismatched devices
        instances_with_errors = []
        for instance in instances:
            if not isinstance(instance, dict):
                continue
            source_ids = instance.get('source_device_ids', [])
            if not isinstance(source_ids, list):
                continue
            # Check if any mismatched device ID is in this instance's source IDs
            if any(str(did) in mismatched_device_ids for did in source_ids):
                instances_with_errors.append(instance)

        if not instances_with_errors:
            return

        # Find and highlight corresponding instance symbols on the schematic
        instance_names = {inst.get('name', '') for inst in instances_with_errors}

        for item in scene.items():
            if not isinstance(item, shp.schematicSymbol):
                continue
            if item in seen_items:
                continue

            # Check if this symbol is one of the instances with errors
            inst_name = getattr(item, 'instanceName', '')
            if inst_name not in instance_names:
                continue

            seen_items.add(item)
            color = self._next_highlight_color()
            item.setSelected(True)

            # Draw highlight rectangle around the instance symbol
            scene_rect = item.sceneBoundingRect().adjusted(-12, -12, 12, 12)
            rect_item = self._make_lvs_rect(
                scene_rect.toRect(), color, alpha=80,
                pen_style=Qt.PenStyle.DashLine,
                pen_width=5,
                z_offset=item.zValue() + 100,
            )
            # Add cell name annotation
            cell_name = getattr(item, 'cellName', '?')
            rect_item._cell = f"Instance: {inst_name} ({cell_name})"
            scene.addItem(rect_item)
            self._schematic_highlight_rects.append(rect_item)

    def _extract_device_ids_for_view(self, extracted: dict | None) -> set[str]:
        """Extract device IDs that belong to the current extracted hierarchy level.

        When drilling into a nested lvs_schematic, only devices at that hierarchy level
        should be highlighted. This method filters the device list to only include devices
        local to the current view.

        Args:
            extracted: Dictionary containing 'primitive_device_ids' and 'primitive_devices' keys,
                      or None if no extraction data available.

        Returns:
            Set of device ID strings that exist in the current hierarchy level. Always returns
            a set (possibly empty); never None.
        """
        device_ids: set[str] = set()
        if not isinstance(extracted, dict):
            return device_ids

        for device_id in extracted.get('primitive_device_ids', []):
            device_ids.add(str(device_id))
        for device in extracted.get('primitive_devices', []):
            if isinstance(device, dict) and device.get('id') is not None:
                device_ids.add(str(device.get('id')))

        return device_ids

    def _relative_device_refs(self, device: dict) -> set[str]:
        """Extract and normalize device references relative to current hierarchy level.

        Converts device name/id into normalized references, stripping hierarchy prefixes
        if currently in a nested view.

        Args:
            device: Dictionary with 'name' and 'id' keys (typically from LVS parser).

        Returns:
            Set of normalized reference strings (e.g., {'R1', 'R_BIAS'} for a resistor).
        """
        refs = set()
        for raw_ref in (device.get('name'), device.get('id')):
            relative_ref = self._relative_ref_for_hierarchy(raw_ref)
            normalized_ref = self._normalize_ref(relative_ref)
            if normalized_ref:
                refs.add(normalized_ref)
        return refs

    def _relative_ref_for_hierarchy(self, raw_ref) -> str:
        """Strip hierarchy path prefix from a device reference.

        When drilling into nested extracted schematics (e.g., opamp.opamp_core),
        device names are fully qualified (e.g., 'opamp.opamp_core.M1'). This method
        strips the hierarchy prefix to get the local name (e.g., 'M1').

        Args:
            raw_ref: Device name or ID string (may include hierarchy prefix).

        Returns:
            Local reference (hierarchy prefix removed), or empty string if hierarchy
            path doesn't match (meaning device is not in current view).
        """
        text = str(raw_ref or '').strip()
        if not text:
            return ''

        path = self._schematic_hierarchy_path
        if not path:
            return text  # Top-level: return unchanged

        parts = [part for part in text.split('.') if part]
        if len(parts) < len(path):
            # Reference doesn't have enough hierarchy levels; not in current view
            logging.getLogger('reveda').debug(
                f'Device reference {raw_ref!r} has insufficient hierarchy levels '
                f'(expected {len(path)}, got {len(parts)}); not local to {path}')
            return ''
        if tuple(parts[:len(path)]) != path:
            # Hierarchy path doesn't match; device is in different branch
            logging.getLogger('reveda').debug(
                f'Device reference {raw_ref!r} hierarchy path {tuple(parts[:len(path)])} '
                f'does not match expected {path}')
            return ''

        return '.'.join(parts[len(path):])

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

        Pins are typically highlighted via their connected nets. This method attempts to
        find and highlight the net(s) associated with the pin.
        """
        # Pins are part of nets; highlighting the net effectively highlights the pin.
        # Try to highlight by net relationship if parser provides net info.
        schem_pin_id = pin.get('schem_pin', '')
        layout_pin_id = pin.get('layout_pin', '')

        if schem_pin_id and self.parser and self._current_schem_cell:
            # Attempt to find connected net via parser (implementation depends on parser API)
            # For now, pins are implicitly highlighted when their nets are highlighted.
            pass
        if layout_pin_id and self.parser and self._current_layout_cell:
            # Attempt to find connected net via parser
            pass

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

