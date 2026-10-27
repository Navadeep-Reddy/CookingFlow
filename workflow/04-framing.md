# Step 4: Framing

Runs in the main agent, with optional per-shot delegation to vision-capable workers. Measure and verify a subject-centered frame for every planned shot. This is framing inspection, not a repeat of footage analysis.

## Inputs

- `workdir/inputs.json` and its source geometry/metadata
- `workdir/plan.json`
- `workdir/footage.json` and its subject notes
- Existing `workdir/framing.json` and previews when resuming

## Rules

- Center on the actual subject, not the source frame's center: board shots around the board, pan shots around the pan. Include the food, essential action area, and acting hands or utensils; trim dead counter without clipping the action or losing useful context.
- Choose zoom from measured subject size and source sharpness, not a fixed multiplier. Avoid a cramped crop even if a tighter rectangle is geometrically possible.
- One fixed framing per shot; changes occur only at hard cuts. Keep phases of the same action visually consistent unless the subject moved.

## Actions

1. Reuse verified framing for unchanged shots. Inspect frames across each new or changed shot, including entry, last included frame, and action extremes. Increase sampling where the subject or utensils travel; evenly spaced samples alone can miss a pour or lift.
2. Measure the subject span in displayed, rotation-corrected source pixels. Account for pixel aspect ratio if non-square; record the coordinate space so rendering uses the same geometry. Form a union of the observed action bounds.
3. Choose a legal 9:16 crop around that span with sufficient context, inside the displayed source. Respect the execution tool's dimension/alignment requirements. If full containment and centering are incompatible, first loosen or reposition framing. If no acceptable crop exists, return the specific shot to step 3 or ask for a framing exception; do not silently clip it or declare an impossible crop verified.
4. Generate and view cropped preview sequences/contact sheets. Verify subject position, action containment, size, and sharpness across the shot, not just its midpoint. Save measurements, crop parameters, and evidence in `framing.json`.
5. Per-shot workers write separate files in `workdir/`; the step owner merges them into `framing.json`. A timeline change belongs to step 3, not a framing worker.

## Output contract

`workdir/framing.json`:

```json
{
  "step": 4,
  "status": "partial",
  "shots": [
    {"id": "s01", "coordinate_space": "displayed source pixels",
     "subject": "", "subject_bbox": {"x": null, "y": null, "w": null, "h": null},
     "crop": {"x": null, "y": null, "w": null, "h": null},
     "evidence": [], "verified": false, "note": ""}
  ],
  "limitations": []
}
```

Record any approved non-crop framing explicitly as a per-shot alternative with reproducible parameters; a null crop is not permission to invent a default center crop. Output size comes from the plan. Preview paths and supplementary measurements are free-form.

## Done when

- [ ] Every planned shot has measured, reproducible framing in an explicit coordinate space
- [ ] Crops are legal 9:16 rectangles inside the source, or an approved alternative is recorded
- [ ] Viewed previews cover action extremes and confirm readable centering, containment, size, and sharpness
- [ ] Framing stays fixed within each shot; no unresolved framing defect is hidden as a pass
- [ ] `framing.json` satisfies its contract and has `status: complete`
