# Symbol Labels and Typed Instance Parameters

## Why `sg13_lv_nmos` says it has no parameters

A symbol can display instance values without declaring **typed instance parameters**. This is the situation for a symbol such as `sg13_lv_nmos` when it contains parameter-looking labels but has no `paramDefs` definition.

The **F3 Instance Parameters** form is intentionally driven by `paramDefs`, not inferred from labels. Therefore:

- labels alone can display or carry an instance value;
- `paramDefs` declare which values are editable parameters, their types, defaults, limits, and choices;
- F3 reports that there are no typed parameters when a symbol has labels but no `paramDefs`.

This distinction keeps legacy and PDK-provided symbols compatible: Revolution EDA does not have to guess whether a label is a resistor value, a model name, a display-only annotation, or an input that must be validated as a number.

## The two layers of instance data

| Concept | What it is for | Where it is defined | F3 behavior |
|---|---|---|---|
| **Symbol label** | Visible text, an instance value carrier, or a computed display | Symbol graphics | Does not independently create an input field |
| **Typed parameter** | An explicit CDF-lite declaration of an editable, validated value | Symbol attribute `paramDefs` | Creates a field when `display` is enabled |

The same instance can use both layers. A typed parameter must correspond to an editable, value-carrying **NLP label**—normally `@<parameter-name>`—so its value has a persistent `sys.ld` location. A `paramDefs` entry without that carrier is ignored by both the F3 form and the typed section of Instance Properties.

## Symbol labels

Labels belong to the symbol drawing and have several jobs.

### Normal labels

Normal labels are plain annotations. They are useful for fixed text such as a technology name, a model-family heading, or a note. They are not parameters.

### NLP labels

An NLP label provides a label name, optional display format, and an optional text default. For example:

```text
[@w:W=%:W=1u]
```

This can display `W=1u` and carry an instance value associated with `@w`. The value is stored on the instance in the schematic JSON label data (`sys.ld`). However, the label syntax does **not** state whether `w` is a float, integer, string, boolean, or choice; nor does it specify legal limits. For that reason an NLP label alone is not enough to build a typed F3 form.

### PyLabels

PyLabels render a value calculated by a PDK callback. They are output/display conventions, not a declaration that the user may edit that value. A PyLabel may depend on other parameter labels.

## Typed parameters (`paramDefs`)

`paramDefs` is a reserved symbol attribute containing an ordered JSON list of parameter declarations. Each declaration can contain:

| Field | Meaning |
|---|---|
| `name` | Parameter name. It normally matches an NLP label named `@name`. |
| `type` | `float`, `int`, `string`, `boolean`, or `choice`. |
| `default` | Default value. A parameter default takes precedence over an NLP label's literal default. |
| `min`, `max` | Optional numeric bounds for `float` and `int`. |
| `choices` | Allowed values for a `choice`. |
| `display` | `false` keeps the parameter available to validation/default resolution but hides it from F3. |
| `parse` | Allows numeric SI suffixes such as `1k`, `2u`, and `130n` when enabled. |

An explicit instance value always wins over either kind of default. Parameter values remain in the existing instance label data, so adding `paramDefs` supplies type information and UI behavior without moving the values to a separate storage model.

## Make `sg13_lv_nmos` parameters available in F3

Before changing a PDK-supplied symbol, make a writable project copy if the PDK is externally managed. Updating or replacing the PDK can otherwise overwrite the change.

1. Open the `sg13_lv_nmos` **symbol** view in the Symbol Editor.
2. Inspect its existing labels. Identify the editable, parameter-carrying NLP labels, for example labels whose names are `@w`, `@l`, `@nf`, or other names actually present in that symbol. Each `paramDefs` entry needs one of these carriers (preferably `@name`; legacy bare `name` is accepted for compatibility), because values persist through the label data in `sys.ld`.
3. Open **Edit → Cellview Properties...** and use the **Parameters** table. The reserved `paramDefs` attribute is managed by this table rather than by the free-form attribute grid.
4. Add one row for each editable parameter. Choose the exact label name without the leading `@`, the intended type, default, and validation rules.
5. Save the symbol. Reload an already-open schematic view if necessary, then start **Create Instance** again.
6. While the instance placement command is active, press **F3**. The `display`-enabled definitions now appear as typed controls.

