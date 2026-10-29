# Step 6: Render, Audio Mix & Verify

This step turns the saved editing, framing, and grading decisions into the final Reel, mixes the music with original cooking sounds, and checks the finished video.

## Inputs

- `workdir/progress.md` — selected files and user requirements.
- `workdir/plan.json` — shot order, trims, speeds, timings, and music.
- `workdir/framing.json` — zoom and position for each shot.
- `workdir/grade.json` — LUT and colour settings for each shot.
- Original video and music files referenced by the plan.

## Actions

1. **Check the plans:** Confirm that every planned shot has valid source times, framing, and grade settings. Check which shots have original audio. If all source audio is disabled despite available cooking sounds, review that decision before rendering.

2. **Prepare the video edit:** Use the exact shot order, trims, speeds, and output timings from `plan.json`. Apply each shot's zoom and position from `framing.json` and colour settings from `grade.json`.

3. **Prepare the audio mix:** Use one continuous section of music starting at `music.start` and lasting the full Reel. Place retained original audio at the matching shot times. Keep useful cooking sounds audible beneath the music, especially from normal-speed shots. Mute sped-up source audio when it would sound unnatural, and Use the continuous music section selected in plan.json, preserving its natural ending without adding a fade-out.

4. **Render the Reel:** Use the ffmpeg skill to render only the selected footage with video and audio together. Export `workdir/final.mp4` as a 1080×1920, 30 fps, H.264 video with AAC stereo audio.

5. **Inspect the result:** Run the skill's Reels checks. Inspect frames around shot transitions and a contact sheet of the final Reel for awkward cuts, missing actions, poor framing, and unnatural food colours. Check audio levels, clipping, music continuity, and whether retained cooking sounds are actually present in the mix.

6. **Finish and report:** Correct any failed checks and verify the result again. Save the findings to `workdir/verification.md` and deliver the verified `workdir/final.mp4`.

## Output

- `workdir/final.mp4` — finished Reel.
- `workdir/verification.md` — technical, visual, and audio checks, including any limitations.

## Done when

- The Reel is vertical, Max resolution 9:16, 30 fps, and under 30 seconds.
- The shots follow `plan.json`, with framing and grading applied as saved.
- The music plays continuously, and suitable original cooking sounds are included where available.
- The rendered video passes Reels checks and its shot transitions, framing, colours, and audio have been checked.
- `workdir/final.mp4` and `workdir/verification.md` are saved.










































