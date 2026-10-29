# Step 2: Music Analysis

## Inputs

- `workdir/progress.md` — selected song.

## Actions

1. **Analyze the song:** Run `python3 tools/music.py "Sounds/SONG"` (NumPy/SciPy required; `--help` for options). It caches skill-decoded PCM, pooled channel power, and spectral onsets; reports 1-second RMS and ranks 4-second energy rises: `10 log10(after / before)`.

2. **Find the best high point:** Examine promising energy increases using 0.1-second windows to locate their precise onsets. Choose the strongest suitable musical high point with enough music remaining for the Reel.

3. **Choose the starting point:** Set the music start approximately 1 second before the selected high point to create a short build-up. Adjust slightly for a natural musical entry.

4. **Map the beats:** Analyze onsets in the selected 30-second section; estimate beat period and phase, match grid positions to detected onsets, and verify alignment across the beginning, middle, and end. Save supported timestamps and alignment errors.

5. **Save the result:** Review `workdir/music-analysis/analysis.json`; use `--high-point SECONDS` to refine selection with cached measurements. Only a validated run emits `music.json`; `--publish workdir/music.json` writes the handoff (`--overwrite` to replace). Numerical validation does not replace musical judgement.

## Output

```json
{
  "start_song_t": 41.3,
  "beats_song_t": [42.3, 43.1, 43.9, 44.7]
}
```

- All timestamps use the original song's decoded playable timeline; record any container-padding difference.
- Include detected, supported beat positions in chronological order.
- Step 3 uses the start and beat timestamps to plan the final edit.

## Done when

- A suitable starting point with a short build-up has been selected.
- The chosen music section has been analyzed for beats and prominent accents.
- `music.json` contains the final start and valid synchronization timestamps.
