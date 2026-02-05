#!/usr/bin/env python3
"""
KLayout DRC XML report to dictionary converter using lxml.
Handles nested categories, cells, and DRC violations with polygons.
"""

import sys
from typing import Dict, Any, List

from PySide6.QtCore import (
    QPoint,
    Qt,
)
from PySide6.QtGui import QPolygonF, QPen, QColor
from PySide6.QtWidgets import (
    QApplication,
)
from PySide6.QtWidgets import (
    QGraphicsPolygonItem,
)
from lxml import etree

from revedaEditor.backend.pdkLoader import importPDKModule

process = importPDKModule("process")


class DRCErrorPolygon(QGraphicsPolygonItem):
    def __init__(self, polygon: QPolygonF) -> None:
        super().__init__(polygon)
        # self.setBrush(QBrush(QColor(255, 0, 0, 100)))
        self.setZValue(100)
        self.setPen(QPen(QColor(255, 0, 0), 20, Qt.DashLine))
        self._errorCategory = ""
        self._cell = ""

    def __repr__(self) -> str:
        return f"DRCErrorPolygon({self.polygon})"

    def __str__(self) -> str:
        return f"DRCErrorPolygon({self.polygon})"

    @property
    def errorCategory(self):
        return self._errorCategory

    @errorCategory.setter
    def errorCategory(self, value: str):
        if isinstance(value, str):
            self._errorCategory = value

    @property
    def cell(self):
        return self._cell

    @cell.setter
    def cell(self, value: str):
        if isinstance(value, str):
            self._cell = value


class DRCOutput:
    def __init__(self, path: str) -> None:
        self.path = path
        self.tree = etree.parse(path)
        self.root = self.tree.getroot()
        self.result = {}

    def parseDRCOutput(self) -> Dict[str, Any]:
        result = {
            "metadata": {},
            "categories": {},
            "cells": {},
            "violations": [],  # list of dicts for DRC items
        }

        # Parse top-level metadata
        for child in self.root:
            tag = child.tag
            if tag == "description":
                result["metadata"]["description"] = child.text
            elif tag == "generator":
                result["metadata"]["generator"] = child.text
            elif tag == "top-cell":
                result["metadata"]["top_cell"] = child.text
            elif tag == "categories":
                result["categories"] = self.parseCategories(child)
            elif tag == "cells":
                result["cells"] = self.parseCells(child)
            elif tag == "items":
                result["violations"] = self.parseViolations(child)
        self.result = result

    def parseCategories(self, categoryElement: etree._Element) -> Dict[str, Dict]:
        """Parse nested categories structure."""
        cats = {}
        for cat in categoryElement.findall("category"):
            name = cat.find("name")
            desc = cat.find("description")
            cats[name.text if name is not None else ""] = (
                desc.text if desc is not None else ""
            )
        return cats

    def parseCells(self, cells_el: etree._Element) -> Dict[str, Dict]:
        """Parse cells section."""
        cells = {}
        for cell in cells_el.findall("cell"):
            name = cell.find("name")
            cells[name.text] = self.xmltoDict(cell) if name is not None else {}
        return cells

    def xmltoDict(self, element: etree._Element) -> Dict[str, Any]:
        """Recursively convert lxml Element to dictionary."""
        if element.text and element.text.strip():
            return {
                "tag": element.tag,
                "text": element.text.strip(),
                "tail": element.tail,
            }

        result = {"tag": element.tag}

        # Handle attributes
        if element.attrib:
            result["attrib"] = dict(element.attrib)

        # Handle text content
        if element.text and element.text.strip():
            result["text"] = element.text.strip()

        # Handle children
        children = {}
        for child in element:
            child_dict = self.xmltoDict(child)
            child_tag = child_dict["tag"]
            if child_tag in children:
                if not isinstance(children[child_tag], list):
                    children[child_tag] = [children[child_tag]]
                children[child_tag].append(child_dict)
            else:
                children[child_tag] = child_dict

        if children:
            result["children"] = children

        return result

    def parseViolations(self, items_el: etree._Element):
        def parsePolygon(valueStr: str) -> tuple[str, List[QPoint], List[str]]:
            def parseCoords(point_list: List[str]) -> List[QPoint]:
                coords = []
                for pt in point_list:
                    pt = pt.strip()
                    if "," in pt:
                        try:
                            x, y = map(float, pt.split(","))
                            coords.append(QPoint(x * process.dbu, y * process.dbu))
                        except ValueError:
                            continue
                return coords

            if valueStr.startswith("polygon:"):
                points = valueStr[9:].strip("()").split(";")
                return ("polygon", parseCoords(points), points)
            elif valueStr.startswith("edge-pair:"):
                edge_str = valueStr[10:].strip()
                points = []
                for pair in edge_str.split("/"):
                    points.extend(pair.strip("()").split(";"))
                return ("edge-pair", parseCoords(points), points)
            return ("", [], [])

        """Parse violations/items section."""
        violations = []
        for item in items_el.findall("item"):
            violation = {
                "category": (
                    item.find("category").text.strip("'")
                    if item.find("category") is not None
                    else None
                ),
                "cell": (
                    item.find("cell").text if item.find("cell") is not None else None
                ),
                "visited": (
                    item.find("visited").text == "true"
                    if item.find("visited") is not None
                    else False
                ),
                "multiplicity": (
                    int(item.find("multiplicity").text)
                    if item.find("multiplicity") is not None
                    else 1
                ),
                "polygons": [],
                "points": [],
            }

            # Parse values (polygons)
            values = item.find("values")
            if values is not None:
                for value_el in values.findall("value"):
                    errorType, polyCoords, points = parsePolygon(value_el.text)
                    if polyCoords:
                        violation["points"].append(points)
                        polygonItem = DRCErrorPolygon(QPolygonF(polyCoords))
                        polygonItem.cell = violation["cell"]
                        polygonItem.errorCategory = errorType
                        polygonItem.setToolTip(
                            f'{violation['cell']}, {violation['category']}, {violation["points"]}'
                        )
                        violation["polygons"].append(polygonItem)

            violations.append(violation)
        return violations


def main(file_path: str):
    """Main function to parse DRC file and print JSON-like dict."""
    drcDataObj = DRCOutput(file_path)
    drcDataObj.parseDRCOutput()
    # import json
    # Pretty print with indentation
    # print(json.dumps(drc_data, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python drc_parser.py <drc_xml_file>")
        sys.exit(1)
    main(sys.argv[1])
