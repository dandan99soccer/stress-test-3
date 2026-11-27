# Outcomes — a percentage on each likely outcome, at every level

Owner requirement, 27 Nov 2026: "I want all levels of stress test programmed to output a percentage of each likely outcome in the best way possible." Read this with `level-1.md` and `reasoning.md` for any pass above the stakes floor. Every level prints one fixed block, **Outcomes**, and logs it; the two early exits of Step 0 print none. `scripts/outcomes.py` builds, checks and prints the block, so its form and arithmetic are the same at every level. Where no shell exists, write the same lines by hand under section 3's rules and say the script did not run.

## 1. The block

```
**Outcomes** — if the call is followed (Pilot first), by 31 Mar 2027
- **55%** (40–70) Works: 20+ qualified leads a month
- **25%** Partly: leads up, under 20
- **15%** Fails: no lift, kill line hit
- **5%** Not listed: overtaken, dropped, unreadable, or something nobody named

Same test, other options: Full launch now 40% · Do nothing 10%
Basis: 3 of 6 similar cases met the test (in-house launches 2024-26; 90% interval 22–78%, estimated); level 1, lead's judgment, from the base rate
Logged: 4 rows → <ledger path> (run pilot-first-2026-11-27-L1)
```

It sits directly under the call at levels 1–5 and on page one at level 6, pasted as printed and outside the level's word limit. Level 1's short form (steps 1, 2, 7 and 8) uses the one-line form, `--compact`.

## 2. The rows

The rows are built on two lines the pass already writes:

- **Works**: the success line is met by its date. This is the headline row, always first.
- **Fails**: the abandon line fires (at levels 4–6, a kill criterion). A kill that fired before the date is Fails even when the number later recovers.
- **Partly**: the plan ran and ended between the two lines.
- **Not listed**: none of the three can be said. The plan was overtaken, was not carried out as called, or its measure cannot be read; and whatever nobody named. The script adds this row with whatever is left of 100.

Rules. Write the rows before any number, and the numbers before the call is worded (at level 1, between steps 6 and 7), so the odds inform the call instead of decorating it. Each row is an observable an outsider could check on the date, and exactly one row can happen. Three named rows are the default; use up to five only when the end states differ in kind. Split the failing side as finely as the succeeding side: a row unpacked into parts draws more probability than the same row left whole. A story is a path to a row, never a row; detail makes a story feel more likely while making it less likely. The date is the success line's; where that line is a trigger, use the day the owner will look, 90 days out by default and marked assumed.

"Decide nothing yet" still gets a block (`--fact`): the rows are the answers the deciding check can come back with, each with the call it leads to. A pre-mortem's block is on the plan under test; a ranking's, on its first item.

## 3. The numbers

Work in this order. Each step answers a measured bias (section 9).

1. **The reference class first, as a count.** Name the class of similar cases and how many met a test like this one ("3 of 6"), before reasoning about this case: `--base 3/6 --base-class "<class>"`. The script prints the 90% interval and marks a count under 30 as estimated. With no class in reach, say so; the line then reads "judgment; no base rate found". Never invent a count.
2. **The failing side first.** Put numbers on Fails, Not listed and Partly before Works. Works is what is left, then checked against the base rate.
3. **The range before the point.** For the headline row write the lowest plausible number, the highest, then the best one: `--range 40-70`.
4. **Leave the base rate only with a reason.** A headline number outside the base rate's interval needs `--reason`; without one the script raises a `Check:`.
5. **One reason it may be too high, one it may be too low** (`--high`, `--low`). They are logged with the row, and a set without them is not logged.
6. **The guardrails are the ledger's** (`forecast.md` section 6): nothing under 5% or over 95% without a named class behind it; Not listed never under 5%, class or no class (level 6's cut rows excepted); the rows add to 100. Whole percentages, no decimals. A number that was computed (a count, a model run, a median of several sets) is printed as computed and never rounded to a coarser grid. Never words in place of numbers.
7. **An even split is a warning.** When the named rows sit within 10 points of each other the script asks why: either the record supports it, or the pass says the record is silent.
8. **A plan that needs every part to hold** is no more likely than its weakest part, and less likely the more independent the parts are: `--all-of 0.8,0.7,0.9` prints the product (independent parts) and the smallest (one shared cause). Place the number between the two and say which parts share a cause.
9. **Never shade a number by hand toward the middle or away from it.** The record does the correcting: once the `Record:` line shows a headline lean on 30 or more resolved sets, move the headline number against it by that amount and say so with `--reason`.

