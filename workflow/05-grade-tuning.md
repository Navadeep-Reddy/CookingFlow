# Step 5: Grade tuning

**Owner:** Grading subagent with vision, in parallel with step 4. Tune Kodak 2383 to planned source samples, not a fixed strength; step 6 checks the final framed result.

## Inputs

- `workdir/progress.md` and saved source probes
- `workdir/plan.json`
- Reusable grade assets in `assets/` and any user-named assets
- Existing `workdir/grade.json` and comparison evidence when resuming

## Rules

- Start at partial strength and compare before/after frames. Keep the filmic character while food colors stay true: creams read cream, whites read white, nothing pushed orange. Verify the lightest-colored food as well as saturated and dark shots.
- Reduce strength when the look causes drift. If the picture looks lifeless, diagnose exposure, white balance, input color handling, and strength rather than automatically increasing the LUT.
- Aim for a consistent look across sources; per-shot adjustments are allowed where the footage requires them. No fixed percentage or numerical starting recipe.

## Actions

1. Reuse valid grade choices and comparisons for unchanged sources/shots. Research the reference look only when uncertain and save useful findings with the result.
2. Identify the LUT and expected input color space. Use source metadata to resolve required pixel conversions or corrections; metadata relabeling is not conversion. Reuse applicable provenance and compatibility findings.
3. Compare representative light, saturated, dark, and differing-source samples through supported skill operations before full-Reel rendering. Tune food color, detail, and consistency; revisit only failing shots. If strength behaves unexpectedly, inspect the generated command before further trials.
4. Record asset, input preparation, intended strength, actual tool arguments/version, and overrides in `grade.json` for step 6. Keep comparison evidence and research in `workdir/`.

## Output contract

`workdir/grade.json`:

```json
{
  "step": 5,
  "status": "partial",
  "look": "Kodak 2383 print film emulation",
  "lut_path": null,
  "input_preparation": {},
  "strength": null,
  "per_shot_overrides": {},
  "evidence": [],
  "limitations": []
}
```

`input_preparation` is keyed by clip ID and records its color-space assumptions and any ordered conversion/correction parameters; state explicitly when none are needed. Overrides are keyed by shot ID and inherit unchanged default parameters. Evidence identifies source frames and final-setting comparisons. Extra research and run notes are free-form.

## Done when

- [ ] The actual grade asset exists and its input handling matches the sources
- [ ] Before/after comparisons at final settings show true food colors, retained detail, and a filmic look across representative shots
- [ ] The lightest-colored food has been checked; any failing source/shot has been resolved
- [ ] Asset, input preparation, strength, and overrides are reproducible without guessing
- [ ] `grade.json` satisfies its contract and has `status: complete`
