# Intake — ask before spending (levels 4, 5 and 6)

Read this with the level 4 files. Levels 4 to 6 cost more than a conversation, so a question that moves the result is cheaper than any lookup — and the research on decisions finds that owners omit about half of their own objectives until prompted, and that the analyst's guess at the weights is the element most often wrong. The intake collects what only the owner has, before the spend, without ever asking whether to spend.

**When.** After Step 0 and after one read of the record and the conversation — a question asked before the record has been read is a question the record would have answered — and before any research round or subagent. On a level 5 that escalates a finished level 4, the intake asks only what level 4 left open: its frame-or-values questions and the critical uncertainties the owner may know outright. When level 5 runs its own level 4 base, the intake runs once, at the start, with the level 5 question count.

**What to ask.** Up to three questions at level 4, up to eight at levels 5 and 6, chosen because the answer would change the call, the fallback, a threshold or the ranking — not because the answer would be nice to have. Draw them from these, and skip any the record already answers:

- *The one objective to protect.* "If you could protect only one of cost, speed, reversibility, risk, people, reputation — which, and which would you give up first?" The answer sets the weights that otherwise stay the analyst's guess.
- *Constraints the record does not show.* Deadlines, budgets, approvals, promises already made, things not for trading.
- *Numbers the model turns on.* Take the top one or two critical uncertainties the owner might simply know — a real cost, a volume, a renewal date — and ask for the number, not the opinion.
- *Earlier decisions of this kind.* "Has this kind of decision been made here before, and how did it go?" An in-house base rate beats any public one.
- *People.* Who signs, who else must act, who genuinely disagrees and why. An authentic dissenter outperforms any assigned one.
- *Documents the owner can supply* that the web cannot: the contract, the export, the vendor's actual quote. At levels 5 and 6 these are not spent as questions; they go in the documents list below.
- *Risk attitude* (level 6, always asked; level 4 or 5 when the call is a size). "If this fell 40% in a month, what loss in dollars or % of NAV would you accept before the plan must have cut it; and which would you regret more, holding through a 30% drawdown or trimming before a 30% rally?" The answer is the criterion the call decides by and the tolerance the loss budget divides. **Default: drawdown-first for any book with a position above 20% of NAV**, marked `default, owner may override in one word`, with the expected-value criterion printed as a sensitivity line; below 20%, expected value subject to a drawdown floor at the stated tolerance (default 15% of NAV, `assumed (intake)`).

**The pack line (level 6).** The intake message opens with `Pack: <name> — <the decision's object>` (`equities` for a stock, an ADR, an ETF held as a position or a weight in a book; `none (routes)` otherwise), so the owner can correct the domain before the pass reads the pack's checklist, and names the two or three inputs only the owner holds for that pack (for equities: the lots file's date, the cash need, any rule version in force).

**How to ask.** One message. Each question carries one line on why it matters — which element of the decision it moves — and the default that will be assumed if it goes unanswered, so the owner can answer with a word, correct the default, or say go. Never ask "shall I run it", "are you sure" or "which level": the trigger settled that, and a pass that re-asks has turned consent into friction. If the gate failed, the warning line sits above the questions and says what the level is likely to buy here; "level 4 instead" or "stop" are answers the owner may give, not questions the pass asks.

Example, for a vendor switch at level 5:

> Before the pass, four questions whose answers change it. Answer any, or say go and I run on the defaults.
> 1. If you could protect only one of cost, speed and reversibility this year, which? — sets the weights. Default: cost, then reversibility.
> 2. The order form's 50-seat minimum: negotiable, or has the vendor already said no? — the break-even moves by about a third. Default: unknown, swept 23–50 seats.
> 3. Has a tool switch like this been done here before, and how did it go? — an in-house base rate. Default: none on record.
> 4. Who signs, and does anyone argue for staying? — commitment and the dissent pass. Default: you sign; no known dissenter.
>
> Documents that would help, if you have them: the current order form (settles the minimum and the exit terms, Q2), last year's invoice (the real per-seat cost, now estimated), and the notes from the last tool switch, if there was one (Q3).
>
> Model: Opus leads; a Fable agent adjudicates only if the runs disagree, the call changes, or it rests on an inferred link.
> Pace: I finish in this sitting and wait on no one's reply. Say "fast" for a shorter pass — the top questions only and one replication.

**Documents and data (level 5).** The level 5 intake message ends with a short list, separate from the questions, of the documents and data the owner can supply and the web cannot — three to six items — each naming the load-bearing claim it is primary for and what it settles: the signed contract rather than the summary of it, the system-of-record export rather than the dashboard, the vendor's actual quote, the last renewal's invoice, the outcome of the earlier decision of this kind. Whatever the owner supplies feeds the provenance audit in level 5's Phase 2 and is read and graded as a primary source. The list is optional for the owner and never a gate: the pass proceeds without any item, and the claim it would have settled keeps its level 4 mark with "primary unavailable" beside it and appears in the packet under **Answers that would change this**. A document already in the record is not asked for.

**Budget (budget mode, levels 4 and 5).** When the mode in `budget.md` is on, a `Budget:` line sits above the Model line: the binding window's percent used and reset time, extra usage on or off, the pass's estimated points, and whether it fits — or, when it does not, the phase after which the pass will pause and the time it resumes, with the owner's choices at that pause: wait, continue on paid usage, or a trade ("fast", "level 4 instead"). The intake itself is cheap and always runs; the pause, if any, comes after it.

**Model and pace (level 5).** Above the pace line, a `Model:` line names the lead's model and when Fable adjudicates, and — on a model below Opus or on Fable — says what that means for the run, as `level-5b.md` sets out. The message's last line, not counted as a question, says how the pass will run — in this sitting, waiting on no one's reply — and that "fast" shortens it (`level-5.md`, Pace). When the trigger already set the pace ("level 5 fast", a time limit), the line confirms it instead. On the fast form the intake asks at most three questions and lists at most three documents; when the owner has said to run without questions, it asks none and runs on the defaults.

**Then.** Answers go into the ledger marked `measured (owner)`, or `estimated (owner)` when the owner says it is a guess. Every default used is `assumed (intake)` and is treated as an estimate: it is swept in the model and named in the packet. When the owner is not there — an unattended run, a scheduled one, a subagent, a harness — do not wait: run on the defaults and list the questions in the packet under **Answers that would change this**, each with the value at which the call would change, so the owner can read the packet and answer afterwards. A pass that stops dead because nobody answered has confused a question with a gate.

**What the intake is not.** Not a questionnaire: three to eight questions, only those that move the result, and a documents list only at level 5. Not a substitute for the record: read first, ask second. Not elicitation: the people who are not the owner — the dissenter, the expert, the counterparty — are reached in level 5's elicitation phase, with thresholds written before the ask.
