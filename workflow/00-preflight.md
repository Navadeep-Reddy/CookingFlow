# Step 0 — Preflight

**Owner:** Main agent

## Goal
Confirm the video and music files to use, and verify that visual footage analysis is possible. Do not analyze or edit media in this step.

## Actions
1. Check that `Clips/` and `Sounds/` exist. List the available media files in each. If a directory is missing or empty, tell the user what is missing; do not invent or substitute files.
2. Determine which clips and sounds the user has selected. If their selection is already explicit, reuse it. Otherwise, show the available filenames and ask them to choose. **Never choose footage or music on their behalf.**
3. Verify that every selected file exists and is accessible. If a selection is invalid, ask for a replacement.
4. Verify that the current model supports vision (image understanding). If vision is unavailable or cannot be confirmed, stop and report the blocker.
5. Record only the confirmed clip and sound paths in the workflow's existing `workdir/progress.md`

## Output
- Confirmed paths for `clips` and `sounds`, saved in the existing workflow state.
- Preflight marked complete only when the selections are valid and vision is available.

## Boundaries
- Do **not** inspect content, extract frames, transcribe, or analyze shots or music.
- Do **not** collect duration, FPS, resolution, or other metadata; later steps obtain what they need.
- Do **not** ask the user to reconfirm selections already made.
- Do **not** start footage or music analysis until Preflight is complete.
