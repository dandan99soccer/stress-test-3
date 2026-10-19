# Reasoning beyond the record

Read this, with `level-1.md`, for any pass above the stakes floor: it is the basis every level marks its claims and builds its case on. Levels 2–5 add the shared section of `level-2.md`.

Most decisions rest partly on claims nobody has measured. The record — the source, the system, the contract — states some facts; the rest of the case follows from them by logic, mechanism or analogy. That reasoning is legitimate and often where the answer lives, but only when it is visible enough to be attacked. So every load-bearing claim carries one of three marks:

- **Measured** — from data you saw.
- **Estimated** — a number from priors, with no data behind it.
- **Inferred** — follows from measured facts by a chain you can show. Write the chain: "A raises X (measured); X drives B (measured); so A likely affects B (inferred — weakest link: whether X→B holds at this scale, in this case)." Name the weakest link every time; it is what the adversarial check attacks first and what a sensitivity flip tests.

Marks are inline tags, not paragraphs. At level 1, write out only the one or two chains the call leans on hardest and tag the rest; levels 2–5 write out every chain in the facts file.

**Build the case by inference; do not only audit it.** Marking is the control, not the method. Level 1 does less than levels 2–5: when the record is silent it still builds the one chain the call leans on instead of reporting no data, and a case that turns out to rest entirely on inference is a stated reason to offer level 2. How levels 2–5 build every chain is in the shared section of `level-2.md`.

**Read the silence before counting it as a no.** When nothing published or recorded addresses the question, say why that might be, because the reason sets how much weight inference deserves: too obvious for anyone to test; nobody with the means to test it profits from the answer; unethical or impractical to test; too new. Absence of evidence is evidence of absence only when someone with the means and the motive to look has looked.

**Treat mechanism as a hypothesis, not a finding.** "It should work because of M" has a poor record wherever it has been checked against outcomes: improving the proxy that M predicts has repeatedly worsened the outcome the proxy stood for. Every mechanistic link therefore gets a falsifier — the observation that would show the chain is broken — and the outcome that matters is named separately from the proxy. If no falsifier can be stated, the link is a belief, and the output says so.

**Let reversibility decide whether inference is enough.** Acting on inference alone is fine when the downside is small and undoable — then the cheap move is to act and watch. When the downside is serious or permanent, the inference becomes the thing to test, not the thing to act on: a pilot, a trial period, a small test with the measure and the stopping date named up front. Put that test on the table in step 2; it often dominates both "trust the source" and "trust the logic." Where a licensed professional or a named decision owner would normally make the call, the output is the question to bring them — chain and weakest link written out — not an action.

**Average-to-this-case is an inference.** A study, a benchmark or a track record reports an average over its sample. Applying it to the case in front of you is a step the record does not make for you: say what was in the sample, what was excluded, and why this case matches or does not. Where it does not match, the small test above is the default option.

**Chase the second-order implications.** If the record shows X works by M, ask what else must then be true — interactions, knock-on effects, the cases it cannot cover, what it implies about the measurement itself. The decision often sits in an implication the source never spelled out.

**Reason across neighbors.** When the record is silent on the exact case, do not stop at "no data" — look for neighbors that share its structure: the same mechanism in a different setting, the same setting under a different mechanism, an earlier instance of this kind of decision, a sibling component of this decision, a case that went the opposite way. Transfer what holds, with a similarity check: what must be true for the neighbor to predict this case, and where it differs. Mark the result inferred, name the neighbor as the premise and the difference as the weakest link. Two neighbors that agree are stronger than one; two that disagree show the fact the answer depends on, which is then the thing to go find.

**Sweep what is already on the table.** Before concluding, connect the facts already in the conversation, the files and the lookups gathered for other purposes. For each stated fact ask what else it implies for this question, and which two facts together imply something neither states. Say the implication unprompted; a conclusion that only uses the facts the person labeled as relevant has left most of the evidence unused. At level 1, surface the one or two implications the call leans on.

**Model what the numbers allow.** When the record holds the numbers the call turns on, compute rather than eyeball. Level 1 states the break-even — the value of the dominant uncertainty at which the call flips — when it can be had in one line, and otherwise names it as the thing to compute; levels 2–5 compute it in code, as the shared section of `level-2.md` describes.

## Failures in the reasoning

**Inference dressed as evidence.** A chain of plausible steps read back as a measured fact. If the case for an option rests on an unmarked inference, mark it, name the weakest link, and ask whether a small test beats the commitment.

**Stopping at the literal question.** Answering only from the facts labeled as relevant, when neighboring cases or other stated facts imply more. Run the neighbor and sweep moves above before calling the record silent.

**Silence read as a verdict.** "There is no evidence for it" treated as "it does not work." Say why the record is silent before deciding what the silence means; the opposite failure — treating silence as permission — gets the same check.

**Eyeballed break-evens.** A threshold stated from intuition ("that is about break-even") when the record held the numbers to compute it. The structure a hand estimate drops — the share affected, the base rate, the interaction with a second quantity — is usually where the error sits.
