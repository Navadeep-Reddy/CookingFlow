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

2. **Prepare the video edit:** Apply `plan.json` with exact crops from `framing.json` and settings from `grade.json`. Use planned picture timing, not audio-padded container duration, for retiming. Minimize encoding passes through supported skill operations; reuse valid intermediates.

3. **Prepare the audio mix:** Use one continuous section from `music.start` for the full Reel, without a music fade-out. Align retained cooking sounds to their shots and keep them audible beneath music, especially at normal speed. Mute unnatural sped-up audio; record per-shot gain/mute and source-edge fades.

4. **Render the Reel:** Render only selected footage through the skill. Export `workdir/final.mp4`: 1080×1920, 30 fps, H.264, AAC stereo.

5. **Inspect the result:** Combine Reels, under-30-second, and content checks in the final QC pass. View a contact sheet and transition frames for awkward cuts, missing actions, framing, and food colors. Verify audio levels, clipping, music continuity, and retained cooking sounds. Distinguish signal checks from listening.

6. **Finish and report:** Correct failures and rerun affected checks; reuse unchanged results. Save findings and limitations to `workdir/verification.md` and deliver verified `workdir/final.mp4`.

## Output

- `workdir/final.mp4` — finished Reel.
- `workdir/verification.md` — technical, visual, and audio checks, including any limitations.

## Done when

- The Reel is 1080×1920 (9:16), 30 fps, and under 30 seconds.
- The shots follow `plan.json`, with framing and grading applied as saved.
- The music plays continuously, and suitable original cooking sounds are included where available.
- The rendered video passes Reels checks and its shot transitions, framing, colours, and audio have been checked.
- `workdir/final.mp4` and `workdir/verification.md` are saved.
