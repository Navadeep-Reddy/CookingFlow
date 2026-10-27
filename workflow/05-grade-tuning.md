# Step 5: Grade tuning

Runs in the main agent with vision. Tune Kodak 2383 print film emulation to the footage, not a fixed strength. Work independently of step 4 on source moments selected by the plan; step 7 checks the final framed result.

## Inputs

- `workdir/inputs.json` and its source paths/color metadata
- `workdir/plan.json`
- Reusable grade assets in `assets/` and any user-named assets
- Existing `workdir/grade.json` and comparison evidence when resuming

## Rules

- Start at partial strength and compare before/after frames. Keep the filmic character while food colors stay true: creams read cream, whites read white, nothing pushed orange. Verify the lightest-colored food as well as saturated and dark shots.
- Reduce strength when the look causes drift. If the picture looks lifeless, diagnose exposure, white balance, input color handling, and strength rather than automatically increasing the LUT.
- Aim for a consistent look across sources; per-shot adjustments are allowed where the footage requires them. No fixed percentage or numerical starting recipe.

## Actions

1. Reuse valid grade choices and comparisons for unchanged sources/shots. Research the reference look only when uncertain and save useful findings with the result.
2. Identify the actual LUT asset and its expected input color space. Use source metadata to establish any required conversion or correction before applying the creative look. Do not substitute a label change for a pixel conversion or assume every 2383 LUT accepts every camera source. If the needed asset or input interpretation is missing, resolve that instead of guessing.
3. Select representative light, saturated, dark, and differing-source frames. Apply the look through supported skill operations and view before/after evidence. Tune based on the food, highlight detail, shadows, and consistency; revisit only failing shots.
4. Record the asset path, input preparation, chosen strength, and any overrides as reproducible parameters. Discovered commands and run evidence belong in `workdir/`, not these instructions. Write `grade.json` for step 7.

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
