# `revedaEditor\tests\test_plugin_api.py`

**Module:** `revedaEditor.tests.test_plugin_api`

## Purpose

Plugin contract tests: version/capability negotiation and update checks.

## Classes

- `_FakePool` — QThreadPool stand-in that records started workers.
  - `start()`

## Functions

- `_make_plugin()` — Write a minimal importable plugin package under `root`.
- `app_logger()` — Give the session QApplication the `logger` pluginsLoader expects.
- `test_parse_version()`
- `test_version_newer()`
- `test_empty_config_is_compatible()`
- `test_supported_api_version_is_compatible()`
- `test_newer_api_blocks_import()`
- `test_non_integer_api_blocks_import()`
- `test_min_app_version()`
- `test_max_app_version()`
- `test_unparseable_app_constraint_blocks()`
- `test_requires_core()`
- `test_multiple_issues_reported()`
- `test_updates_available()`
- `test_updates_available_handles_junk()`
- `test_loader_gates_and_capabilities()`
- `test_incompatible_or_failed_sdl_plugin_is_not_provider()`
- `test_licensed_capability_provider_controls_menu_injection()`
- `test_loader_pluginless_config_still_imports()` — A package without config.json loads under the api-1 contract.
- `test_update_check_throttle()`
- `test_update_check_skipped_without_plugins()`
- `test_registry_result_logs_updates()`

## Depends on

- [[revedaEditor\backend\__init__|revedaEditor.backend.__init__]]
- [[revedaEditor\backend\pluginsLoader|revedaEditor.backend.pluginsLoader]]
