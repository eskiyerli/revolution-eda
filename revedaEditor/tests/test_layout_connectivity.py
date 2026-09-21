"""Tests for the unified layout connectivity engine and layoutScene
integration (connectivity.layout + adapters.fromLayoutItems)."""

import pytest
from PySide6.QtCore import QLineF, QPoint
from PySide6.QtWidgets import QApplication

from defaultPDK.layoutLayers import m1Layer_drw, m2Layer_drw, m1layer_txt
from defaultPDK.process import v1
from revedaEditor.common import layoutShapes as lshp
import revedaEditor.connectivity as conn
from revedaEditor.connectivity.layout import LayRect

from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _rect(x1, y1, x2, y2, layer=m1Layer_drw):
    return lshp.layoutRect(QPoint(x1, y1), QPoint(x2, y2), layer)


def _analyze(items, touchTolerance=0.0):
    shapes, vias, anchors, _s, _v, _a = conn.fromLayoutItems(items)
    groups = conn.buildConnectivity(shapes, vias,
                                    touchTolerance=touchTolerance)
    names, conflicts, autoCount = conn.assignNetNames(
        groups, anchors, touchTolerance=touchTolerance)
    return groups, names, conflicts, autoCount


def test_same_layer_touching_rects_merge():
    a = _rect(0, 0, 100, 100)
    b = _rect(100, 0, 200, 100)  # shares edge x=100
    groups, *_ = _analyze([a, b])
    assert len(groups) == 1
    assert len(groups[0].shapes) == 2


def test_same_layer_separated_rects_stay_separate():
    a = _rect(0, 0, 100, 100)
    b = _rect(200, 0, 300, 100)
    groups, *_ = _analyze([a, b])
    assert len(groups) == 2


def test_different_layers_do_not_merge():
    a = _rect(0, 0, 100, 100, layer=m1Layer_drw)
    b = _rect(0, 0, 100, 100, layer=m2Layer_drw)  # fully overlapping, diff layer
    groups, *_ = _analyze([a, b])
    assert len(groups) == 2


def test_via_bridges_lower_and_upper_metal():
    m1 = _rect(0, 0, 100, 100, layer=m1Layer_drw)
    m2 = _rect(0, 200, 100, 300, layer=m2Layer_drw)
    via = lshp.layoutVia(QPoint(25, 50), v1, 50, 100)
    # via footprint spans y=50..150: touches m1 (0..100) and m2 (200..300)?
    # No — adjust m2 to overlap the via footprint.
    m2 = _rect(0, 100, 100, 300, layer=m2Layer_drw)
    groups, *_ = _analyze([m1, m2, via])
    assert len(groups) == 1
    assert len(groups[0].vias) == 1


def test_via_does_not_merge_unrelated_shapes():
    m1 = _rect(0, 0, 100, 100, layer=m1Layer_drw)
    m2 = _rect(500, 0, 600, 100, layer=m2Layer_drw)
    via = lshp.layoutVia(QPoint(25, 25), v1, 50, 50)  # lands only on m1
    groups, *_ = _analyze([m1, m2, via])
    assert len(groups) == 2
    m1Group = next(g for g in groups if g.vias)
    assert len(m1Group.vias) == 1


def test_path_footprint_merges_with_rect():
    # Horizontal path from x=0..200 at y=50, width 20 -> spans y=40..60.
    path = lshp.layoutPath(QLineF(0, 50, 200, 50), m1Layer_drw,
                           width=20, mode=2)
    rect = _rect(190, 40, 300, 60)
    groups, *_ = _analyze([path, rect])
    assert len(groups) == 1


def test_touch_tolerance_bridges_small_gap():
    a = _rect(0, 0, 100, 100)
    b = _rect(105, 0, 200, 100)  # 5-unit gap
    groups, *_ = _analyze([a, b], touchTolerance=0.0)
    assert len(groups) == 2
    groups, *_ = _analyze([a, b], touchTolerance=10.0)
    assert len(groups) == 1


def test_label_names_net():
    rect = _rect(0, 0, 100, 100)
    label = lshp.layoutLabel(QPoint(50, 50), "vss", "Arial", "Regular",
                             "1.0", "Left", "R0", m1layer_txt)
    groups, names, conflicts, _ = _analyze([rect, label])
    assert len(groups) == 1
    assert names == ["vss"]
    assert not conflicts


