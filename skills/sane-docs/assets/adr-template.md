---
title: "ADR-NNNN: <Short Decision Title in Active Voice>"
doc_type: adr
status: active
date: YYYY-MM-DD
sync_commit: <git-short-sha>
code_paths:
  - src/<affected_path>
symbols:
  - <AffectedSymbol>
---

# ADR-NNNN: <Short Decision Title in Active Voice>

## 1. Problem and Constraints

<One paragraph stating the problem we must solve and the hard constraints from the codebase, runtime, or callers that make the decision non-trivial.>

## 2. Decision

We chose **<Chosen Option>**, implemented in `<src/path>` via `<Symbol>`.

<Two to four sentences stating how the chosen design works and which invariants it enforces.>

## 3. Trade-offs Accepted

- We accept **<downside / cost X>** in exchange for **<benefit / guarantee Y>**.
- We accept **<constraint A>** so that callers do not have to manage **<complexity B>**.

## 4. Alternatives Rejected

### Alternative 1: <Name of Rejected Shape>
- **Why rejected:** <One or two concrete sentences explaining the failure mode, complexity exposed to callers, or invariant it could not uphold.>

### Alternative 2: <Name of Rejected Shape>
- **Why rejected:** <One or two concrete sentences.>

## 5. Verification Contract

- **Enforced by:** `<test file, linter, or runtime check that fails if this decision is violated>`
- **Condition to revisit:** Revisit this ADR only if <concrete measurable threshold or requirement change>.
