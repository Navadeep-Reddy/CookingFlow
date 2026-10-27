# Step 1: Footage analysis

Runs as `footage-analyst`, using a vision-capable model. Understand the source once and save enough detail for planning without another full footage review.

## Inputs

- `workdir/inputs.json` and its selected clips and saved metadata
- Existing `workdir/footage.json` and its evidence when resuming

## Actions

1. Resume saved coverage and findings. Save results incrementally in `footage.json`, noting completed source ranges and where to continue; never discard completed coverage after a context change.
2. Inspect the clips using the skill's frame extraction and scene-analysis capabilities. Automatic boundaries are hints. View action beginnings, endings, and ambiguous transitions, not only a sparse overview.
3. Label the whole source as coherent segments or idle stretches. Segment kinds are `one_shot`, `repetitive`, `beauty` (finished dish), `setup`, and `idle`; activity is `high`, `low`, or `none`. Keep short one-shot actions intact in this analysis. Later time-skip phases are selections within a repetitive segment, not separate takes.
4. Record action onset and completion from viewed frames, including bowl tilt or utensil entry before a pour's peak. For segments without a discrete action, use null action times and describe the visible movement or lack of it. Note moving finished-dish material suitable for the opening or ending.
5. Analyze source audio where present. Listen when available; otherwise correlate measured audio events with visible contacts or motions. Record distinct cooking sounds, event times, useful source ranges, and the evidence basis. A peak alone does not identify a chop. Mark unknown sound identity or unavailable analysis explicitly; a source with no audio is not applicable, not a failure.
6. Detect alternate takes of the same action, including changes of angle. Compare completeness, motion, framing, and mistakes; recommend exactly one best take per group with a reason. Repeated chops within one take are not retakes.
7. For repetitive actions, propose useful forward-moving phases according to the footage, without a mandatory phase count. For slow but active stretches, suggest a speed of `1.5` or `2.0` where natural; do not suggest speeding up idle or one-shot actions.
8. Describe each subject's position for step 4, without duplicating its crop measurements. Save evidence paths and explain any gap instead of returning an empty result.

## Output contract

`workdir/footage.json`:

```json
{
  "step": 1,
  "status": "partial",
  "coverage": [],
  "clips": [
    {"id": "c1", "summary": "", "audio_analysis": "unavailable", "segments": [
      {"id": "c1-seg01", "label": "", "kind": "one_shot", "activity": "high",
       "src_in": null, "src_out": null, "action_start": null, "action_end": null,
       "subject_note": "", "evidence": [], "sounds": [
         {"id": "c1-sound01", "event_t": null, "src_in": null, "src_out": null,
          "type": null, "basis": "inferred", "evidence": ""}
       ]}
    ]}
  ],
  "retake_groups": [],
  "time_skip_candidates": [],
  "speed_candidates": [],
  "limitations": []
}
```

- `coverage`: completed ranges `{clip, src_in, src_out}`; optional resume notes identify unfinished work.
- `audio_analysis`: `listened`, `measured`, `unavailable`, or `not_applicable`. Empty `sounds` alone does not establish that no cooking sounds exist. Sound `basis` is `listened` or `inferred`; explain the measured/visual evidence.
- Retake groups: `{id, members, best, reason}` with segment IDs. Time-skip candidates: `{segment, phases: [{src_in, src_out, note}]}`. Speed candidates: `{segment, suggested_speed, reason}`.
- Extra notes and evidence are free-form. Unknown labels or times remain null with a limitation; never fabricate event timing.

## Done when

- [ ] All source time is accounted for, with coherent action boundaries and verified action times where applicable
- [ ] Retakes, moving finished-dish material, useful repetitive phases, and speed candidates are recorded where present
- [ ] Audio findings have evidence, or an explicit unavailable/not-applicable reason; event ranges lie inside their segments
- [ ] `footage.json` satisfies its contract, has `status: complete`, and identifies any limitations for step 3
