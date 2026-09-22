# InsightHub Backend — Spec

**Context:** Portfolio rebuild of a coursework project. Solo build, backend-first (Django REST + PostgreSQL), feeding a React frontend. This spec covers backend scope only — frontend is a separate track, referenced here only where it constrains the API contract.

---

## Problem Statement

Last year's coursework version of InsightHub had a backend that parsed uploaded CSVs synchronously inside the request cycle, which froze the UI on any upload of meaningful size, and had no clear data model separating raw ingestion from chart configuration from public sharing. As a portfolio piece meant to demonstrate backend engineering judgment (data modeling, API design, handling long-running work correctly), the rebuild needs a backend that a reviewer — a hiring manager or technical interviewer — can look at and see deliberate architecture, not just working CRUD.

The cost of not solving this: a backend that "just works" in a demo but reveals sync-blocking, no separation of concerns, or no access control on shared data the moment someone asks "what happens with a 50MB file?" or "can I see someone else's dashboard by guessing the URL?" — exactly the kind of question a technical interviewer would ask.

---

## Goals

1. **CSV ingestion never blocks the request cycle** — upload returns immediately; parsing happens asynchronously via a background worker
2. **Reliable type inference** on arbitrary uploaded CSVs (numeric / date / categorical / text), with sane handling of messy real-world data (mixed types, missing values, inconsistent headers)
3. **Clean data model** separating `Dataset` (raw ingestion), `Dashboard`/`Chart` (configuration + layout), and `ShareLink` (public access) — each with a single clear responsibility
4. **Public share links are unguessable, not merely unlisted** — access control by token, not security-by-obscurity-of-URL-structure alone
5. **API is frontend-agnostic enough to demo cleanly** — a reviewer could hit the API directly (Postman/curl) and understand the model without reading frontend code

---

## Non-Goals

- **Multi-dataset dashboards** (a dashboard charting across more than one uploaded file) — v1 is one dataset per dashboard; the FK structure doesn't preclude this later, but building for it now is premature
- **Real-time collaborative editing** (multiple users editing one dashboard simultaneously) — this is a solo-account tool, not a team tool, for v1
- **Data transformation/cleaning UI** (letting users fix malformed columns post-upload) — out of scope; the backend infers types as best it can and surfaces what it couldn't confidently type, but doesn't offer in-app data cleaning
- **Horizontal scaling concerns** (multiple worker nodes, load balancing) — this is a portfolio demo, not a production system with real traffic; django-rq with a single worker is sufficient and the right scope
- **Fine-grained sharing permissions** (view vs. edit access for other authenticated users) — v1 sharing is binary: private (owner only) or public-via-token (anyone with the link, read-only)

---

## User Stories

**Dashboard owner (authenticated)**
- As a dashboard owner, I want to upload a CSV and get immediate confirmation that it's processing, so that I'm not staring at a frozen screen wondering if my upload worked
- As a dashboard owner, I want the system to tell me which columns it understood and how (numeric/date/categorical), so that I can build charts without guessing what the backend inferred
- As a dashboard owner, I want to create and arrange charts on a dashboard, so that I can turn raw data into a visual story
- As a dashboard owner, I want to generate a shareable link for a dashboard, so that I can send it to someone without giving them an account
- As a dashboard owner, I want to revoke/regenerate a share link, so that an old link stops working if I no longer want it accessible
- As a dashboard owner, I want a clear error if my CSV fails to parse (e.g., corrupted file, no valid rows), so that I know to fix and re-upload rather than waiting indefinitely

**Public viewer (unauthenticated)**
- As a public viewer with a share link, I want to see the dashboard's charts and layout without needing an account, so that I can view the data immediately after scanning a QR code
- As a public viewer, I want a clear "this link is no longer valid" response if the dashboard was unshared, so that I'm not confused by a broken page

---

## Requirements

### Must-Have (P0)

