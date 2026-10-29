# Reel Editing Workflow Retrospective

The main opportunity is to preserve the editorial decisions while replacing the improvised execution around them. The successful methods were source-time-aligned visual analysis, onset-supported music timing, frame-count-based planning, explicit crop geometry, visual grade comparisons, and measurable audio verification.

The avoidable work was primarily:
- Repeated video encoding between simple operations.
- Video-based assembly of still-image inspection sheets.
- Full-Reel renders for grade experiments.
- Repeated analysis and tool discovery.
- Limited reuse of evidence between stages.

This report documents the completed edit of `Clips/IMG_5777.mp4` with `Sounds/stay for the night.mp3`. Recommendations are proposals, not changes already implemented. Existing workflow files and installed skill scripts were not modified for this retrospective.

## Evidence and timing limits

The saved artifacts support exact command counts and parameters, but not a complete minute-by-minute breakdown of the roughly 40-minute session. Three stages have recorded elapsed times:

| Operation | Recorded time | Evidence |
|---|---:|---|
| Assemble prepared shots | 20.26 s | `workdir/assembly_cache/25c4b6a6121020b5e28db5450c3a7ec9dc653afe.json` |
| Mix continuous music with cooking audio | 1.33 s | `workdir/final_cache/8288794325291c3bb7cb01aad012e5b587043503.json` |
| Final export stage | 12.73 s | `workdir/final_cache/3cbccaa26d3e8212de4cb927a1e088f50f0ede33.json` |

Those three stages total **34.32 seconds**. The final export itself was therefore not the main bottleneck. Other costs below are identified from the executed processing structure; their exact elapsed times were not logged.

---

## 0. Preflight and orchestration

**Relevant files:** `workflow/00-preflight.md`, `workflow/00-index.md`

### Executed

1. Read project rules, skill instructions, workflow index, and existing progress.
2. Listed `Clips/`, `Sounds/`, and `workdir/`.
3. Resolved the request to:
   - `Clips/IMG_5777.mp4`
   - `Sounds/stay for the night.mp3`
4. Confirmed vision availability and recorded the paths in `workdir/progress.md`.
5. Delegated footage and music analysis together.
6. Later delegated framing; grading was performed by the main agent.

### Useful technique beyond the instructions

Very little needs adding to preflight itself. It correctly avoided media analysis and unnecessary confirmation of an unambiguous selection.

The important discovery is an **orchestration mismatch**:

- `00-index.md` assigns grading to a subagent and specifies parallel framing/grading.
- `05-grade-tuning.md` assigns grading to the main agent.
- Actual execution waited for framing, prepared the assembled edit, and only then tuned the grade. The intended overlap did not happen.

### Cost and faster execution

The delay was dependency-related rather than expensive preflight processing. Grading became dependent on the completed assembly even though its instructions allow representative source moments.

**Proposed, not executed:** While framing examines planned shots, the main agent should tune the LUT on representative source samples. Once both finish, rendering can start immediately.

### Exact additions recommended

**`workflow/00-index.md`:**
- Resolve the grading-owner contradiction.
- State that grade previews depend on the plan and source samples, **not the assembled Reel**.
- Assign ownership of shared probe records and sampled frames so stages reuse them.
- Add a requirement to record elapsed time per subprocess and per stage.

**Reusable tooling:**
- A small execution ledger recording command, input fingerprint, parameters, output, exit status, verification result, elapsed seconds, and cache hit/miss.

---

## 1. Footage analysis

**Relevant file:** `workflow/01-footage-analysis.md`

**Actual scripts:**
- `workdir/footage_survey.py`
- `workdir/footage_boundaries.py`
- `workdir/validate_footage.py`

### Executed

The source was **471.533333 seconds, 2160×3840, 30 fps, SDR BT.709**, approximately 4.5 GB.

The analysis used:

1. Skill `probe.py` → `workdir/footage_source_probe.json`.
2. A silent, full-duration **360×640, 30 fps proxy**, preserving the source time origin:
   - `workdir/footage_proxy.mp4`
3. An initial coarse contact sheet:
   - `workdir/footage_full_survey.png`
4. Six denser chronological surveys, implemented in `footage_survey.py`:
   ```text
   cut.py footage_proxy.mp4 --start A --end B --accurate --fast
   look.py survey_slice.mp4 --tiles 6x7 --width 1920
   ```
   The intervals were 0–80, 80–160, …, 400–471.533333 seconds.
