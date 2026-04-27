# PawPal+ RAG Architecture

This diagram shows how the Retrieval-Augmented Generation (RAG) layer
fits into PawPal+. The deterministic scheduler in `pawpal_system.py` is
the source of truth for plans; the RAG layer only **explains** plans
with cited evidence — it never edits them.

```mermaid
flowchart TD
    %% ─── INDEX BUILD ─────────────────────────────────────────────
    subgraph BUILD["🛠️ INDEX BUILD — runs once, cached by @st.cache_resource"]
        DOCS[/"assets/knowledge/*.md<br/>5 reference documents"/]
        LOAD["load_docs()"]
        CHUNK["chunk()<br/>200 words, overlap 40"]
        EMBED["embed()<br/>sentence-transformers<br/>all-MiniLM-L6-v2 · 384-d"]
        INDEX[("INDEX<br/>11 chunks in RAM")]
        DOCS --> LOAD --> CHUNK --> EMBED --> INDEX
    end

    %% ─── QUERY FLOW ──────────────────────────────────────────────
    subgraph QUERY["🔎 QUERY FLOW — every Get answer click"]
        USER(["👤 User"])
        APP["app.py<br/>Streamlit form"]
        SVC["RagService.explain(query)"]
        RETR["① embed query<br/>② cosine similarity, top-3"]
        FMT["③ format context<br/>+ source citations"]
        LLM["④ Anthropic API<br/>Claude Haiku 4.5<br/><br/>SYSTEM PROMPT enforces:<br/>• use only context<br/>• say don't know if insufficient<br/>• cite source filenames"]
        OUT["⑤ Streamlit displays:<br/>answer · sources · token usage"]
        LOG[("logs/pawpal.log<br/>full audit trail")]

        USER -->|question| APP
        APP --> SVC
        SVC --> RETR
        RETR --> FMT
        FMT --> LLM
        LLM --> OUT
        SVC -.->|writes| LOG
    end

    INDEX -.->|read at query time| RETR

    %% ─── HUMAN CHECKS ────────────────────────────────────────────
    subgraph CHECKS["🧑‍🔬 HUMAN-IN-THE-LOOP VERIFICATION"]
        C1["① Source citations<br/>user opens the .md file<br/>to verify the answer"]
        C2["② Cosine scores in logs<br/>low top score flags drift<br/>(0.03 = off-topic)"]
        C3["③ Pre-integration test queries<br/>direct / tangential / off-topic<br/>run before wiring to UI"]
        C4["④ Plan-authority boundary<br/>scheduler is deterministic<br/>RAG never edits the plan"]
    end

    OUT -.->|reviewed by| C1
    LOG -.->|audited via| C2

    %% ─── styling ────────────────────────────────────────────────
    classDef store fill:#fff4d6,stroke:#c89412,stroke-width:1px;
    classDef ai fill:#e8f0ff,stroke:#3a6ad4,stroke-width:1px;
    classDef human fill:#eaf7ea,stroke:#3c8a3c,stroke-width:1px;
    classDef io fill:#fbe9e7,stroke:#b14a3a,stroke-width:1px;

    class INDEX,LOG store;
    class EMBED,LLM,RETR,FMT ai;
    class USER,C1,C2,C3,C4 human;
    class DOCS,APP,OUT io;
```

## Data flow summary

| Phase | Trigger | Cost | Artifact |
|---|---|---|---|
| Index build | App startup (cached) | ~3 sec, no API | `INDEX` (in-memory, 11 chunks × 384-d) |
| Per query | User clicks **Get answer** | ~1–2 sec, ~$0.002 | Answer + sources + log line |

## Architectural decisions

- **Authority separation.** The scheduler is the single source of truth for *what* happens; the RAG layer only adds explanation *about* what happens. The AI can hallucinate freely without breaking the schedule — failure mode is "wrong explanation," not "wrong plan."
- **Two grounding layers.** Prompt rules (model-enforced) plus cited source filenames (human-verifiable). Cosine scores in logs add a third layer for after-the-fact audit.
- **Dumb-on-purpose retriever.** Pure cosine similarity, no reranking, no thresholding. Verified across direct (0.66), tangential (0.48), and off-topic (0.03) queries — the system prompt handles edge cases without a hard threshold.
