# Step 1: Footage Analysis

## Inputs

- `workdir/progress.md` — selected source clips.

## Actions

1. Survey each clip from beginning to end using frames sampled across its full timeline. Identify the cooking stages and distinct actions actually present.
2. Inspect each action through multiple frames to find its start and end times. When the original video suddenly jumps to a different scene, end the current moment before the jump and start a new moment after it. For long repetitive actions, identify visually interesting parts that show progress.
3. Compare separate takes of the same action for visual appeal, clarity, and completeness and only keep the best take;
4. Group the chosen moments by cooking stage in natural story order. Include the meaningful actions needed to represent the full cooking process.
5. Check frames near the start and end of each selected moment to confirm its timestamps, then write `workdir/footage.json`.

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

