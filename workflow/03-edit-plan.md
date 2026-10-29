# Step 3: Edit plan

Select shots, order, timing, and speeds from the footage and music analyses; save the edit for rendering.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/footage.json` — cooking stages, selected actions, and source timestamps.
- `workdir/music.json` — music starting point and beat timestamps.

## Actions

1. **Establish the story:** Use the cooking stages in `footage.json` to plan a complete narrative. Open with a showcasing finished-dish shot, follow the cooking process in order, and end with the same finished-dish showcasing shot.

2. **Prepare music timing:** Use the starting point from `music.json` and convert its beat timestamps into positions relative to the Reel's beginning.

3. **Select and arrange shots:** Tell the story in under 30 seconds. Include at least one shot of each distinct cooking stage so transitions show meaningful progress.

4. **Plan cuts and speeds:** Determine precise source ranges, shot durations, and playback speeds between 1.0× and 2.0×. Choose each shot's speed based on its action, keeping natural movements at 1.0× and speeding up slow or repetitive parts when useful. Vary shot lengths and cutting patterns to create natural, engaging pacing.

5. **Finalize the timeline:** Prioritize storytelling and natural action flow. Use measured beats where alignment improves the edit, not accumulated rounded beat intervals. Accumulate integer output frames at 30 fps, then derive timestamps and duration. Retain original audio for mixing.

6. **Save the plan:** Save a draft `workdir/plan.json`, then use `python3 tools/evidence.py shots workdir/plan.json` (`--help` for options) to obtain cached first/middle/last source frames for each shot. Review natural action boundaries and transitions; revise as needed. Validate source-window containment, speed/duration arithmetic, consecutive timing, stage coverage, and duration under 30 seconds before finalizing.

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

Timestamps are seconds; source ranges are half-open `[src_in, src_out)`. Use one shot per continuous range.

## Done when

- The edit tells the complete cooking story with natural action continuity.
- All shots have valid source ranges, speeds, and consecutive output timestamps.
- Music synchronization is planned and the total duration is under 30 seconds.
- `workdir/plan.json` is valid and complete.
