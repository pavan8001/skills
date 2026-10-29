# Documentation Hierarchy and Behavioral Contracts

Documentation is a multi-resolution map of the codebase and its runtime execution units. Create files and directories **lazily**—only when you have actual resolved concepts, decisions, runtime topologies, or behavioral specs to write down.

---

## 1. Lazy Creation & Mirroring the Codebase Structure

Never scaffold empty directories or placeholder files up front:
- If no `GLOSSARY.md` exists, create one when the first domain term is resolved.
- If no `docs/adr/` exists, create it when the first ADR passes the three-part ADR gate.
- When documenting a module `src/<module>/`, mirror its path under `docs/architecture/modules/<module>/`.

```text
Repository Source                  Documentation Mirror (Created Lazily)
─────────────────                  ─────────────────────────────────────
src/                               docs/
                                   ├── INDEX.md
                                   ├── GLOSSARY.md
                                   ├── adr/
                                   │   ├── INDEX.md
                                   │   └── 0001-record-decision.md
                                   ├── concepts/
                                   │   └── INDEX.md
                                   └── architecture/
                                       ├── INDEX.md
                                       ├── hld.md        # Boundaries, Runtime Units, Call Flows, Log Lineage
├── ingestion/                         └── modules/
│   ├── pipeline.py                        ├── INDEX.md
│   └── chunker.py                         ├── ingestion/
│                                          │   ├── INDEX.md
│                                          │   ├── lld.md
│                                          │   └── entities/
│                                          │       └── document-chunk.md
└── storage/                               └── storage/
    ├── engine.py                              ├── INDEX.md
    └── wal.py                                 ├── lld.md
                                               └── entities/
                                                   └── wal-segment.md
```

### Why Mirroring Matters
1. **Predictable discovery for agents:** When an agent edits `src/ingestion/chunker.py`, it immediately knows the governing behavioral contract lives at `docs/architecture/modules/ingestion/lld.md` and `entities/document-chunk.md`.
2. **Scoped blast radius:** Module internals stay out of `hld.md`. Minute field-level validation rules stay in `entities/<entity>.md`, keeping `lld.md` readable.
3. **Orphan detection:** If `src/legacy_sync/` is deleted, `docs/architecture/modules/legacy_sync/` stands out immediately as dead documentation to delete.

---

## 2. What Belongs in Each Document Type

Never mix modes in a single file (Diátaxis separation). `GLOSSARY.md` contains pure domain definitions with zero implementation details; technical reference contracts (`hld.md`, `lld.md`, `entities/*.md`) stay dry and exact; design rationale lives in ADRs.

| Document Type | Path Pattern | Primary Question Answered | Granularity |
|---|---|---|---|
| **Glossary** | `GLOSSARY.md` or `docs/GLOSSARY.md` | "What is a `<Term>` in this domain, and which synonyms are banned?" | 1–2 sentences per project-specific noun; zero implementation details |
| **Index** | `**/INDEX.md` | "Where do I find X, and in what order do I read?" | Directory routing table |
| **ADR** | `docs/adr/NNNN-*.md` or `docs/architecture/adr/NNNN-*.md` | "Why did we choose X over Y, and what did we trade away?" | Single decision passing all 3 ADR criteria (hard to reverse, surprising without context, real trade-off) |
| **HLD** | `docs/architecture/hld.md` | "How do the execution units, cross-boundary call flows, and telemetry pipelines connect?" | Execution topology, end-to-end call flows, telemetry sources & sinks, trust boundaries |
| **Concept** | `docs/concepts/*.md` | "How does cross-cutting domain model X work across modules?" | Mental model spanning ≥2 modules (e.g., tenancy, permission inheritance) |
| **LLD** | `docs/architecture/modules/<mod>/lld.md` | "How does module `<mod>` execute, what telemetry does it emit, and how does it fail?" | Public API, internal call flow, concurrency, emitted logs/spans, error table, edge cases |
| **Entity / Drill-down** | `docs/architecture/modules/<mod>/entities/<name>.md` | "What are the exact field invariants, state transitions, and minute edge cases of `<name>`?" | Byte/field schema, state machine matrix, idempotency, boundary inputs |

