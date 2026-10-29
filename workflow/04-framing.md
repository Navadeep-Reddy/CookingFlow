# Step 4: Framing

Choose each shot's **zoom and position** to center the cooking subject and fill the frame.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/plan.json` — selected shots and their source timestamps.
- Original video files — for inspecting each selected shot.

## Actions

1. Use `python3 tools/evidence.py shots workdir/plan.json` (`--help` for options) for cached first/middle/last included source frames and their frame-index/time manifest. Add `--include-outside` for uncertain boundaries when that frame is before EOF; increase `--width` for source-resolution detail.
2. Identify what the viewer should focus on, such as the food, pan, or active area of the cutting board.
3. Choose a tight **9:16 "Fill the Frame"** zoom that makes the subject occupy most of the frame and removes unnecessary surroundings. Include hands and utensils when they contribute to the action, showing only as much as needed.
4. Position the crop to center the subject and leave enough room for important movements, such as pouring, chopping, or lifting food.
5. Map preview coordinates to the upright source; record every shot's trial zoom, center, and even-pixel, in-bounds 9:16 rectangle in `workdir/framing.json`. Add `--framing workdir/framing.json` to the `shots` command for original/crop views using the same cached PNGs. Crops are HTML/browser views; use skill-generated crop previews if browser pixels cannot be inspected. Refine and save after visual review.

## Output

Write `workdir/framing.json`:

```json
{
  "shots": [
    {
      "id": "s01",
      "zoom": 1.2,
      "center_x": 0.5,
      "center_y": 0.45,
      "crop": {"x": 180, "y": 128, "width": 1800, "height": 3200}
    }
  ]
}
```

The example assumes a 2160×3840 upright source.

- `id` — matches the shot in `plan.json`.
- `zoom` — zoom multiplier; `1.0` is the widest 9:16 crop, and larger values zoom in.
- `center_x`, `center_y` — crop center in the original frame, normalized from `0` to `1`.
- `crop` — exact source-pixel rectangle after rounding; must agree with zoom and center. Divide the widest source 9:16 rectangle's dimensions by zoom and position around the normalized source center.

Use one fixed crop per shot. The final rendering stage applies these settings.

## Done when

- Every shot has a valid zoom and crop position.
- The main cooking subject fills most of the frame.
- Important actions remain visible throughout each shot.
- `workdir/framing.json` is valid and complete.
