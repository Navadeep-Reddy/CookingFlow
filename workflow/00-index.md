# Workflow Index

Turn user-selected clips and music into a 9:16 Reel.

## Steps

| Step | File | Owner | Output |
|---|---|---|---|
| 0 | 00-preflight.md | Main | progress.md |
| 1 | 01-footage-analysis.md | Footage subagent | footage.json |
| 2 | 02-music-analysis.md | Music subagent | music.json |
| 3 | 03-edit-plan.md | Main | plan.json |
| 4 | 04-framing.md | Framing subagent | framing.json |
| 5 | 05-grade-tuning.md | Grading subagent | grade.json |
| 6 | 06-render-audio-verify.md | Main | final.mp4, verification.md |

## Execution

0 → [1 || 2] → 3 → [4 || 5] → 6

- Steps 1 and 2 run as parallel subagents.
- Steps 4 and 5 run as parallel subagents.
- Read each step's MD file before executing it.
- Follow its inputs, instructions, and completion criteria.
- Mark completed steps in `workdir/progress.md`.
- Only the main agent updates progress.

## Handoffs

- Each step owns its output and validates it before completion.
- Later steps reuse saved outputs instead of repeating analysis.
- Pass file paths to subagents, not large context summaries.
- Subagents return brief summaries; detailed results stay in files.