# AGENTS.md

Purpose of this repo: a private setup kit so OpenCode can edit Instagram videos (Reels) in a specific style. There is no application code — the repo is configuration plus an ffmpeg skill.

- **Video editing lives in the ffmpeg skill** at `.claude/skills/ffmpeg-skill/`. Read its `SKILL.md` before any video task; it defines a strict workflow (probe → dry-run → execute → check → verify), script routing, and hard rules (never overwrite the source, never invoke raw `ffmpeg`/`ffprobe` outside `scripts/*.py`). Do not duplicate its rules here.
- Videos edited with the skill run via `python3 <skill-dir>/scripts/<name>.py` (Python 3.10+, stdlib only). Every script has `--help` and `--dry-run --json`.
- `.opencode/commands/ffmpeg-skill.md` is the user-facing `/ffmpeg-skill` command; it just forwards `$ARGUMENTS` to the skill. `.opencode/` has its own `package.json` (`@opencode-ai/plugin`) but no build/test scripts.
- `Clips/` and `Sounds/` are working directories for user media. They are empty and untracked — don't delete them, and don't commit user media: new binaries there are assumed to be source/working files, not repo content. Only commit config, skill files, and text assets.
- No lint, typecheck, or test command exists. Verification for video jobs is running the skill's `check.py --platform X` and `probe.py` on the output, per `SKILL.md`.
- Default branch is `master`; remote is private repo `Navadeep-Reddy/Instagram-Video-Editor`.
