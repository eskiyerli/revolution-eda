# Cellview Schema Version and Migration Policy

## Purpose

Revolution EDA cellviews are long-lived design records. A saved schematic, symbol, or layout must remain readable after the application gains new persisted fields. This policy defines how cellview JSON evolves without silently changing or discarding historical data.

## Scope

The policy applies to ordinary JSON cellviews:

- `schematic`
- `symbol`
- `layout`

Each is an array whose first record is a view header and whose second record is a settings object. PCell definition files use a smaller two-record format and are validated through the same compatibility service, while retaining their established unversioned header format.

## Header contract

New ordinary cellviews use the canonical header:

```json
{"viewType":"schematic","schemaVersion":"1.0"}
```

The active version is defined once by `revedaEditor.fileio.schemaValidation.CURRENT_SCHEMA_VERSIONS`; writers must use `make_view_header(viewType)` rather than embed version literals.

The header declares the persisted format, not the application release. A new application release does not require a schema version change unless stored field semantics change.

## Compatibility rules

| Source format | Loader behavior |
|---|---|
| No `schemaVersion` | Accepted as the legacy baseline. Existing loader defaults handle absent optional fields. The document is not mutated just by opening it. |
| Current labelled version | Accepted unchanged. |
| Earlier labelled version with registered migrations | Migrated through each explicit, ordered migration step before item reconstruction. |
| Earlier labelled version without a complete migration path | Rejected before item construction. |
| Future or unknown labelled version | Rejected before item construction. This prevents a current editor from partially loading and then destroying unknown data on save. |
| Malformed version value | Rejected before item construction. |

The settings record must be an object. `null` settings are rejected because every editor loader reads settings through `.get()`; accepting them at validation time produced inconsistent load failures.

## Migration requirements

A migration is registered centrally in `schemaValidation.py` for one `(viewType, sourceVersion)` transition. It must:

1. Be pure: do not mutate the decoded input.
2. Return a complete JSON array with the normal header/settings structure.
3. Change only fields whose persisted meaning changed.
4. Preserve unknown records and unrelated extension fields.
5. Advance exactly one declared version step.
6. Have regression tests covering source input, transformed output, idempotent preparation, and a real scene load.

Migrations run in memory. Opening a historical cellview never rewrites it. A file acquires the current header only on a later explicit save.

## Persistence checklist for a new field

Before adding any new persisted field:

1. Define the field and its default/absent behavior.
2. Add encoder support in the applicable encoder or scene save path.
3. Add loader support with a safe legacy default.
4. Extend the relevant JSON schema.
5. Add strict-schema and load-path tests.
6. Add a save/load semantic round-trip test.
7. If the field changes existing stored meaning rather than merely adding an optional field, create a new schema version and migration.
8. Update this document and the format-specific documentation.

Optional additive fields should normally retain the current schema version when an older loader can safely ignore them and a newer loader has a correct absence default. A version bump is required when interpretation of existing data changes, an old default becomes unsafe, or loading without conversion would change design meaning.

## PCell definitions

PCell definition files require:

```json
[
  {"cellView":"pcell"},
  {"reference":"PcellClassName"}
]
```

The shared PCell validator checks the two records and reference before either PCell preview or layout instance construction. Existing PDK PCell files remain valid without `schemaVersion`. Add a labelled PCell version only when the definition format itself changes.

## Historical revision safety

A future version-control integration must open checked-in historical cellviews through this compatibility layer. If the application cannot prepare a revision safely, it must show an incompatibility error and leave the historical data untouched rather than opening a partially reconstructed scene.
