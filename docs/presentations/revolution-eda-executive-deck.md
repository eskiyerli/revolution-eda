---
marp: true
theme: default
paginate: true
size: 16:9
footer: "Revolution EDA • Executive briefing"
style: |
  :root {
    --ink: #3d4449;
    --muted: #7f888f;
    --accent: #f56a6a;
    --panel: #f4f7f8;
    --line: #d2d7d9;
  }
  section {
    background: linear-gradient(135deg, #ffffff 0%, #ffffff 72%, #f7eeee 100%);
    color: var(--ink);
    font-family: Lato, Aptos, Arial, sans-serif;
    padding: 58px 72px;
  }
  section::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 8px;
    background: var(--accent);
  }
  section::after { color: var(--muted); font-size: 16px; }
  h1, h2, h3 { font-family: "Roboto Slab", Georgia, serif; }
  h1 { color: var(--ink); font-size: 48px; line-height: 1.05; letter-spacing: -1.2px; }
  h2 { color: var(--ink); font-size: 34px; letter-spacing: -0.6px; }
  h3 { color: var(--accent); font-size: 23px; }
  p, li { font-size: 24px; line-height: 1.32; }
  li { margin: 10px 0; }
  strong { color: var(--accent); }
  table { font-size: 19px; width: 100%; }
  th { background: var(--ink); color: #ffffff; }
  td { background: rgba(244, 247, 248, 0.94); }
  th, td { border-color: var(--line); }
  blockquote {
    border-left: 5px solid var(--accent);
    color: var(--ink);
    font-size: 29px;
    padding-left: 24px;
  }
  footer { color: var(--muted); font-size: 14px; }
  .lead { font-size: 31px; color: #596168; max-width: 920px; }
  .small { font-size: 17px; color: var(--muted); }
  .kicker { color: var(--accent); font-size: 18px; text-transform: uppercase; letter-spacing: 2px; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 34px; align-items: center; }
  .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; }
  .card { background: rgba(244, 247, 248, 0.96); border: 1px solid var(--line); border-top: 4px solid var(--accent); border-radius: 8px; padding: 20px; }
  .card p { font-size: 19px; }
  .metric { color: var(--accent); font-size: 38px; font-weight: 700; }
  img { border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 10px 30px rgba(61,68,73,.18); }
  section.title { justify-content: center; }
  section.title h1 { font-size: 58px; max-width: 850px; }
  section.cta { text-align: center; justify-content: center; }
  section.cta h1 { font-size: 56px; }
---

<!-- _class: title -->
<!-- _footer: "Revolution EDA • Decision-maker briefing • September 2026" -->

<div class="kicker">Custom IC design, without a closed workflow</div>

# Give your design team another degree of freedom

<p class="lead"><strong>Revolution EDA</strong> is an open, extensible environment for custom IC schematic, simulation, and layout workflows.</p>

**Executive briefing — current status and controlled adoption**

<!--
SPEAKER NOTE: This is not a proposal to replace a qualified production flow overnight. It is an invitation to test a strategic option: a modern, inspectable design environment that can coexist with what the organization already trusts.
VISUAL: Bright editorial layout with a subtle chip floorplan or interconnect pattern in charcoal and coral. Keep the product name and thesis dominant.
-->

---

# The strategic risk is bigger than license cost

<div class="cards">
<div class="card">
<div class="metric">Locked</div>
<h3>Data & workflows</h3>
<p>Opaque formats and vendor-specific automation make change expensive.</p>
</div>
<div class="card">
<div class="metric">Fragmented</div>
<h3>Engineering flow</h3>
<p>Design intent is handed between disconnected capture, simulation, and physical tools.</p>
</div>
<div class="card">
<div class="metric">Constrained</div>
<h3>Innovation</h3>
<p>New methods wait for vendor roadmaps, scarce specialists, or brittle integrations.</p>
</div>
</div>

> The question is not “Can we buy another tool?” It is “Can we preserve strategic control of how we design?”

<!--
SPEAKER NOTE: Avoid invented savings figures. Ask the audience to map these three constraints to their own environment: tool access, integration backlog, reproducibility, and retention of design knowledge.
VISUAL: Three executive-level risk cards, not screenshots.
-->

---

# The proposal: add optionality, not disruption

<div class="columns">
<div>

## Start beside the incumbent flow

- Select a **bounded, non-tapeout-critical** design
- Connect one relevant **PDK and simulator path**
- Reproduce a known result
- Measure engineering effort and workflow fit
- Keep every pilot artifact portable

</div>
<div>

## Earn expansion with evidence

**No forced migration**  
**No proprietary database commitment**  
**No enterprise-wide rollout to approve**

A pilot can answer the real question:

> Where does Revolution EDA create leverage for us now?

</div>
</div>

<!--
SPEAKER NOTE: Lead with reversibility. The decision requested at the end is permission for a controlled evaluation, not a platform standardization decision.
VISUAL: A two-lane diagram: “trusted production flow” continues while a short “Revolution EDA pilot” lane runs beside it and rejoins at a review gate.
-->

---

# One environment across the custom IC loop

![bg right:52%](../assets/schematicEditor.png)

- **Schematic & symbol** editing with typed parameters and hierarchy navigation
- Hierarchical, configuration-driven **multi-simulator netlisting**
- Optional **simulation, plotting, LVS, and AI** plugins
- Connectivity-aware **layout** with Python PCells and SDL integration
- **EDIF 2 0 0, GDS, and OAS** interoperability paths
- RC parasitic extraction to **SPICE, SPEF, Spectre, and VACASK**
- In-app library, PDK, and plugin registries

<p class="small">Current project version: 1.0.0, released 29 September 2026. Optional capabilities depend on installed plugins, PDKs, external tools, and qualification for the target flow.</p>

<!--
SPEAKER NOTE: Describe the product as a coherent environment, not a claim that every signoff function is internally replaced. External simulators and verification tools remain valid parts of a deployable flow.
VISUAL: Use the real schematic editor screenshot shown on the right.
-->

---

# Version 1.0.0: a broader, more integrated platform

<div class="cards">
<div class="card">
<div class="metric">Design</div>
<h3>Production-shaped editing</h3>
<p>Typed instance parameters, net expressions and inherited connections, hierarchy navigation, persistent check markers, find/replace, arrays, and unified copy/paste workflows.</p>
</div>
<div class="card">
<div class="metric">Flow</div>
<h3>Connected verification</h3>
<p>One connectivity model now serves editing, diagnostics, netlisting, probing, SDL, LVS integration, and RC extraction across schematic and layout.</p>
</div>
<div class="card">
<div class="metric">Deploy</div>
<h3>Managed extensibility</h3>
<p>Plugin registry, compatibility and capability negotiation, update discovery, commercial licensing, and standalone Windows/Linux distribution paths.</p>
</div>
</div>

> This is a release milestone—not a blanket signoff qualification. Readiness remains PDK-, plugin-, and flow-specific.

<!--
SPEAKER NOTE: The September 2026 release consolidates substantial workflow infrastructure. Emphasize that the platform is ready for structured evaluation while target-process qualification remains an explicit pilot activity.
VISUAL: Three coral-accented release pillars: Design, Flow, Deploy.
-->

---

# Design data your organization can inspect

<div class="columns">
<div>

## Human-readable JSON

- Diffable in standard version-control systems
- Scriptable with familiar engineering tools
- Reviewable without a proprietary database reader
- Suitable for automation and reproducible transformations

</div>
<div>

```json
{
  "cellView": "schematic",
  "viewType": "schematic"
}
```

> The design database becomes an accessible engineering asset—not a black box.

</div>
</div>

<!--
SPEAKER NOTE: The value is governance and automation, not hand-editing every design. Inspectable data enables code review patterns, diagnostics, migration tooling, and durable ownership.
VISUAL: Show a clean JSON diff flowing into a schematic thumbnail and a Git review icon.
-->

---

# Integrate where standards already exist

| Boundary | Revolution EDA path | Executive value |
|---|---|---|
| Process enablement | Python PDK modules, callbacks, and PCells | Adapt the environment to the process |
| Simulation | Xyce, Spectre, and VACASK netlisting paths | Preserve simulator choice |
| Design intake | EDIF 2 0 0, Verilog-A, Spectre and VACASK subcircuits | Reuse established design and model assets |
| Physical exchange | GDS / OAS import and export | Fit established downstream flows |
| Verification | Hierarchical LVS integration and RC extraction | Connect intent, comparison, and analysis |
| Extracted output | SPICE / SPEF / Spectre / VACASK | Feed existing downstream stages |
| Automation | Python console, JSON, versioned plugin capabilities | Build workflow IP with common skills |

<!--
SPEAKER NOTE: “Supports” does not mean qualification for a specific company flow. The pilot must verify the exact PDK, model, simulator, and exchange path that matters to the sponsor.
VISUAL: Replace the table with a hub-and-spoke graphic if presenting live: Revolution EDA at center, standards and existing tools around it.
-->

---

# A platform, not a fixed appliance

<div class="cards">
<div class="card">
<h3>PDK layer</h3>
<p>Process layers, callbacks, labels, and PCells are supplied through Python packages.</p>
</div>
<div class="card">
<h3>Plugin layer</h3>
<p>Plugins add menus, custom views, simulation, plotting, LVS, SDL, and AI capabilities without changing core code.</p>
</div>
<div class="card">
<h3>Automation layer</h3>
<p>An integrated Python console and transparent files expose practical extension points.</p>
</div>
</div>

## Build differentiated workflow IP at your pace

Source and binary plugin models allow **open collaboration** and **controlled commercial extensions** to coexist. Version/capability checks and in-app update discovery make that ecosystem manageable.

<!--
SPEAKER NOTE: This is the strategic architecture slide. Internal methodology can be expressed in extensions rather than waiting for a monolithic vendor release. Governance still matters: version, test, review, and qualify internal extensions.
VISUAL: Three-layer stack: open core, enterprise workflow extensions, company methodology/PDK.
-->

---

# AI assistance—with a reversible operating model

![bg right:51%](../assets/aiTerminalExample.png)

- Natural-language editing of **schematics, symbols, and layouts**
- Choice of **OpenAI, Google, or Anthropic** backends
- A backup before each AI modification
- One-click restore / undo path
- Direct inspection of design JSON
- Encrypted local storage for API keys

## Treat AI as an accelerator—not an authority

<p class="small">Deployment should follow company policy for model access, design-data handling, review, and approval.</p>

<!--
SPEAKER NOTE: Do not lead with AI hype. The important design choice is reversibility and inspection. In a pilot, AI can be optional and separately governed.
VISUAL: Use the actual AI terminal screenshot. Highlight “backup,” “undo,” and model choice with subtle callouts.
-->

---

# Physical design remains connected to intent

![bg right:54%](../assets/layoutEditorWindow.png)

- Hierarchical custom layout with configurable display depth
- Rectangles, paths, polygons, pins, labels, and via arrays
- Python parametric cells with editable parameters
- Layer visibility, selectability, and used-layer filtering
- Versioned schematic-driven-layout adapter for compatible plugins
- Shared connectivity, net naming, probing, and highlighting
- GDS / OAS exchange, LVS integration, and RC extraction

<!--
SPEAKER NOTE: This establishes that Revolution EDA is not merely a schematic viewer. Be precise: final signoff readiness depends on the target process and external verification flow selected for the pilot.
VISUAL: Use the real layout editor screenshot on the right.
-->

---

# The business case is strategic leverage

<div class="cards">
<div class="card">
<h3>For design leadership</h3>
<p>Another path for prototyping, education, research, smaller programs, and workflow experiments.</p>
</div>
<div class="card">
<h3>For engineering</h3>
<p>One inspectable environment with Python automation and fewer hard boundaries between design stages.</p>
</div>
<div class="card">
<h3>For the enterprise</h3>
<p>Reduced dependence on any single interface, file format, deployment model, or vendor roadmap.</p>
</div>
</div>

> Optionality compounds: every reusable PDK element, plugin, and automation script increases future choice.

<!--
SPEAKER NOTE: This is intentionally a value hypothesis, not a promised ROI. Quantify only after the pilot establishes baseline and observed effort.
VISUAL: A flywheel: adopt → automate → reuse → broaden optionality.
-->

---

# Open core changes the control model

<div class="columns">
<div>

## MPL 2.0 licensed core

- Use for any purpose
- Inspect and modify source
- Distribute under the license terms
- Build commercial services and derivatives

</div>
<div>

## Practical implications

- Audit the implementation
- Preserve access to the core
- Qualify changes internally
- Keep plugins, PDKs, and libraries under their own applicable terms

</div>
</div>

<p class="small">This slide is an operational summary, not legal advice. Legal review should confirm obligations for the organization’s intended distribution model.</p>

<!--
SPEAKER NOTE: Open source does not mean zero cost or zero obligations. It changes what the organization can inspect, control, and continue. Separate core licensing from the licenses of each plugin, PDK, library, and external tool.
VISUAL: “Control” balance scale: inspectability, continuity, and extensibility on one side; governance and qualification on the other.
-->

---

# Address the adoption risks directly

| Leadership concern | Pilot control |
|---|---|
| “Is it production mature?” | Treat v1.0.0 as an evaluation milestone; qualify the exact PDK, plugins, and signoff handoffs |
| “Will it disturb the current flow?” | Run side-by-side; exchange only through agreed files and interfaces |
| “Can it support our process?” | Make one PDK plus DRC/LVS/simulator path a pass/fail workstream |
| “Can extensions be governed?” | Pin compatible versions, review capabilities, and test registry updates before rollout |
| “What about security and IP?” | Apply approved AI settings, dependency review, access controls, and artifact handling |
| “Will it scale?” | Test a representative hierarchy and dataset; record load, edit, netlist, check, and export behavior |

<!--
SPEAKER NOTE: Credibility comes from acknowledging maturity. This slide turns objections into evaluation criteria rather than debating them abstractly.
VISUAL: Risk register with coral “controlled experiment” gates—not checkmarks implying the risks are already closed.
-->

---

# A focused pilot can produce a decision

## Suggested scope: one representative block, one PDK, one simulator path

<div class="cards">
<div class="card">
<h3>1 — Establish</h3>
<p>Install v1.0.0, register the PDK and libraries, import via EDIF or recreate the reference design, and capture baseline effort.</p>
</div>
<div class="card">
<h3>2 — Exercise</h3>
<p>Edit hierarchy, netlist and simulate, exercise DRC/LVS handoffs, change layout, exchange GDS/OAS, and test one automation.</p>
</div>
<div class="card">
<h3>3 — Decide</h3>
<p>Compare results, document gaps, estimate ownership needs, and choose stop / extend / adopt.</p>
</div>
</div>

**Deliverables:** reproducible project • verified result comparison • issue log • workflow-fit scorecard • recommendation

<!--
SPEAKER NOTE: Keep timing adaptable to organizational complexity. The purpose is not a polished demo; it is a reproducible evidence package that another engineer can run.
VISUAL: Three gated stages with a decision diamond after stage 3.
-->

---

# Agree on success before the pilot starts

| Dimension | Example evidence—not a preclaimed result |
|---|---|
| Correctness | Connectivity checks, netlist, LVS comparison, and selected simulation outputs meet approved criteria |
| Interoperability | Required EDIF/model, GDS/OAS, and extracted-netlist paths complete without material data loss |
| Productivity | Engineers complete defined edits and automation tasks; effort is recorded against baseline |
| Extensibility | One small plugin, script, PCell, or PDK adaptation is implemented and reviewed |
| Governance | Project is reproducible from controlled source, configuration, and dependency records |
| Adoption | Pilot users identify credible use cases and blocking gaps |

## Score the evidence. Do not grade the demo.

<!--
SPEAKER NOTE: The sponsor should choose tolerances and weights. “Successful” can mean finding a narrow high-value use case; it does not require replacing every incumbent capability.
VISUAL: A simple scorecard with columns for baseline, target, observed, and decision. Populate only after the pilot.
-->

---

<!-- _class: cta -->
<!-- _footer: "Revolution EDA • Proposed next step" -->

# Authorize a controlled evaluation

<p class="lead" style="margin: 0 auto 28px;">Choose one sponsor, one engineering lead, one representative design, and one explicit decision date.</p>

## The ask

**Approve the pilot scope and success criteria—not a migration.**

The downside is bounded.  
The learning is reusable.  
The upside is strategic design freedom.

<!--
SPEAKER NOTE: End on the precise decision required. Offer a short follow-up working session to select the block, PDK, simulator, security posture, owner, and scorecard weights.
VISUAL: Minimal slide. One coral call-to-action button shape: “Select the pilot.”
-->
