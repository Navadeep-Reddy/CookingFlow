# Step 2: Music analysis

Runs as `music-analyst`. Find a strong start and measured rhythm references for one continuous song window, without rearranging or preparing the final music bed.

## Inputs

- `workdir/inputs.json` and its selected song, metadata, and effective duration limit
- Existing `workdir/music.json` and its measurements when resuming

## Actions

1. Reuse saved measurements. Decode samples through a currently supported skill route only when needed; do not assume that a tool exposing rhythm analysis accepts audio-only input. Temporary code may analyze skill-decoded samples under the global rules.
2. Use energy-jump analysis every time: measure RMS in one-second windows across the track, then compare the four seconds after each candidate time with the four seconds before it. Pool mean-square energy before converting to dB so the comparison is reproducible; document channel handling and silence handling with the saved series.
3. Rank the strongest positive jumps, then inspect plausible transitions with 0.1-second RMS windows to locate their onsets. Save the coarse series, refinements, and candidate evaluations incrementally; do not repeat the whole analysis to recover context. The candidate count and refinement extent depend on the song.
4. Listen to candidates when possible and consider rhythm, structure, sustained energy, and the available tail. A jump alone is not a musical beat drop. Without listening, use an energy-based recommendation and state which musical qualities remain unverified.
5. Recommend a start and usable end for a window that can support the requested edit. No internal cuts, splices, or loops. Flag natural fade-outs and weak tails. Insufficient material for the maximum duration is not automatically a blocker: step 3 may choose a shorter edit.
6. Measure beat/onset references using a supported route or analysis of decoded samples. Save times on the original song timeline, method, and reliability. Distinguish onset-supported beats from an extrapolated regular grid. If a reliable reference cannot be obtained, save an explicit unavailable result and the useful energy findings; do not invent tempo or beats.
7. Record vocals as present, absent, or unknown with evidence. Lack of listening must not become a confident claim of absence. Step 6 evaluates any required removal.

## Output contract

`workdir/music.json`:

```json
{
  "step": 2,
  "status": "partial",
  "song": "Sounds/example.mp3",
  "rms_series": null,
  "candidates": [],
  "recommended": {"start": null, "max_end": null, "basis": "energy", "reason": ""},
  "rhythm": {"status": "unavailable", "tempo_bpm": null, "beats_song_t": [],
             "method": "", "reliability": null, "evidence": ""},
  "vocals": {"present": null, "basis": "unknown", "evidence": ""},
  "limitations": []
}
```

Candidates carry `{onset_t, jump_db, evidence}` on the song timeline. `recommended.basis` is `energy` or `beat_drop_confirmed`; the latter requires listening. `rhythm.status` is `measured` or `unavailable`; record the reason if unavailable, and the interpretation of reliability when measured. Restrict `beats_song_t` to references supported by the measured signal. Evidence and resume notes are free-form and live in `workdir/`.

## Done when

- [ ] The full-track RMS comparison and fine onset inspection are saved and candidates have been evaluated
- [ ] The recommended continuous window has a measured range and any coverage or natural-fade concern is recorded
- [ ] Rhythm references are measured with a reliability explanation, or their unavailability is explicit
- [ ] Beat-drop and vocal claims match the available evidence; lack of listening has not discarded numerical findings
- [ ] `music.json` satisfies its contract and has `status: complete`