5. Targeted detail sheets around:
   - Ingredient additions: 262–276 s.
   - Sauce-to-eggs transition: 302–332 s.
6. Scene candidates from:
   ```text
   scenes.py --threshold 8 --min-scene 0.5 --json
   ```
7. Boundary inspection for 18 selected moments:
   - `start + 0.1 s`
   - `end − 0.1 s`
   - 36 PNGs extracted from the proxy using `look.py`.
8. Validation of IDs, ranges, source existence, chronological order, and evidence.

**Outputs:** `footage.json`, `footage_analysis.md`, `footage_validation.json` in `workdir/`.

### Useful techniques developed

- **Coarse → dense → targeted inspection.** Broad coverage established the story; focused sampling resolved ambiguous additions and missing cooking steps.
- **Explicit source/local timestamp conventions.** Slice sheets contained local timestamps, while selected moments used original-source timestamps. The handoff documented the offsets.
- **Visual detection supplemented scene detection.** The scene detector missed meaningful cooking-state changes. Visual review identified softened onions, reduced sauce, and suddenly present cooked eggs.
- **Source windows were separated from final cuts.** The 18 moments contained 140.4 seconds of usable material; the edit planner chose shorter subranges.
- **Missing actions were recorded explicitly.** The edit preserved the genuine ellipsis rather than implying egg addition had been filmed.

These are worth formalizing as execution methods. The actual choice of strongest moments should remain editorial.

### Cost and unnecessary processing

- The full proxy required decoding the entire long 4K source.
- Six survey slices were then encoded from that proxy only to generate PNG sheets.
- Additional detail slices introduced more temporary video encoding.
- Many separate `look.py` processes repeated startup/probe/seek work.

A proxy was useful; **encoding additional proxy slices solely for sheet generation was avoidable infrastructure work**.

### Faster method preserving quality

**Proposed:**
- Keep one time-aligned analysis proxy when justified by source size.
- Generate interval-specific contact sheets directly from that proxy, without first creating sliced MP4s.
- Extract a timestamp batch per source rather than launching one process per frame.
- Reuse the resulting frames for planning and framing whenever timestamps match.

### Exact additions recommended

**`workflow/01-footage-analysis.md`:**
- Document the coarse/dense/targeted inspection sequence.
- Require a timestamp manifest containing source path, original timestamp, slice offset if applicable, and image path.
- Require recording observed discontinuities separately from detector candidates.
- Explain that the output contains usable windows, not final shot durations.

**Reusable tooling:**
- A skill-supported range contact-sheet operation with start/end and absolute source labels.
- A batched frame extractor with a timestamp manifest.
- Generalize `validate_footage.py`; avoid hard-coded source duration or stage counts.

---

## 2. Music analysis

**Relevant file:** `workflow/02-music-analysis.md`

**Actual scripts:**
- `workdir/analyze_music.py`
- `workdir/verify_music_beats.py`

### Executed

1. Probed the song and decoded it once using skill `audio.py`:
   - `workdir/music_full_samples.wav`
   - Stereo PCM s16le, 44.1 kHz.
2. Computed channel-averaged sample power.
3. Built a cumulative power sum for efficient arbitrary-window measurements.
4. Measured:
   - One-second RMS across the entire song.
   - Four-second pooled energy before/after candidate times.
5. Ranked energy increases, keeping candidates at least five seconds apart.
6. Inspected the top 12 candidate regions with 0.1-second windows.
7. Built onset features:
   - Downsampled by four.
   - STFT: `nperseg=1024`, `noverlap=914`.
   - Mean channel magnitudes, avoiding stereo cancellation.
   - Positive log-magnitude spectral flux.
   - Median-filter baseline subtraction.
8. Estimated beat period using autocorrelation and a period/phase comb search.
9. Matched predicted beats to detected onsets within ±60 ms.
10. Fitted period/phase and validated alignment across three ten-second blocks.

**Actual result:**
- Music start: **24.319002 s**.
- High point: **25.319002 s**.
- Build-up: **1.0 s**.
- Four-second energy rise: **15.01 dB**.
- Beat interval: **0.790515 s**, approximately **75.90 BPM**.
- Supported positions: **38/38**.
- Alignment error: **5.03 ms median**, **17.38 ms p95**.

**Artifacts:** `workdir/music.json`, `workdir/music_analysis.json`, RMS/energy/onset/alignment CSVs, `workdir/music_onset_features.npz`.

### Useful techniques developed

