# Step 6: Audio prep

Runs in the main agent. Prepare a continuous music bed with contributing cooking sounds, balanced and ducked to the picture. Save enough evidence to verify music coverage independently of other sounds in the mix.

## Inputs

- `workdir/inputs.json` and its media, capabilities, and user exceptions
- `workdir/plan.json` (music range, shots, retained audio ranges, and sync)
- `workdir/music.json` and its energy and rhythm findings
- `workdir/footage.json` and its sound-event evidence
- Existing `workdir/audio.json`, stems, and mix when resuming

## Rules

- The song is one continuous source window: no internal cuts, splices, or loops. Any cleanup must preserve its timing.
- Keep only distinct contributing cooking sounds. Exclude room noise and non-contributing speech, and mute all original sound from sped-up shots.
- Music covers the edit with a natural entrance and one closing fade to the endpoint, with no prematurely silent tail. Tune fades, gains, and ducking from the source and mix, not fixed starting values. Cooking sounds remain clear without draining the music's rhythm or ending.

## Actions

1. Reuse valid existing stems and settings. Discover supported operations for the selected inputs; do not assume extraction, trimming, placement, and removal belong to one particular script or render stage.
2. Prepare the planned music window without changing its timing. Apply supported cleanup options as appropriate.
3. Prepare retained cooking ranges and place them using the plan's source-to-output mapping. Preserve silence elsewhere in that layer. Omit unselected and sped-up source audio; do not add it again when the video is assembled.
4. Mix and duck under contributing cooking events, letting the bed recover. Verify event clarity and music presence; whole-file loudness alone does not establish either. If no contributing cooking sounds exist, record why ducking is not applicable rather than adding a meaningless operation.
5. Check the music contribution through the closing shot, including the effects of ducking and any fades. A source fade, a long duck release, and an added closing fade can combine into a dead tail. Inspect the music layer or its gain envelope as well as the mix; room tone in the mix is not evidence that music remains present.
6. Apply each entrance/closing fade once, here or in final assembly, and record what has already been applied. A planned closing fade may reach silence at the endpoint; music need not remain loud at the final sample. It must not disappear before that intended fade.
7. Measure the mix against the current destination requirements exposed by the skill. Tune where needed; final encoded compliance is checked again in step 7. Save `audio.wav`, matching the planned duration within sample precision, and `audio.json`.
8. Return a proposed window or timeline change to step 3 with the specific reason; never move the song or edit `plan.json` unilaterally. Reuse the original song measurements when the plan is revised.

## Output contract

`workdir/audio.wav` is the prepared mix. `workdir/audio.json`:

```json
{
  "step": 6,
  "status": "partial",
  "duration": null,
  "music_bed": null,
  "cooking_layer": null,
  "fades": {"in": {"applied": false, "duration": null},
            "out": {"applied": false, "duration": null}},
  "ducking": {"state": "not_applicable", "parameters": {}, "evidence": ""},
  "music_tail_evidence": [],
  "loudness": {},
  "limitations": []
}
```

Ducking state is `applied` or `not_applicable`. Save paths and actual processing parameters as evidence; null stem paths require an explanation and equivalent coverage evidence. Fade records tell step 7 which fades remain to be applied. Extra measurements, ranges, and listening notes are free-form.

## Done when

- [ ] The bed matches the plan's continuous song range without timing changes
- [ ] Only selected cooking ranges are included, correctly placed, with no original audio from sped-up shots
- [ ] Cooking sounds are clear and music stays present through the close; ducking and fade interaction have been checked without mistaking other sounds for music
- [ ] Mix duration and loudness are measured; applied/pending fades and listening limitations are recorded
- [ ] `audio.wav` is usable and `audio.json` satisfies its contract with `status: complete`
