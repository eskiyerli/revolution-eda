# Plan Investigation Report

## Summary Answer

The best-candidate ranking section appears at **lines 438-459** (lines 39-60 of the truncated output from lines 400-470). The exact text is the 7-item lexicographic ranking list, followed by the "This ranking is the single definition of 'best.'" paragraph and the subsequent 4-item stagnation reporting section.

## Evidence

### File Reference
- **Path:** `c:\Users\eskiye50\OneDrive - Revolution Semiconductor\Projects\design_software\revolution-eda\plans\plan-a4dfbeb8933db7b2.md`
- **Total Lines:** 724
- **Total Size:** 53,811 bytes

### Section Title
Line 389: `### 10. Add a deterministic bounded optimizer and best-candidate ledger`

### Exact Text Around Lines 400-470

#### Lines 400-419 (Bounds Resolution)
```
2. intersect any declared min/max/choices with IHP adapter safety limits;
3. intersect the agent-proposed useful search range;
4. show the result for user approval;
5. if no trustworthy lower/upper range remains (common for current IHP MOS `w/l` definitions), require a conservative characterized IHP policy range or explicit user bounds—never infer an unbounded range.

Use no new optimizer dependency. Implement a deterministic mixed-domain search with NumPy:

1. evaluate the approved initial vector;
2. create a seeded space-filling initial design over continuous log/linear, integer, and choice domains, always including bounds and the initial point;
3. run adaptive coordinate/pattern search around the incumbent, reducing step sizes after a complete unsuccessful sweep;
4. cache duplicate vectors and failed deterministic evaluations;
5. optionally use measured finite-difference trends only to order coordinates, never to extrapolate outside approved bounds;
6. stop on all-required pass plus one confirmation rerun, evaluation/simulation/elapsed cap, minimum step, repeated failures, cancellation, or stagnation.
```

#### Lines 420-437 (Normalized Violation Definition)
```
Define the per-metric normalized violation:

- `>=`/`>`: `max(0, target - measured) / scale`;
- `<=`/`<`: `max(0, measured - target) / scale`;
- equality/tolerance: excess distance outside the approved tolerance divided by scale;
- default `scale = max(abs(target), explicit tolerance, unit-aware floor)`;
- unavailable required measurements receive a fixed dominant penalty and can never make a candidate feasible.

Rank candidates lexicographically:

1. complete required measurements before incomplete evaluations;
2. feasible (all required pass) before infeasible;
3. weighted sum of squared normalized required violations;
4. maximum normalized required violation;
5. weighted optional-objective violation;
6. larger minimum required-spec margin;
7. lower simulation cost, then earlier evaluation index for deterministic ties.

This ranking is the single definition of "best." Pass count alone is never the objective. Persist `study.json`, append-only `evaluations.jsonl`, best-history changes, and per-candidate metric artifacts so the result can be replayed without re-running simulations.

At run limit or ordinary stagnation:

- select the global best successfully measured candidate across every approved topology study;
- show measured value, target, absolute gap, normalized gap, pass/fail/unknown, and best iteration for every metric;
- show bound hits, local sensitivity/trend evidence, simulation failures, budgets used, and why the stop criterion fired;
- if no candidate completed required measurements, retain the OP-verified initial candidate in the workspace, leave the user target unchanged, and report that no measured best exists;
- ask the user to accept/commit the best candidate, keep the original, or approve a topology replan.
```

### Exact Best-Candidate Ranking List (Lines 438-459)
```
Rank candidates lexicographically:

1. complete required measurements before incomplete evaluations;
2. feasible (all required pass) before infeasible;
3. weighted sum of squared normalized required violations;
4. maximum normalized required violation;
5. weighted optional-objective violation;
6. larger minimum required-spec margin;
7. lower simulation cost, then earlier evaluation index for deterministic ties.

This ranking is the single definition of "best." Pass count alone is never the objective. Persist `study.json`, append-only `evaluations.jsonl`, best-history changes, and per-candidate metric artifacts so the result can be replayed without re-running simulations.

At run limit or ordinary stagnation:

- select the global best successfully measured candidate across every approved topology study;
- show measured value, target, absolute gap, normalized gap, pass/fail/unknown, and best iteration for every metric;
- show bound hits, local sensitivity/trend evidence, simulation failures, budgets used, and why the stop criterion fired;
- if no candidate completed required measurements, retain the OP-verified initial candidate in the workspace, leave the user target unchanged, and report that no measured best exists;
- ask the user to accept/commit the best candidate, keep the original, or approve a topology replan.
```

## Conclusions and Recommendations

### Key Findings

1. **The ranking section is clearly delineated** as a 7-item lexicographic list starting at line 438, with the critical note that "Pass count alone is never the objective" at line 448.

2. **The "best" is defined by measurement completeness first** - candidates must have all required measurements before they are comparable. This is the most important constraint.

3. **The fallback reporting section is critical** - lines 449-459 specify exactly what to show users when no candidate completes required measurements: retain the OP-verified initial candidate, keep the user target unchanged, and report "no measured best exists."

4. **The section numbering has a duplicate issue** - lines 389 and 461 both show `### 11. Add fallback strategy...` and `### 11. Constrain and correct the IHP layout assistant`. This appears to be a typo (should be 11 and 12).

### Recommendations

1. **For implementation:** Ensure the ranking function uses the exact 7-item lexicographic order as written. The key distinction is that feasibility (all required pass) beats optimization quality.

2. **For the fallback case:** Implement the "no measured best exists" path explicitly - it should retain the OP-verified initial candidate without writing to the user target.

3. **Fix the section numbering:** Change line 461 from `### 11.` to `### 12.` to avoid confusion.

4. **Consider adding a test fixture:** The text mentions "normalized-gap fixtures cover every comparator, units, unknown measurements, feasible/infeasible ordering" in the verification section, suggesting the current implementation may not yet have this coverage.

## Files to Modify (for context)

The investigation report identifies the exact text to use for replacement when the user wants to implement improvements to the best-candidate ranking logic.
