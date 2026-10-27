# Workflow index

Procedure for turning user-selected clips plus one song into a 9:16 Reel. Defaults are in `AGENTS.md`; step 0 records the effective requirements and user overrides for this edit.

## Steps

| # | File | Runs as | Reads | Writes |
|---|------|---------|-------|--------|
| 0 | `00-preflight.md` | main agent | user prompt, `Clips/`, `Sounds/` | `inputs.json` |
| 1 | `01-footage-analysis.md` | subagent `footage-analyst` | `inputs.json` | `footage.json` |
| 2 | `02-music-analysis.md` | subagent `music-analyst` | `inputs.json` | `music.json` |
| 3 | `03-edit-plan.md` | main agent | `inputs.json`, `footage.json`, `music.json` | `plan.json` |
| 4 | `04-framing.md` | main agent (optional delegation) | `inputs.json`, `plan.json`, `footage.json` | `framing.json` |
| 5 | `05-grade-tuning.md` | main agent | `plan.json`, `inputs.json` | `grade.json` |
| 6 | `06-audio-prep.md` | main agent | `inputs.json`, `plan.json`, `music.json`, `footage.json` | `audio.wav`, `audio.json` |
| 7 | `07-render-verify.md` | main agent | all handoffs above and their evidence | `final.mp4`, `verification.md` |

Handoffs and generated evidence live in `workdir/`. Each step may read the media and assets referenced by its inputs, plus the skill instructions and current tool help. Step files define outcomes, not fixed commands or render chains.

## Order and parallelism

```
0  ->  [ 1 || 2 ]  ->  3  ->  [ 4 || 5 || 6 ]  ->  7
```

- Steps 1 and 2 are independent. Launch both subagents in the same message, wait for both, then continue.
- Step 3 joins the analyses and owns shot selection, timeline, speed, sync, and the music window. Do it yourself; never delegate it.
- Steps 4, 5 and 6 can run independently once the plan is settled, using the inputs in the table. Do them inline first; delegate when useful. They must return proposed timeline changes to step 3 rather than edit the plan themselves.
- If subagents are unavailable, run the same steps inline in order. The files and checks do not change.

## Rules for every step

1. Read the step file in full before starting it. Never work from memory of it.
2. A step is done only when every line of its "Done when" holds. Then tick it in `workdir/progress.md`.
3. Use declared inputs and referenced media/assets. Never reconstruct earlier results from conversation memory.
4. One owner per output. Only the main agent updates `progress.md`. Per-shot workers write separate results for the owner to merge; they never overwrite the shared handoff.
5. Follow the execution and limitation rules in `AGENTS.md`. Discover supported tools at runtime instead of copying commands into these files.
6. Validate JSON syntax and its contract: referenced IDs and paths exist, ranges are valid, and dependent timings agree. A parse alone is not validation.

## Resume without repeating work

On resume, read progress and saved outputs before doing any work. Reuse completed results unless their inputs changed or a specific defect was found. During long analyses, save findings as you go and note where to continue in the same handoff. Rework only the affected portion; never restart an analysis just to recover context. If an output is missing or incomplete, recover its saved measurements and findings before running anything again.

## Data conventions

- Times are seconds. Preserve frame/sample precision during calculations; round only for display. Source ranges are start-inclusive, end-exclusive; inspect the last included frame, not the next shot's first frame. Use measured frame timestamps for variable-rate sources.
- `src_*` times refer to the source clip's timeline. `out_*` times refer to the final video's timeline.
- Music beat and onset times use the original song timeline (`song_t`); subtract the chosen music start to map them into the output. Recompute alignments whenever that start changes.
- Ids: clips `c1`, `c2`; segments `c1-seg01`; shots `s01`, `s02` in output order.
- Handoff paths are relative to the repo root. Translate them to the execution tool's path convention when building a render recipe.
- Allowed playback speeds are exactly `1.0`, `1.5` and `2.0` (see step 3).
- Each handoff has `step`, `status` (`partial`, `complete`, or `blocked`), and `limitations`. Use `null` for unknown values, not invented numbers or false negatives. Optional notes and evidence are free-form. JSON examples show field shapes, not measured results.
- A completed analysis can contain explicit unavailable findings if its Done checks permit them; step 3 decides whether those gaps affect a required result. A blocked step remains unchecked. User-approved exceptions are recorded in `inputs.json` and inherited by later steps.

## Delegation message

```
Read workflow/0N-name.md and follow it exactly.
Inputs: workdir/<input files>
Write: workdir/<output file>
Resume from saved findings if present; scope any rework to the named items.
Reply with 10 lines or fewer.
```

Pass paths, not summaries. The subagent gets its rules from the step file.

## Rework

Return a defect to its owning step with the affected shots or ranges. The main agent unticks that step and only affected dependents, recording the reason in Notes. Preserve all unaffected findings and artifacts. A grade change usually affects steps 5 and 7; a timing or music-window change belongs to step 3 and requires updated sync, audio, and any affected framing/grade selections before rendering. Reuse song measurements when moving the window; request only missing coverage from step 2.

Do not blindly retry an unsupported operation. After two unsuccessful repair cycles for the same defect, report the unresolved requirement and ask for a decision. Never mark a failed or unverified requirement passed because retries were exhausted.

## `workdir/progress.md` template

Create it at the start of step 0 if it does not exist.

```
- [ ] 0 Preflight
- [ ] 1 Footage analysis
- [ ] 2 Music analysis
- [ ] 3 Edit plan
- [ ] 4 Framing
- [ ] 5 Grade tuning
- [ ] 6 Audio prep
- [ ] 7 Render and verify

## Notes
(deviations, rework reasons, user overrides)
```
