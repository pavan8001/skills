# ASD-STE100 Rules Adapted for Software Documentation

ASD-STE100 (Simplified Technical English) was created for aerospace maintenance manuals where ambiguous prose causes fatal errors. In software engineering, ambiguous prose causes broken integrations, hallucinated agent edits, and silent invariant violations.

Apply these rules to every sentence in `docs/`, `README.md`, ADRs, and PR descriptions.

---

## 1. Word Choice Rules

### Rule 1.1: One word, one meaning; one concept, one word
Assign each word a single part of speech and a single meaning. Never cycle synonyms for stylistic variety.

- **Bad (synonym cycling):** "The `Scheduler` dispatches jobs to the queue. When a task is sent, the worker executes the item." (Are `job`, `task`, and `item` the same entity or three different types?)
- **Good (consistent noun):** "The `Scheduler` appends a `Job` to the `JobQueue`. The `Worker` reads the `Job` from the `JobQueue` and runs it."

### Rule 1.2: Replace unapproved / vague words with approved plain words

| Avoid (Unapproved) | Use Instead (Approved) | Part of Speech / Note |
|---|---|---|
| `utilize`, `leverage` | `use` | Verb |
| `facilitate`, `assist` | `help` | Verb (better: state exact mechanism) |
| `initiate`, `commence`, `launch` | `start` | Verb |
| `terminate`, `cease`, `abort` | `stop` | Verb |
| `modify`, `alter`, `mutate` | `change` | Verb |
| `verify`, `validate`, `ensure`, `insure` | `check` (by caller) / `assert` (in code) | Verb |
| `purchase`, `acquire`, `obtain` | `get` | Verb |
| `demonstrate`, `exhibit`, `indicate` | `show` | Verb |
| `approximately`, `roughly`, `around` | `about` (or state exact bound) | Adverb |
| `sufficient`, `adequate` | `enough` (or state exact threshold) | Adjective |
| `numerous`, `multiple`, `various` | `many` (or state exact count/range) | Adjective |
| `subsequently`, `thereafter` | `then`, `after` | Adverb |
| `prior to`, `in advance of` | `before` | Preposition |
| `in order to`, `so as to` | `to` | Preposition |
| `due to the fact that`, `inasmuch as` | `because` | Conjunction |
| `in the event that`, `should` (conditional) | `if` | Conjunction |
| `and/or`, `A/B` | `A, B, or both` | Conjunction |
| `via`, `by means of`, `through the use of` | `by`, `with`, `through` | Preposition |
| `simply`, `easily`, `just`, `obviously` | *(delete)* | Filler adverbs |
| `seamless`, `robust`, `powerful`, `flexible` | *(delete or state measurable property)* | Marketing adjectives |

### Rule 1.3: Contract Modal Verbs (`must`, `does`, `may`, `must not`)
Never use `should` in behavioral specifications. `should` leaves the reader guessing whether a rule is mandatory or optional.

- **Present indicative (`reads`, `returns`, `throws`)**: States current, verified code behavior.
- **`must` / `must not`**: States a hard invariant or caller precondition. Violating it is a bug.
- **`may`**: States an explicitly permitted optional behavior.

---

## 2. Noun Cluster & Technical Noun Rules

### Rule 2.1: Maximum 3 nouns in a cluster
Technical English collapses when writers stack four or more nouns together without prepositions.

- **Bad (6-noun cluster):** "Configure the database connection pool retry backoff policy."
- **Good (prepositions + code symbol):** "Configure the retry backoff for the database connection pool (`DB_POOL_BACKOFF_MS`)."

### Rule 2.2: Always use exact codebase identifiers in backticks
Never paraphrase a symbol name in prose. If the class is `ExtractionOrchestrator`, do not call it "the extraction manager" or "the orchestrator service".

---

## 3. Sentence Structure & Length Rules

### Rule 3.1: Length limits
- **Procedural sentences (how-to, runbooks, verification steps):** Maximum **20 words**. One command per sentence.
- **Descriptive / explanatory sentences (HLD, LLD, concepts, ADRs):** Maximum **25 words**. One idea per sentence.
- *Exception:* Inline backticked file paths or CLI commands count as 1 word toward the limit.

### Rule 3.2: Condition before action
Always place the condition, trigger, or warning *before* the action or consequence.

- **Bad:** "Drop the staging table if the checksum matches the archive." (A hasty reader or parser sees "Drop the staging table" first.)
- **Good:** "If the checksum matches the archive, drop the staging table."

### Rule 3.3: Active voice only
State `<Actor> <verb> <object>`. Passive voice hides which module owns the responsibility.

- **Bad:** "Expired tokens are pruned every 60 seconds, and an audit event is emitted." (Which process prunes them? Which module emits the event?)
- **Good:** "`TokenReaper` deletes expired rows from `sessions` every 60 seconds and writes a `SESSION_EXPIRED` event to `AuditLog`."

### Rule 3.4: Keep articles (`the`, `a`, `an`) and `that`
Telegraphic style creates syntactic ambiguity where nouns look like verbs.

- **Bad:** "Update index entries that reference stale shards." (`Update` = verb or noun? `index` = noun or verb?)
- **Good:** "Update the index entries that reference stale shards."

### Rule 3.5: Unambiguous pronoun reference
Never start a sentence with a bare `This`, `It`, or `Which` referring to the entire preceding clause. Repeat the noun.

- **Bad:** "`IngestWorker` buffers 1,000 records before flushing to disk. This reduces write amplification but risks data loss on `SIGKILL`." (What does "This" refer to?)
- **Good:** "`IngestWorker` buffers 1,000 records before flushing to disk. This batching reduces write amplification, but a `SIGKILL` drops buffered records."

---

## 4. Before & After Examples

### Example 1: Module Behavior (LLD)

**Before (Ambiguous, passive, synonym drift):**
> Token validation is performed by the auth middleware layer prior to request routing. Should the bearer credential be expired or malformed, an error response will be returned to the client and the request context is terminated. Additionally, rate limiting is leveraged here to prevent abuse.

**After (ASD-STE100 + Behavioral Contract):**
> `AuthMiddleware.handle` (`src/auth/middleware.ts`) verifies the `Authorization` header before routing a `Request`.
> 1. If the header is missing or malformed, `AuthMiddleware` returns HTTP `401` (`ERR_INVALID_TOKEN`) and stops the pipeline.
> 2. If `Token.expires_at <= now()`, `AuthMiddleware` returns HTTP `401` (`ERR_TOKEN_EXPIRED`).
> 3. If the caller exceeds 100 requests per minute per `client_id`, `RateLimiter.check` returns HTTP `429` with a `Retry-After` header.

### Example 2: Glossary Entry

**Before (Verbose, explains what it does instead of what it IS, leaks implementation details, includes generic concept):**
> **Timeout**: A timeout is used when a network request takes too long so the system doesn't hang forever.
> **Lease**: This component facilitates distributed locking by acquiring a record in the `job_leases` database table (`src/scheduler/lease.py`) and heartbeating it every 5 seconds so other workers don't run the same job.

**After (Tight, project-specific, defines what it IS, zero implementation details, lists `_Avoid_`):**
> *(Timeout omitted — general programming concept.)*
>
> ### **Lease**
> A time-bounded grant of exclusive ownership over a Job given to a single Worker.
> - _Avoid:_ lock, claim, reservation, heartbeat token
