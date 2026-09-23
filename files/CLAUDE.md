# InsightHub

Portfolio rebuild of a coursework project — a CSV-to-dashboard web app. Fresh build, not a fork of last year's version. Solo project, backend-first.

## Stack

- **Backend:** Django REST Framework + PostgreSQL
- **Async jobs:** django-rq (Redis-backed) — used for CSV parsing, not Celery (overkill for this scope)
- **Frontend:** React (Vite, not Next.js — no SSR/routing-convention needs here)
- **Charts:** Recharts (client-rendered, real SVG — not canvas)
- **Drag/resize:** react-rnd (DOM-based absolute positioning) — explicitly NOT Konva. Konva renders to `<canvas>` and can't host interactive DOM/SVG chart components without rasterizing them, which kills chart interactivity. Don't suggest switching to Konva for the dashboard canvas.
- **QR codes:** generated client-side (e.g. `qrcode.react`), not server-side
- **Sharing:** random unguessable token (UUID4-equivalent), not sequential IDs. Public share pages are unauthenticated but token-gated, not fully public/indexable.

## Docs

- `docs/build-spec.md` — architecture, data model, API surface, milestone order
- `docs/backend-spec.md` — PRD-style spec: goals, non-goals, user stories, requirements (P0/P1/P2) with acceptance criteria
- `docs/engineering-tickets.md` — tickets broken out by milestone, scoped to hand to Claude Code one at a time

Read the relevant doc before starting work on a milestone. Don't re-derive architecture decisions already made in these docs — treat them as settled unless the user says otherwise.

## Key architectural decisions (don't relitigate these)

1. **CSV parsing is async, not request-blocking.** Upload endpoint saves the file and returns immediately with `status: pending`; a django-rq worker does the actual pandas parsing and updates status to `ready`/`failed`. Frontend polls `GET /datasets/:id/` and shows a simple "processing..." indicator — no progress bar, no websockets, that's out of scope.
2. **One dataset per dashboard for v1.** Multi-dataset dashboards are an explicit non-goal — don't build toward it.
3. **Public share endpoint returns 404 for invalid/revoked tokens, not 403.** Don't leak whether a dashboard exists behind a bad token.
4. **Layout is free-form (x/y/width/height), not grid-snapped.** This is a deliberate choice for the portfolio demo (a Figma-like feel), not an oversight — don't "simplify" it to `react-grid-layout` without asking first.

## Conventions

- Ownership checks belong on every endpoint that touches user-owned data (`Dataset`, `Dashboard`, `Chart`) — this was called out explicitly per-ticket in `engineering-tickets.md` rather than handled once globally, because it's easy to forget per-endpoint. Keep doing that.
- Acceptance criteria in the tickets/spec docs are the test cases. When implementing a ticket, check the work against its acceptance criteria explicitly before considering it done.
- Work one ticket at a time, in the milestone order given. Don't jump ahead to a later milestone's ticket even if it seems related.
- **Write code like a junior dev, at senior dev quality.** Explicit and boring over clever: no one-liners that pack multiple things together, no cute abstractions, no metaprogramming, obvious control flow (plain `if`/`for` over comprehension chains or reflection). But underneath that plainness, hold the senior-dev bar — correct edge-case handling, real test coverage, no skipped validation. A reviewer skimming the diff should never have to stop and figure out a trick; the code should read the way it was reasoned through, not the way it was compressed.

## Open questions (not yet decided — ask before assuming)

- Coercion vs. flagging strategy for ambiguous CSV columns (mostly-numeric with a few malformed cells)
- Layout units: absolute pixels vs. relative/percentage coordinates
- Max upload file size to support

## TDD Development Rules

### Core Principles
1. **Tests first**: Any new feature must have failing tests first
2. **Minimal implementation**: Only write code just enough to pass tests
3. **Continuous refactoring**: Consider refactoring after each green light

### Development Flow
1. Receive requirement → Write tests first
2. Confirm test fails (Red)
3. Write minimal code to pass tests (Green)
4. Refactor (keep Green)
5. Repeat

### Forbidden
- ❌ Don't write feature code without tests
- ❌ Don't delete or skip existing tests
- ❌ Don't write "tests later" code