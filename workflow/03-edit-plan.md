# Step 3: Edit plan

Runs in the main agent; never delegate. Own shot selection, ordering, timing, speeds, sync, and the continuous music window. Plan from saved analyses rather than reviewing all source media again; return a specific missing fact to its analyst.

## Inputs

- `workdir/inputs.json`
- `workdir/footage.json` and its saved evidence
- `workdir/music.json` and its saved measurements
- Existing `workdir/plan.json` when resuming or revising

## Rules

- Open with a moving preview of the finished dish when available, then show the cooking process and end on the result with visible movement. If no suitable moving finished-dish material exists, choose the strongest active process shot and record the fallback. Do not keep idle stretches or static presentations.
- A short one-shot action (pour, flip, drop) starts with enough context to build naturally and plays through to a readable result at normal speed. Choose lead-in and tail from the footage, not fixed durations.
- Condense long repetitive actions using forward time-skips, selecting as many clear phases as useful. A later phase may enter an action already underway if the progression reads naturally; it need not restart the whole action. Preserve complete individual gestures where needed to avoid awkward cuts.
- Choose only the best take in each retake group. Several phases from that chosen take are allowed. A deliberate opening finished-dish teaser may reuse material shown at the ending; this is not permission to repeat alternate takes.
- Speeds are `1.0`, `1.5`, or `2.0`, constant per shot. Speed up only slow but active stretches when it looks natural, never idle or one-shot actions, and never just to squeeze extra content under the duration cap. Mute original audio on sped-up shots.
- Keep only distinct cooking audio that contributes; do not retain a whole noisy shot merely because it contains one useful sound. Sync salient short sounds to measured beats where compatible with the action; do not force continuous sizzling or pours onto every beat.
- The song is one uninterrupted window. Fit by selecting its start and end, never by internal cuts or loops. Prioritize sustained energy and a usable tail, not just the largest jump.

## Actions

1. Reuse the existing plan when valid. Evaluate candidates from the analyses, excluding idle material and losing retakes. Resolve material limitations with the user under the global rules; do not assume missing rhythm or sound analysis means permission to omit a required result.
2. Choose source ranges and repetitive phases, speeds, and ordering using the rules above. Record drops and their reasons. Select an output frame rate from source motion, destination support, and any user override.
3. Compute contiguous output timing using `(src_out - src_in) / speed`, accounting for source frame boundaries and output frame rounding. Keep the measured final duration strictly below `inputs.output.max_duration`, with room for actual frame rounding rather than an arbitrary margin. Drop lower-value moments when needed, not the completion of a kept one-shot action.
4. Choose a music window covering the actual timeline, using saved candidates and measurements. If the start moves, rebase beats from their original song times and reassess the new window's energy and tail. Ask step 2 only for missing coverage; do not repeat its full analysis.
5. Align cooking events in output time, not by blindly snapping source clip boundaries to a song grid:
   - `sound_out_t = out_start + (sound_src_t - src_in) / speed`
   - `beat_out_t = beat_song_t - music.start`
   Adjust legal lead-ins, tails, phase selection, or ordering while preserving action readability and the song window. Recalculate affected durations and placements. Do not sync sounds in muted sped-up shots or claim uncertain events as confirmed.
6. For retained original sound, record its source ranges and map each to `out_start + (range.src_in - shot.src_in) / speed`. All other source sound is omitted. Save `plan.json` as editorial data, not as a directly executable skill project.

## Output contract

`workdir/plan.json`:

```json
{
  "step": 3,
  "status": "partial",
  "output": {"width": 1080, "height": 1920, "fps": null, "duration": null},
  "shots": [
    {"id": "s01", "segment": "c1-seg01", "clip": "c1", "role": "action",
     "src_in": null, "src_out": null, "speed": 1.0,
     "out_start": null, "out_end": null,
     "keep_original_audio": false, "audio_ranges": [], "sync": [], "note": ""}
  ],
  "music": {"song": "Sounds/example.mp3", "start": null, "end": null, "reason": ""},
  "dropped": [],
  "limitations": []
}
```

Roles are `action`, `time_skip_phase`, `teaser`, `finished_dish`, or `setup`. Audio ranges carry `{src_in, src_out}`; sync entries carry `{sound_src_t, sound_out_t, beat_song_t, beat_out_t, basis}` referencing the analyses. Empty sync means no claimed alignment. Drops carry `{segment, reason}`. Optional reasoning is free-form.

## Done when

- [ ] The selected timeline fits effective output requirements; IDs, source ranges, speeds, and output timing are valid within frame precision
- [ ] One-shot actions are intact, time-skips progress naturally, only chosen takes are used, and the moving-dish opening/ending or recorded fallback is planned
- [ ] Audio ranges contain contributing sounds only; sped-up shots retain none
- [ ] The music range covers the edit continuously; sync uses the final window and valid output-time calculations
- [ ] Drops, limitations, and user decisions are recorded; no unresolved requirement blocks execution
- [ ] `plan.json` satisfies its contract and has `status: complete`
