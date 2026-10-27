# Step 0: Preflight

Runs in the main agent. Establish the selected media, effective requirements, and inspection capabilities. On resume, reuse saved selections and probes; fill missing information without starting the job over.

## Inputs

- User request and any saved selection in `workdir/inputs.json`
- `Clips/`, `Sounds/`, and referenced reusable assets
- `AGENTS.md` and the skill instructions

## Actions

1. Read progress and saved outputs first. Create the checklist from the index only if missing. Check that the saved selection and requirements still describe this edit; do not silently mix results from another edit.
2. Confirm image inspection using a real image, preferably an already-extracted source frame. Record whether direct audio listening is available separately; its absence does not prevent numerical audio analysis.
3. Use the files named by the user or already selected for this edit. Ask together for unresolved footage/song choices. If a source is missing, ask the user to place it in the appropriate media folder.
4. Inspect selected source metadata through the skill. Reuse existing probe results unless the source changed or the result is defective. Save duration, audio availability, displayed geometry, rotation, frame timing, and color information needed downstream.
5. Record effective output requirements: Instagram Reels, 1080x1920, strictly under the default duration limit unless overridden, and any requested frame rate or other exception. Preserve user overrides verbatim in `user_notes`; keep later user-approved exceptions here too.
6. Write `workdir/inputs.json`. Preserve useful existing fields when upgrading an older handoff.

## Output contract

`workdir/inputs.json` carries the following fields; source probe details and notes may be added as needed:

```json
{
  "step": 0,
  "status": "partial",
  "capabilities": {"vision": null, "listening": null},
  "output": {"platform": "reels", "width": 1080, "height": 1920, "max_duration": 30.0, "fps": null},
  "clips": [
    {"id": "c1", "path": "Clips/example.mp4", "duration": null,
     "display_width": null, "display_height": null, "fps": null,
     "rotation": null, "has_audio": null, "probe_path": null}
  ],
  "song": {"path": "Sounds/example.mp3", "duration": null, "probe_path": null},
  "user_notes": "",
  "limitations": []
}
```

`probe_path` references a saved metadata result in `workdir/`. A null output frame rate leaves its selection to step 3. Required source facts must be measured before completion; unavailable optional metadata is explained, not invented.

## Done when

- [ ] Image inspection works; direct listening capability is recorded honestly
- [ ] The user selected the footage and song, and every selected file exists and has usable saved metadata
- [ ] Effective requirements and user exceptions are recorded
- [ ] `inputs.json` satisfies its contract and has `status: complete`
