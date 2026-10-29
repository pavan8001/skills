---
name: sane-docs
description: >
  Actively build and sharpen a project's domain model, ubiquitous language,
  runtime topology, observability contracts, and behavioral documentation as an
  enforceable contract between code, users, and AI agents. Challenges ambiguous
  terms against GLOSSARY.md, stress-tests edge cases with concrete scenarios,
  cross-references claims against code, writes ASD-STE100 Simplified Technical
  English, and creates ADRs, HLD (execution units, cross-boundary call flows,
  and log/telemetry source-to-sink lineage), LLD, entity specs, INDEX.md maps,
  Mermaid diagrams, and HTML visualizations lazily as decisions crystallise. Use
  when designing features, discussing domain models or runtime/logging
  architecture, resolving terminology, writing or auditing docs, or visualizing
  system flows.
license: MIT
compatibility: Requires python3 (stdlib only) to run bundled verification scripts in scripts/.
metadata:
  author: pavan
  version: "1.4.0"
  standard: ASD-STE100
---

# Sane Docs

Actively build and sharpen the project's domain model as you design. This is the active discipline: challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely reading GLOSSARY.md for vocabulary is not this skill: that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

Create files lazily: only when you have something to write. If no GLOSSARY.md exists, create one when the first term is resolved. If no docs/adr/ exists, create it when the first ADR is needed.

Documentation is not an information dump. It is a **behavioral contract** between the codebase, human engineers, and AI agents. Every claim and diagram in `docs/` is a testable assertion about what the code is, what it does, how its runtime units interact, where its telemetry flows, and what it refuses to do.

---

## 1. During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in GLOSSARY.md, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account': do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships, cross-boundary calls, or failure modes are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"

### Update GLOSSARY.md inline

When a term is resolved, update GLOSSARY.md right there. Don't batch these up: capture them as they happen.
GLOSSARY.md should be totally devoid of implementation details. Do not treat GLOSSARY.md as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

- Hard to reverse: the cost of changing your mind later is meaningful
- Surprising without context: a future reader will wonder "why did they do it this way?"
- The result of a real trade-off: there were genuine alternatives and you picked one for specific reasons

---

## 2. Glossary Rules (`GLOSSARY.md`)

Use the template in [assets/glossary-template.md](assets/glossary-template.md).

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others under _Avoid_.
- **Keep definitions tight.** One or two sentences max. Define what it IS, not what it does.
- **Only include terms specific to this project's context.** General programming concepts (timeouts, error types, utility patterns) don't belong even if the project uses them extensively. Before adding a term, ask: is this a concept unique to this context, or a general programming concept? Only the former belongs.
- **Group terms under subheadings when natural clusters emerge.** If all terms belong to a single cohesive area, a flat list is fine.
- **Keep `GLOSSARY.md` pure.** No file paths, class names, database tables, or implementation mechanics.

Each entry follows this exact structure:

```markdown
### **<Canonical Term>**
<One or two sentences max. Define what it IS, not what it does. Zero implementation details.>
- _Avoid:_ <synonym-1>, <synonym-2>
```

Whenever you encounter a term listed under `_Avoid_` in conversation, prose, diagrams, or new symbols, challenge it or replace it with the canonical term.

---

## 3. Writing Standard: ASD-STE100 Simplified Technical English

Write so a tired engineer or cold-start agent parses every sentence on the first read with zero ambiguity. For the complete rulebook and approved/unapproved word tables, read [references/ste100-rules.md](references/ste100-rules.md).

- **One meaning per word, one word per meaning.** If `check` means "verify against an invariant", never use `check` to mean "halt" or "throttle". Pick `start`, not `start` in one file and `initiate` or `launch` in another.
- **One thought per sentence.** Keep procedural instructions to **≤ 20 words** and descriptive sentences to **≤ 25 words**. Split compound thoughts with a period, not a semicolon or em dash.
- **Active voice and explicit actors.** Name the exact actor: "`ExtractionOrchestrator` parses the file", never "the file is parsed".
- **Imperative verbs for procedures.** Start every step with a command verb ("Run `pytest`", "Set `TIMEOUT_MS=500`"). Put conditions and warnings *before* the action they guard ("If the migration alters a primary key, lock the table before running `migrate`").
- **Break noun clusters.** Maximum **3 nouns** in a row. Rewrite "the worker thread pool shutdown timeout configuration parameter" as "the timeout parameter for shutting down the worker pool (`WORKER_SHUTDOWN_MS`)".
- **Keep articles and structural connectors.** Always include `the`, `a`, `an`, and `that`. "Remove backup file" is ambiguous; "Remove the backup file" has one reading.
- **Ban ambiguous pronouns and slash constructions.** Every `it`, `this`, or `they` must point to a single noun in the same sentence; otherwise repeat the noun. Replace `a/b` and `and/or` with "a, b, or both".
- **Ban AI slop and hedging.** Never write `utilize` (use `use`), `facilitate` (use `help`), `leverage` (use `use`), `seamless`, `robust`, `simply`, `easily`, or `should`. In contracts, use `must` (invariant), `does` (fact), or `may` (optional).

---

## 4. Runtime Topology, Call Flows, & Telemetry Lineage

Every codebase runs as one or more **execution units** (processes, threads, UI/daemon pairs, serverless functions, containers, or cloud services). Do not assume a fixed infrastructure; derive the runtime model from the codebase itself and document three consistent flows in `hld.md` and `lld.md` (details in [references/doc-hierarchy-and-contracts.md](references/doc-hierarchy-and-contracts.md)):