def test_pin_names_net():
    pin = lshp.layoutPin(QPoint(0, 0), QPoint(100, 100), "vdd",
                         "Input", "Signal", m1Layer_drw)
    rect = _rect(50, 50, 300, 150)
    groups, names, conflicts, _ = _analyze([pin, rect])
    assert len(groups) == 1
    assert names == ["vdd"]


def test_unnamed_nets_get_deterministic_auto_names():
    a = _rect(0, 0, 100, 100)
    b = _rect(500, 0, 600, 100)
    _groups, names, _c, autoCount = _analyze([a, b])
    assert names == ["net0", "net1"]
    assert autoCount == 2


def test_auto_names_skip_used_names():
    named = _rect(0, 0, 100, 100)
    label = lshp.layoutLabel(QPoint(50, 50), "net0", "Arial", "Regular",
                             "1.0", "Left", "R0", m1layer_txt)
    unnamed = _rect(500, 0, 600, 100)
    _groups, names, _c, _a = _analyze([named, label, unnamed])
    assert names == ["net0", "net1"]


def test_conflicting_labels_reported():
    rect = _rect(0, 0, 100, 100)
    l1 = lshp.layoutLabel(QPoint(20, 50), "vss", "Arial", "Regular",
                          "1.0", "Left", "R0", m1layer_txt)
    l2 = lshp.layoutLabel(QPoint(80, 50), "vdd", "Arial", "Regular",
                          "1.0", "Left", "R0", m1layer_txt)
    _groups, names, conflicts, _ = _analyze([rect, l1, l2])
    assert names == ["vss"]  # first anchor wins
    assert len(conflicts) == 1


def test_group_order_is_canonical():
    """Group ordering follows geometry, not input order."""
    a = _rect(0, 0, 100, 100)
    b = _rect(500, 0, 600, 100)
    c = _rect(1000, 0, 1100, 100)
    g1, n1, _c1, _a1 = _analyze([a, b, c])
    g2, n2, _c2, _a2 = _analyze([c, a, b])
    centers1 = [g.shapes[0].footprint.x1 for g in g1]
    centers2 = [g.shapes[0].footprint.x1 for g in g2]
    assert centers1 == centers2 == sorted(centers1)
    assert n1 == n2 == ["net0", "net1", "net2"]


def test_via_array_bridges_metals():
    m1 = _rect(0, 0, 200, 100, layer=m1Layer_drw)
    m2 = _rect(0, 100, 200, 300, layer=m2Layer_drw)
    proto = lshp.layoutVia(QPoint(0, 0), v1, 50, 50)
    # 2x1 array: cuts at x=0 and x=80, each 50 wide; positioned via pos()
    # like the loader does -> footprint x 25..155, y 50..125.
    array = lshp.layoutViaArray(QPoint(0, 0), proto, 30, 0, 2, 1)
    array.setPos(QPoint(25, 50))
    groups, *_ = _analyze([m1, m2, array])
    assert len(groups) == 1
    assert groups[0].vias[0].nx == 2


def test_layrect_point_containment():
    r = LayRect(0, 0, 100, 100)
    assert r.contains_point(50, 50)
    assert r.contains_point(105, 50, tol=10)
    assert not r.contains_point(105, 50)


# --- layoutScene integration -----------------------------------------------


def test_layoutScene_connectivity_groups_and_names(qapp):
    scene = makeLayoutScene()
    scene.addItem(_rect(0, 0, 100, 100))
    scene.addItem(_rect(100, 0, 200, 100))
    scene.addItem(_rect(500, 0, 600, 100))
    groups = scene.connectivity
    assert len(groups) == 2
    named = sorted(g.name for g in groups)
    assert all(name for name in named)


def test_layoutScene_cache_invalidates_on_add(qapp):
    scene = makeLayoutScene()
    scene.addItem(_rect(0, 0, 100, 100))
    assert len(scene.connectivity) == 1
    scene.addItem(_rect(500, 0, 600, 100))
    assert len(scene.connectivity) == 2


def test_layoutScene_highlight_net(qapp):
    scene = makeLayoutScene()
    rectA = _rect(0, 0, 100, 100)
    rectB = _rect(50, 50, 200, 150)  # touches rectA -> same net
    rectC = _rect(500, 0, 600, 100)
    for item in (rectA, rectB, rectC):
        scene.addItem(item)
    name = scene.highlightNetAtPoint(QPoint(10, 10))
    assert name is not None
    # Two member shapes -> two overlay rects; rectC's net is untouched.
    assert len(scene._netHighlightItems) == 2
    assert rectA in scene._netHighlightItems
    assert rectB in scene._netHighlightItems
    assert rectC not in scene._netHighlightItems
    scene.clearNetHighlights()
    assert not scene._netHighlightItems


