# Eval set — past decisions with known outcomes

The scripts have smoke tests, but until now nothing checked that a level 2 pass beats level 1 on decisions whose outcome is known, and the cost table rested on two or three measured runs. This folder is the harness: decisions that were actually made, the record as it stood when they were made, what happened, and a tally script that compares levels on them. It is empty of decisions until the owner adds them; the laptop's answer keys (`references/owner-profile.md`, "Where things live") are the first candidates, and eight to ten decisions is the target for a first tally, twenty eventually.

## What goes in

Each decision is a folder `evals/decisions/<slug>/` with two files from `TEMPLATE.md`:

- `BRIEF.md` — what was known **as of the decision date**: the decision as stated, the owner, the deadline, the record as it stood, the rules in force then. Nothing dated after that day. This is all the pass under test ever sees.
- `KEY.md` — sealed: what was chosen, what happened, by what date, the observable that settled it, which kill criterion or tripwire fired if any, and what the owner would do again or differently. The pass under test never sees it.

A decision qualifies when its outcome is observable (a number, a date, a yes or no an outsider could check), when the record as of the decision date can be written without the outcome leaking into it, and when it cleared the stakes floor of Step 0. Resolved decisions whose outcome is still ambiguous do not qualify; neither do ones whose brief cannot be separated from hindsight.

## How a run works

1. A fresh context — a subagent, or a new session — receives `BRIEF.md` only, the trigger phrase for the level under test ("level 1", "level 2", …), the as-of date, and the instruction that any lookup is cut at that date (web search off, or results dated after it discarded). It never receives `KEY.md`, this README, or any earlier run.
2. The pass's full output is saved as `evals/runs/<slug>/level-<N>-<YYYY-MM-DD>.md`, with the git commit of the skill that ran on its first line.
3. A scorer — a different context, or the owner — reads the output against `KEY.md` and writes one row to `results.csv`. Columns: `slug, level, run_date, model, effort, skill_commit, call_matched, kill_criterion_right, weakest_link_named, first_step_right, points, words, notes`. `model` and `effort` are the lead's, as the Spend line names them (`opus`, `high`); a row from before 4 Nov 2026 leaves `effort` empty. `call_matched` is 1 when the call matches what turned out right, 0.5 when the pass said "decide nothing yet" and named the fact that would have decided it, 0 otherwise. `kill_criterion_right` is 1 when a kill criterion or tripwire named the thing that actually happened, 0 when none did, `na` when nothing went wrong. `weakest_link_named` is 1 when the link the pass marked weakest is the one that broke (or none broke and none was wrong). `first_step_right` is 1 when the first step would have been the right first move. `points` is the usage the run cost, in 5-hour-window points where readable, else the token count.
4. `python3 scripts/eval_tally.py evals/results.csv` prints, per level, the hit rate on each measure with a Wilson 90% interval, and for every pair of adjacent levels the paired comparison on the decisions run at both: wins, losses, ties, and the mean points per decision — the number that says whether the higher level earned its cost.

## What counts

- The primary measure is the call. A level earns its cost when it beats the level below on `call_matched` on the paired set, not on one decision and not on word count.
- Secondary measures say where the extra spend went: a better kill criterion, the right weakest link, a usable first step.
- The tally reports intervals, not just rates. On eight decisions a difference of one call is inside the interval; say so rather than reading a trend into it.

## Rules

- `KEY.md` is never in the context that runs a pass. A leak voids the row; write `void` in `notes` and run it again in a fresh context.
- Rows are never edited after the fact; a correction is a new row that names the old one in `notes`.
- Re-run the set when a rule in SKILL.md or a reference file changes (`research-6b.md` section 4), and record the commit that ran, so a rule's effect is measured on this skill rather than borrowed.
- Eval runs spend usage like any pass. Level 1 and 2 across the whole set are cheap; levels 4 and up on the set run a few at a time under the budget mode (`references/budget.md`), and never in a window where a real decision is waiting.
