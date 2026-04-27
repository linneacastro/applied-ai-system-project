# PawPal+ Model Card

This model card documents the RAG layer in PawPal+. It complements `README.md` and `reflection.md`.

---

## 1. System Overview

**What is PawPal+ trying to do?**

PawPal+ is a Streamlit pet-care scheduler. The deterministic scheduler in `pawpal_system.py` builds the daily plan; the RAG layer in `pawpal_rag_service.py` explains the plan and answers pet-care questions using five vetted reference documents. The AI explains, it never edits.

**What inputs does PawPal+ take?**

- Owner profile (name, available minutes, preferred task categories)
- Pet info (name, species, age)
- Care tasks (title, category, duration, priority)
- Free-text pet-care questions for the RAG layer
- Five markdown reference docs in `assets/knowledge/`
- `ANTHROPIC_API_KEY` from `.env`

**What outputs does PawPal+ produce?**

- A scheduled daily plan with start times, durations, and any deferred or too-long tasks
- For each question: an answer, the cited source filename(s), the retrieved chunks with cosine scores, and token usage
- A log line per retrieval and per LLM call to `logs/pawpal.log`

---

## 2. Retrieval Design

**How does your retrieval system work?**

- **Indexing:** at app startup, all `.md` files in `assets/knowledge/` are loaded, chunked into 200-word windows with 40-word overlap, and embedded with `sentence-transformers/all-MiniLM-L6-v2` (384-dim, normalized). The result is 11 chunks held in memory.
- **Scoring:** the query is embedded the same way; cosine similarity is computed as a dot product because vectors are pre-normalized.
- **Snippet selection:** top-3 chunks by cosine score, no minimum threshold.

**What tradeoffs did you make?**

- **Simplicity over cleverness.** No reranking, no hybrid search, no metadata filters. The retriever is dumb on purpose so I could see whether prompt grounding alone could carry the system. It did.
- **In-memory index, rebuilt at startup.** Streamlit caches the `RagService` via `@st.cache_resource` so the 90MB embedding model loads once per session, not on every interaction.
- **No minimum cosine threshold.** Even weak chunks reach the LLM. The system prompt's "say I don't know" rule covers this — verified across direct (0.66), tangential (0.48), and off-topic (0.03) queries.

---

## 3. Use of the LLM (Claude Haiku 4.5)

**When does PawPal+ call the LLM?**

Only when the user clicks **Get answer** on a pet-care question. The query is embedded, the top-3 chunks are retrieved, and they're sent to Claude Haiku 4.5 along with the system prompt. The scheduler itself never calls the LLM — plan generation is pure deterministic Python.

**What instructions do you give the LLM to keep it grounded?**

The system prompt enforces three rules:

1. Use only the provided context.
2. If the context doesn't contain enough information, say so directly — don't guess.
3. Cite the source filename(s) at the end of the answer.

---

## 4. Experiments and Comparisons

PawPal+ has one retrieval mode (RAG). Instead of comparing modes, I tested behavior across the cosine score landscape with three queries chosen to span direct, tangential, and off-topic.

| Query | Top cosine | Observed behavior | Helpful? |
|---|---|---|---|
| how often should I feed a young dog | 0.66 | Confident structured answer; cited `feeding_by_life_stage.md` | Helpful |
| my senior cat seems tired | 0.48 | Hedged, named the gap, recommended a vet; cited `vet_checkups_and_preventive_care.md` | Helpful |
| what kind of pizza should I order | 0.03 | Refused cleanly, redirected to pet-care topics | Helpful |

**What patterns did you notice?**

- The prompt grounding does the work. I had been planning a hard cosine threshold as a guardrail and dropped it after these three queries — the model already hedged at 0.48 and refused at 0.03 without one.
- The senior-cat case was the surprise. I expected a binary answer (improvise or refuse) and got a third behavior: name the gap, pivot to the closest relevant chunk, recommend a vet. That fell out of the three system-prompt rules without being explicitly requested.

---

## 5. Failure Cases and Guardrails

**Failure case 1 — Streamlit reruns (caught and fixed).** Before adding `@st.cache_resource` and the duplicate-handler guard, every Streamlit interaction would reload the 90MB embedding model and stack a new log handler. Not a model failure but a system-reliability one. Fixed by caching the `RagService` and guarding the logger with `if not logger.handlers:`.

**Failure case 2 — confidently-wrong on near-miss queries (still possible).** A user asks something the docs *almost* cover but not quite. The retriever might pull the wrong chunk and the model could answer confidently from it. The mitigation is human-side: cited filenames are shown in the UI so the user can open the file and verify. I haven't stress-tested this beyond three queries — it's the gap I want to close next.

**When should PawPal+ say "I don't know based on the docs I have"?**

- When the retrieved chunks don't contain the answer (off-topic queries, e.g. cosine ~0.03).
- When the question is in scope but the retrieved chunks only weakly relate — e.g. asking about symptom diagnosis when the docs cover scheduling.
- When the user asks for medical, legal, or other advice the knowledge base doesn't authoritatively cover.

**What guardrails did I implement?**

- System prompt with three rules (use only context, refuse if insufficient, cite sources).
- Source filenames surfaced in the UI for human verification.
- Authority separation: the AI cannot edit the schedule. Worst-case failure mode is a wrong explanation, never a wrong plan.
- Full audit logging: cosine scores, chunk sources, token usage, and tracebacks to `logs/pawpal.log`.
- Vetted knowledge base: I picked the five reference docs by hand. The model cannot pull in unvetted internet content.

---

## 6. Limitations and Future Improvements

**Current limitations**

1. Small knowledge base — five docs, 11 chunks. Anything outside that returns "I don't know."
2. General-purpose embedding model (`all-MiniLM-L6-v2`). Not pet-care tuned. Can miss domain synonyms.
3. No minimum cosine threshold and no reranking. Weak chunks still reach the LLM — the prompt covers it, the retriever doesn't.
4. Three test queries is enough for an MVP, not enough to claim coverage.
5. English-only docs that reflect mainstream Western pet-care norms.

**Future improvements**

1. Build a ~20-query evaluation set with expected behaviors (answer / hedge / refuse) and run it as a regression suite.
2. Surface cosine scores in the UI itself, not just the logs, so the user can see how confident the retrieval was — not just what got cited.
3. Expand the knowledge base — add docs on behavioral training, exotic pets, and regional differences.

---

## 7. Responsible Use

**Where could this system cause real-world harm if used carelessly?**

The realistic harm is someone treating an AI explanation as veterinary advice. A confidently-wrong answer about a sick pet could delay a vet visit. I mitigate this with prompt-level hedging, a knowledge base that contains no diagnostic content, and an explicit instruction for the model to recommend a vet when symptoms come up. The mitigations work in testing, but they depend on the user actually reading them.

**What instructions would you give real users who want to use PawPal+ safely?**

- Treat answers as a guide, not a diagnosis. If your pet shows symptoms, see a vet.
- Open the cited source file before acting on a claim. The citation is there so you can verify.
- Trust the plan; question the explanation. The schedule comes from a deterministic function, not the AI.

---