---

## 3. Offering ADRs Sparingly

Do not write an ADR for routine implementation choices or self-evident patterns. Only offer to create an ADR when **all three** are true:

1. **Hard to reverse:** The cost of changing your mind later is meaningful.
2. **Surprising without context:** A future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off:** There were genuine alternatives and you picked one for specific reasons.

---

## 4. Runtime Topology & End-to-End Call Flows (Architecture-Agnostic)

Adapt the topology to what the codebase actually builds—whether that is a single CLI binary, a native desktop/mobile app with a UI process and local background daemon talking to remote servers, a browser SPA + API, serverless functions, or distributed cluster workloads.

### 4.1 Execution Units & Process Boundaries (`hld.md`)
Document every runnable unit that executes code from this repo:
- **Execution unit:** Process, thread, daemon, UI shell, worker, function, or service container, plus any config/manifest file that defines it.
- **Code entrypoint:** Exact startup file or symbol (`src/main.rs`, `src/daemon/server.ts`, `AppDelegate.swift`).
- **Communication boundary:** How callers or peer units reach it (in-process function call, IPC pipe, Unix domain socket, localhost HTTP, gRPC, WebSocket, message broker, or cloud event trigger).
- **Lifecycle & state ownership:** How the unit starts, stops, or restarts; whether it is stateless, holds in-memory state, owns a local file/SQLite database, or connects to remote storage.

### 4.2 End-to-End Call Flow Across Boundaries
For each primary flow, trace the path from the initial trigger across every process, IPC, or network boundary to the exact codebase modules:
1. **Trigger / Entry Boundary:** User UI gesture, CLI command, OS event, IPC message, or incoming client request, and the codebase handler that receives it.
2. **Boundary Hops (In-Process, IPC, or Network):** Every hop between execution units (e.g., Frontend UI → IPC Bridge → Local Daemon → Remote Server), including serialization format, timeout budget, retry/backoff policy, and offline or fallback behavior.
3. **State Mutation & Side Effects:** Which execution unit validates invariants, mutates local or remote state, and returns the result or error back across the chain.

---

## 5. Telemetry & Log Lineage Contract (Sources → Transport → Sinks)

Logs, metrics, traces, crash reports, and audit events are part of the behavioral contract. Regardless of where the software runs, document the complete lineage from **Source** (code emission) through **Transport** to **Sink** (final storage/consumption).

### 5.1 System Telemetry Pipeline (`hld.md`)
Map each telemetry stream end-to-end:
- **Source (Code Emission API):** Which logger, tracer, or event emitter the codebase calls.
- **Transport & Buffering:** How records travel from the emitting thread/process (e.g., synchronous write to `stderr`, IPC forwarding from UI to daemon, async ring buffer, local log rotation, or network batch shipper).
- **Sink (Destination & Retention):** Where the records live and how they are inspected (e.g., local file `~/.local/state/<app>/app.log`, OS unified log / Event Viewer, local SQLite table, `stdout`, or remote log/metric/trace store) plus rotation or retention limits.
- **Backpressure, Offline, & Failure Policy:** What happens when disk is full, IPC is disconnected, or a remote sink is unreachable (e.g., drop oldest from ring buffer, spool to local disk until reconnect, or fail-closed).
- **Correlation & Context Propagation:** Which identifiers (`request_id`, `trace_id`, `session_id`, `ipc_call_id`) are attached to records and passed across thread, IPC, or network boundaries.
- **Redaction Invariants:** Credentials, tokens, keys, or personal data fields that must never be written to any log sink.

### 5.2 Module-Level Emission Contract (`lld.md`)
In each module's `lld.md`, list the key log events, metrics, or traces emitted by that module:

