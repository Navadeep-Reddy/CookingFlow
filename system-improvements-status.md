# System improvements — reset-safe handoff

## Fresh-session test outcome: editorially rejected

- The fresh test missed a readable cream addition and repeated finished-food shots; see `fresh-session-analysis.md` for verified findings and recommendations. The workflow remains steps 0–6, with helper recommendations in the relevant step files.
- Footage/music analysis run in parallel; framing/grading run in parallel after planning. Editorial choices remain with the agents.
- Source-cut detection is a separate unfinished task. The previous edit used skill scene detection plus visual review; the detector missed meaningful discontinuities. `evidence.py cuts` inspects planned output transitions, not source cuts.

## Implemented helpers

- `tools/evidence.py`: shared cached probes/PNG samples, native survey sheets, shot samples and adjacent output-transition frames. Crop views are HTML/browser views, not baked PNG crops; inspect actual pixels through supported previews when needed.
- `tools/music.py`: cached skill-decoded PCM, pooled energy/onset features, high-point candidates, supported beat fits and the existing two-field music handoff. Tested on all four songs in `Sounds/`; the original song exactly reproduced the previous handoff.
- `tools/render_edit.py`: frame/crop/audio-policy validation, skill-backed execution, version-aware LUT blend handling, hash-validated stage reuse, execution ledgers, final technical checks and optional numerical two-stem evidence.
- `tools/benchmark_render.py`: isolated baseline/optimized render comparison and unchanged cached repeat, timed from saved creative decisions.
- Usage contracts: helper `--help` and `tools/README.md`. Music and optional audio regression require NumPy/SciPy (`tools/requirements-music.txt`).

## Latest resolution policy and verification

- No fixed delivery-resolution cap. The renderer derives the largest common 9:16 dimensions available from the selected source crops, without upscaling; the tightest crop determines the common native output size.
- Fit and join use those dimensions; Reels export uses `--no-scale` to preserve them.
- Full real-media verification: **1440×2560, 30 fps, 884 frames, 29.482 s container / 29.466667 s picture, H.264, AAC stereo 48 kHz**.
- Reels/under-30-second/content checks: **16 PASS, 1 optional-subtitles WARN, 0 FAIL**; −13.2 LUFS, −1.0 dBTP, no detected black/frozen/silent spans or digital dropouts. Native output survey visually inspected.
- **34 automated tests passed**; whitespace checks passed. Resolution changes replaced existing source lines without increasing their line counts.

## Historical controlled benchmark

- Before the native-resolution change, at the former fixed delivery size: baseline **174.71 s / 54 per-shot video encodes**, optimized cold **168.78 s / 48**, optimized warm **1.99 s / zero new encodes** and 73 cache hits with zero media-skill calls.
- A one-shot audio-gain change reused 66 stages and rebuilt only seven dependents. Full trim/arbitrary-crop/resize fusion is not exposed by the unchanged installed skill.
- These timings do not describe the latest native-resolution output or a fresh editorial session. They are a single sequential paired run with empty artifact caches; filesystem caches were not flushed.

## Reset expectations

- `reset.py` clears generated state, caches, detailed run logs and renders under `work/` and `workdir/`, plus matching root exports/recipes. It preserves source media, assets, helpers, workflow instructions and this handoff.
- The next session is intentionally a cold-cache test. Reset creates a fresh checklist matching the current workflow's steps 0–6.
- Do not reuse old source-specific gains, crop choices, LUT strengths or song sections as mandatory recipes. Save the new session's actual decisions and verification results before the next reset.
