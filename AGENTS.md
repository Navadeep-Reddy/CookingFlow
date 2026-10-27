# AGENTS.md

Private setup kit so OpenCode can edit Instagram Reels (cooking content) in a specific style. No application code: configuration, step files, and an ffmpeg skill.

## Repo map

- `workflow/` - the editing procedure, one file per step. Start at `workflow/00-index.md`.
- `workdir/` - generated state between steps (JSON, WAV, renders). Gitignored. Never commit.
- `.claude/skills/ffmpeg-skill/` - media execution toolkit. Read its `SKILL.md` before any video task; keep the installed skill unchanged.
- `.opencode/agent/` - subagent definitions. `.opencode/commands/ffmpeg-skill.md` forwards `$ARGUMENTS` to the skill.
- `Clips/` and `Sounds/` - user media. Untracked. Never delete, never commit. Anything new in them is source material, not repo content.

Only commit config, skill files, step files, and text assets. Default branch is `master`; remote is private repo `Navadeep-Reddy/Instagram-Video-Editor`. There is no application lint, typecheck, or test command; video jobs require the skill's output inspection and Instagram Reels compliance checks plus the editorial checks in step 7.

## How to run any video edit

1. Read `workflow/00-index.md`. It lists the steps, their order, and which can run in parallel.
2. Read `workdir/progress.md` and saved outputs (create the checklist from the index if missing). Resume according to the index; do not restart completed work to recover context.
3. Before starting a step, read that step's file in full. Never start a step from memory.
4. A step is finished only when every line of its "Done when" holds. Then tick it in `progress.md`.
5. Steps pass data through files in `workdir/`, not through conversation memory. Use each step's declared inputs, including source media and assets those inputs reference.
6. When delegating to a subagent, pass file paths, not summaries: the step file to read, the input files, the output file to write. The subagent writes its full result to disk and replies with 10 lines or fewer.
7. Never redo delegated analysis to regain confidence. Read its saved result and return only missing or defective items to its owner. Later steps inspect media for their own framing, grade, and final-verification duties, not to repeat the analysis.

## Global rules (apply to every step, every time)

- **Format:** every deliverable is an Instagram Reel, 9:16 vertical, final video under 30 seconds.
- **Vision:** confirm the model can view images before any edit. If not, tell the user you can't visually inspect output and switch to a vision-capable model before starting. Subagents that look at frames must be vision-capable too.
- **Verify, don't assume:** never treat memory or knowledge cutoff as fact. Web search anything uncertain (for example what a Kodak 2383 grade should look like), then verify locally with the skill.
- **Media selection:** use the user's named files or their saved selection for this edit. Ask only for unresolved choices; if media is missing, ask the user to place it in `Clips/` or `Sounds/`.
- **Execution:** use only the skill's scripts for media probing, decoding, extraction, and transformation. Read the relevant script's current `--help` and check input compatibility; never guess flags or invoke raw `ffmpeg` or `ffprobe`. Dry-run writing operations before execution, following the skill's measurement exceptions. Keep discovered commands and run evidence in `workdir/`, not in step instructions.
- **Analysis code:** temporary code in `workdir/` may analyze decoded samples and metadata. It must not bypass the skill for media processing. Check dependencies before relying on them; no particular helper is mandatory.
- **Source safety:** never overwrite source files. Put generated files and scratch work in `workdir/`, not beside source media.
- **Limitations:** distinguish measured, inferred, and unknown results. Lack of listening is not lack of numerical audio analysis. Save usable findings and explain gaps. Try supported alternatives; omit an optional enhancement with disclosure, but ask the user about an unmet requirement before treating the edit as complete. Never fabricate verification.
- **Style is fixed:** the channel's style rules live in the step files. The user should never have to repeat them in a prompt. If a step file and a user prompt conflict, the user's prompt for this specific edit wins; say so.