- **Prefix-sum energy measurement:** many RMS queries without repeatedly scanning samples.
- **Channel-magnitude onset analysis:** avoids cancellation from averaging stereo waveforms.
- **Detected onset timestamps saved instead of an unsupported synthetic grid.**
- **Alignment validated across the whole selected section**, not just its opening.
- **Codec-padding distinction recorded:** decoded playable audio was 179.629569 s, while the MP3 container probe included padding.

### Cost and unnecessary processing

There is a concrete script issue:

```python
from analyze_music import ROOT, np, signal, save, table, ms, db, duration
```

`analyze_music.py` runs its analysis at module scope. Therefore, running `verify_music_beats.py` **also reran full-song RMS, candidate analysis, and STFT computation** before beat verification.

Other limitations:
- The scripts depend on installed NumPy/SciPy.
- Candidate-region bounds and phase-search bounds in the beat script are specific to this song.
- Full-song onset analysis was computed although beat fitting concerned only the selected section.

### Faster method preserving quality

**Proposed:**
- Split reusable functions from executable entry points.
- Cache decoded audio and energy/onset features by source fingerprint and analysis parameters.
- Perform inexpensive full-song energy ranking first.
- Compute detailed onset features only for promising sections and the chosen 30-second interval.
- Parameterize candidate region, tempo range, and phase search.

### Exact additions recommended

**`workflow/02-music-analysis.md`:**
- Specify pooled channel energy, cumulative-sum measurement, onset-supported grid validation, and playable-audio timestamp convention.
- Require section-wide support/error metrics.
- State that numerical alignment is evidence, not a substitute for musical judgment.

**Reusable tooling:**
- Consolidate both scripts into a parameterized music-analysis utility.
- Eliminate import-time execution.
- Declare dependencies and cache formats explicitly.

---

## 3. Edit planning

**Relevant file:** `workflow/03-edit-plan.md`

**Actual script:** `workdir/build_plan.py`

### Executed

The plan was constructed from tuples containing:

```text
moment_id, source_in, output_frame_count, playback_speed
```

For every shot:

```text
output_duration = output_frames / 30
source_out = source_in + output_duration × speed
output_start = accumulated_output_frames / 30
```

The script:
- Assigned shot IDs.
- Accumulated integer output frame counts.
- Converted music beats to Reel-relative timestamps.
- Checked every source range against its selected moment.
- Asserted fewer than 900 output frames.

**Result:** 18 shots, **884 frames**, **29.466667 s** of picture, saved in `workdir/plan.json`.

The opening hero lasted 30 frames. Most action shots used 48 frames; longer deposits/reveal used 72 frames. Short exceptions preserved concise actions.

### Useful techniques developed

- **Integer-frame timeline construction** prevented accumulated floating-point duration drift.
- **Source-window containment checks** caught invalid subranges before rendering.
- **Short-action exceptions** avoided stretching a compact pour to fit a longer musical slot.
- The first major cut occurred at **1.0 s**, matching the selected musical high point.

### Important distinction: what was not executed

The script saved actual relative beats, but **did not algorithmically snap shot boundaries to them**.

Most durations were selected around a rounded 0.8-second rhythmic unit rather than each measured 0.7905-second interval. It was rhythm-informed editorial timing, not a fully beat-snapped timeline.

### Cost and faster execution

Planning itself was inexpensive. Its main inefficiency was duplicated boundary inspection across planning, framing, and final QC.

**Proposed:** Use a shared frame-evidence manifest so planning requests only missing timestamps; framing can consume the same boundary evidence.

### Exact additions recommended

**`workflow/03-edit-plan.md`:**
- Define output timing in integer frames, with seconds derived afterward.
- Resolve “total length being 30 seconds” against the actual requirement of **under 30 seconds**.
- Require continuity, speed-range, stage-coverage, and source-containment validation.
- Record musical alignment explicitly when used: target beat, actual cut frame, and difference.

**Reusable tooling:**
- Generalize `build_plan.py` into a plan compiler/validator accepting editor-selected shots.
- Preserve manual control over ranges, speeds, duration variation, and beat choices.

---

## 4. Framing

**Relevant file:** `workflow/04-framing.md`

**Actual scripts:**
- `workdir/inspect_framing.py`
- `workdir/build_framing.py`

### Executed

For each of 18 shots:

1. Converted source times to 30 fps frame indices.
2. Extracted:
   - First included frame.
   - Middle frame.
   - Last included frame.
   - First excluded frame.