## 4. The other options

Each other surviving option gets one number: the chance that option, if chosen, meets the same success test by the same date. Do nothing is on the line whenever it is possible at all, screened out or not; its number is the chance the test is met anyway, and the gap between it and the call is what the plan adds. Make these numbers in the same step as the call's rows. An option whose odds are at least as good as the call's raises a `Check:`; the answer is what the call wins on (cost, reversibility, upside, a hard constraint), given as `--why` and printed on the line, or a changed call. An option not taken never resolves, so these numbers are kept in the headline row's notes, not as rows. If the owner takes another option, the call's rows are voided, never scored as a miss, and that option's number is logged as a new row.

## 5. How each level makes the numbers

Each level uses the independent pieces it already runs and the base rates its grounding already holds. No level starts an agent, a lookup or a round for the block.

| Level | What makes the set | The headline range |
|---|---|---|
| 1 | The lead, in section 3's order. | The lead's own lowest and highest. |
| 2 | Phase 1 writes the success and abandon lines, so every lens agent judges one test. Each lens agent returns, blind, its set for its top-ranked option and a Works number for every option. `--sets` takes the median. The adversarial pass supplies the too-high reason and may raise Not listed. | The spread across the lens agents. |
| 3 | Each component analysis returns the chance its call holds. The strategy's Works number is composed with `--all-of`, the shared causes named. The second derivation returns its own blind set, and the two are the `--sets`. | The spread between the two derivations. A sensitivity flip that changes the call is the too-high reason. |
| 4 | Each strategy's outside-view line is the prior for its Works number (`--base`). The three blind derivations each return a set (`--sets`); the Phase 3 assessments return each strategy's number for the options line. A pre-mortem cause left unanswered raises Fails or Not listed. Under a robustness table, "works in 3 of 4 futures" is a count of futures, and the Basis line says so. | The spread across the derivations. |
| 5 | The named-case table's rate is the prior (`--base k/n`). A graded finding moves it only through a likelihood ratio applied in code (`forecast.md` section 4). The replications return their own sets; they saw less, so they are printed as dispersion and the lead's set stays primary (`forecast.md` section 5). | The Wilson interval or the replications' spread, whichever is wider. |
| 6 | The rows are the pack's primary row cut at the decision's own thresholds (the kill level, the success line). Their percentages are the reference distribution's mass in each cut, from `--bins`, moved only by the forecasters' capped deltas (`level-6.md` Phase 4). `--exhaustive` drops Not listed: every value of a measured number falls in a row. | The reference against the posterior. |

Scenario points are not equal shares: at the 5th, 50th and 95th percentiles bear, base and bull stand for about 18.5%, 63% and 18.5% of the distribution; at the 10th, 50th and 90th, about 30%, 40% and 30% (Hammond and Bickel, *Decision Analysis* 10(1), 2013; secondary). `--bins` reads threshold rows off a t fit through the five quantiles, never off straight lines between them.

## 6. Logging: every pass, every level

Owner's decision, 27 Nov 2026 ("Always log"): every pass that prints the block logs its rows, unattended and scheduled runs included. The cost is the one script call that prints the block; no agent, lookup or file read is added. Levels 1–3 use `--log`. Levels 4–6 use `--rows FORECASTS.csv`, so the set travels with the run's other rows through `--check` and `--append`.

The rows go where `forecast.md` section 9 says, and the `Logged:` line reports it:

- **Laptop:** the shared folder, appended to `LEDGER.csv`.
- **Cloud session:** `ledger/runs/<run>.csv` in the working repository, one file per run so that sessions on different branches never edit the same file; committed and pushed with the session's work, under that session's git rules. Outside any repository the script writes nothing and says so.
- **Chat:** the sheet the owner profile names, through its connector (`--tsv` prints the rows). With no sheet, `--not-logged "<reason>"` in place of `--log` prints `Logged: no — <reason>`, and the block is the only record.

`Logged: no` is never dropped from the reply. Three kinds of line may follow the block and are not part of it. `Next:` is a step the pass takes (commit and push the run file; check and append `FORECASTS.csv`); a pass that cannot take it says so in place of the `Logged:` line. `Record:` (rows past their date; the measured lean once 15 sets have resolved) is relayed to the owner in one line. `Check:` is answered in the reply, or fixed and the command run again; it is never pasted.

