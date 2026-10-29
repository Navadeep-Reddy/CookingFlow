# Step 4: Framing

This step decides the **zoom and position** for each shot to keep the main cooking subject centered and make the footage look visually appealing.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/plan.json` — selected shots and their source timestamps.
- Original video files — for inspecting each selected shot.

## Actions

1. Inspect frames from the beginning, middle, and end of each shot to identify the main subject and its movement.
2. Identify what the viewer should focus on, such as the food, pan, or active area of the cutting board.
3. Choose a tight **9:16 "Fill the Frame"** zoom that makes the subject occupy most of the frame and removes unnecessary surroundings. Include hands and utensils when they contribute to the action, showing only as much as needed.
4. Position the crop to center the subject and leave enough room for important movements, such as pouring, chopping, or lifting food.
5. Check the zoom and position across the shot's sampled frames. Adjust them so the important action stays visible, then save the decisions to `workdir/framing.json`.

## Output

Write `workdir/framing.json`:

```json
{
  "shots": [
    {
      "id": "s01",
      "zoom": 1.3,
      "center_x": 0.5,
      "center_y": 0.45
    }
  ]
}
```

- `id` — matches the shot in `plan.json`.
- `zoom` — zoom multiplier; `1.0` is the widest 9:16 crop, and larger values zoom in.
- `center_x`, `center_y` — crop center in the original frame, normalized from `0` to `1`.

Use one fixed crop per shot. The final rendering stage applies these settings.

## Done when

- Every shot has a valid zoom and crop position.
- The main cooking subject fills most of the frame.
- Important actions remain visible throughout each shot.
- `workdir/framing.json` is valid and complete.