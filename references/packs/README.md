# Packs — the domain layer of level 6

A level 6 stays domain-neutral in procedure and takes a **pack** for the domain: a reference file that seeds what the procedure cannot know on its own — the outcome variables and how they are scored, the evidence types with their clocks, the base-rate classes, the market and crowd benchmarks, the domain's hard rules, the linked quantities, the tools. The pack is chosen in Phase 0 from the decision's object, named on the Mode line (`Pack: equities`), and read with the level's files. `equities.md` with `equities-b.md` (built 18 Oct 2026) is the first pack. `general.md` is not yet written: a decision outside any pack runs on the eighteen routes, prints `Pack: none (routes)`, and counts its Coverage line against the routes, as `research-6.md` section 3 already says. The Ads notes in the workspace sketch a paid-search pack.

## What a pack is, and is not

A pack **seeds; it does not run**. It names the quantities the level computes and the script that computes them, the evidence the level reads and in what order, the classes a prior may start from, the reference a forecast is scored against, and the domain's own hard rules. It may add hard rules and fixed lines; it may not relax a rule in SKILL.md, `forecast.md`, `research-6b.md` or `level-6-simulation.md`, move a fixed line, or change what counts as a graded finding. Every figure in a pack carries a source, a date and a provenance state (verified passage, primary read, secondary); a figure with none is `estimated`. A pack may name an owner's project files as inputs (an account folder, a price panel, a harness), and when it does it says which of them a cloud routine, the laptop and the chat build can reach, because a watcher may never depend on a source only one of them can read.

## The template (every pack carries these sections, in this order)

1. **Name and trigger.** The decision objects that select it in Phase 0 (for equities: a listed stock, an ADR or its ordinary line, an ETF held as a position, or the weight of one of them in a book) and the Mode line text.
2. **Decision forms.** The shapes a decision in this domain takes, and the one or two quantities that decide each. "Do nothing" is always a form with full forecasts.
3. **Outcome variables and the scoring rule.** Each with its horizons, the resolution criterion an outsider could apply, the resolution source, and the **reference forecast** it is scored against (a market reference, a crowd number, a named-class base rate). The score (Brier, pinball, CRPS), skill against the reference, n counted in independent clusters, and the detectable-gap line the `Calibration:` line must carry.
4. **Constraints first.** What the pass computes and prints before any research — the constraint-only call — and the bar an edge must clear to change it.
5. **Market and crowd benchmarks.** What exists for the domain, the known bias of each (a risk-neutral density is not a forecast; a longshot price is an upper bound; a consensus walks down through the year), and the **transform** the pack applies before a benchmark becomes the reference forecaster.
6. **The prior model.** The structure every forecast is built on (for equities, the driver tree); the two numbers the call turns on, named on the Mode line; what completeness is measured against.
7. **Sizing and the objective.** The quantity the call maximizes or protects (for equities, after-tax NAV at the horizon, paired against hold) and how size is set (a loss budget; the formula; what is a sensitivity line only).
8. **The brief.** What page one holds, in how many words, before any process line; the exits.
9. **Domain hard rules.** What the pass may never do in this domain, on top of SKILL.md's rules.
10. **The reading order.** For a single object, the fixed order in which the evidence is read, each step a retrieval agent returning verbatim passages.
11. **The evidence-type checklist.** The completeness list for the evidence map: each type with its **clock** (how stale it is when read) and its **role** (trigger, explanatory, direction only, never a trigger). A type with no clock is not on the list.
12. **The base-rate class library.** Each class as the pack's unit (for equities, an effect size in volatility units), with the source, publication year and sample end, n as independent events, the decay haircut applied and whether decay was measured, and the status `measured | estimated`. The object's own record comes first where a script can compute it.
13. **Linked quantities.** How the pack states the links `level-6-simulation.md` asks for — nodes, sign, size, lag, grade, source — and which script propagates a shock through them.
14. **Situation rows.** What the four Situation tables of `level-6.md` Phase 0b hold in this domain, and when the actor map and regimes are switched on.
15. **Point-in-time and data rules.** The replay harness, what a replay may read, what is `unavailable PIT`, and the data hygiene the domain needs.
16. **Tools and routes.** Connectors (read-only), data pulls, replay harnesses, scripts with their smoke tests; what runs on the laptop, in the cloud and in chat.
17. **Open items.** What the pack's research could not find, carried as open and re-checked when the pack runs.

## Size and style

Each pack file stays under 15,000 characters (the chat build packs it) and splits into `<pack>-b.md` when it must; scripts are standard-library Python with an offline smoke test under `__main__`, run with `py -3 -X utf8`; a pack's first run on a real decision is its test, and its Built note in the outline's section 10 records what that run changed.
