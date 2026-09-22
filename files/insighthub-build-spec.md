# InsightHub — Build Spec

**Portfolio rebuild of the coursework project.** Fresh implementation, backend-first, free-form drag/resize dashboard builder.

**Stack:** Django REST Framework + PostgreSQL (backend) · React (Vite) + Recharts + react-rnd (frontend) · random-token share links · client-side QR generation

---

## 1. Data Model

### `Dataset`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `owner` | FK → User | |
| `name` | string | user-facing label, defaults to filename |
| `raw_file` | file | original CSV, stored as-is |
| `status` | enum | `pending` → `processing` → `ready` (or `failed`) — parsing happens in a background worker, not the request cycle |
| `schema` | JSON, nullable until `ready` | inferred column list: `[{name, type: numeric\|date\|categorical\|text}]` |
| `row_count` | int | for display/validation |
| `created_at` | datetime | |

### `Dashboard`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `owner` | FK → User | |
| `dataset` | FK → Dataset | one dataset per dashboard for v1 (simplifies a lot — revisit only if multi-dataset dashboards become a real need) |
| `title` | string | |
| `created_at` / `updated_at` | datetime | |

### `Chart`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `dashboard` | FK → Dashboard | |
| `chart_type` | enum | `line`, `bar`, `pie`, `scatter` |
| `x_column` / `y_column` | string | references `Dataset.schema` column names |
| `narrative` | text, nullable | optional descriptive text under the chart |
| `x` / `y` / `width` / `height` | float | free-form canvas position (px or relative units — decide based on whether you want responsive scaling; relative is safer for the public share view rendering on different screen sizes) |
| `z_index` | int | stacking order if charts ever overlap |

### `ShareLink`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `dashboard` | FK → Dashboard | |
| `token` | string, unique, indexed | UUID4 or nanoid, unguessable |
| `created_at` | datetime | |
| `revoked_at` | datetime, nullable | supports "regenerate link" — old token stops resolving |

---

## 2. API Endpoints (Django REST)

**Auth**
- `POST /auth/register/`, `POST /auth/login/` — or whatever your existing auth scaffold from last year provides

**Datasets**
- `POST /datasets/` — multipart upload, saves file, creates `Dataset(status='pending')`, enqueues background parse job, returns immediately with `{id, status}` (does not block on parsing — see §4a)
- `GET /datasets/:id/` — metadata + status; frontend polls this (~every 1-2s) while `status` is `pending`/`processing`, showing a "processing..." indicator, until it flips to `ready` (schema included once ready) or `failed`
- `GET /datasets/:id/preview/` — first N rows for the chart-builder UI to reference while picking columns
- `GET /datasets/:id/data/?x=col&y=col` — returns the actual data points needed to render a specific chart (avoids shipping the whole dataset to the frontend for every chart)

**Dashboards**
- `POST /dashboards/` — `{title, dataset_id}`
- `GET /dashboards/` — list owned dashboards
- `GET /dashboards/:id/` — full dashboard incl. nested charts + layout
- `PATCH /dashboards/:id/` — update title
- `DELETE /dashboards/:id/`

**Charts**
- `POST /dashboards/:id/charts/` — create chart `{chart_type, x_column, y_column, x, y, width, height}`
- `PATCH /charts/:id/` — update layout (position/size) or config — this is the endpoint react-rnd's `onDragStop`/`onResizeStop` calls
- `DELETE /charts/:id/`

**Sharing**
- `POST /dashboards/:id/share/` — creates (or returns existing active) `ShareLink`, returns token
- `POST /dashboards/:id/share/regenerate/` — revokes old token, issues new one
- `GET /public/dashboards/:token/` — unauthenticated, read-only. Returns dashboard + charts + layout + resolved chart data in one payload (avoid N+1 round trips for a page a cold visitor lands on via QR scan)

---

## 3. Frontend Structure (React + Vite)

- **Upload flow** → `Dataset` created, schema returned, redirect to dashboard builder
- **Dashboard builder**
  - Canvas area: charts rendered as `react-rnd` wrapped `<ChartWidget>` components, each containing a Recharts chart sized to its container
  - Sidebar/toolbar: "Add chart" → column picker (using inferred schema to suggest chart type — date+numeric → line, categorical+numeric → bar)
  - Layout changes debounced and PATCHed to `/charts/:id/` on drag/resize stop (don't fire on every pixel of movement)
- **Public share page** (`/share/:token`)
  - Same layout renderer as the builder, but `react-rnd` interactivity disabled — just absolutely-positioned divs at the saved coordinates
  - QR code for *this* page's own URL can be generated client-side (`qrcode.react`) and shown/downloadable from the owner's dashboard view, not the public page itself

---

## 4a. CSV parsing — background job, not request-blocking

Last year's version parsed synchronously in the request, which made the UI feel frozen on upload. Fix: move parsing off the request-response cycle entirely.

- Queue: **django-rq** (Redis-backed) — lighter setup than Celery, appropriate for this single-purpose task
- `POST /datasets/` returns instantly after saving the file and enqueuing the job
- Worker does the pandas parse (`pd.read_csv`, dtype + date heuristics) and updates `Dataset.status`/`schema` when done
- Frontend shows a simple "processing..." state while polling, no progress bar needed for v1
- Portfolio note: this is a good before/after story to mention in an interview — noticed sync parsing blocked the UI, fixed it with a background worker + status polling

---

## 4b. Chart-type suggestion logic (small feature, big demo payoff)

Simple lookup table, no ML needed:

| Column A type | Column B type | Suggested chart |
|---|---|---|
| date | numeric | line |
| categorical | numeric | bar |
| numeric | numeric | scatter |
| categorical | (count only) | pie |

Surface this as a default suggestion when the user picks two columns — they can override.

---

## 5. Milestones

1. **Auth + CSV upload + type inference**, parsed via a django-rq background job with status polling (not request-blocking) — spend real time here; messy headers, mixed-type columns, and missing values are what separate a portfolio piece from a toy demo
2. **Dashboard/Chart CRUD + static grid rendering** (no drag/resize yet — prove data flows end to end first)
3. **react-rnd integration** — drag/resize working, layout persisted
4. **Chart-type suggestion logic**
5. **Public share endpoint + QR generation + regenerate-link**
6. **Polish** — empty states, loading states, maybe CSV export of underlying data

---

## 6. Open decisions to revisit as you build

- Layout units: pixel-absolute vs. relative/percentage (affects how the public share page looks across screen sizes)
- Whether `Dashboard` stays one-dataset-per-dashboard or needs to support multiple datasets later
- Auth scaffold: reuse patterns from last year's build, or rebuild for practice
