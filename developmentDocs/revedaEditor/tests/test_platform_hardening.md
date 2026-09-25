# `revedaEditor\tests\test_platform_hardening.py`

**Module:** `revedaEditor.tests.test_platform_hardening`

## Purpose

Phase 7 — platform hardening: autosave/crash recovery, cellview lock
files, configurable bindkeys, and session save/restore in reveda.conf.

## Functions

- `init_qapp()`
- `test_cellview_sidecar_paths()`
- `test_lock_write_read_roundtrip()`
- `test_acquire_lock_held_then_contended()`
- `test_acquire_lock_takes_over_stale()`
- `test_acquire_lock_malformed_is_stale()`
- `test_acquire_lock_does_not_probe_or_replace_remote_owner()`
- `test_release_lock_only_ours()`
- `test_process_alive_checks()`
- `test_is_autosave_newer()`
- `_editor_stub()` — Duck-typed editorWindow for driving its Phase-7 methods unbound.
- `test_autosave_writes_when_dirty()`
- `test_autosave_skips_clean_and_unchanged()`
- `test_autosave_skips_readonly_and_preview()`
- `test_save_cellview_to_dispatches_scene_method()`
- `test_save_cellview_to_reports_false_save_result()`
- `test_resolve_load_path_prompts_and_restores()`
- `test_resolve_load_path_decline_removes_autosave()`
- `test_resolve_load_path_no_prompt_without_lock()` — A read-only (contended) editor never gets the restore prompt.
- `test_lock_contention_forces_readonly()`
- `test_clear_autosave()`
- `test_devdocs_sources_exclude_private_ignored_modules()`
- `test_bindkey_defaults_shipped_loadable()`
- `test_bindkey_user_override_merges()`
- `test_bindkey_malformed_files_skipped()`
- `test_apply_bindkeys_sets_shortcuts()`
- `test_apply_bindkeys_viewtype_scoping()`
- `_library_model()` — Real QStandardItemModel with lib/cell/view items for restore tests.
- `_fake_mainwindow()`
- `test_session_snapshot_entries()`
- `test_session_restore_opens_views()`
- `test_session_restore_skips_missing()`
- `test_session_restore_no_duplicates()`
- `test_project_manager_persists_session()` — reveda.conf round-trip: snapshot entries land in saved config.

## Depends on

- [[revedaEditor\backend\bindkeys|revedaEditor.backend.bindkeys]]
- [[revedaEditor\backend\cellviewState|revedaEditor.backend.cellviewState]]
- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\revedaMain|revedaEditor.gui.revedaMain]]
