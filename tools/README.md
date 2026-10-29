# Workflow helpers

Generated outputs belong under `workdir/`. Installed skill scripts perform all media operations; originals are never overwritten. Run each helper's `--help` for its complete contract.

## Evidence

```bash
python3 tools/evidence.py shots workdir/plan.json --framing workdir/framing.json
python3 tools/evidence.py cuts workdir/final.mp4 --plan workdir/plan.json
```

Shared PNG cache, native survey sheets, and HTML crop views. HTML crops are browser views, not baked PNG crops. `cuts` inspects **planned output transitions**, not source-cut detection. View the PNG evidence before approving.

## Music

```bash
python3 tools/music.py "Sounds/song.mp3"
```

Requires `tools/requirements-music.txt` (NumPy/SciPy). Full-song decoded PCM, pooled energy, and onsets are cached. Review high-point candidates and beat evidence in `workdir/music-analysis/analysis.json`; `--high-point` changes the selection without re-decoding. Only validated runs emit a two-field `music.json`; `--publish workdir/music.json` publishes it, with `--overwrite` required for replacement. Numerical alignment is not musical judgement or listening.

## Saved-edit rendering

```bash
python3 tools/render_edit.py workdir/plan.json \
  --framing workdir/framing.json --grade workdir/grade.json \
  --audio-policy workdir/audio-policy.json --footage workdir/footage.json \
  --audio-evidence
```

`--validate-only` checks the source timeline, exact crops, audio policy, and optional selected-moment/stage coverage before encoding. Sources must be prepared SDR/CFR; technical colour conversions are not inferred. Rendering checks complete grade decisions and version-specific LUT blend semantics. Overrides accept `lut_path`/`strength`; unsupported corrections are refused.

Explicit audio policy, keyed by every shot ID:

```json
{
  "shots": {
    "s01": {"gain_db": -5, "mute": false, "fade_in": 0.02, "fade_out": 0.025}
  },
  "music_gain_db": -3,
  "mix_fade_in": 0.025
}
```

Values above illustrate the schema, not mandatory mix levels. Decide gains/mutes for the actual footage; `keep_original_audio: false` or `mute: true` silences that shot. Ending music/mix fades are refused. `--audio-evidence` uses NumPy/SciPy and currently requires stereo, independently measurable non-silent cooking/music stems; omit it for an intentionally music-only edit and document that policy.

The helper:
- Validates integer frame timing, speed arithmetic, bounds, crop geometry and actual encoded frame counts.
- Uses accurate cuts and exact pixel crops through the installed skill.
- Combines speed/resize in `fit.py` when retiming is needed. Normal-speed, 30-fps shots defer resizing to the already-required join encode.
- Compensates `fit.py`'s container-duration-based calculation so planned speed is not changed by AAC tails; refuses unexpected frame counts.
- Applies the approved LUT, continuous music, Reels export and a combined under-30-second/content/platform check.
- Optionally verifies both audio stems with sample-rate-aware, both-channel regression and a bounded offset search. This does not establish perceptual balance or replace listening.
- Stores source/tool/parameter dependencies, output SHA-256, verified probes, dry runs, commands, stage times and cache hits/misses. Changed/missing/corrupt artifacts invalidate affected work.

`workdir/render-edit/manifest.json` names the content-addressed final MP4 and checks; `runs.jsonl` preserves timing history. Cache hits reuse saved probes only when output hashes still match. Outputs do not replace an existing `workdir/final.mp4`. After picture/editorial review, use skill `export.py --preset copy` to publish to the desired unused delivery path. A mechanical pass leaves editorial review pending; view survey/boundary PNGs through `evidence.py` and record the review.

**Supported limit:** the installed skill has no combined trim + arbitrary exact crop + resize operation, or per-clip crop/LUT project fields. Full fusion would require a separately approved supported-tool extension. Lossless `cut.py --edit-list` was investigated; a non-keyframe test ran past the requested end and fell back to encoding. It is not assumed frame-exact here. No raw FFmpeg bypass or installed-skill changes are used.

## Controlled benchmark

```bash
python3 tools/benchmark_render.py workdir/plan.json \
  --framing workdir/framing.json --grade workdir/grade.json \
  --audio-policy workdir/audio-policy.json --footage workdir/footage.json
```

Runs baseline/optimized renders sequentially with isolated empty artifact caches, then an unchanged optimized repeat. Both use the same saved editorial choices, sources, mix, grade, quality and presets; baseline always fits every shot, optimized skips redundant normal-speed fits and corrects speed inference. Wall times include process startup, export, compliance/content checks, and two-stem numerical verification. Music refresh and picture-evidence generation are measured separately. This times mechanical execution **from saved decisions**, not fresh editorial selection or the former ~40-minute session. A single paired run does not establish a universal speedup; OS/filesystem caches are not flushed.

Measured on the 18-shot, 884-frame saved edit:

| Execution | Render + technical QC | Newly executed per-shot video encodes |
|---|---:|---:|
| Baseline | 174.71 s | 54 |
| Optimized cold | 168.78 s | 48 |
| Optimized warm | 1.99 s | 0 |

Cold reduction: **3.4%**, six fewer per-shot encodes. Warm repeat reused 73 stages with zero media-skill calls. The full baseline/optimized manifests retain all command records; their cached `commands` describe how an artifact was originally made, not commands executed on a cache hit. Grade, join and delivery video encodes are additional common stages. Source-cut detection remains a separate task.

## Verification

```bash
python3 -m unittest discover -s tools -p 'test_*.py' -v
```
