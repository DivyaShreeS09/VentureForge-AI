# Security posture: no authentication (by design, for now)

This document describes a real, load-bearing limitation of the current system — it is not
aspirational, and it is not solved by anything in this codebase yet. Read this before deploying
anywhere beyond a local/trusted development environment.

## Current state

**VentureForge AI has no user accounts, sessions, login flow, or authorization system anywhere in
the codebase.** There is no `users` table, no auth middleware, no API key/token check on any
route, and no concept of "who owns this analysis."

Concretely:

- Every `startup` and `analysis` row is a bare record identified only by a randomly generated UUID
  primary key (`gen_random_uuid()` — see `backend/alembic/versions/0001_initial.py`).
- Every read endpoint (`GET /api/v1/analyses/{id}`, `GET /api/v1/startups/{id}`) returns the full
  record to anyone who supplies that UUID — there is no check that the caller "owns" it, because
  there is no notion of ownership to check.
- Every **write** endpoint that mutates an existing analysis is exactly as open:
  - `POST /api/v1/analyses/{id}/industry-correction` (Phase C — founder-submitted venture-
    positioning correction)
  - `PATCH /api/v1/analyses/{id}/revenue-assumptions` (production-hardening phase — founder-
    submitted revenue-assumption edits)

  Both endpoints rely entirely on the caller already knowing the analysis's UUID. Knowing the UUID
  is treated as sufficient "authorization" to correct or edit that analysis. This is
  **security-by-obscurity of an unguessable identifier**, not real authorization — anyone who
  obtains or guesses a UUID (e.g. via a shared link, a leaked log line, or a browser history) can
  read and modify that analysis.

## Why this is acceptable for now, and where the line is

This is a reasonable tradeoff for the system's current scope: a single-user or trusted-cohort
tool with no multi-tenant data separation requirement. It is explicitly **not** acceptable once
either of these becomes true:

- The app is deployed somewhere a UUID could realistically leak or be enumerated by someone
  outside the intended user base.
- Two different people's startups/analyses need to be kept private from each other.

## What a production deployment must add before either condition applies

1. **Authentication** — a real login/session or token mechanism (e.g. OAuth, a session cookie, a
   signed JWT) identifying *who* is making a request.
2. **Per-analysis ownership** — a `user_id` (or `owner_id`) column on `startups` (and transitively
   on `analyses`, via the existing `startup_id` foreign key), populated at creation time.
3. **Authorization checks on every read and write route** — `GET /analyses/{id}`,
   `POST /analyses/{id}/industry-correction`, and `PATCH /analyses/{id}/revenue-assumptions` must
   all verify `analysis.startup.owner_id == current_user.id` (or equivalent) before proceeding,
   returning 403/404 (prefer 404, to avoid confirming an ID exists to someone who doesn't own it)
   otherwise.
4. **Audit trails already exist and should carry the identity forward** — both
   `positioning_correction_history` and `revenue_assumptions_history` already record *what*
   changed and *when* (see `backend/app/models/analysis.py`); once authentication exists, each
   history entry should also record *who* made the change (a `corrected_by`/`edited_by` user id),
   which is a trivial addition once a `current_user` exists to attribute it to.

## Scope note

Per the explicit direction for this phase, authentication itself is **not** being added now — this
document exists so the gap is visible and intentional rather than silently assumed away, and so
the exact endpoints affected (industry-correction, revenue-assumptions) are named precisely for
whoever picks up the authentication work next.
