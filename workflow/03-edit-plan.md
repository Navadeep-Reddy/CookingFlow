# Step 3: Edit plan

This stage uses the completed footage and music analyses to plan the final Reel. It selects and arranges shots, determines their timing and playback speeds, and synchronizes them with the music. It saves the resulting edit plan for the final rendering stage.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/footage.json` — cooking stages, selected actions, and source timestamps.
- `workdir/music.json` — music starting point and beat timestamps.

## Actions

1. **Establish the story:** Use the cooking stages in `footage.json` to plan a complete narrative. Open with a showcasing finished-dish shot, follow the cooking process in order, and end with the same finished-dish showcasing shot.

2. **Prepare music timing:** Use the starting point from `music.json` and convert its beat timestamps into positions relative to the Reel's beginning.

3. **Select and arrange shots:** Choose the actions that best tell the story with total length being 30 seconds. Include atleast one shot of each distinct cooking stage so each transition shows meaningful visual progress.

4. **Plan cuts and speeds:** Determine precise source ranges, shot durations, and playback speeds between 1.0× and 2.0×. Choose each shot's speed based on its action, keeping natural movements at 1.0× and speeding up slow or repetitive parts when useful. Vary shot lengths and cutting patterns to create natural, engaging pacing.

5. **Finalize the timeline:** Prioritize visual storytelling and natural action flow over musical synchronization. Align cuts and significant moments with nearby beats when it improves the edit. Calculate consecutive output timestamps and the final duration. Retain original clip audio for mixing during rendering.

6. **Save the plan:** Inspect frames around selected shot boundaries to ensure transitions look natural and actions progress clearly. Verify timestamps and total duration under 30 seconds. Write `workdir/plan.json`.

## Output

Write `workdir/plan.json`:

```json
{
  "shots": [
    {
      "id": "s01",
      "moment_id": "m01",
      "clip": "Clips/example.mp4",
      "src_in": 42.0,
      "src_out": 44.0,
      "speed": 1.0,
      "out_start": 0.0,
      "out_end": 2.0,
      "keep_original_audio": true
    }
  ],
  "music": {
    "file": "Sounds/example.mp3",
    "start": 11.9
  },
  "duration": 2.0
}
```

All timestamps are in seconds. Use one shot entry per continuous source range.

## Done when

- The edit tells the complete cooking story with natural action continuity.
- All shots have valid source ranges, speeds, and consecutive output timestamps.
- Music synchronization is planned and the total duration is under 30 seconds.
- `workdir/plan.json` is valid and complete.