3. Floored seek times to milliseconds to avoid rounding a requested frame forward.
4. Ran extraction with `ThreadPoolExecutor(max_workers=3)`.
5. Inspected **72 source-frame PNGs**, resized to 540×960.
6. Defined crops in that 540×960 coordinate system.
7. Converted them back to original source pixels by multiplying by four.
8. Generated three-frame applied-crop sheets per shot.
9. Validated geometry and checked that `plan.json` remained unchanged.

For this native-vertical source:

```text
crop_width  = 2160 / zoom
crop_height = 3840 / zoom
crop_x      = center_x × 2160 − crop_width / 2
crop_y      = center_y × 3840 − crop_height / 2
```

Examples:
- Hero: `(144, 0, 1800, 3200)`.
- Garlic: `(320, 1120, 1440, 2560)`.
- Working pan: `(112, 0, 1872, 3328)`.

**Artifacts:** `workdir/framing.json`, `workdir/framing_evidence.json`, `workdir/framing_validation.json`, `workdir/framing_notes.md`, 18 cropped sheets.

### Useful techniques developed

- **Last-included/first-excluded evidence** made trim boundaries explicit.
- **Crop choices were made on smaller images but stored in source coordinates.**
- **Exact even-pixel 9:16 boxes** avoided downstream rounding ambiguity.
- **Three-worker concurrency was actually used successfully.**
- Repeated compositions reused the same crop while still being checked individually.

### Cost and unnecessary processing

Applied-crop evidence required approximately:
- 54 cropped mini-videos: three per shot.
- 18 grid videos.
- 18 PNG extractions.

That is **90 media operations just to produce 18 still comparison sheets**, beyond the original 72 frame extractions.

The 72 initial extractions also repeatedly decoded the original large source, including duplicate hero timestamps.

### Faster method preserving quality

**Proposed:**
- Cache source frames by source fingerprint and frame index.
- Apply and display crops directly in PNG output.
- Assemble PNG sheets directly, without video encoders.
- Use the time-aligned proxy for composition; inspect original-resolution frames only where sharpness or crop-edge detail needs confirmation.

### Exact additions recommended

**`workflow/04-framing.md`:**
- Add the preview-to-source coordinate conversion method.
- Define half-open source ranges and frame-index evidence conventions.
- Require even, in-bounds source-pixel crop boxes.
- Clarify that these formulas use the **widest source 9:16 rectangle**; the simple `2160/zoom` formula is specific to this already-vertical source.

**Reusable tooling:**
- An applied-crop PNG sheet generator consuming `plan.json`, `framing.json`, and cached source frames.
- Store exact pixel rectangles alongside normalized centers to remove renderer interpretation ambiguity.

---

## 5. Grade tuning

**Relevant file:** `workflow/05-grade-tuning.md`

**Actual execution:** `workdir/execute_edit.py grade …`

### Executed

1. Inspected the existing asset:
   - `assets/luts/kodak_2383_constlclip.cube`
   - G’MIC header, 13³ LUT, domain 0–1.
2. Used SDR BT.709 source metadata and treated the asset as a display-referred creative look.
3. Rendered the **entire assembled Reel three times**:
   - `--lut-strength 0.30` → `workdir/edit_grade30.mp4`
   - `--lut-strength 0.12` → `workdir/edit_grade12.mp4`
   - `--lut-strength 0.88` → `workdir/edit_grade88.mp4`
4. Compared ungraded/graded frames at 0.5, 2, 17, and 24 seconds:
   ```text
   look.py edit_ungraded.mp4 --compare graded.mp4 --at …
   ```
5. Viewed all 12 comparisons.
6. Saved the approved execution details in `workdir/grade.json`.

### Critical discovery: reversed partial-strength behavior

The installed skill, version 2.17.2, emits:

```text
[original][graded]blend=all_mode=normal:all_opacity=FLAG
```

For intermediate flag values, this weights the **original** by `FLAG`.

Consequently:
- Flag 0.30 produced roughly 70% LUT contribution.
- Reducing the flag to 0.12 made the look stronger.
- Flag 0.88 produced the intended subtle, approximately 12% contribution.

The installed code has separate branches for exactly zero and one, so this should **not** become an unconditional “always invert the flag” rule.

### Useful techniques developed

- Recording **creative intent separately from actual execution parameters** made the result reproducible despite the tool behavior.
- Comparing light food, saturated ingredients, and dark surfaces exposed the problem.
- Inspecting the generated command resolved contradictory visual results.

### Cost and unnecessary processing

- Two rejected full-Reel grade renders.
- Three rounds of comparison extraction.
- Large web fetches of G’MIC source and FFmpeg documentation.
- Grading was delayed until after assembly, defeating intended overlap with framing.

