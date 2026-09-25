# `revedaEditor\tests\test_layout_connectivity.py`

**Module:** `revedaEditor.tests.test_layout_connectivity`

## Purpose

Tests for the unified layout connectivity engine and layoutScene
integration (connectivity.layout + adapters.fromLayoutItems).

## Functions

- `init_qapp()`
- `_rect()`
- `_analyze()`
- `test_same_layer_touching_rects_merge()`
- `test_same_layer_separated_rects_stay_separate()`
- `test_different_layers_do_not_merge()`
- `test_via_bridges_lower_and_upper_metal()`
- `test_via_does_not_merge_unrelated_shapes()`
- `test_path_footprint_merges_with_rect()`
- `test_touch_tolerance_bridges_small_gap()`
- `test_label_names_net()`
- `test_pin_names_net()`
- `test_unnamed_nets_get_deterministic_auto_names()`
- `test_auto_names_skip_used_names()`
- `test_conflicting_labels_reported()`
- `test_group_order_is_canonical()` — Group ordering follows geometry, not input order.
- `test_via_array_bridges_metals()`
- `test_layrect_point_containment()`
- `test_layoutScene_connectivity_groups_and_names()`
- `test_layoutScene_cache_invalidates_on_add()`
- `test_layoutScene_highlight_net()`
- `test_layoutScene_highlight_by_label()`
- `test_layoutScene_removed_member_drops_overlay()`
- `_instance()`
- `test_instance_internals_join_top_level_net()` — Internal metal/pin merge geometrically with routing landing on them.
- `test_instance_pin_names_do_not_anchor_nets()` — Instance terminal names must not rename or conflict with the net.
- `test_layoutScene_highlight_through_instance()` — The psub-tap case: highlighting the routed net paints the tap's
- `test_highlight_reaches_mosaic_elements()` — Array-element clones join connectivity like the base element.
- `test_highlight_reaches_nested_instances()` — Internals of an instance nested inside another instance resolve.
- `_bruteforcePartition()` — Reference O(n^2) grouping: returns a frozenset of frozensets of shape
- `_groupPartition()`
- `test_grid_matches_bruteforce_random()` — Randomized equivalence: grid grouping == pairwise grouping.
- `test_grid_prunes_far_shapes()` — The index must not quadratic-scan: N spaced-out shapes should cost

## Depends on

- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[defaultPDK\process|defaultPDK.process]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor\connectivity\layout|revedaEditor.connectivity.layout]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
