# Research at level 5 — plan it, run it by several routes, compile it by question

Read this with `level-5.md`. Level 4 researches in aimed rounds and marks what it finds; level 5 turns research into a program: a plan, several routes to each answer, a grade on every source, inference where no source exists, and one compiled brief a reader can check. It is built against the common research failures: retrieving a summary and trusting it; searching for the case for and calling it research; piling up sources until the facts that matter are diluted; trying one route and reading an empty result as "no data"; and leaving facts already in hand unconnected. Level 4's aimed rounds may borrow the routes in section 2 when a round comes back empty.

## 1. The research plan

Before any lookup, write the plan as a file. It lists research questions, not sources: each load-bearing claim and critical uncertainty from the level 4 ledger becomes a question phrased so that an answer could be wrong. For each: the **value of information** — the swing in the call, a threshold or the fallback if the answer moves across its plausible range, set against the cost of delay; the **flip threshold**, written before the search, at which the call changes; the **routes** to try (section 2), at least two for every question that could flip the call and at least one of them not the direct route; and a lookup budget. Rank by value of information and spend in that order. A question whose answer could change nothing is closed with a line saying so, not researched — the stopping rule applied in advance. Six to twelve questions is typical; past that the decision has not been framed. The owner's intake answers close some questions before a lookup is spent; say which. The plan ends with a Dispatch line per question (section 7).

## 2. Routes

A route is a kind of place an answer lives. The direct route is tried first; when it is thin, the others are not a fallback but the method, because most questions worth a level 5 have no document that answers them outright.

