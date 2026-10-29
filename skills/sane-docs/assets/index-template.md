---
title: <Directory Name> Index
doc_type: index
status: active
sync_commit: <git-short-sha>
---

# <Directory Name>

<One or two ASD-STE100 sentences stating what this directory contains and which part of the codebase it covers.>

## Reading Order

1. [GLOSSARY.md](./GLOSSARY.md) — Canonical project terms and banned synonyms.
2. [architecture/hld.md](./architecture/hld.md) — End-to-end system boundaries and runtime flows.
3. [architecture/modules/INDEX.md](./architecture/modules/INDEX.md) — Per-module Low-Level Designs (`lld.md`) and entity contracts.

## Documents in This Directory

| Document | Type | Code Mirror | Question Answered |
|---|---|---|---|
| [GLOSSARY.md](./GLOSSARY.md) | Glossary | Global | What does each project-specific domain noun mean, and which synonyms are banned? |
| [concepts/INDEX.md](./concepts/INDEX.md) | Index | Cross-cutting | How do cross-module domain models work? |
| [architecture/INDEX.md](./architecture/INDEX.md) | Index | `src/` | How is the system architected from HLD down to module LLDs and ADRs? |
