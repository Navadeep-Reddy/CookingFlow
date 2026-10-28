---
description: Analyze the selected song to find all the required information about the music
mode: subagent
---

Read `.claude/skills/ffmpeg-skill/SKILL.md` and `workflow/02-music-analysis.md`.

Use the ffmpeg skill to decode the selected song into audio samples. Perform energy, onset, and beat analysis on those samples using appropriate numerical analysis tools save the results to `workdir/music.json`.