On or after the date, the row that happened is marked 1 and the rest 0, from the row's named source and never from memory; `forecast_ledger.py --score` then scores the file. At levels 4–6 the review-date task of `forecast.md` section 13 does this. Levels 1–3 schedule nothing: the next pass's `Record:` line brings the overdue rows back. A run logged again the same day replaces its own open rows; once a row has resolved, nothing is edited.

## 7. Scoring

A set is scored whole, by the multi-category Brier score, beside what an even split over the same rows would score. Only the headline row joins the pooled yes-or-no figures of `CALIBRATION.md`, because a set's rows add to one and would pull the yes-lean to zero. `forecast_ledger.py --calibrate` prints the sets, how often Not listed happened against the share it was given, and a by-level table, which shows whether a level 4's numbers beat a level 1's. The eval set records the same per run as `p_realized` (`evals/README.md`).

## 8. Commands

`<skill dir>` is the folder holding `SKILL.md`; `python3` is `py -3` on Windows; add `-X utf8` where the console is not UTF-8. `--cutoff` is the model's training cutoff.

```
python3 <skill dir>/scripts/outcomes.py --decision <slug> --level 1 --call "<the call, in a few words>" --by <YYYY-MM-DD> \
    --outcome "Works: <success line>=55" --outcome "Partly: <between>=25" --outcome "Fails: <abandon line>=15" \
    --range 40-70 --base 3/6 --base-class "<named class>" --option "<other option>=40" --option "Do nothing=10" \
    --high "<why 55 may be too high>" --low "<why too low>" --source "<where it is read>" --cutoff <YYYY-MM> --log
  ... --sets "55,25,15,5" "45,30,20,5" "60,25,10,5"   # blind sets in place of the numbers on the rows
  ... --rows FORECASTS.csv   # levels 4-6, in place of --log
python3 <skill dir>/scripts/outcomes.py --bins --q <q05,q25,q50,q75,q95> --cuts <kill level,success line>
```

## 9. Why these rules

Every source here is **secondary**: read through search summaries on 27 Nov 2026, the primary not read. None was measured on this skill; each rule is a prior to re-test on the eval set.

- **Worth printing, worth checking.** The best language-model systems forecast a little behind the best human forecasters (ForecastBench, Oct 2025: 0.101 against the superforecasters' 0.081, difficulty-adjusted Brier; Metaculus, spring 2026: professionals ahead by a margin no longer significant). Asked cold, with no retrieval, most models scored near chance in 2024 (Halawi et al., arXiv 2402.18563), so level 1 marks its numbers as judgment.
- **Base rate first, as a count; updates in code.** Of 38 prompt variants most changed nothing, base-rate-first and frequency framing helped a little, and an explicit Bayesian-reasoning prompt hurt (Schoenegger et al., arXiv 2506.01578). An hour's training with base rates among its parts improved human Brier scores by 6 to 11% (Chang et al., *Judgment and Decision Making* 11(5), 2016).
- **Several blind sets; the failing side first.** An ensemble of twelve models was statistically level with a human crowd, while its mean forecast sat above 50% with outcomes split about evenly (Schoenegger et al., *Science Advances*, 2024, and an earlier arXiv version).
- **No shading by hand.** Models hedge toward the middle, and one system corrects for it statistically afterwards (AIA Forecaster report, arXiv 2511.07678). The correction belongs to the measured record.
- **Sums enforced by code.** Models' separate probability judgments break the rules of probability in human-like ways (Zhu and Griffiths, arXiv 2401.16646), and consistency tracks later accuracy (Paleka et al., arXiv 2412.18544).
- **The even-split warning.** Assessed probabilities drift toward equal shares over whatever rows are drawn, in decision analysts too (Fox and Clemen, *Management Science* 51(9), 2005).
- **Not listed with a floor; both sides split alike.** People do not fully move a pruned branch's probability to "all other" (Fischhoff, Slovic and Lichtenstein, 1978), and unpacking a hypothesis raises its judged probability (Tversky and Koehler, 1994).
- **Numbers, not words, not coarsened.** "Likely" was read as about 55% to 90% (Mauboussin and Mauboussin, *Harvard Business Review*, 2018); rounding forecasts into verbal-style bands cost accuracy (Friedman et al., *International Studies Quarterly* 62, 2018); a numeric range costs little trust (van der Bles et al., *PNAS* 117(14), 2020).
- **Limits before the point; too high, too low.** Asking for the limits first cut expert overconfidence (Speirs-Bridge et al., *Risk Analysis* 30(3), 2010; no gain in a 2020 study of non-experts), and listing alternatives before stating confidence improved a model's calibration (Tian et al., EMNLP 2023).
