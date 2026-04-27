# PawPal+ Loom Walkthrough

**Target:** ~5 minutes
**Setup before recording:** app running at `streamlit run app.py`, terminal open with `tail -f logs/pawpal.log` ready, knowledge dir visible somewhere.

---

## 0. Intro (~20 sec)

*[App on screen, home view]*

> "Hi, I'm Linnea. This is PawPal+ — a Streamlit pet-care scheduler I built in Module 2 and extended in Week 9 with a RAG layer. The scheduler builds the daily plan deterministically. Claude Haiku 4.5 explains the plan using five vetted reference docs — and only those docs."

---

## 1. End-to-end system run (~1.5 min)

*[Owner form]*

> "Step one — owner. I'll add myself: Linnea, 60 minutes available, preference for grooming."

*[Pet form]*

> "Step two — pet. Lulu, dog, 4 years old."

*[Task list — add three tasks]*

> "Step three — three tasks: a 30-minute walk, high priority. A 10-minute feeding, high priority. And a 25-minute grooming session, medium priority."

*[Click Generate Schedule]*

> "The scheduler is greedy and time-budgeted. High-priority tasks go in first, it respects the 60-minute cap, and grooming wins the tiebreaker because it's my preference. Here's the plan."

*[Walk the schedule output line by line — point to start times, durations, what got deferred if anything]*

---

## 2. AI feature behavior — RAG (~1 min)

*[Scroll to the explanation panel]*

> "This is the RAG layer. I ask a pet-care question, the app embeds it, retrieves the top-3 chunks from the knowledge base by cosine similarity, and asks Claude Haiku 4.5 to answer using only that context."

*[Type: `how often should I feed a young dog`]*

> "Direct match first — top cosine around 0.66."

*[Show answer]*

> "Structured answer with feeding schedules by puppy age. And the cited source — `feeding_by_life_stage.md`. I can open that file and verify the claim in seconds. That's the human-in-the-loop check."

---

## 3. Reliability and guardrail behavior (~1.5 min)

*[Type: `my senior cat seems tired`]*

> "Now a tangential query. Top cosine drops to about 0.48. The knowledge base doesn't cover symptom diagnosis — watch what happens."

*[Show answer]*

> "The model names the gap out loud, pivots to the closest relevant chunk, and recommends a vet visit. It refuses to improvise. That behavior comes from three rules in the system prompt: use only the context, say 'I don't know' if that's not enough, cite the source."

*[Type: `what kind of pizza should I order`]*

> "And off-topic. Top cosine 0.03."

*[Show answer]*

> "Clean refusal, redirects back to pet-care topics. No improvisation."

*[Switch to terminal showing `logs/pawpal.log`]*

> "Every retrieval and every LLM call is logged here. Chunk sources, cosine scores, token usage, full tracebacks on errors. That's the audit trail — if the system starts drifting, I have the receipts to find it."

---

## 4. Closing (~30 sec)

*[Back to app or camera]*

> "Two things to call out. First — authority separation. The scheduler is deterministic Python. The AI only explains, it can't edit the plan. Worst-case failure is a wrong explanation, never a wrong schedule. Second — 37 of 37 scheduler unit tests pass, and the RAG layer was validated against three test queries spanning direct, tangential, and off-topic before I wired it into the UI."

> "That's PawPal+. Thanks for watching."

---

## Pre-record checklist

- [ ] `.env` has `ANTHROPIC_API_KEY` set
- [ ] `streamlit run app.py` is up and clean
- [ ] Terminal with `tail -f logs/pawpal.log` visible in a second window
- [ ] Browser zoom set so text is readable
- [ ] Mic input checked
- [ ] Close Slack, email, anything that pings
