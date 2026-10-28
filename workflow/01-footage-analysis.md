# Step 1: Footage Analysis

## Inputs

- `workdir/progress.md` — selected source clips.

## Actions

1. Survey each clip from beginning to end using frames sampled across its full timeline. Identify the cooking stages and distinct actions actually present.
2. Inspect the identified actions through multiple frames to establish accurate start and end timestamps. For long repetitive actions, choose a visually satisfying complete cycle.
3. Compare separate takes of the same action for visual appeal, clarity, and completeness. Keep the best-looking usable take; prefer the latest when quality is comparable.
4. Group the chosen moments by cooking stage in natural story order. Include the meaningful actions needed to represent the full cooking process.
5. Verify the timestamps and write `workdir/footage.json`.

## Output

```json
{
  "stages": [
    {
      "name": "Ingredient preparation",
      "moments": [
        {
          "id": "m01",
          "clip": "Clips/cooking.mp4",
          "action": "Chopping onions",
          "start": 42.5,
          "end": 46.8,
          "note": "Clean close-up and smooth knife movement"
        }
      ]
    }
  ]
}
```

Use source timestamps in seconds. Step 3 uses these selected takes to decide final cuts, pacing, and sequence.

## Done when

- [ ] Every selected clip has been surveyed across its full timeline.
- [ ] Each meaningful action is represented by its strongest usable take, with complete action boundaries.
- [ ] The stages cover the cooking story, and `footage.json` is valid with accurate source timestamps.