### Illustrative table entries

Use the actual label names and technology limits for the PDK symbol. The following values are an example of structure only; they are not SG13 design-rule recommendations.

| Name | Type | Default | Min | Max | Parse | Notes |
|---|---|---:|---:|---:|---|---|
| `w` | `float` | `1u` | technology minimum |  | enabled | Must match an `@w` label if the width is displayed. |
| `l` | `float` | `0.13u` | technology minimum |  | enabled | Must match an `@l` label if the length is displayed. |
| `nf` | `int` | `1` | `1` |  | enabled | Use only if the symbol actually has an `@nf` value. |
| `model` | `choice` | a valid model |  |  | disabled | Populate `choices` with the valid model strings. |

For a width parameter, the persisted definition is conceptually equivalent to:

```json
{
  "name": "w",
  "type": "float",
  "default": "1u",
  "min": "<technology minimum>",
  "display": true,
  "parse": true
}
```

The application serializes rows like this into the symbol's reserved `paramDefs` attribute. Prefer the Parameters table over manually editing the JSON attribute.

## Unified editing behavior

Both editable-instance flows use the same binding rule:

1. `paramDefs` defines every **typed** field, in the definition order.
2. The definition must have an editable NLP value-carrier label named `@name` (preferred) or legacy bare `name`.
3. A definition with `display=false` remains persisted and validated, but is hidden from both F3 and the typed Instance Properties section.
4. Normal/NLP labels that are not claimed by a `paramDefs` entry appear under **Legacy / Other Labels** in Instance Properties as untyped text fields. This preserves existing PDK symbols without pretending their labels have declared types, bounds, or choices.
5. PyLabels appear under **Computed Labels** and are read-only.

Consequently, F3 intentionally does not expose label-only legacy fields: F3 is the typed placement form. Instance Properties retains those fields as an explicit compatibility section.

## What adding `paramDefs` does—and does not do

Adding a definition **does**:

- expose a typed F3/placement control when `display` is enabled;
- validate values during placement, property editing, and headless schematic checks;
- provide defaults, including `pPar("otherParameter")` references to sibling values;
- allow safe numeric suffix handling for numeric parameters.

Adding a definition **does not**:

- create an independent instance parameter store; every editable typed value still needs a matching NLP carrier in `sys.ld`;
- automatically create a missing label carrier;
- infer PDK legal limits or PCell parameter mappings;
- change a simulator model, callback, netlister, or layout PCell by itself;
- make a PyLabel editable.

For a PDK device, keep the names, units, callback expectations, PCell mappings, and netlisting conventions aligned. The symbol's label names remain the interoperability contract; `paramDefs` formalize the expected user input.

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| F3 says there are no typed parameters | The symbol has no `paramDefs`, no matching editable label carriers, or only `display=false` definitions | Add display-enabled definitions in Cellview Properties → Parameters and matching `@name` labels, then save and restart placement. |
| A declared parameter is absent from F3 or Typed Parameters | Its carrier label is missing, is a PyLabel, or its `display` option is disabled | Add/fix a non-PyLabel `@name` carrier and enable `display` when the value should be user-editable. |
| Valid-looking numeric input is rejected | Type, bounds, or `parse` settings do not allow it | Check type/min/max and enable parsing for SI suffixes where appropriate. |
| PCell, callback, or netlist does not react to a new value | The downstream PDK convention expects a different label name or mapping | Use the PDK's expected label names and update the PDK mapping/callback only when appropriate. |

See also: [Labels](./labels.md) and [Symbol Editor](./symbolTutorial.md).
