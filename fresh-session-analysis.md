# Fresh-session test: system-level analysis

## Verdict and evidence

The test failed editorially while exercising much of the reusable infrastructure successfully. The central failure was an incomplete, inaccurate action inventory being accepted as a complete story. Caching and platform checks cannot compensate for that. This is a workflow/test-design failure to address, not evidence that choosing a cheaper model alone caused it.

Reviewed `workdir/edit-retrospective.md`, `footage.json`, `plan.json`, `grade.json`, `progress.md`, `verification.md`, the evidence manifests and saved PNGs. Reran the inspected `workdir/audit_metrics.py` to reproduce the recorded timing totals. No source media or rejected edit was changed.

## How the failure propagated

| Boundary | Evidence | What the system accepted incorrectly |
|---|---|---|
| Source survey → footage handoff | One 6×4 survey at 540 pixels total width: approximately 90 pixels per tile, with samples about 19.6 seconds apart. | Orientation-level evidence was treated as sufficient action identification. Brief additions can fall between samples; individual ingredients/utensils are hard to identify at that scale. |
| Footage handoff → plan | Only five moments. `m04` spans 215–323 s and combines butter, garlic, onion and tomatoes. `m05` spans 323–471.4 s and claims egg cracking/cooking/finishing. | Several independent events were collapsed into broad labels. Actual egg entry was not established by the cited finishing pictures. Cream had no separate entry or selection obligation. |
| Plan → story approval | `s07` uses 326–328.933 s, described as eggs going in, then `s08` resumes at 353 s. | A cooked-state shot was accepted as an ingredient-entry action; the cream addition was not given a readable story beat. |
| Story approval → grading/rendering | Grade trials proceeded while selected actions still required correction. | Appearance was polished before the semantic errors were resolved; later source changes invalidated whole-picture processing. |
| Final evidence → delivery approval | Technical checks passed; the review enumerated selected shots as the complete process. | Evidence that selected frames look acceptable was mistaken for evidence that essential events had been selected. |

### Cream evidence

I viewed the cached frames at 328, 329 and 330 s. They show already-cooked eggs and a separate white ingredient being deposited with utensils; the user identifies this as cream. The second addition is clearly visible at 329–330 s, outside the selected range. An early dollop may be glimpsed before the cut; this does not make the addition a clear, complete story beat. These samples do not establish the exact start/end of every addition, so a corrected source window still needs inspection.

### Repetition and omitted information

The plan allocates 2.8 s to the opening hero, 3.7 s to serving and 2.1 s to the closing hero: 9.3/24 s, or 38.75%, of explicitly finished-food coverage. The last two shots occupy 6.5 s. The prescribed opening/closing bookend does not require another redundant payoff between them. Each intermediate finishing shot should introduce an event, transformation or genuinely new information.

The Reel is 24 s; duration was not the constraint that forced the omission. Extending it is not automatically the right repair either: the first question is which selected seconds advance the causal story.

### Blind spot in our earlier baseline

The earlier 18-shot reference plan in this conversation also skipped the cream range: its lid-reveal selection ended around 326 s and its finishing selection resumed around 338 s. Our original smoke tests established faithful execution of saved decisions and technical correctness, not independent recipe completeness. The new test exposed a blind spot that already existed in that reference, as well as the cheaper model's coarser action grouping and more repetitive ending.

## Where time went: defensible measurements

| Measurement | Reproduced value | Interpretation |
|---|---:|---|
| Initial source survey | 108.385 s | The skill's sheet-extraction call accounts for 107.966 s. A costly pass produced a temporally sparse, low-resolution overview. |
| Additional source frames | 33.113 s across 5 requests | 72 misses, 6 hits; useful extraction, followed by interpretation and repairs that are not separately timed. |
| Shot evidence | 21.810 s across 9 requests | 177 hits, 49 misses: cache reuse worked despite repeated selection revisions. |
| Output-transition evidence | 20.391 s across 2 requests | Checks the chosen cuts; cannot discover a never-selected ingredient addition. |
| Music helper | 2.104 s cold, 0.058 s cached | Not a significant measured bottleneck. |
| Latest assembly + grade + export | 93.131 s | 35.508 + 27.360 + 30.263 s; about 86% of the latest recorded render subset, not of the session. |
| Latest recorded render subset, including preparation/mix/cache checks | About 108.4 s | Excludes other passes, some direct commands, retries and editorial work. |
| Largest gap between evidence events | 623.352 s | 10 min 23 s spanning grade work and subsequent decision repairs; not an isolated grading timer. |
| First-to-last evidence completion window | 1,910.003 s | 31 min 50 s; not exact session duration or a complete partition of work. |

