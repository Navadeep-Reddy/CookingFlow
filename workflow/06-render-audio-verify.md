# Step 6: Render, Audio Mix & Verify

Render the saved edit, mix music with cooking sounds, and verify the finished Reel.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/plan.json` — shot order, trims, speeds, timings, and music.
- `workdir/framing.json` — zoom and position for each shot.
- `workdir/grade.json` — LUT and colour settings for each shot.
- Original video and music files referenced by the plan.

## Actions

1. **Check the plans:** Validate every shot's source times, framing, grade, and audio policy. Review an all-muted source mix if useful cooking sounds are available.

2. **Prepare execution:** Check `python3 tools/render_edit.py --help` against the required output. The runner applies saved trims/crops/speeds/grade, checks frame counts and LUT semantics, avoids redundant resizing, and reuses validated stages. Export at max source 9:16 resolution, using the largest common source-crop dimensions without upscaling; resolve unsupported input handling through supported skill operations. See [execution details](../tools/README.md#saved-edit-rendering).

3. **Prepare the audio mix:** Use one continuous section from `music.start` for the full Reel, without a music fade-out. Align retained cooking sounds to their shots and keep them audible beneath music, especially at normal speed. Mute unnatural sped-up audio; write explicit per-shot gain/mute/source-edge fades and music/mix levels to `workdir/audio-policy.json` using the runner's documented schema.

4. **Render the Reel:** For a compatible job, pass `workdir/plan.json` and the framing, grade, audio-policy, and footage paths to the runner, first with `--validate-only`, then without it. Its manifest names the cached final, dependencies, timings, and Reels/under-30-second/content checks. Add `--audio-evidence` for measurable stereo stems to check presence/alignment numerically. For skill-project execution, apply the same saved decisions, planned picture speeds, required resolution, 30 fps, H.264/AAC stereo, and final checks.

5. **Inspect the result:** Review technical checks. Use `python3 tools/evidence.py survey FINAL` for a cached PNG contact sheet and its `cuts FINAL --plan workdir/plan.json` mode for adjacent frames at planned output transitions (`--help` for options). View the PNGs for awkward cuts, missing actions, framing, and food colors. Check audio levels, clipping, music continuity, and cooking sounds; distinguish signal checks from listening. These samples do not detect source cuts.

6. **Finish and report:** Correct failures and rerun affected checks; reuse unchanged results. After editorial review, publish the verified output to `workdir/final.mp4`; for a cached runner output, use skill `export.py --preset copy`, following output safety rules. Save technical, picture, and audio findings and limitations to `workdir/verification.md`.

When investigating execution performance, use `python3 tools/benchmark_render.py --help`: it compares isolated baseline/optimized renders and a cached repeat from saved decisions, with wall times and encode counts. This diagnostic is separate from normal edit delivery.

## Output

- `workdir/final.mp4` — finished Reel.
- `workdir/verification.md` — technical, visual, and audio checks, including any limitations.

## Done when

- The Reel is max source 9:16 resolution, 30 fps, and under 30 seconds.
- The shots follow `plan.json`, with framing and grading applied as saved.
- The music plays continuously, and suitable original cooking sounds are included where available.
- The rendered video passes Reels checks and its shot transitions, framing, colours, and audio have been checked.
- `workdir/final.mp4` and `workdir/verification.md` are saved.