| Event / Metric Name | Level / Kind | Source (`file:symbol`) | Trigger Condition | Mandatory Fields | Target Sink |
|---|---|---|---|---|---|
| `<event.started>` | Log `INFO` | `src/<mod>/<file>:<fn>` | Operation begins after validation | `correlation_id`, `<entity_id>` | `<Sink Name>` |
| `<event.failed>` | Log `ERROR` | `src/<mod>/<file>:<fn>` | Boundary call or invariant fails | `correlation_id`, `error_code`, `reason` | `<Sink Name>` |
| `<metric_duration_ms>` | Histogram / Timer | `src/<mod>/<file>:<fn>` | Operation completes or aborts | `status` (`ok`\|`err`), `unit` | `<Sink Name>` |

---

## 6. Writing Technical Specs as an Executable Behavioral Contract

Standard prose describes *intent* ("The service handles retries gracefully"). A behavioral contract (`hld.md`, `lld.md`, `entities/*.md`) specifies *observable behavior under exact conditions*:

### 6.1 Input / Output & Precondition Contracts
State what the caller must guarantee, what the function guarantees on return, and what happens when preconditions fail:
- **Preconditions:** Exact types, ranges, encodings, and required state before invocation.
- **Postconditions:** Return value invariants, mutated state, emitted events/logs, or written files/rows.
- **Error Conditions:** Exact exception class, error code, status code, or exit code for each invalid input or dependency failure.

### 6.2 State Machines over Prose Paragraphs
Whenever an entity or execution unit has lifecycle states (e.g., `disconnected`, `connecting`, `connected`, `backoff`), document it as an explicit transition table plus a `stateDiagram-v2` Mermaid block:

| Current State | Trigger / Event | Guard Condition | Next State | Side Effect & Emitted Log |
|---|---|---|---|---|
| `pending` | `Worker.claim(job_id)` | `attempts < max_attempts` | `leased` | Sets `lease_expires_at = now() + 30s`; logs `job.leased` (`INFO`) |
| `leased` | `Worker.complete(job_id)` | `caller == lease_owner` | `completed` | Deletes active lease; logs `job.completed` (`INFO`) |
| `leased` | `LeaseReaper.tick()` | `now() > lease_expires_at` | `pending` | Increments `attempts` by 1; logs `job.lease_expired` (`WARN`) |
| `pending` | `Worker.claim(job_id)` | `attempts >= max_attempts` | `dead_letter` | Emits `JobExhaustedEvent`; logs `job.dead_lettered` (`ERROR`) |

Also list **Forbidden Transitions** explicitly (e.g., "`completed` → `pending` is rejected with `InvalidTransitionError`; create a new `Job` instead").

### 6.3 Minute Behavioral Drill-Downs (Edge Cases & Boundaries)
In `lld.md` and `entities/<entity>.md`, explicitly answer the questions that force engineers to read source code line by line:
- **Empty / Zero / Null inputs:** What does `chunk_text("")` return? `[]` or `[""]`?
- **Boundary values:** At `max_tokens = 512`, is `512` inclusive (`<=`) or exclusive (`<`)?
- **Ordering & Determinism:** Are results sorted? By what key? How are ties broken?
- **Idempotency:** If the same call runs twice with identical arguments, does the second call no-op, overwrite, or raise a duplicate error?
- **Concurrency & Locking:** Is the structure thread-safe? Which lock guards which state? What happens under contention?
- **Partial Failure & Rollback:** If step 2 of 3 fails, is step 1 rolled back in a transaction, left as orphan state, or cleaned up on the next run?

---

## 7. Keeping Docs Consistent with Code (Drift Prevention)

1. **Code Anchors in Spec Frontmatter:** Every technical spec (`hld.md`, `lld.md`, `entities/*.md`, `adr/*.md`) lists its `sync_commit`, `code_paths`, and `symbols`. (`GLOSSARY.md` is excluded because it must remain devoid of implementation details.)
2. **Co-located Updates:** Any commit that changes a signature, execution boundary, log event key/sink, state transition, threshold, or error code in `code_paths` must update the corresponding `hld.md`, `lld.md`, or `entities/*.md` in the same change.
3. **Verification Gate:** Run `scripts/verify_docs.py` after every doc or code change. If `git log <sync_commit>..HEAD -- <code_paths>` is non-empty, re-verify every claim in the document against the current code before bumping `sync_commit`.