- **Direct.** The system of record, the primary document, the original study, the vendor's own terms at this volume. Read it; do not read about it.
- **Named cases.** Instances where this strategy was tried, with outcomes: post-mortems, case studies, "lessons learned", conference talks, regulatory and court filings, trade-press archives, "why we moved away from X". Six or more make a reference class. Record the outcome on the objective that matters, not the fact that the case exists.
- **Analogue.** The same mechanism in a different industry, size or era; the same setting under a different mechanism; the sibling decision one step over. Structural likeness, not surface likeness: a pricing precedent in another subscription business predicts better than a different kind of decision at a similar company.
- **Proxy signals.** Data produced for another purpose that bounds the answer: job postings (what a vendor is investing in), pricing pages and their archived versions (where prices are going), issue trackers and support forums (reliability), earnings calls and filings (viability), procurement notices (who else bought it), review sites, search-interest trends. Each proxy carries the chain from proxy to the quantity wanted, marked inferred.
- **Adversarial.** Search for the opposite claim on purpose: "<X> failed", "<X> problems", the strongest published critic, the stakeholder who lost when this was done before, the conditions under which the reference class did worst. Route each lookup to the kind of source most likely to hold a counter-case. This is the disconfirmation round, judged against the flip thresholds written in the plan.
- **Practitioner language.** Search for the words the people who do this use, not the words in the question, and find where they talk. The thread by someone who ran the migration outranks the vendor's white paper on it.
- **Temporal.** How did this question look five years ago, what was predicted, and what happened? The track record of forecasts in this class is itself a base rate.
- **Internal.** The user's own files, history and earlier decisions of this kind; the owner's intake answers. An in-house outcome beats a public average when the setting matches.
- **Human.** The person who would know — the counterparty, the expert, the dissenter — with the question and its threshold written for them (level 5's elicitation).
- **Bounding.** When no route yields a number, derive an upper and a lower bound from quantities that are known and check the call at both. A question whose answer leaves the call unchanged at both bounds is closed.

Search hygiene: vary the phrasing three ways before concluding a route is empty; add the year and the setting; search the primary term and the practitioner's term; read the strongest critic before a second supporter; check dates and whether a page has changed; and record every empty route with where it looked, because an empty search of the right places is evidence and an empty search of the wrong places is not.

## 3. Grading and reconciling

Every source that carries a load-bearing claim gets three grades beside its mark: **replication** — a single observation, repeated, a replicated study, a meta-analysis, or contested; **sample match** — whether what was measured matches this case in scale, setting and time, with the mismatch named; **independence** — how many sources it rests on once those sharing an origin count as one. A claim that reaches no primary source is `untraceable`. Secondary sources are leads to the primary, not evidence; a claim quoted twice from one origin is one source. When two sources conflict, the record-level one outranks the summary, and the conflict is written into the brief, never silently resolved. When every route is silent, write why it might be — too obvious to test, nobody with the means profits from the answer, unethical or impractical, too new — because the reason decides how much weight inference may carry.

## 4. Inference where the record is silent

Research that stops at "no data" has stopped early. The moves below produce claims, marked, each with its premise, weakest link and falsifier beside it, so they can be attacked and swept like any number. They extend `reasoning.md`; its rules on mechanism, silence and average-to-this-case still apply.

- **Structural analogy.** Find two or three neighbors that share the mechanism, not the surface. Score the similarity on the dimensions that drive the outcome — scale, incentives, reversibility, time, who bears the cost — and say where this case differs. Transfer the neighbor's outcome with an adjustment and a written reason; mark `inferred (analogy: <neighbor>)`, weakest link the dimension that differs most. Two neighbors that agree are stronger than one; two that disagree have found the fact the answer depends on, which goes back into the plan as a question.
- **Bounding.** Bracket the unknown between quantities that are known — a cost cannot exceed the budget that paid it, a churn rate cannot exceed the cohort — and test the call at both ends; mark `inferred (bound)`. Where the call holds at both, the unknown is closed; where it flips inside the bracket, the bracket is the research target.
- **Mechanism chains.** "A raises X; X drives B; so A affects B", each step marked, the weakest link named, and a falsifier — the observation that would show the chain broken. A chain with no statable falsifier is a belief, and the brief says so. Chase what else must be true if the chain holds; the decision often sits in an implication no source spelled out.
- **Backward reasoning.** From the call, list what must be true for it to be right, then check which of those the record supports. The unsupported ones are the research questions the plan was missing.
- **Consilience.** When independent routes — a named case, an analogue, a proxy, a chain — point the same way, confidence rises and the brief says by how many routes; when they split, the split is the finding and goes into the packet as the fact to settle, not averaged away.
- **Sweep.** Before closing, connect every fact already in hand: the record, the intake answers, the lookups made for other questions. For each, what else does it imply here; which two together imply something neither states.

## 5. The research brief

One compiled file, organized by question — not by source and not by phase — so a reader sees for each question what is known, how well, and what it does to the decision. Template:

```
# Research brief — <decision>, <date>

## Questions, by value of information
| # | Question | Moves what | Flip threshold (pre-registered) | Routes tried | Status: answered / bounded / inferred / open |

## Findings, by question
### Q1 — <question>
- Found: <finding> — <source, primary or secondary, date> — grade R / S / I
- Conflict: <A says / B says> — resolved by <record-level source>, or unresolved
- Inferred: <claim> — <method and premise> — weakest link — falsifier
- Implies: <what it does to the strategies, thresholds or fallback>
- Confidence: high / medium / low, because <...>
- Open: <what remains> — cheapest closer: <test, person or source>, cost, time

## Reference classes
| Strategy | Named class | Cases (n) | Base rate on the objective | This case's adjustment, with reason | Figure it replaces |

## Disconfirmation
Flip conditions as pre-registered → routes and places searched → found / not found → verdict: stands / flips / decide nothing yet, with the fact named

## Surprises
Findings nobody asked for that change the picture, and what each changes

## What changed in the model
Each number re-entered, the output that moved, and whether the call, fallback or a threshold changed

## Sources
| # | Source | Primary? | Date | R / S / I | Used for | Found by (lead, or agent and model) |
```

The brief is the deliverable: the packet quotes from it and points to it, and the ledger's marks and grades agree with it. A brief that reads as a list of sources has been written by phase; rewrite it by question.

## 6. Stopping and cost

Spend follows the plan's ranking and stops per question when a route has answered it to the flip threshold's precision, when two routes agree, or when two rounds change nothing. Typical spend: eight to sixteen lookups across the plan's routes, the disconfirmation round included; six to twelve primary-source reads; the named-case tables; and a model re-run after each number that changed. Past the point where a flip threshold is settled, more sources dilute rather than sharpen; the brief says what was skipped and why.

## 7. Dispatch — research agents on lighter models

The lead is the main context, on the model the run started with. With subagents available, it decides at the end of the plan which questions to research itself and which to hand out, and writes a **Dispatch** line for each: in-line, or agent and model, and why. Handing out runs questions in parallel, so the pass finishes sooner; reads pages on a cheaper model, so the run uses less of the plan; and keeps the lead's context for judgment.

**When to hand out.** A question needs three or more lookups of its own and does not wait on another question's answer; or one route needs a long sweep — a named-case table of six or more cases, a run of archived pricing pages, a forum search in several phrasings; or the run is on the fast form. **When to keep it in-line.** It takes one or two lookups; its search depends on what another question finds; its sources are the owner's documents already in the lead's context; or there are no subagents, in which case the Dispatch line says so once.

**Which model.** Never one stronger than the lead's.

- *Light* (Haiku in Claude Code): retrieval and extraction from a named source — read this contract, page or export and return the clause, price, date or figure with the passage it sits in; compare archived versions of a page; turn cases already found into the table. Work with a right answer on the page and little judgment.
- *Middle* (Sonnet): searches by route — direct searches that need rephrasing, named cases, analogues, proxy signals, practitioner language, the temporal route — and the disconfirmation lookups. These need judgment about what counts as a case, which a light model does less well.
- *Lead:* the plan, the final grades, reconciling conflicts, every Phase 3 inference, the disconfirmation verdict, the brief and the packet; and the replications, for the reason `level-5.md` Phase 5 gives.

Pass the model on the agent call; where the environment ignores it, the agent inherits the lead's model and the Spend line says so.

**How many.** No fixed cap: one agent per dispatched question, spawned together in one message, plus the replications. A long sweep may be split further, one agent per strategy's case table. Questions that share sources share an agent, so no two agents search the same places. Splitting wider finishes sooner without adding to the lead's grading, which grows with the questions, not the agents; but each agent has a setup cost, so when usage is tight, cluster related questions into fewer. More than about twelve usually means too many questions (section 1). If the environment runs fewer at once, the rest queue. The disconfirmation lookups always go to their own agent, never to one researching the case for.

**What each agent gets.** Only its question, phrased so an answer could be wrong; the flip threshold; the routes to try and the lookup budget; the names, dates and setting it needs; and the search hygiene from section 2. Not the provisional call, not the ledger, not the other questions: an agent that knows which answer the lead is hoping for tends to find it. The disconfirmation agent gets the leading strategy and its mechanism, and the instruction to find where it failed or would fail.

**What each returns,** in a fixed form so the lead can grade without redoing the work: for each finding, the claim; the source with its link or path, its date, and whether it is primary; the exact passage the claim rests on; a proposed grade (R / S / I) with its reason; then every route tried, the empty ones included, with where it looked; and anything surprising. No conclusions, status lines, implications or "what this means": the lead writes those after grading. Agents retrieve; analysis runs on the lead, Opus at minimum (owner rule, 5 Oct 2026).

**What the lead checks.** Agents propose grades; the lead assigns them. Every finding that crosses a flip threshold, changes a number in the model or feeds a base rate is checked against its quoted passage, and its primary source is re-read by the lead when the passage does not settle it — a lighter model misreads a table's units or a study's scope more often, and the error would land where it matters most. A finding with no reachable source is `untraceable`, whoever found it. The brief's sources table names the agent and model behind each finding.