**Async CSV ingestion**
- Upload endpoint persists the file and returns immediately with `status: pending`
- Background worker (django-rq) parses the file, infers per-column types, updates `status` to `ready` or `failed`
- Acceptance criteria:
  - [ ] `POST /datasets/` returns within ~200ms regardless of file size (excluding upload transfer time itself)
  - [ ] `GET /datasets/:id/` reflects current status (`pending` → `processing` → `ready`/`failed`) accurately at any poll
  - [ ] A malformed or empty CSV results in `status: failed` with a human-readable reason, not a silent hang or 500 error

**Type inference**
- Each column classified as `numeric`, `date`, `categorical`, or `text`
- Acceptance criteria:
  - [ ] A column of clean integers/floats is classified `numeric`
  - [ ] A column of ISO-format or common date strings is classified `date`
  - [ ] A column with low cardinality relative to row count (e.g., <20 distinct values) is classified `categorical`
  - [ ] A column that doesn't fit the above is classified `text` and excluded from chart-axis suggestions
  - [ ] Missing/blank cells in an otherwise-numeric column don't force the whole column to `text`

**Dashboard & Chart CRUD**
- Full CRUD for dashboards and charts, charts store layout (x/y/width/height) for free-form positioning
- Acceptance criteria:
  - [ ] Creating a chart requires valid `x_column`/`y_column` referencing the parent dataset's schema
  - [ ] Layout fields (`x`, `y`, `width`, `height`) persist independently of chart config, updatable via a lightweight PATCH (so drag/resize doesn't require resending the full chart config)
  - [ ] A user cannot create, read, update, or delete a dashboard/chart they don't own

**Public sharing**
- Share link generation, unguessable token, read-only public endpoint
- Acceptance criteria:
  - [ ] `ShareLink.token` is a UUID4 or equivalent-entropy random string, never sequential/predictable
  - [ ] `GET /public/dashboards/:token/` returns dashboard + charts + resolved chart data in one response, no auth required
  - [ ] A revoked token returns 404 (not a 403 revealing that a dashboard exists but access was denied — don't leak existence)
  - [ ] Regenerating a link invalidates the old token immediately

### Nice-to-Have (P1)

- **Chart-type suggestion** — given selected columns' inferred types, suggest a default chart type (line/bar/scatter/pie) rather than requiring the user to pick blind
- **Dataset preview endpoint** — sample rows returned alongside schema so the frontend can show real data while building charts, not just column names
- **Soft delete** on datasets/dashboards (recoverable for a grace period) rather than hard delete — minor polish, not core to the demo

### Future Considerations (P2)

- Multi-dataset dashboards (joining/comparing across uploads)
- Scheduled/recurring CSV ingestion (e.g., a dashboard that refreshes from a recurring data source)
- Per-viewer analytics on public share links (view counts) — would require the `ShareLink` model to track access events, worth keeping the model open to this even though not building it now

---

## Open Questions

- **Coercion vs. flagging for ambiguous columns** (e.g., 95% numeric with a few malformed cells) — force-coerce and drop bad rows, or flag back to the user as low-confidence? *Owner: you, before finalizing the type-inference logic.*
- **Layout units** — absolute pixels vs. relative/percentage coordinates for chart position, affecting how the public share page renders across screen sizes. *Owner: you, before building react-rnd integration, since it affects both frontend and the stored data shape.*
- **File size limit** — what's the max upload size worth supporting/testing for the demo? Not blocking to start building, but worth a stated number before you write "handles large files" anywhere in a portfolio writeup.

---

## Timeline Considerations

No external deadline — this is self-paced portfolio work. Suggested phasing (mirrors the build spec's milestone order):

1. Auth + async CSV upload/parsing (P0 ingestion requirements)
2. Dashboard/Chart CRUD, static layout (P0 CRUD requirements)
3. Layout persistence for drag/resize (P0 CRUD requirements, layout fields)
4. Chart-type suggestion (P1)
5. Public sharing (P0 sharing requirements)
6. Polish: dataset preview, soft delete (P1)
