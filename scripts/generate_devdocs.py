#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.

"""Generate the developmentDocs Obsidian vault.

Walks the Python sources, extracts module docstrings / classes / functions /
internal imports via AST, and emits one Markdown note per file plus per-package
index notes. Links are path-qualified Obsidian wikilinks so they resolve
unambiguously even for files that share a basename.

Re-run after structural changes:  poetry run python scripts/generate_devdocs.py
Hand-written notes (Home.md, Architecture.md, DataFormats.md) are NOT touched.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAULT = REPO / "developmentDocs"

# Packages scanned for per-file notes. Each entry maps a directory (or single
# file) to the vault-relative folder that receives its notes.
SOURCES = [
    ("reveda.py", "reveda.md"),
    ("revedaEditor", "revedaEditor"),
    ("defaultPDK", "defaultPDK"),
    ("scripts", "scripts"),
]

PRIVATE_SOURCES = {
    Path("scripts/generate_license.py"),
    Path("scripts/obfuscate_key.py"),
}

# Curated one-line purposes; overrides the module docstring when present.
PURPOSES = {
    "reveda.py": "Application entrypoint: builds ``revedaApp`` (a QApplication subclass), resolves the project directory, loads ``.env``, configures ``reveda.log``, discovers the PDK/plugins, opens :class:`MainWindow`, and drives the project-switch restart loop.",
    "revedaEditor/__init__.py": "Package marker; carries ``__version__``/``__author__`` metadata.",
    "revedaEditor/backend/__init__.py": "Package marker for the non-GUI backend layer (library model, undo commands, loaders, process/project management).",
    "revedaEditor/backend/bindkeys.py": "Bindkey configuration: ``{section: {keySeq: actionName}}`` maps (shipped defaults in ``resources/bindkeys.json`` + project ``bindkeys.json`` override) applied to editor QActions; unknown actions/keys are skipped safely.",
    "revedaEditor/backend/cellviewState.py": "Qt-free cellview lifecycle state: ``.lock`` files (``{pid,user,host,time}``, stale-pid takeover) and ``.autosave`` sidecars (newer-than check, parseability check).",
    "revedaEditor/backend/correspondence.py": "Schematic↔layout correspondence engine (Phase 6): canonical ``sdl`` record accessors, name-correspondence diff → ``SyncPlan``, ``pcellParamsFor`` label→kwarg mapping, ``flylineEndpoints``.",
    "revedaEditor/backend/dataDefinitions.py": "Shared data types: ``edLayer``/``layLayer`` dataclasses and the namedtuple records (``viewNameTuple``, ``viewItemTuple``, pin/layer defs) exchanged between GUI, scenes and fileio.",
    "revedaEditor/backend/drcModelView.py": "Qt table model/view pair used to browse KLayout DRC results.",
    "revedaEditor/backend/editFunctions.py": "Shared small widgets (``shortLineEdit``, ``boldLabel``, ``longLineEdit``); the ``gui/editFunctions.py`` copy is the actively imported one.",
    "revedaEditor/backend/hdlBackEnd.py": "Container classes describing HDL text views (``verilogaC``, ``spiceC``, ``spectreC``, ``vacaskC``).",
    "revedaEditor/backend/libBackEnd.py": "Library model items — ``libraryItem``/``cellItem``/``viewItem`` (QStandardItem subclasses carrying filesystem paths) plus cell/view creation helpers.",
    "revedaEditor/backend/libraryMethods.py": "Model lookup helpers: ``getLibItem``/``getCellItem``/``getViewItem``/``findViewItem`` over the design-libraries QStandardItemModel.",
    "revedaEditor/backend/libraryModelView.py": "``BaseDesignLibrariesView`` and its column/tree concrete views — library tree population, ``openView``/``openCellView`` dispatch through ``EditorFactory``, cell/view create/delete/rename flows, text-view handlers.",
    "revedaEditor/backend/licenseManager.py": "Open-source licensing shim: re-exports the proprietary ``revedaLicense`` module when present, otherwise stubs so the unlicensed build still runs.",
    "revedaEditor/backend/LVSModelView.py": "Qt table models/views for the LVS results browser (nets, devices, cells, cross-references, parameter mismatches).",
    "revedaEditor/backend/pdkLoader.py": "PDK loading: ``importPDKModule`` resolves ``<pdk>.<module>`` against ``REVEDA_PDK_PATH`` and applies PDK menu items declared in the PDK's ``config.json``.",
    "revedaEditor/backend/pluginsLoader.py": "Plugin discovery over ``REVEDA_PLUGIN_PATH`` (``pkgutil`` scan, ``config.json`` menu wiring, ``viewTypes`` dispatch to plugin ``openCellView``/``createCellView``).",
    "revedaEditor/backend/processManager.py": "``ProcessManager`` — QProcess-based launcher for external tools (simulators, checkers) from editor windows.",
    "revedaEditor/backend/projectManager.py": "Project open/switch orchestration and ``reveda.conf`` persistence: paths, view lists, window geometry, autosave prefs, and the ``openCellviews`` session; plus the QSettings-backed recent-projects store.",
    "revedaEditor/backend/startThread.py": "Thin ``QThread`` wrapper used to run background work off the GUI thread.",
    "revedaEditor/backend/undoStack.py": "``undoStack`` (QUndoStack subclass) and every ``QUndoCommand`` used for undoable scene edits (add/delete/move/copy/rotate/transform/group/rename...).",
    "revedaEditor/checks/__init__.py": "Package marker for design-rule check modules.",
    "revedaEditor/checks/schematic.py": "Schematic check rules producing ``checkViolation`` records: symbol overlaps, unconnected/dangling nets, floating pins, shorted outputs, net-name conflicts — the data behind the marker browser.",
    "revedaEditor/common/__init__.py": "Package marker for shared graphics items and helpers.",
    "revedaEditor/common/fileCache.py": "``FileCache`` — file-content cache keyed by modification time, used to avoid re-reading unchanged JSON.",
    "revedaEditor/common/labels.py": "Label items (``schematicLabel``, ``symbolLabel``) and PyLabel machinery — labels whose text is computed by PDK callback classes and rendered with ``quantiphy.Quantity``.",
    "revedaEditor/common/layoutBoolean.py": "Phase 5 boolean layer operations — per-layer or/and/xor, A-NOT-B subtraction, grow/shrink via ``gdstk``; returns ``(produced, consumed)`` items for undo commands.",
    "revedaEditor/common/layoutFlatten.py": "Hierarchy restructuring helpers: ``flattenInstance`` bakes instance subtrees (arrays, rotations, multipart children) to scene-coordinate leaf items; ``makeCellFromSelection`` writes a new cell and swaps in an instance.",
    "revedaEditor/common/layoutMerge.py": "Geometry engine behind layout Merge: union-find over touching same-layer shapes, path merging, rect/polygon unions via gdstk.",
    "revedaEditor/common/layoutShapes.py": "All layout graphics items — ``layoutRect/Path/Via/Pin/Label/Polygon``, ``layoutInstance``/``layoutPcell`` (incl. mosaics), ``layoutRuler``, ``layoutFlightLine``, and the ``layoutMultipart`` family (guard ring, shielded path, bus route).",
    "revedaEditor/common/net.py": "Schematic wire/bus graphics items (``schematicNet``), net-name label items, and name-strength machinery.",
    "revedaEditor/common/params.py": "Typed instance-parameter model (CDF-lite): ``ParamDef`` definitions, validation/normalization, default resolution, and schematic-label↔parameter bridging.",
    "revedaEditor/common/shapes.py": "Schematic/symbol graphics items: base ``symbolShape`` classes, pins, rectangles, lines, arcs, circles, polygons, text, and the ``schematicSymbol`` instance item.",
    "revedaEditor/connectivity/__init__.py": "Package facade re-exporting the unified connectivity engine API used by GUI scenes, decoded JSON records, importers and tests.",
    "revedaEditor/connectivity/adapters.py": "Adapters converting decoded records and live scene items into engine shapes — including hierarchy expansion of ``layoutInstance``/``layoutPcell``/multipart children for net highlight.",
    "revedaEditor/connectivity/diagnostics.py": "Headless semantic checks on decoded design arrays (dangling ends, param problems, layout record diagnostics).",
    "revedaEditor/connectivity/graph.py": "Union-find connectivity graph: merges shapes through geometric touch and via-stack rules into net groups.",
    "revedaEditor/connectivity/layout.py": "Layout-domain connectivity analysis: ``analyzeLayoutItems``, net naming, via stacks and PCell pin bridging.",
    "revedaEditor/connectivity/netexpr.py": "Net-expression / inherited-connection (``netSet``) parsing and evaluation — ``<*N>`` replication, global nets, expression terminals.",
    "revedaEditor/connectivity/primitives.py": "Shared primitives: shape-record normalization and point/segment/rect predicates consumed by the engine.",
    "revedaEditor/connectivity/resolve.py": "Net-name resolution — the single implementation behind ``nameSceneNets`` semantics (sheet pins, SET-strength wire names, conflict handling).",
    "revedaEditor/fileio/__init__.py": "Package marker for file format importers/exporters/encoders.",
    "revedaEditor/fileio/createSymbols.py": "Symbol generation from schematics (Create→Symbol): derives symbol pins from schematic pins and emits ``symbol.json``.",
    "revedaEditor/fileio/exportGDS.py": "GDS/OAS stream-out: walks the layout scene through hierarchy into ``gdstk``, honoring ``layerMap``/``cellNameMap``/``flattenDepth`` stream options.",
    "revedaEditor/fileio/extractedSchematic.py": "``klayoutSchematicGenerator`` — reconstructs a schematic view from an extracted (RCX/LVS) netlist.",
    "revedaEditor/fileio/importGDS.py": "GDS stream-in: ``gdsImporter`` reads gdstk records into ``lib/cell/layout.json`` files, with merge mode that appends to existing cells.",
    "revedaEditor/fileio/importLayp.py": "``.lyp`` layer-properties XML import (KLayout-style) converting layer definitions/stipples into Revolution EDA layer data.",
    "revedaEditor/fileio/importlvsdb.py": "KLayout LVS database (``.lvsdb``) parser producing error markers (``LVSErrorRect``) for the results browser.",
    "revedaEditor/fileio/importlyrdb.py": "KLayout DRC XML report (``.lyrdb``) to dictionary/marker conversion.",
    "revedaEditor/fileio/importSpectre.py": "Spectre netlist/model import into cellviews.",
    "revedaEditor/fileio/importSpice.py": "SPICE subcircuit import — converts ``.sp`` netlists into schematic/symbol cellviews.",
    "revedaEditor/fileio/importVacask.py": "VACASK netlist import into cellviews.",
    "revedaEditor/fileio/importVeriloga.py": "Verilog-A module import into cellviews.",
    "revedaEditor/fileio/importXschemSym.py": "Xschem symbol-file import/conversion into symbol cellviews.",
    "revedaEditor/fileio/layoutEncoder.py": "``layoutEncoder`` — json.JSONEncoder mapping layout scene items to ``Rect/Path/Via/Pin/Label/Polygon/Inst/Pcell/Multipart`` records (scene-origin-relative coordinates, optional ``sdl`` metadata).",
    "revedaEditor/fileio/loadJSON.py": "JSON→scene reconstruction: ``schematicItems``/``layoutItems`` loaders, symbol pin locators, draft-symbol fallback for missing libraries, PCell instance creation.",
    "revedaEditor/fileio/schematicEncoder.py": "``schematicEncoder`` — scene items → ``sys/scn/scp/txt/pin/label/attr/net`` JSON records.",
    "revedaEditor/fileio/schemaValidation.py": "JSON-schema validation of design files (``schemas/*.schema.json``) with readable error formatting.",
    "revedaEditor/fileio/spiceNetlist.py": "SPICE/extracted-netlist parsing utilities: subcircuit hierarchy trees, device-line parsing.",
    "revedaEditor/fileio/symbolEncoder.py": "``symbolEncoder`` — symbol scene items → ``symbol.json`` records.",
    "revedaEditor/gui/__init__.py": "Package marker for windows, dialogs and editor chrome.",
    "revedaEditor/gui/alignItems.py": "Align-items dialog plus the edge/line alignment geometry helpers it invokes.",
    "revedaEditor/gui/configEditor.py": "Hierarchy config-view editor: ``configEditor`` window + container driving switch/stop view traversal.",
    "revedaEditor/gui/editFunctions.py": "Shared small widgets (``shortLineEdit``, ``boldLabel``, ``longLineEdit``) used across dialogs.",
    "revedaEditor/gui/editorFactory.py": "``EditorFactory.createEditor`` — viewType → editor-class dispatch for the standard editors.",
    "revedaEditor/gui/editorTypes.py": "``Protocol`` definitions typing the editor-window/container contract (``EditorContainer``, ``BaseEditor``).",
    "revedaEditor/gui/editorViews.py": "``editorView`` (QGraphicsView): zoom/pan, ``viewRect`` tracking, grid/line background rendering, mouse/key event forwarding to the scene.",
    "revedaEditor/gui/editorWindow.py": "``editorWindow`` — QMainWindow base class for all editors: menus/toolbars/actions, hardcoded+bindkey shortcuts, cellview lock acquisition, autosave timer, autosave-restore prompt, print/export plumbing.",
    "revedaEditor/gui/fileDialogues.py": "Cell/view/library dialogs: create/delete/rename/copy/select-cellview dialogs and the library dialogs.",
    "revedaEditor/gui/findDialogue.py": "Non-modal find/replace dialog and the check-marker browser for the schematic editor.",
    "revedaEditor/gui/helpBrowser.py": "Markdown documentation browser plus about/license dialogs.",
    "revedaEditor/gui/layoutDialogues.py": "Layout creation/property dialogs: instance placement (incl. arrays), paths, pins, labels, vias, multipart parameters, layer ops.",
    "revedaEditor/gui/layoutEditor.py": "``layoutEditor`` window + ``layoutContainer``: layout menus/actions, save/load, GDS export, SDL sync, flyline and cross-probe actions.",
    "revedaEditor/gui/libraryBrowser.py": "``libraryBrowser`` — the design-libraries window hosting the column/tree view, context menus, and new/open cellview entry points.",
    "revedaEditor/gui/libraryRegistry.py": "Library registry window for managing configured libraries.",
    "revedaEditor/gui/lsw.py": "Layer Selection Window (LSW): layer table model/view, object-filter table, stipple delegate.",
    "revedaEditor/gui/lvsResults.py": "LVS results dialog presenting the imported LVS database.",
    "revedaEditor/gui/pdkRegistry.py": "PDK registry window for managing configured PDKs.",
    "revedaEditor/gui/pluginsRegistry.py": "Plugin registry window with background download thread.",
    "revedaEditor/gui/propertyDialogues.py": "Schematic/symbol property and creation dialogs (instance placement, pins, labels, parameter widgets).",
    "revedaEditor/gui/pythonConsole.py": "Interactive Python console widget embedded in the main window (stdin/stdout redirection, history).",
    "revedaEditor/gui/revedaMain.py": "``MainWindow`` — application shell: menus, library-browser host, ``openViews`` registry, ``reveda.conf`` app state + session persistence, bindkey map loading, autosave preferences.",
    "revedaEditor/gui/revinit.py": "Version constant (``__version__``).",
    "revedaEditor/gui/schematicEditor.py": "``schematicEditor`` window + ``schematicContainer``: schematic menus/actions, load/save flows, config-view creation.",
    "revedaEditor/gui/stippleEditor.py": "Stipple-pattern editor for LSW fill textures.",
    "revedaEditor/gui/symbolEditor.py": "``symbolEditor`` window + ``symbolContainer``: symbol drawing actions, label/attribute dialogs.",
    "revedaEditor/gui/textEditor.py": "Text-editor family (JSON/Verilog-A/SPICE/Spectre/VACASK/Xyce) with per-language syntax highlighters.",
    "revedaEditor/gui/toolsDialogues.py": "``findProjectEditors`` dialog for locating open editor windows.",
    "revedaEditor/gui/utilDialogues.py": "Customized print dialog (``revedaPrintDialog``).",
    "revedaEditor/netlisting/__init__.py": "Package marker for netlist writers.",
    "revedaEditor/netlisting/exprSupport.py": "Inherited-connection (netSet / net-expression) support helpers shared by the netlisters.",
    "revedaEditor/netlisting/spectreNetlist.py": "Spectre netlist writer built on the unified connectivity engine.",
    "revedaEditor/netlisting/vacaskNetlist.py": "VACASK netlist writer built on the unified connectivity engine.",
    "revedaEditor/netlisting/xyceNetlist.py": "Xyce netlist writer built on the unified connectivity engine.",
    "revedaEditor/rcextraction/__init__.py": "Package marker for the RC-extraction flow.",
    "revedaEditor/rcextraction/extractor.py": "Unified RC extractor consuming the RCX database: parasitic R/C modeling, device pin anchoring, coupling capacitance.",
    "revedaEditor/rcextraction/layoutGeometry.py": "Record-driven layout geometry reader feeding the extractor — independent of the live scene.",
    "revedaEditor/rcextraction/netlist.py": "Parasitic (DSPF-style) netlist emission for extraction results.",
    "revedaEditor/rcextraction/rcxExport.py": "RCX database export helpers.",
    "revedaEditor/rcextraction/rcx_schema.py": "RCX database schema definitions.",
    "revedaEditor/rcextraction/tech.py": "RCX technology-file (process stackup) parsing.",
    "revedaEditor/resources/resources.py": "Compiled Qt resource module (icons) generated from ``reveda.qrc`` by ``pyside6-rcc`` — regenerated, never edited.",
    "revedaEditor/scenes/__init__.py": "Package marker for the editor scenes.",
    "revedaEditor/scenes/editorScene.py": "``editorScene`` — QGraphicsScene base: edit modes, selection machinery, undo stack, mouse dispatch, grid settings, read-only event filter, ``_safeLoadDesign``/``reloadScene``.",
    "revedaEditor/scenes/layoutScene.py": "``layoutScene`` — layout editing state: ``saveLayoutCell``/``loadDesign``, connectivity + net highlighting, SDL incremental sync, flylines, boolean/flatten/merge/multipart operations.",
    "revedaEditor/scenes/schematicScene.py": "``schematicScene`` — wires/pins/labels/instances editing: ``saveSchematic``/``loadDesign``, ``nameSceneNets``, checks + markers, EIP ghost hierarchy, bus ripper, clipboard.",
    "revedaEditor/scenes/symbolScene.py": "``symbolScene`` — symbol drawing editing: ``saveSymbolCell``/``loadDesign``, attribute list.",
    "defaultPDK/__init__.py": "Default PDK package marker.",
    "defaultPDK/callbacks.py": "PDK callbacks evaluated by PyLabels/parameter resolution (``Quantity``-rendered values).",
    "defaultPDK/layoutLayers.py": "Layout layer definitions (``layLayer`` dataclasses) for the default PDK.",
    "defaultPDK/pcells.py": "Parameterized-cell classes for the default PDK; exposed through the ``pcells`` registry dict.",
    "defaultPDK/process.py": "Process definitions: GDS layer map, via definitions, path defaults, dbu scale (``fabproc``).",
    "defaultPDK/schLayers.py": "Schematic layer definitions (``edLayer`` dataclasses).",
    "defaultPDK/symLayers.py": "Symbol layer definitions (``edLayer`` dataclasses).",
    "scripts/machine_fingerprint.py": "Machine-fingerprint helper used by license generation.",
    "scripts/generate_devdocs.py": "This generator — rebuilds the developmentDocs vault from the sources.",
    "revedaEditor/tests/__init__.py": "Test package marker.",
    "revedaEditor/tests/conftest.py": "pytest fixtures: offscreen ``QApplication`` and a minimal ``qtbot`` shim (no pytest-qt dependency).",
    "revedaEditor/tests/sceneTestUtils.py": "Headless scene construction helpers — stubbed ``editorWindow``/``appMainW`` so scenes build without real windows.",
    "revedaEditor/tests/test_ai_snapshot_undo.py": "aiTerminal snapshot/undo integration tests.",
    "revedaEditor/tests/test_connectivity.py": "Connectivity engine tests — records→net groups, name resolution, via merging.",
    "revedaEditor/tests/test_correspondence.py": "Phase 6 tests: ``sdl`` persistence, incremental ``updateFromSchematic`` sync, flylines, cross-probing.",
    "revedaEditor/tests/test_diagnostics.py": "Headless connectivity-diagnostics tests.",
    "revedaEditor/tests/test_import_gds.py": "GDS import tests, including merge mode and grid snapping.",
    "revedaEditor/tests/test_labels_nlp.py": "Label/PyLabel evaluation tests.",
    "revedaEditor/tests/test_layout_connectivity.py": "Layout connectivity and hierarchy-aware net-highlight tests (instance internals, mosaics, tap cells).",
    "revedaEditor/tests/test_layout_merge.py": "Layout merge-geometry tests.",
    "revedaEditor/tests/test_layout_productivity.py": "Phase 5 tests: instance mosaics, multipart items, boolean layer ops, flatten/make-cell, stream options, rulers.",
    "revedaEditor/tests/test_layout_ruler.py": "Ruler item tests.",
    "revedaEditor/tests/test_layout_stretch.py": "Layout stretch-edit tests.",
    "revedaEditor/tests/test_layout_transforms.py": "Layout transform/rotation tests.",
    "revedaEditor/tests/test_lvs_mismatch_view.py": "LVS mismatch view tests.",
    "revedaEditor/tests/test_netexpr.py": "Net-expression / netSet tests.",
    "revedaEditor/tests/test_netlisting.py": "Netlister output tests.",
    "revedaEditor/tests/test_net.py": "Schematic net item tests.",
    "revedaEditor/tests/test_params.py": "CDF-lite parameter-model tests.",
    "revedaEditor/tests/test_platform_hardening.py": "Phase 7 tests: lock files, autosave/crash recovery, bindkeys, session save/restore.",
    "revedaEditor/tests/test_schematic_checks.py": "Schematic check-rule tests.",
    "revedaEditor/tests/test_schematic_ux.py": "Schematic UX tests (Phase 4: find/replace, bus ripper, clipboard, edit-in-place).",
    "revedaEditor/tests/test_schema_validation.py": "JSON schema-validation tests.",
    "revedaEditor/tests/test_selection_state.py": "Selection-state machinery tests.",
    "revedaEditor/tests/test_spiceNetlist.py": "SPICE netlist-parsing tests.",
    "revedaEditor/tests/test_symbol_pins.py": "Symbol pin and pin-locator tests.",
    "revedaEditor/tests/test_wire_editing.py": "Wire-editing semantics tests.",
}

PACKAGE_PURPOSES = {
    "revedaEditor": "Revolution EDA application package.",
    "revedaEditor/backend": "Non-GUI backend: library model, undo commands, loaders, correspondence/connectivity state, project/process management.",
    "revedaEditor/checks": "Design-rule check rules and violation records.",
    "revedaEditor/common": "Shared graphics items and geometry/parameter helpers.",
    "revedaEditor/connectivity": "Unified connectivity engine shared by GUI scenes, decoded JSON records, importers and tests.",
    "revedaEditor/fileio": "File-format layer: JSON encoders/loaders, GDS stream in/out, netlist and report importers, schema validation.",
    "revedaEditor/gui": "Windows, dialogs and editor chrome (QMainWindow/QDialog layer).",
    "revedaEditor/netlisting": "Netlist writers for the supported simulators.",
    "revedaEditor/rcextraction": "RC-extraction pipeline (technology parsing, geometry reader, extractor, netlist emission).",
    "revedaEditor/resources": "Compiled Qt resources (icons) and shipped default configuration.",
    "revedaEditor/scenes": "QGraphicsScene subclasses holding editing state per editor type.",
    "revedaEditor/tests": "pytest suite (offscreen Qt) covering connectivity, encoders, layout ops, correspondence and platform hardening.",
    "defaultPDK": "Bundled minimal PDK: layers, process definitions, callbacks, pcells.",
    "scripts": "Build/licensing tooling, not part of the runtime app.",
}


def dottedName(relPath: Path) -> str:
    parts = list(relPath.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts[-1] = "__init__"
    return ".".join(parts)


def notePath(sourceRel: Path) -> Path:
    """Vault-relative note path for a source file."""
    if sourceRel == Path("reveda.py"):
        return Path("reveda.md")
    return sourceRel.with_suffix(".md")


def wikiLink(targetRel: Path, label: str) -> str:
    return f"[[{targetRel.with_suffix('')}|{label}]]"


def mdText(text: str) -> str:
    """Normalize RST-style markup in docstrings/purposes to Markdown."""
    return text.replace("``", "`")


def teaser(purpose: str, limit: int = 140) -> str:
    """First-clause teaser for index listings, without mid-word cuts."""
    text = mdText(purpose).split("\n")[0]
    for sep in (" — ", ". ", ": "):
        head = text.split(sep)[0]
        if len(head) >= 20:
            text = head
            break
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text.rstrip(".:— ")


def extract(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    classes = []
    functions = []
    imports = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "bases": [ast.unparse(b) for b in node.bases],
                "methods": [n.name for n in node.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                "doc": (ast.get_docstring(node) or "").split("\n")[0],
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({"name": node.name,
                              "doc": (ast.get_docstring(node) or "").split("\n")[0]})
        elif isinstance(node, ast.Import):
            imports.update(a.name for a in node.names if a.name.startswith(
                ("revedaEditor", "defaultPDK", "revedaLicense")))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(
                    ("revedaEditor", "defaultPDK", "revedaLicense")):
                imports.add(node.module)
    return {"doc": ast.get_docstring(tree) or "",
            "classes": classes, "functions": functions,
            "imports": sorted(imports)}


def collectSources() -> list[Path]:
    files = []
    for src, _ in SOURCES:
        p = REPO / src
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
    return [
        f for f in files
        if "__pycache__" not in f.parts
        and f.relative_to(REPO) not in PRIVATE_SOURCES
    ]


def main() -> None:
    files = collectSources()
    meta = {f.relative_to(REPO): extract(f) for f in files}
    noteIndex = {rel: notePath(rel) for rel in meta}
    dottedToRel = {dottedName(rel): rel for rel in meta}

    # Reverse dependencies: module -> files importing it
    importedBy = {rel: [] for rel in meta}
    for rel, m in meta.items():
        for imp in m["imports"]:
            # Resolve dotted import to a file (module or package __init__)
            target = dottedToRel.get(imp)
            if target is None:
                target = dottedToRel.get(imp + ".__init__")
            if target is not None and target != rel:
                importedBy[target].append(rel)

    # Fresh vault content (keep hand-written top-level notes)
    for keep in ("Home.md", "Architecture.md", "DataFormats.md", ".obsidian"):
        pass  # listed for clarity; deletion below preserves them
    if VAULT.exists():
        for child in VAULT.iterdir():
            if child.name in ("Home.md", "Architecture.md", "DataFormats.md",
                              ".obsidian"):
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    # --- per-file notes -----------------------------------------------------
    for rel, m in meta.items():
        out = VAULT / notePath(rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        dotted = dottedName(rel) if rel.suffix == ".py" else rel.stem
        purpose = mdText(PURPOSES.get(str(rel))
                         or m["doc"].split("\n\n")[0].strip()
                         or f"Module in `{rel.parent}`.")
        lines = [
            f"# `{rel}`",
            "",
            f"**Module:** `{dotted}`",
            "",
            "## Purpose",
            "",
            purpose,
            "",
        ]
        if m["doc"] and str(rel) in PURPOSES and m["doc"].strip():
            lines += ["## Module docstring", "", mdText(m["doc"].strip()), ""]
        if m["classes"]:
            lines += ["## Classes", ""]
            for c in m["classes"]:
                bases = f"({', '.join(c['bases'])})" if c["bases"] else ""
                doc = f" — {mdText(c['doc'])}" if c["doc"] else ""
                lines.append(f"- `{c['name']}{bases}`{doc}")
                pub = [x for x in c["methods"] if not x.startswith("_")]
                priv = [x for x in c["methods"] if x.startswith("_")
                        and x != "__init__"]
                for meth in pub:
                    lines.append(f"  - `{meth}()`")
                if priv:
                    shown = ", ".join(f"`{x}()`" for x in priv[:12])
                    more = f" … (+{len(priv) - 12})" if len(priv) > 12 else ""
                    lines.append(f"  - internals: {shown}{more}")
            lines.append("")
        if m["functions"]:
            lines += ["## Functions", ""]
            for f in m["functions"]:
                doc = f" — {mdText(f['doc'])}" if f["doc"] else ""
                lines.append(f"- `{f['name']}()`{doc}")
            lines.append("")
        deps = [r for r in (dottedToRel.get(i)
                        or dottedToRel.get(i + ".__init__") for i in m["imports"])
                if r is not None]
        if deps:
            lines += ["## Depends on", ""]
            for d in sorted(set(deps)):
                lines.append(f"- {wikiLink(noteIndex[d], dottedName(d))}")
            lines.append("")
        users = sorted(set(importedBy.get(rel, [])))
        if users:
            lines += ["## Used by", ""]
            for u in users:
                lines.append(f"- {wikiLink(noteIndex[u], dottedName(u))}")
            lines.append("")
        out.write_text("\n".join(lines), encoding="utf-8")

    # --- package index notes ------------------------------------------------
    packages = {}
    for rel in meta:
        if rel == Path("reveda.py"):
            continue
        packages.setdefault(rel.parent, []).append(rel)
    for pkgDir, members in sorted(packages.items()):
        relMembers = sorted(members, key=lambda r: r.name)
        idx = VAULT / pkgDir / "index.md"
        idx.parent.mkdir(parents=True, exist_ok=True)
        purpose = PACKAGE_PURPOSES.get(str(pkgDir), "")
        lines = [f"# `{pkgDir}`", ""]
        if purpose:
            lines += [purpose, ""]
        lines += ["## Modules", ""]
        for r in relMembers:
            first = teaser(PURPOSES.get(str(r))
                           or meta[r]["doc"].split("\n\n")[0].strip())
            lines.append(f"- {wikiLink(noteIndex[r], r.name)}"
                         + (f" — {first}" if first else ""))
        idx.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"developmentDocs: {len(meta)} file notes + {len(packages)} package "
          f"indexes written to {VAULT}")


if __name__ == "__main__":
    main()
