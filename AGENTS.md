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

Read `workflow/00-index.md` and follow its workflow,step instructions, handoffs, and completion criteria.
Apply the global rules below throughout the edit.

## Global rules (apply to every step, every time)

- **Format:** every deliverable is an Instagram Reel, 9:16 vertical, final video under 30 seconds.
- **Verify, don't assume:** never treat memory or knowledge cutoff as fact. Web search anything uncertain (for example what a Kodak 2383 grade should look like), then verify locally with the skill.
- **Execution:** use only the skill's scripts for media probing, decoding, extraction, and transformation. Read the relevant script's current `--help` and check input compatibility;
- **Source safety:** never overwrite source files. Put generated files and scratch work in `workdir/`, not beside source media.
- **Style is fixed:** the channel's style rules live in the step files. The user should never have to repeat them in a prompt. If a step file and a user prompt conflict, the user's prompt for this specific edit wins; say so.
