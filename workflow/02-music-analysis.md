# Step 2: Music Analysis

## Inputs

- `workdir/progress.md` — selected song.

## Actions

1. **Analyze the song:** Measure RMS energy in 1-second windows across the entire song. Identify strong energy increases by comparing the pooled mean-square energy of the 4 seconds before and after each point, converting the ratio to dB.

2. **Find the best high point:** Examine promising energy increases using 0.1-second windows to locate their precise onsets. Choose the strongest suitable musical high point with enough music remaining for the Reel.

3. **Choose the starting point:** Set the music start approximately 1 second before the selected high point to create a short build-up. Adjust slightly for a natural musical entry.

4. **Map the beats:** Analyze the selected 30-second section to estimate the beat interval. Determine the beat grid's starting position using detected audio onsets, then verify its alignment with the music across the section. Save the aligned beat timestamps on the original song timeline.

5. **Save the result:** Verify the selected start and detected timestamps, then write `workdir/music.json`.

## Output

```json
{
  "start_song_t": 41.3,
  "beats_song_t": [42.3, 43.1, 43.9, 44.7]
}
```

- All timestamps are in seconds on the original song timeline.
- Include detected, supported beat positions in chronological order.
- Step 3 uses the start and beat timestamps to plan the final edit.

## Done when

- A suitable starting point with a short build-up has been selected.
- The chosen music section has been analyzed for beats and prominent accents.
- `music.json` contains the final start and valid synchronization timestamps.