def test_layoutScene_highlight_by_label(qapp):
    scene = makeLayoutScene()
    scene.addItem(_rect(0, 0, 100, 100))
    label = lshp.layoutLabel(QPoint(50, 50), "vss", "Arial", "Regular",
                             "1.0", "Left", "R0", m1layer_txt)
    label.setPos(QPoint(0, 0))
    scene.addItem(label)
    name = scene.highlightNetAtPoint(QPoint(50, 50))
    assert name == "vss"
    assert len(scene._netHighlightItems) == 1


def test_layoutScene_removed_member_drops_overlay(qapp):
    scene = makeLayoutScene()
    rect = _rect(0, 0, 100, 100)
    scene.addItem(rect)
    scene.highlightNetAtPoint(QPoint(10, 10))
    assert scene._netHighlightItems
    scene.removeItem(rect)
    assert not scene._netHighlightItems
    assert scene.connectivity == []


# --- Instance internals (highlight through hierarchy, e.g. psub taps) -----


def _instance(children, scene, pos=(0, 0), name="X1"):
    inst = lshp.layoutInstance(list(children))
    inst.libraryName = "lib"
    inst.cellName = "cell"
    inst.viewName = "layout"
    inst.counter = 1
    inst.instanceName = name
    inst.setPos(*pos)
    scene.addItem(inst)
    return inst


def test_instance_internals_join_top_level_net():
    """Internal metal/pin merge geometrically with routing landing on them."""
    innerM1 = _rect(0, 0, 50, 50)
    pin = lshp.layoutPin(QPoint(0, 0), QPoint(50, 50), "SUB",
                         "Input", "Signal", m1Layer_drw)
    inst = lshp.layoutInstance([innerM1, pin])
    inst.setPos(1000, 0)
    wire = _rect(950, 10, 1010, 40)
    shapes, vias, anchors, _s, _v, _a = conn.fromLayoutItems(
        [inst, wire])
    groups = conn.buildConnectivity(shapes, vias, touchTolerance=1.0)
    assert len(groups) == 1
    memberItems = {s.item for s in groups[0].shapes}
    assert memberItems == {innerM1, pin, wire}
    # Internal pins contribute no name anchors.
    assert not anchors


def test_instance_pin_names_do_not_anchor_nets():
    """Instance terminal names must not rename or conflict with the net."""
    pin = lshp.layoutPin(QPoint(0, 0), QPoint(50, 50), "SUB",
                         "Input", "Signal", m1Layer_drw)
    inst = lshp.layoutInstance([pin])
    inst.setPos(1000, 0)
    wire = _rect(950, 10, 1010, 40)
    groups, names, conflicts, _a = _analyze([inst, wire])
    assert names == ["net0"]
    assert not conflicts


def test_layoutScene_highlight_through_instance(qapp):
    """The psub-tap case: highlighting the routed net paints the tap's
    internal metal, and clicking the tap's metal resolves the top net."""
    scene = makeLayoutScene()
    innerM1 = _rect(0, 0, 50, 50)
    pin = lshp.layoutPin(QPoint(0, 0), QPoint(50, 50), "SUB",
                         "Input", "Signal", m1Layer_drw)
    # Keep the instance wrapper alive: GC'ing it deletes the C++ item and
    # its children (the scene's itemsRefSet exists for the same reason).
    inst = _instance([innerM1, pin], scene, pos=(1000, 0))
    wire = _rect(950, 10, 1010, 40)
    scene.addItem(wire)

    name = scene.highlightNetAtPoint(QPoint(1020, 25))
    assert name is not None
    assert wire in scene._netHighlightItems
    assert innerM1 in scene._netHighlightItems
    scene.clearNetHighlights()

    name = scene.highlightNetAtPoint(QPoint(960, 25))
    assert name is not None
    assert innerM1 in scene._netHighlightItems
    assert pin in scene._netHighlightItems


def test_highlight_reaches_mosaic_elements(qapp):
    """Array-element clones join connectivity like the base element."""
    scene = makeLayoutScene()
    innerM1 = _rect(0, 0, 50, 50)
    tap = _instance([innerM1], scene)
    tap.setArray(rows=1, cols=2, rowPitch=0, colPitch=200)
    # Wire landing on the second element's metal (offset +200).
    wire = _rect(240, 10, 300, 40)
    scene.addItem(wire)

    name = scene.highlightNetAtPoint(QPoint(250, 25))
    assert name is not None
    assert wire in scene._netHighlightItems
    assert any(item in tap.arrayShapes
               for item in scene._netHighlightItems)