### Faster method preserving quality

**Proposed:**
- Test representative source samples before rendering the full grade.
- Validate strength direction on a small sample before a search.
- Once approved, apply the grade once to the full edit.
- Save a compact LUT asset manifest with provenance, known input interpretation, and version-specific behavior.

The recorded research supports the display-image interpretation, but the asset header alone is not a rigorous input-color-space specification. Future documentation should distinguish documented facts from working assumptions.

### Exact additions recommended

**`workflow/05-grade-tuning.md`:**
- Require small representative previews before full-Reel grading.
- Require checking generated blend semantics if visual behavior contradicts the requested adjustment.
- Store effective creative contribution and actual script arguments separately.
- Fix references to nonexistent `inputs.json` and obsolete “step 7.”

**Reusable tooling:**
- A version-aware LUT-strength compatibility check.
- A compact LUT metadata/provenance file.
- Prefer an upstream correction for the reversed partial blend; keep the installed skill unchanged under current project rules.

---

## 6. Rendering, audio, and verification

**Relevant file:** `workflow/06-render-audio-verify.md`

### 6A. Video preparation and assembly

**Actual script:** `workdir/execute_edit.py`

For every shot, the executed chain was:

| Operation | Important parameters | Intermediate |
|---|---|---|
| Accurate source cut | `cut.py --accurate --preset ultrafast` | `sNN_cut.mp4` |
| Exact crop | `crop.py --x … --y … --width … --height … --preset ultrafast` | `sNN_crop.mp4` |
| Resize/retime | `fit.py --width 1080 --height 1920 --fps 30 --duration … --preset superfast` | `sNN_fit.mp4` |
| Audio edges/gain | `audio.py --fade-in .02 --fade-out .025 --gain …` | `sNN_sound.mp4` |

Each call had a saved dry-run JSON and execution JSON. Intermediates were stored in `workdir/`.

Then:
- `workdir/assembly_project.json` joined all 18 prepared clips.
- Transition type: `none`.
- `render.py` used explicit work/cache directories.
- Result: `workdir/edit_ungraded.mp4`.

#### Cost

This created **72 per-shot operations**, including **54 video re-encodes** before assembly: cut, crop, and fit for each shot.

A delivered frame then passed through assembly, grading, and final export as well: **six lossy video encoding generations along the successful path**. Rejected grade trials were additional branches.

There was also a small timing discrepancy: `workdir/s03_fit.json` shows `atempo=1.506250` although the plan says 1.5×. `fit.py` derived the ratio from the intermediate container duration, including audio-tail effects, rather than strictly from planned picture duration.

#### Exact improvements recommended

**Add to the workflow:**
- Compile exact trims, crop, scale, speed, and audio treatment from saved decisions.
- Base retiming on planned source-picture ranges/frame counts, not AAC-padded intermediate duration.
- Avoid separate full-resolution cut and crop encodes where a supported combined operation exists.

**Proposed tooling:**
- A plan-to-render compiler with a combined per-shot operation and strong validation.
- Ideally combine trim → crop → scale → retime in one video encode.

**Capability distinction:** The current `render.py` project schema does not expose per-clip crop/LUT settings. Merely moving the existing JSON into `render.py` cannot deliver that fusion. It needs a supported skill extension or an explicitly approved execution-tooling change, not raw FFmpeg bypasses.

### 6B. Audio mix

#### Executed

- Retained cooking audio on every shot.
- Used pitch-preserving retiming.
- Applied source attenuation:
  - Normal-speed shots: −5 dB.
  - Sped-up shots: −11 dB.
- Applied 20 ms/25 ms source-edge fades.
- Extracted one continuous song section using:
  ```text
  cut.py song.mp3 --start 24.319002 --duration 29.466667 --accurate
  ```
- Mixed through `workdir/project.json`:
  - Music gain: −3 dB.
  - Music ending fade: 0.6 s.
  - Mix edge fades: 0.025 s in, 0.12 s out.
  - Stereo output.
- Exported with Reels preset and normalization enabled.

**Actual final measurements:** −13.3 LUFS, −1.7 dBTP.

These gains were successful choices for this source, **not reusable mandatory mix levels**.

#### Useful technique and faster execution

Separating the continuous music bed from shot-local cooking audio worked well. The audio mix itself took only **1.33 s**, so optimizing it is lower priority.

