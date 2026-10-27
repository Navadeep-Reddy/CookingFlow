# Step 7: Render and verify

Runs in the main agent with vision. Assemble the agreed edit through the skill, then verify the actual encoded result. Technical compliance does not establish editorial quality, and an unverified requirement is not a pass.

## Inputs

- `workdir/inputs.json`, `footage.json`, `music.json`, and `plan.json`
- `workdir/framing.json`, `grade.json`, `audio.wav`, and `audio.json`
- Referenced media, assets, and saved evidence; existing render artifacts and verification on resume

## Assembly requirements

1. Reuse unchanged intermediates and evidence. Translate the editorial handoffs into the skill's currently supported execution format; do not pass `plan.json` to a tool merely because both use JSON. If a required per-shot operation needs prepared intermediates, discover and use a supported route rather than inventing project keys.
2. Choose stages and their order from the actual inputs and current skill interface. Preserve the agreed source ranges, shot ordering, speed, framing, input color handling, grade overrides, and audio placement. Keep generated recipes, commands, and run evidence in `workdir/`, not in these instructions.
3. Inspect the execution plan before writing. Do not let automatic snapping, duration fitting, transitions, or platform defaults silently change the settled edit. The prepared mix replaces source sound; it must not be layered over another copy of the original audio. Complete only pending fades recorded in `audio.json`.
4. Produce `workdir/final.mp4` at the effective output geometry/frame rate, strictly within the requested duration cap. Keep the music window continuous and the closing shot covered until the intended fade reaches the endpoint. Verify the actual encoded loudness and true peak after all fades and export processing.

## Verification

Record evidence and a verdict for each applicable requirement in `workdir/verification.md`. Reuse earlier analysis as the reference; inspect the output to verify execution, not to rebuild the footage or music analysis.

### File

- Confirm actual dimensions, frame rate, duration, audio stream, and destination compliance through the skill. Independently enforce the channel/user duration cap even if the platform permits longer videos.
- Check tool verification results, not just exit success. Fix failures; evaluate and report warnings without silently changing editorial choices. Use frame/sample-aware tolerances for timing comparisons and account for encoding/container padding.

### Picture

- View sequences around cuts: complete one-shot actions build naturally and finish visibly. Time-skip phases enter readably and advance to distinct later points; they do not need a fresh whole-action onset.
- Verify the moving finished-dish opening when suitable footage exists, then the process and moving result. Check any planned fallback and intentional teaser reuse against the plan.
- Compare framing across the shot, including action extremes, and confirm a fixed crop/transform within each shot. A midpoint image cannot establish that the framing never moved. Food, essential actions, and utensils stay readable and in context.
- Compare successive frames or short sequences to identify idle/static stretches. A single sampled still cannot prove motion. Distinguish useful small movement from nothing happening.
- Verify only the chosen take of each action appears. Multiple forward-moving phases from it and the planned finished-dish teaser are allowed; alternate retakes are not.
- Check playback speed against the plan and visible motion. Compare final-grade frames with the source, especially light food and differing sources; preserve natural food colors, detail, and the tuned filmic look.

### Sound

- Verify the song follows one continuous range and is not inadvertently looped, spliced, or doubled. Check the entrance and closing fade occur once.
- Verify music coverage using stem/processing evidence as well as the encoded mix. Cooking sounds or room tone must not disguise missing music. The intended fade can reach silence at the endpoint; there must be no preceding dead-air stretch caused by source fades or ducking.
- Confirm selected cooking sounds are present at their planned output times, clear against the bed, with muted/omitted audio remaining absent. Verify the sync of claimed sound events against song beats within the chosen output frame's precision; do not treat cuts alone as proof of sound sync.
- Listen when available. Otherwise use numerical evidence for timing, levels, continuity, and transients, explicitly separating it from unverified perceptual or semantic claims. Required vocal/noise or perceptual checks without adequate evidence need a user decision, not a fabricated pass.

## Rework and report

Return defects to their owner under the index's rework rule: action selection/timing to step 3, crop to step 4, color to step 5, mix to step 6, or assembly mistakes within step 7. Preserve unaffected work and refresh only affected dependents. Exhausted retries never convert a defect into success.

Keep the user-facing summary compatible with the skill's report format: output path, measured delivery facts, technical/editorial verification, evidence path, and limitations. Save shot details, drops/reasons, music start/basis, speed choices, and individual check results in `verification.md` rather than forcing a long chat report.

## Done when

- [ ] `final.mp4` exists and its measured properties meet the effective output requirements and destination checks
- [ ] Picture, audio, and timeline checks above have evidence and passed, or a specific user-approved exception is recorded
- [ ] Unverified claims, warnings, and approved exceptions are disclosed; no unresolved required result is labeled complete
- [ ] `verification.md` records the final result and supporting evidence, and the user has received the summary