There are four source grade samples, 13 graded sample videos and 17 comparison PNGs. That supports substantial grading activity, but neither asset counts nor the largest gap establish its exact duration. Reasoning, image review, orchestration waits and some direct commands lack complete timing coverage. Failed render histories are not fully appended. Do not subtract the measured tool totals from the observed window and label the remainder “model reasoning” or “grading.”

The most consequential waste is avoidable rework: a shaky inventory led to mislabeled selections, late replacements, repeated assembly/grade/export and an audio detour. It is reasonable to prioritize decision quality and bounded grade iteration over further small render-pass savings; the logs do not establish an exact ranking of every elapsed activity.

## Concrete engineering issues revealed

1. **Survey defaults and readability.** The evidence CLI uses one width parameter for individual frames and total survey width. Passing 540 to a six-column sheet produces tiny tiles. The guidance/tool should make per-tile readability explicit, and long-source overview strategy should be chosen with measured decode costs in mind.
2. **Semantic coverage is too weak.** The runner checks source containment and stage-name coverage. Any finishing shot inside `m05` satisfies the broad stage even when a meaningful addition is missing. An action-level plan check helps only after a visually verified inventory exists; it cannot find an event omitted from that inventory.
3. **LUT trial/final provenance is inconsistent.** `grade.json` records a trial flag of 0.05; the runner maps intended contribution 0.05 to flag 0.95 for this installed script's blend order. The handoff does not establish that previews and final used the same actual contribution. This must be resolved before trials, rather than interpreted as a new aesthetic problem on each iteration. It is not proof that every preview was executed incorrectly.
4. **Grade handoff typing is underspecified.** A string meaning “no operations” is truthy and was rejected as pending preparation. The agreed no-operation representation should be an empty list, validated before rendering.
5. **Audio recovery repeated picture work.** An export with −0.98 dBTP was refused by the runner, while the display-rounded general check showed −1.0. The strict refusal was appropriate. The proven audio-only recovery with additional peak headroom should have been reused instead of repeating diagnostic picture export.
6. **Failure history is incomplete.** The current failure manifest is useful, but successful-run ledgers omit failed attempts. Complete failure/timing records are needed before claiming precise session bottlenecks.

## Targeted next corrections

| Area | Correction | Acceptance evidence |
|---|---|---|
| Step 1 | Treat the overview as orientation. Split compound windows into distinct observed actions; inspect readable before/during/after evidence for additions and investigate unexplained state changes. Leave unsupported action identities unresolved. | Footage descriptions agree with source pixels; additions are not hidden inside a broad finishing label. |
| Step 3 | Map essential actions to selected shots or documented omission reasons before downstream polishing. Review what each late shot adds and preserve readable entry/change/result before fitting cuts to music. | Action-to-shot coverage and a causal sequence, including meaningful finishing additions; bookends do not license redundant intermediate payoffs. |
| Steps 4/5 | Keep framing/grading parallel after the story is validated. Reopen affected decisions when selected ranges change; bind evidence to the actual ranges, parameters and immutable artifacts. | No stale shot references; grade comparisons use the final intended contribution and actual version-correct arguments. |
| Step 5/tooling | Resolve strength mapping and schema before preview trials; compare representative samples and stop refining once the stated visual criteria are met. | A reproducible chosen look instead of unexplained strength chasing. No arbitrary fixed strength or mandatory trial count. |
| Step 6 | Review the selected actions against the source inventory, explicitly checking missing additions and redundant payoffs, independently of technical compliance. New evidence of an omission reopens approval. | Editorial acceptance is supported separately from codec, frame-count, loudness and cut-frame checks. |
| Execution/logging | Reuse verified audio-only recovery; append failed runs and stage timing/provenance. | Retries are targeted, and the next retrospective can distinguish measured processing from elapsed gaps. |

These are recommendations, not changes already made to the editing workflow or tools. The next priority is action-inventory/story-review reliability and grade-preview reproducibility. Source-cut detection remains useful as a separate task, but it would not by itself identify a cream addition inside a continuous shot.

## Files and review limits

The detailed model-produced audit remains at `workdir/edit-retrospective.md`; repeatable metric aggregation is `workdir/audit_metrics.py`. Those generated files and source PNGs will be removed by reset. This root report preserves the critical findings and measured totals. No fresh full-motion audition, new edit, or perceptual audio review was performed for this system audit.
