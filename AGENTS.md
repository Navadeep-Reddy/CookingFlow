# AGENTS.md

Purpose of this repo: a private setup kit so OpenCode can edit Instagram videos (Reels) in a specific style. There is no application code — the repo is configuration plus an ffmpeg skill.

- **Video editing lives in the ffmpeg skill** at `.claude/skills/ffmpeg-skill/`. Read its `SKILL.md` before any video task; it defines a strict workflow (probe → dry-run → execute → check → verify), script routing, and hard rules (never overwrite the source, never invoke raw `ffmpeg`/`ffprobe` outside `scripts/*.py`). Do not duplicate its rules here.
- Videos edited with the skill run via `python3 <skill-dir>/scripts/<name>.py` (Python 3.10+, stdlib only). Every script has `--help` and `--dry-run --json`.
- `.opencode/commands/ffmpeg-skill.md` is the user-facing `/ffmpeg-skill` command; it just forwards `$ARGUMENTS` to the skill. `.opencode/` has its own `package.json` (`@opencode-ai/plugin`) but no build/test scripts.
- `Clips/` and `Sounds/` are working directories for user media. They are empty and untracked — don't delete them, and don't commit user media: new binaries there are assumed to be source/working files, not repo content. Only commit config, skill files, and text assets.
- No lint, typecheck, or test command exists. Verification for video jobs is running the skill's `check.py --platform X` and `probe.py` on the output, per `SKILL.md`.
- Default branch is `master`; remote is private repo `Navadeep-Reddy/Instagram-Video-Editor`.

Every video edit for this channel (cooking content, Instagram Reels) must follow the style rules below, every time — the user should not have to repeat them in a prompt.

## Before any edit

- Confirm you can view images (vision-capable model). If not, inform the user you can't visually inspect output and switch to a vision-capable model before starting.
- Never trust memory/knowledge cutoff as fact — web search to verify anything uncertain (e.g. what a Kodak 2383 grade should look like), then verify locally with the skill.
- Check inputs in the repo first: if `Sounds/` is empty, tell the user to download and place their chosen song there; if not, ask which one to use. Same for footage: if `Clips/` is empty, tell the user to place the clips they want edited there; otherwise ask which clip(s) to edit. Never pick music or footage yourself.

## Context first

- Before any edit, build a full understanding of the video's content — visually and by analyzing its audio. Any section you cut out must be understood as a coherent whole and labeled for what it is.
- Split points must never cut a coherent action (one chop sequence, one pour) across pieces you'll stitch back together. Every selected clip is a complete, self-contained moment.

## Format

- Every deliverable is an Instagram Reel: 9:16 vertical, final video under 60 seconds.

## Beat sync

- Beats must align with the video's distinct cooking sounds — each chop, pour, or placement lands on a beat (`scenes.py --beats`, `cut.py --snap`).
- Only sync moments with a distinct short sound; don't force sync on sections that have none.

## Preserve actions (aesthetics first, time-boxed)

- Aesthetic cooking actions (a full pour, a complete chopping run) must be intact — never cut one mid-action.
- If everything can't fit in 60 s, evaluate every candidate moment and select the subset that maximizes the cooking aesthetic within the time limit — drop lower-value moments, never truncate the ones you keep.

## Audio hygiene

- Keep original audio only for distinct cooking sounds (stirring, pouring, sizzling, placing things on the pan); strip room noise and non-contributing sound.
- Balance the mix: song clearly audible and rhythmic, cooking sounds never drowned out (duck the music, loudness-check the final mix).

## Color

- Color grade to the gold standard of filmic grading — Kodak 2383 print film emulation. Research the look (web search) if unsure, apply it in the skill, and visually verify the result.