1. **Execution Units & Deployment Topology (`hld.md`):**
   - Identify each deployable or runnable unit in the project (e.g., Desktop UI process + local background daemon, mobile app + remote API, CLI binary, web frontend + backend service, serverless function, or cluster workload).
   - Map each execution unit to its codebase entrypoint (`file:symbol`), lifecycle (how it starts, stops, or scales), state ownership (in-memory, local disk/SQLite, or shared store), and communication channels (IPC, unix socket, shared memory, HTTP/gRPC, WebSocket, message queue).
2. **End-to-End Call Flow Across Boundaries (`hld.md` & `lld.md`):**
   - Trace how a user action, client request, or system trigger enters the first boundary, crosses threads, processes, IPC, or network hops, and executes in specific codebase modules (`Entrypoint` → `Boundary/Transport` → `Handler` → `Domain/Storage`).
   - Specify timeouts, retry/reconnection rules, offline/degraded behavior, and failure propagation at every boundary hop.
3. **Telemetry & Log Lineage: Sources → Transport → Sinks (`hld.md` & `lld.md`):**
   - **Sources (Code Emission):** Which code paths (`file:symbol`) emit logs, metrics, spans, crash dumps, or audit records, at what severity, under what trigger condition, and with what structured fields.
   - **Propagation:** How correlation identifiers (`trace_id`, `request_id`, `session_id`) travel across function calls, IPC, queues, or network calls.
   - **Sinks (Destination & Retention):** Where emitted records land (local rotating file, OS system log, `stdout`, local SQLite, or remote collector/sink), what happens when the sink is full or unreachable (buffer, drop, rotate, or fail-closed), and which sensitive fields are redacted before emission.

---

## 5. Visualizations: Mermaid Diagrams & Standalone HTML Files

Include visualizations whenever a reader would otherwise have to mentally reconstruct a runtime topology, cross-boundary call sequence, log pipeline, state machine, or data layout from prose. For full rules, read [references/visualizations.md](references/visualizations.md).

| Condition | Format | Where It Lives |
|---|---|---|
| Static topology, call sequence, log source-to-sink pipeline, ER schema, or state machine with **≤ 20 nodes/edges** | Fenced ` ```mermaid ` block | Inline inside the `.md` document |
| Dense graph (**> 20 nodes/edges**) needing pan, zoom, search, filter, or layer toggles | Self-contained `.html` file | `visualizations/<slug>.html` linked from the `.md` doc and `INDEX.md` |
| Step-by-step call tracer across execution units, state-transition simulator, or byte/memory layout inspector | Self-contained `.html` file | `visualizations/<slug>.html` built from [assets/visualization-template.html](assets/visualization-template.html) |

---

## 6. Architecture & Lazy Directory Layout

Documentation mirrors the codebase structure so humans and agents can navigate `src/` and `docs/` in lockstep. Create directories and files **lazily**—only when a term, decision, module contract, or entity spec is ready to be written. Whenever a directory under `docs/` is created, maintain its `INDEX.md` routing table.

```text
docs/
├── INDEX.md                 # Root routing map and reading order (created when docs/ starts)
├── GLOSSARY.md              # Pure domain glossary and _Avoid_ list (or at repo root GLOSSARY.md)
├── adr/                     # Architecture Decision Records (created when first ADR is needed)
│   ├── INDEX.md
│   └── 0001-record-decision.md
├── concepts/                # Cross-cutting domain models (created when needed)
│   └── INDEX.md
└── architecture/
    ├── INDEX.md
    ├── hld.md               # System boundaries, runtime topology, call flows, log lineage
    ├── visualizations/      # Interactive HTML topology/call-flow maps & state simulators
    └── modules/             # Mirrors codebase structure lazily as modules are documented
        ├── INDEX.md
        └── <module>/
            ├── INDEX.md
            ├── lld.md       # Module API, internal call flow, emitted telemetry, edge cases
            ├── visualizations/
            └── entities/    # Deep-dive contracts for domain entities & minute functionality
                └── <entity>.md
```

### Contract Metadata Header (for HLD, LLD, Entity, Concept, and ADR files)

Every technical spec file (except `GLOSSARY.md`, which stays devoid of implementation details) starts with YAML frontmatter that binds it to the codebase:

```yaml
---
title: <Document Title>
doc_type: hld | lld | entity | concept | adr | index
status: draft | active | deprecated | superseded
sync_commit: <git-short-sha>
code_paths:
  - src/path/to/module.py
symbols:
  - CanonicalClassName
---
```

When you modify files listed in `code_paths`, update the corresponding `.md` and `.html` files and advance `sync_commit` to `HEAD` only after verifying every claim, log field, and diagram edge against the code.

---

## 7. Verification & Drift Audit

Run the bundled verification script to check index coverage, broken links, code contract drift (`code_paths`, `symbols`, `sync_commit`), glossary purity, and ASD-STE100 sentence rules:

```bash
python3 .agents/skills/sane-docs/scripts/verify_docs.py --repo-root . --docs-dir docs
```

---

## 8. Bundled Resources

- **STE-100 Rulebook & Word List**: [references/ste100-rules.md](references/ste100-rules.md)
- **Doc Hierarchy, Runtime Topology & Telemetry Contracts**: [references/doc-hierarchy-and-contracts.md](references/doc-hierarchy-and-contracts.md)
- **Visualization Rules (Mermaid & HTML)**: [references/visualizations.md](references/visualizations.md)
- **Templates**:
  - [assets/glossary-template.md](assets/glossary-template.md)
  - [assets/index-template.md](assets/index-template.md)
  - [assets/hld-template.md](assets/hld-template.md)
  - [assets/lld-template.md](assets/lld-template.md)
  - [assets/entity-template.md](assets/entity-template.md)
  - [assets/adr-template.md](assets/adr-template.md)
  - [assets/visualization-template.html](assets/visualization-template.html)
- **Verification Script**: `scripts/verify_docs.py`