def test_highlight_reaches_nested_instances(qapp):
    """Internals of an instance nested inside another instance resolve."""
    scene = makeLayoutScene()
    innerM1 = _rect(0, 0, 20, 20)
    leaf = lshp.layoutInstance([innerM1])
    leaf.libraryName = "lib"
    leaf.cellName = "leaf"
    leaf.viewName = "layout"
    leaf.counter = 2
    leaf.instanceName = "L1"
    child = _instance([leaf], scene, pos=(500, 500), name="I1")
    wire = _rect(510, 505, 600, 515)
    scene.addItem(wire)

    name = scene.highlightNetAtPoint(QPoint(505, 510))
    assert name is not None
    assert innerM1 in scene._netHighlightItems
    assert wire in scene._netHighlightItems


# ---------------------------------------------------------------------------
# Spatial index: correctness parity + candidate pruning
# ---------------------------------------------------------------------------

def _bruteforcePartition(shapes, vias, tol=0.0):
    """Reference O(n^2) grouping: returns a frozenset of frozensets of shape
    indices forming connected nets."""
    import revedaEditor.connectivity.layout as lay
    parent = list(range(len(shapes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            if (lay._layersMatch(shapes[i].layer_name, shapes[j].layer_name)
                    and shapes[i].footprint.intersects(
                        shapes[j].footprint, tol)):
                union(i, j)
    for via in vias:
        hits = [idx for idx, s in enumerate(shapes)
                if s.footprint.intersects(via.footprint, tol)
                and lay._viaMatchesShape(via, s)[0]]
        for idx in hits[1:]:
            union(hits[0], idx)
    parts = {}
    for i in range(len(shapes)):
        parts.setdefault(find(i), set()).add(i)
    return frozenset(frozenset(v) for v in parts.values())


def _groupPartition(groups):
    parts = []
    for g in groups:
        parts.append(frozenset(s.id_index for s in g.shapes))
    return frozenset(p for p in parts if p)


def test_grid_matches_bruteforce_random():
    """Randomized equivalence: grid grouping == pairwise grouping."""
    import random
    import revedaEditor.connectivity.layout as lay
    rng = random.Random(20260308)
    layer_names = ["m1", "m2", "poly", "ndiff"]
    shapes = []
    for i in range(400):
        x = rng.uniform(0, 5000)
        y = rng.uniform(0, 5000)
        w = rng.uniform(10, 400)
        h = rng.uniform(10, 400)
        s = lay.LayShape(kind="rect", layer_name=layer_names[i % 4],
                         gds_layer=0,
                         footprint=lay.LayRect(x, y, x + w, y + h))
        s.id_index = i
        shapes.append(s)
    vias = []
    for _ in range(40):
        x = rng.uniform(0, 5000)
        y = rng.uniform(0, 5000)
        vias.append(lay.LayVia(via_type="v1", lower_layer="m1",
                               upper_layer="m2",
                               footprint=lay.LayRect(x, y, x + 30, y + 30)))
    groups = lay.buildConnectivity(shapes, vias)
    expected = _bruteforcePartition(shapes, vias)
    assert _groupPartition(groups) == expected
    for vg in groups:
        assert vg.shapes or vg.vias


def test_grid_prunes_far_shapes(monkeypatch):
    """The index must not quadratic-scan: N spaced-out shapes should cost
    ~O(N) footprint tests, not N^2."""
    import revedaEditor.connectivity.layout as lay
    n = 2000
    shapes = [
        lay.LayShape(kind="rect", layer_name="m1", gds_layer=0,
                     footprint=lay.LayRect(i * 100, 0, i * 100 + 50, 50))
        for i in range(n)
    ]
    calls = [0]
    orig = lay.LayRect.intersects

    def counted(self, other, tol=0.0):
        calls[0] += 1
        return orig(self, other, tol)

    monkeypatch.setattr(lay.LayRect, "intersects", counted)
    groups = lay.buildConnectivity(shapes, [])
    assert len(groups) == n
    # Pairwise would be n*(n-1)/2 ~= 2e6 tests; the grid should need only a
    # few per shape (neighbour cells).
    assert calls[0] < 4 * n
