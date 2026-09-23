# Data Formats

Everything persistent is JSON under the project directory
(`<project>/<library>/<cell>/<view>.json`). Schemas live in
`revedaEditor/fileio/schemas/` and are enforced by
[[revedaEditor/fileio/schemaValidation|schemaValidation]].

## Cellview JSON

Each view file is a JSON array:

```
[ {"viewType": ..., "schemaVersion": "1.0"},        # header
  {"snapGrid": [x, y], "snapConnectDistance": n},   # grid record
  <item records...> ]                               # encoded scene items
```

Coordinates are **scene-origin-relative** — encoders subtract the content
bounding origin (`_subtract_point`), so instance position moves don't shift
internal geometry.

- **schematic.json** — `sys`/`scn` (instances/pins), `scp` (sheet pins),
  `txt`, `label`, `attr`, `net` (wires), `mrk` (check markers). Written by
  [[revedaEditor/fileio/schematicEncoder|schematicEncoder]], loaded by
  [[revedaEditor/fileio/loadJSON|loadJSON]] `schematicItems`.
- **symbol.json** — shape records + `attr` list. `symbolEncoder` /
  `symbolScene.loadDesign`.
- **layout.json** — `Rect`, `Path`, `Via`, `Pin`, `Label`, `Polygon`,
  `Inst`, `Pcell` (+ optional `rows`/`cols`/`rpt`/`cpt` for mosaics and `sdl`
  for schematic correspondence), `Multipart` (`{"kind", "params"}` — children
  are *never* serialized, they regenerate from params), `Group`
  (`{"items": [...]}` — member records are stored in group-local
  coordinates; the group's own `loc`/`top`/`ang`/`fl` carries the transform
  it accumulated while grouped, same convention as `Inst`; groups nest).
  `layoutEncoder` / `layoutScene.loadDesign`.
- **pcell.json** — `{"cellView": "pcell", "reference": "<pcellClass>"}` —
  resolved against `pcells.pcells` at load time.
- **config.json** (cell-level) — hierarchy config: switch/stop view choices.

## Sidecar files (Phase 7)

Written next to the cellview JSON; the `.tmp` staging files used by the
atomic writers are name-derived (`<file>.tmp`), so the sidecars' staging files
never collide with the primary save's.

| File | Contents | Lifecycle |
|---|---|---|
| `<view>.json.lock` | `{"pid","user","host","time"}` | Created on open; foreign-live-pid → read-only; dead/malformed → taken over; removed on close (ownership-checked) |
| `<view>.json.autosave` | Full cellview JSON snapshot | Written by the autosave timer when dirty; offered for recovery when newer **and** parseable; deleted on save/close/decline |

## `reveda.conf` (project root)

```jsonc
{
  "runPath": "...", "pdkPath": "...", "outputPrefixPath": "...",
  "switchViewList": ["schematic"], "stopViewList": ["layout"],
  "windowGeometry": [x, y, w, h],
  "threadPoolMaxCount": 8,
  "autosaveEnabled": true, "autosaveIntervalSec": 300,
  "openCellviews": [                      // session restore
    {"library": "lib", "cell": "c", "view": "schematic",
     "geometry": [x, y, w, h],
     "viewRect": [x, y, w, h]}            // scene coords → zoom state
  ]
}
```

Written by `MainWindow.saveAppState` and
`ProjectManager.save_current_state`; applied by `loadAppState` /
`ProjectManager._apply_state` (which also calls `_restoreSessionViews`).

## `bindkeys.json`

```jsonc
{
  "*":         {"Ctrl+S": "saveCellAction", "U": "undoAction"},
  "schematic": {"W": "createNetAction"},
  "layout":    {"W": "createPathAction"},
  "symbol":    {"W": "createLineAction"}
}
```

`{keySequence: QAction attribute name}` per section; `"*"` applies to all
editors, the view-type section overrides it. Multiple key sequences may map to
the same action — `applyBindkeys` collects them and calls `setShortcuts` once
per action. Defaults ship in
`revedaEditor/resources/bindkeys.json`; `<project>/bindkeys.json` merges over
them per key. See [[revedaEditor/backend/bindkeys|backend/bindkeys]].

## Other project files

- `library.json` — `{"libdefs": {name: path}}` or `{"include": [...]}`.
- `.env` — `REVEDA_PDK_PATH`, `REVEDA_PLUGIN_PATH` (loaded by ProjectManager).
- `pcellParameterMap.json` (PDK) — schematic label names → pcell kwargs.
