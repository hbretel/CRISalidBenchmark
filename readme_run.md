# Running CRISalid Benchmark with Docker

## Prerequisites

- Docker Desktop running.
- A `.env` file at the repo root (copy `.env.example` → `.env` and fill in `POSTGRES_PASSWORD` / `SECRET_KEY`). The OpenAlex API key is **not** set here — it's entered later via the in-app `/setup` wizard and stored in the database.

## Start the stack

```bash
docker compose up -d --build
```

This builds and starts four containers:

| Service    | URL                     | Purpose |
|------------|-------------------------|---------|
| `frontend` | http://localhost:3000   | Next.js UI |
| `backend`  | http://localhost:8000   | FastAPI (docs at `/docs`) |
| `db`       | localhost:5432           | PostgreSQL 16 |
| `adminer`  | http://localhost:8080   | DB admin UI (server: `db`, user: `crisalid`, password: from `.env`, database: `crisalid_benchmark`) |

On backend startup, Alembic migrations run automatically (see `app/main.py` lifespan hook) — no manual migration step needed.

## First run

1. Open http://localhost:3000 — the app's API returns 503/`/setup` redirects until an instance is configured, so you'll land on (or be redirected to) the `/setup` wizard.
2. Enter the institution's OpenAlex ID, obtain a free OpenAlex API key (openalex.org account → settings), and a contact email.
3. Once configured, the nightly OpenAlex sync and the manual Leiden XLSX import (`POST /api/v1/admin/sync/leiden`) become available.

## Useful commands

```bash
docker compose ps                 # container status
docker compose logs -f backend    # tail backend logs (migrations, sync jobs)
docker compose logs -f frontend
docker compose down               # stop (keeps volumes: postgres_data, leiden_uploads)
docker compose down -v            # stop AND wipe the database/uploads volumes
```

## Issues found and fixed to get this running

The project had never actually been built/run before this pass — four issues surfaced, all now fixed in the repo:

1. **`frontend/package-lock.json` was missing.** The frontend Dockerfile uses `npm ci`, which requires a lockfile (unlike `npm install`, it refuses to run without one). Fixed by running `npm install` once locally to generate `package-lock.json`, now committed alongside `package.json`.

2. **`backend/pyproject.toml` had an invalid build backend.** `build-backend = "setuptools.backends.legacy:build"` is not a real importable module — `pip install -e .` failed with `ModuleNotFoundError: No module named 'setuptools.backends'`. Fixed to the standard `setuptools.build_meta`.

3. **`frontend/next.config.ts` isn't supported by the pinned Next.js version.** `package.json` pins `next@^14.2.0`; TypeScript config files (`next.config.ts`) are only supported from Next.js 15 onward. Converted the file to `next.config.mjs` (same content, plain JS) rather than bumping Next's major version, since that would also require bumping React to 19 and wasn't asked for.

4. **`frontend/public/` directory didn't exist.** The frontend Dockerfile's final stage does `COPY --from=builder /app/public ./public`, which fails if the directory is entirely absent (as opposed to empty). Created `frontend/public/` with a `.gitkeep` placeholder so the directory exists in the build context.

After these four fixes, `docker compose build` and `docker compose up -d` both complete cleanly: all four containers report healthy/running, Alembic migrations apply on backend startup, `GET /health` returns `{"status":"ok"}`, and the frontend serves the app at port 3000.

### 5. `/setup` wizard: HTTP 500 on "Valider et continuer"

**Symptom**: submitting the OpenAlex ID/key/email form in the setup wizard returned an HTTP 500.

**Root cause**: `NEXT_PUBLIC_API_URL` is a Next.js "public" env var — it gets inlined into the **browser** bundle at **build time** (`next build`). `docker-compose.yml` only set it under the `frontend` service's `environment:` block, which only affects the **running container**, not the `docker build` step. So the client bundle was built with this var unset, and the frontend code (`lib/api.ts`) fell back to a relative API path (`/api/v1/...`), routed through the `rewrites()` proxy in `next.config.mjs`. That proxy resolves its destination from the same env var, but this time read at **server runtime inside the frontend container** — where it evaluates to `http://localhost:8000`. Inside that container, `localhost` refers to the frontend container itself (nothing listens on port 8000 there); the backend is only reachable via the Docker network as `http://backend:8000`. The proxied request got connection-refused, and Next.js turned that into a 500 returned to the browser.

Confirmed by testing from inside the frontend container: `http://localhost:8000/health` → connection refused, `http://backend:8000/health` → `{"status":"ok"}`.

**Fix**: pass `NEXT_PUBLIC_API_URL` as a Docker build **arg** (not just a runtime env var), so it's correctly baked into the browser bundle:
- `frontend/Dockerfile`: added `ARG NEXT_PUBLIC_API_URL` + `ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL` in the builder stage, before `npm run build`.
- `docker-compose.yml`: added `build.args.NEXT_PUBLIC_API_URL: http://localhost:8000` under the `frontend` service (kept the `environment:` entry too, as a harmless fallback for the rewrite proxy).

With this fix, the browser calls the backend directly at `http://localhost:8000` (the published host port), bypassing the Next.js rewrite proxy entirely — verified by checking the built client bundle now contains the literal string `http://localhost:8000`, and by re-running the validate call end-to-end.

### 6. Bonus fixes found while diagnosing #5

- **`geo.country_iso_alpha2` doesn't exist in the real OpenAlex API.** `backend/app/api/config.py` read country code from a nonexistent nested field, so `country_code` was always `null` in the setup wizard's validation response. The real field is a top-level `country_code` on the institution object. Fixed in all three places it was read.
- **The OpenAlex client retried permanent 4xx errors** (bad API key, unknown institution ID) with the same exponential backoff as transient failures, adding up to ~15s of pointless delay before surfacing an error that was never going to change on retry. `backend/app/services/openalex_client.py` now only retries rate limits, transport errors, and 5xx server errors — 4xx errors fail immediately.