**Add:** Per-shot audio policy and fades should be explicit saved parameters, rather than inferred from speed inside a script. Keep cooking sounds when useful; selectively reduce or mute unnatural retimed sounds.

### 6C. Picture and audio verification

**Actual script:** `workdir/verify_edit.py`

#### Executed

1. Final 6×3 contact sheet:
   - `workdir/final_sheet.png`
2. Extracted 34 near-cut PNGs:
   - One frame before and one frame after each of 17 cuts.
3. Attempted to grid those PNGs directly.
   - Failed because `grid.py` treated still inputs as zero-duration media.
4. Recovered using:
   - 34 `insert.py --duration .1` still videos.
   - Three grid videos.
   - Three sheet extractions.
5. Viewed all three boundary sheets.
6. Ran:
   ```text
   check.py final.mp4 --platform reels --max-duration 29.999 --content
   ```
7. Decoded final/cooking WAVs and performed a two-stem least-squares measurement against the music section.

**Results:**
- 16 PASS, one optional-subtitles WARN, zero FAIL.
- No detected black spans, frozen spans, silence, or dropouts.
- Both audio stems present.
- Joint explained waveform energy: **99.27%**.

**Evidence:** `workdir/final_check.json`, `workdir/audio_verification.json`, `workdir/boundaries_checked_1.png` through `workdir/boundaries_checked_3.png`, and `workdir/verification.md`.

#### Useful techniques developed

- **Final cut-pair inspection** caught issues a broad contact sheet could miss.
- **Waveform decomposition** supplied evidence that cooking audio had survived the music mix.
- A 44.1/48 kHz mismatch was handled with interpolation during measurement.
- The report explicitly distinguished signal checks from listening.

#### Cost and limitations

- Boundary-sheet assembly added **40 successful media operations after frame extraction**, plus the failed grid attempt.
- Compliance/loudness were measured in the render and again in the explicit final check.
- The audio script initially assumed 48 kHz everywhere and failed.
- Its regression sampled only one channel and excluded the end fades; it establishes stem presence/alignment in the analyzed interval, not perceptual balance or a listening-quality verdict.
- The final `verify_edit.py picture` implementation depends on preexisting extraction logs, so it is not a clean fresh-run utility.

#### Exact additions recommended

**Add to `workflow/06-render-audio-verify.md`:**
- Define a single final QC gate combining platform limits, under-30-second limit, content checks, picture review, and audio evidence.
- Request exact boundary frame indices from the plan.
- Reuse unchanged check results; rerun after relevant output changes.
- Require explicit disclosure when no listening audition occurred.

**Reusable tooling:**
- Direct timestamp/crop PNG sheets, eliminating all still-video wrappers.
- A fresh-run/resume-safe QC command.
- Optional two-stem regression supporting both channels, explicit rates, alignment tolerance, and a clear scope of what it proves.

---

## Cross-cutting changes with the highest payoff

| Priority | Recommended change | Why |
|---|---|---|
| **1** | Direct batched PNG extraction, crop previews, and sheet assembly | Eliminates the mini-video machinery used throughout analysis, framing, and QC. |
| **2** | Representative-sample grading plus strength-semantics check | Avoids full-Reel experiments and the discovered reversed-strength trap. |
| **3** | Supported fused per-shot rendering | Removes repeated 4K encodes and reduces generation loss. |
| **4** | Shared frame/probe/feature cache | Prevents stages from re-extracting the same evidence. |
| **5** | Parameterized music utility without import-time work | Removes demonstrated duplicate full-song analysis. |
| **6** | Resolve workflow ownership and stale references | Restores intended framing/grading overlap and removes agent ambiguity. |
| **7** | Instrumented, fingerprinted resume runner | Makes future bottlenecks measurable and reuse trustworthy. |

### What should be promoted—and what should not

**Promote the methods, not these scripts unchanged.** The generated scripts contain single-source dimensions, fixed 30 fps assumptions, song-specific search bounds, hard-coded shot selections, and run-specific output names.

In particular, `workdir/execute_edit.py` resumes by trusting a completed JSON status. It does **not** verify that inputs/parameters are unchanged or that the output still exists and probes correctly. Its skip mechanism was useful operationally, but needs fingerprinting and output validation before reuse.

A good reusable tool should automate:
- Timestamp arithmetic.
- Evidence extraction.
- Crop conversion.
- Rendering mechanics.
- Cache invalidation.
- Verification.

It should continue accepting editor-selected shots, timing, framing, grading, and mix decisions. **The successful creative choices do not need to become fixed recipes to make future runs substantially faster.**
