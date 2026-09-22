# InsightHub Backend — Engineering Tickets

Broken out from `backend-spec.md`, grouped by milestone. Each ticket is scoped to be completable independently within its milestone. P0 tickets only unless noted.

---

## Milestone 1 — Auth + Async CSV Ingestion

### TICKET-101: Project scaffolding + auth
**Description:** Set up Django project, PostgreSQL connection, DRF, and auth (token or session-based — reuse pattern from last year's build if suitable).
**Acceptance criteria:**
- [ ] Django project runs locally with PostgreSQL
- [ ] User can register and log in via API
- [ ] Authenticated requests carry identifiable user context for ownership checks downstream

---

### TICKET-102: `Dataset` model + migration
**Description:** Create the `Dataset` model per the build spec — `id`, `owner`, `name`, `raw_file`, `status`, `schema`, `row_count`, `created_at`.
**Acceptance criteria:**
- [ ] Migration creates the table with correct field types (`status` as choices/enum: `pending`, `processing`, `ready`, `failed`)
- [ ] `schema` is nullable, only populated once `status == ready`
- [ ] `owner` FK enforces cascade delete or protect (decide and document which)

---

### TICKET-103: Upload endpoint (`POST /datasets/`)
**Description:** Accept multipart CSV upload, save file, create `Dataset(status='pending')`, enqueue background parse job, return immediately.
**Acceptance criteria:**
- [ ] Returns within ~200ms excluding file transfer time, regardless of file size
- [ ] Response includes `{id, status: 'pending'}`
- [ ] Rejects non-CSV file types with a clear error before saving
- [ ] Rejects unauthenticated requests

---

### TICKET-104: django-rq setup + background parse worker
**Description:** Wire up Redis + django-rq. Worker job reads the CSV with pandas, infers column types, updates `Dataset.status` and `schema`.
**Acceptance criteria:**
- [ ] Worker picks up jobs enqueued by TICKET-103
- [ ] Successful parse sets `status='ready'`, populates `schema` and `row_count`
- [ ] Malformed/empty CSV sets `status='failed'` with a stored, human-readable reason — no silent hang, no unhandled exception crashing the worker
- [ ] Worker runs independently of the Django dev server process (documented run command)

---

### TICKET-105: Type inference logic
**Description:** Classify each column as `numeric`, `date`, `categorical`, or `text` based on pandas dtype + heuristics.
**Acceptance criteria:**
- [ ] Clean integer/float columns → `numeric`
- [ ] ISO and common date-string formats → `date`
- [ ] Low-cardinality columns (e.g. <20 distinct values relative to row count) → `categorical`
- [ ] Everything else → `text`
- [ ] Missing/blank cells in an otherwise-numeric column don't force it to `text`
- [ ] **Open question to resolve before starting:** coerce ambiguous columns aggressively, or flag as low-confidence? (see spec's Open Questions)

---

### TICKET-106: Status polling endpoint (`GET /datasets/:id/`)
**Description:** Return current dataset status and, once ready, the inferred schema.
**Acceptance criteria:**
- [ ] Returns accurate `status` at any point in the pending → processing → ready/failed lifecycle
- [ ] Returns `schema` and `row_count` only when `status == 'ready'`
- [ ] Returns failure reason when `status == 'failed'`
- [ ] 403/404 for a dataset not owned by the requesting user

---

## Milestone 2 — Dashboard/Chart CRUD (Static Layout)

### TICKET-201: `Dashboard` model + CRUD endpoints
**Description:** Create `Dashboard` model (`owner`, `dataset` FK, `title`, timestamps) and full CRUD API.
**Acceptance criteria:**
- [ ] `POST/GET/PATCH/DELETE /dashboards/` and `/dashboards/:id/` implemented
- [ ] Ownership enforced on all operations — a user cannot access another user's dashboard via this API
- [ ] Creating a dashboard requires a `dataset_id` with `status == 'ready'` (reject if dataset isn't parsed yet)

---

### TICKET-202: `Chart` model + CRUD endpoints
**Description:** Create `Chart` model (`dashboard` FK, `chart_type`, `x_column`, `y_column`, `narrative`, layout fields, `z_index`) and CRUD API nested under dashboards.
**Acceptance criteria:**
- [ ] `POST /dashboards/:id/charts/`, `PATCH /charts/:id/`, `DELETE /charts/:id/` implemented
- [ ] `x_column`/`y_column` validated against the parent dataset's `schema` — reject references to nonexistent columns
- [ ] Ownership enforced transitively through the parent dashboard

---

### TICKET-203: Dataset preview + chart data endpoints
**Description:** `GET /datasets/:id/preview/` (sample rows) and `GET /datasets/:id/data/?x=&y=` (resolved data points for a specific chart).
**Acceptance criteria:**
- [ ] Preview returns a bounded sample (e.g. first 20 rows), not the full dataset
- [ ] Data endpoint returns only the two requested columns' values, not the whole row set
- [ ] Both respect ownership

---

## Milestone 3 — Layout Persistence (Drag/Resize)

### TICKET-301: Layout fields on `Chart`
**Description:** Add `x`, `y`, `width`, `height` fields to `Chart` (already scaffolded in TICKET-202 model — this ticket covers the update path).
**Acceptance criteria:**
- [ ] Lightweight `PATCH /charts/:id/` accepts partial layout-only updates without requiring the full chart config resent
- [ ] Layout updates are idempotent and safe to fire repeatedly (e.g. from drag-end events)

---

## Milestone 4 — Chart-Type Suggestion (P1)

### TICKET-401: Suggestion endpoint or embedded logic
**Description:** Given two selected columns' inferred types, return a suggested chart type per the lookup table in the build spec (date+numeric→line, categorical+numeric→bar, numeric+numeric→scatter, categorical-count→pie).
**Acceptance criteria:**
- [ ] Suggestion available either as a dedicated endpoint or inline in the preview response
- [ ] Frontend can override the suggestion — this is a default, not a constraint

---

## Milestone 5 — Public Sharing

### TICKET-501: `ShareLink` model + generation endpoint
**Description:** Create `ShareLink` model (`dashboard` FK, `token`, `created_at`, `revoked_at`). `POST /dashboards/:id/share/` creates or returns the active token.
**Acceptance criteria:**
- [ ] Token is UUID4 or equivalent-entropy random string — never sequential or guessable
- [ ] Calling the endpoint again while a link is active returns the existing token, doesn't create duplicates

---

### TICKET-502: Regenerate link endpoint
**Description:** `POST /dashboards/:id/share/regenerate/` revokes the current token and issues a new one.
**Acceptance criteria:**
- [ ] Old token immediately stops resolving (404, not 403 — see TICKET-503)
- [ ] New token is returned and becomes the active link

---

### TICKET-503: Public dashboard endpoint
**Description:** `GET /public/dashboards/:token/` — unauthenticated, read-only, returns dashboard + charts + layout + resolved chart data in one payload.
**Acceptance criteria:**
- [ ] No auth required
- [ ] Invalid or revoked token returns 404 — does not leak whether a dashboard exists behind an invalid token
- [ ] Response includes everything the frontend needs to render the read-only view in one request (no N+1 follow-up calls)
- [ ] Raw CSV data is never exposed — only the resolved chart-level data needed for rendering

---

## Milestone 6 — Polish (P1)

### TICKET-601: Soft delete for datasets/dashboards
**Acceptance criteria:**
- [ ] Deleted records are flagged, not hard-removed, for a grace period
- [ ] Deleted dashboards' share links immediately stop resolving

### TICKET-602: CSV export of underlying dashboard data
**Acceptance criteria:**
- [ ] Owner can download the original or cleaned CSV backing a dashboard
