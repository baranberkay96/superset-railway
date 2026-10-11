# Apache Superset 6 BI Dashboards — composer spec

| Field | Value |
|---|---|
| Listing name | **Apache Superset 6 BI Dashboards** (version label `6` = Superset major; Superset tags releases without a `v`, e.g. `6.1.0`) |
| Description | Explore data and build dashboards on any SQL database. Async workers and cache. (79 chars, unchanged — see note under Open questions) |
| Category | Analytics |
| Tags | superset, bi, dashboards, analytics, sql, data-visualization |
| Base market template | `superset` ("Apache Superset \| Open Source Tableau Alternative": web + worker + beat + Redis + Postgres). Kept its service split; replaced `:latest`, root user, base64 config and dev bootstrap scripts. Also reviewed `S7TBaH` (ju-li, most deployed, single container) and `c0hqeB` (leonardochappuis, default admin/admin). Both source repos have no license → nothing copied. |
| Upstream checked | Apache Superset `6.1.0` (2026-05-13, latest stable): `Dockerfile` (lean target), `docker/entrypoints/run-server.sh`, `docker/docker-init.sh`, `docker/docker-bootstrap.sh`, `docker/pythonpath_dev/superset_config.py`, `superset/config.py`, `pyproject.toml` extras, docs `installation/docker-builds.mdx`. Pinned 2026-10-10. |

## Architecture

```
 users ──HTTPS──► superset (gunicorn :8088, UI + API)
                     │         ▲
                     │         │ headless Chromium loads dashboards (private :8088)
                     ▼         │
 superset-beat ──► Redis ──► superset-worker ──► SMTP (optional)
 (schedules)      (broker, results, caches, rate limits)
 all ──► Postgres (metadata)        superset-init: db upgrade → create-admin → superset init (one-shot)
 superset / worker ──► your data sources (Postgres, MySQL, ClickHouse, … over private network or internet)
```

## Services

All Superset services build one image from `services/superset` (`FROM apache/superset:6.1.0` + drivers + `superset_config.py` + launcher).

| Service | Start command | Public | Healthcheck | Volume | Restart | Replicas |
|---|---|---|---|---|---|---|
| `superset-init` | `/usr/local/bin/superset-railway init` | — | — (one-shot, exits 0) | — | ON_FAILURE ×5 | 1 |
| `superset` | `/usr/local/bin/superset-railway web` | domain → 8088 | `/health`, 900 s | — | ON_FAILURE ×10 | 1+ |
| `superset-worker` | `/usr/local/bin/superset-railway worker` | — | — | — | ON_FAILURE ×10 | 1+ |
| `superset-beat` | `/usr/local/bin/superset-railway beat` | — | — | — | ON_FAILURE ×10 | **exactly 1** |
| `Postgres` | `ghcr.io/railwayapp-templates/postgres-ssl:18` (from `_railway-base`) | — | — | `/var/lib/postgresql/data` | ON_FAILURE | 1 |
| `Redis` | `redis:8.2` (from `_railway-base`) | — | — | `/data` | ON_FAILURE | 1 |

Source for the four Superset services: repo `baranberkay96/superset-railway`, root directory `/services/superset`.

## Variables

**`superset` (owner of shared values)**

| Variable | Default | Notes |
|---|---|---|
| `SUPERSET_SECRET_KEY` | `${{secret(64, alnum)}}` | Flask `SECRET_KEY`; encrypts saved database passwords. Referenced by the other services. Do not rotate without `superset re-encrypt-secrets`. |
| `SUPERSET_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Metadata DB. |
| `SUPERSET_REDIS_URL` | `${{Redis.REDIS_URL}}` | Config derives DB 0 broker, 1 Celery results, 2–6 caches, 7 SQL Lab results, 8 rate limits. |
| `SUPERSET_ENV` | `production` | |
| `PORT`, `SUPERSET_PORT` | `8088` | |
| `SERVER_WORKER_AMOUNT` / `SERVER_THREADS_AMOUNT` | `2` / `20` | gunicorn (gthread). |
| `GUNICORN_TIMEOUT`, `SUPERSET_WEBSERVER_TIMEOUT` | `120` | |
| `SUPERSET_PUBLIC_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}/` | Links in reports. |
| `SUPERSET_ADMIN_USERNAME` / `SUPERSET_ADMIN_PASSWORD` / `SUPERSET_ADMIN_EMAIL` | `admin` / `${{secret(24)}}` / `admin@example.com` | Used by `superset-init`. |

**`superset-init`**: `SUPERSET_DATABASE_URL`, `SUPERSET_REDIS_URL`, `SUPERSET_ENV`, `SUPERSET_SECRET_KEY=${{superset.SUPERSET_SECRET_KEY}}`, admin variables referenced from `superset`.

**`superset-worker`**: common variables plus `SUPERSET_INSTALL_BROWSER=true` (build ARG → Playwright + Chromium only in this image), `SUPERSET_CELERY_CONCURRENCY=4`, `SUPERSET_WEBDRIVER_BASEURL=http://${{superset.RAILWAY_PRIVATE_DOMAIN}}:8088/`, `SUPERSET_PUBLIC_URL=${{superset.SUPERSET_PUBLIC_URL}}`, `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=120`.

**`superset-beat`**: common variables only.

**Optional (add to `superset` and `superset-worker`)**: `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_MAIL_FROM`, `SMTP_STARTTLS` (true), `SMTP_SSL` (false). Without `SMTP_HOST`, alerts/reports run in dry-run mode (logged, not sent). Railway allows outbound SMTP only on the **Pro** plan; on Hobby use an email provider that offers an SMTP endpoint on a non-blocked path, or Slack/webhook notifications instead. `SUPERSET_THUMBNAILS=true` enables dashboard thumbnails; `SUPERSET_ALERT_REPORTS=false` disables Alerts & Reports.

**Baked into the image**: `SUPERSET_BIND_ADDRESS=[::]` (gunicorn dual-stack bind), config at `/app/pythonpath/superset_config.py` (`ENABLE_PROXY_FIX`, secure session cookie, Redis caches, Celery beat schedule, `ALERT_REPORTS` + `PLAYWRIGHT_REPORTS_AND_THUMBNAILS` feature flags).

## Database drivers included

| Source | Package | SQLAlchemy URI example |
|---|---|---|
| PostgreSQL | `psycopg2-binary==2.9.9` | `postgresql://user:pass@postgres.railway.internal:5432/db` |
| MySQL / MariaDB | `mysqlclient==2.2.8` | `mysql://user:pass@mysql.railway.internal:3306/db` |
| ClickHouse | `clickhouse-connect==0.15.1` | `clickhousedb://user:pass@clickhouse.railway.internal:8123/default` |

More drivers (BigQuery, Snowflake, Trino, MSSQL, …): add the package to the `pip-install.sh` line in `services/superset/Dockerfile` (see the Superset "Connecting to Databases" docs). Prefer a read-only database user for each source; do not point Superset at its own metadata database.

## Composer steps (Railway dashboard)

1. Add `Postgres` and `Redis` from `_railway-base/` (keep the names).
2. Create `superset` from GitHub repo `baranberkay96/superset-railway`, root `/services/superset`, start command `/usr/local/bin/superset-railway web`; paste variables; generate domain → 8088; healthcheck `/health`, timeout 900.
3. Duplicate into `superset-init`, `superset-worker`, `superset-beat`; set start commands; replace owned values with `${{superset.*}}` references; remove domains; set `superset-init` restart ON_FAILURE ×5; add `SUPERSET_INSTALL_BROWSER=true` on the worker only.
4. Deploy. `superset-init` migrates and creates the admin; the other roles wait for the schema (`superset db current` reports `(head)`).

## Improvements over market templates

| Area | Market templates | This template |
|---|---|---|
| Version | `apache/superset:latest` (`superset`), unpinned repos | `apache/superset:6.1.0` + pinned drivers |
| Drivers | Postgres only, installed at every boot via dev bootstrap script (`DATABASE_DIALECT`) | Postgres, MySQL and ClickHouse drivers baked in at build |
| Runs as | root (`RAILWAY_RUN_UID=0`) | Image's non-root `superset` user |
| Config | base64 blob in a variable | Readable `superset_config.py` in the repo, all values from variables |
| Init | Migrations + admin on every web start; `c0hqeB` ships admin/admin | One-shot `superset-init`, generated admin password, idempotent |
| Caching | Single Redis cache | Separate Redis DBs for metadata, chart data, filter state, explore state, thumbnails, SQL Lab async results, rate limiting |
| Alerts & Reports | Not configured | Feature flag on, Celery beat schedule, Chromium in the worker image only, private-network webdriver URL, SMTP optional with dry-run fallback |
| Proxy/HTTPS | not set | `ENABLE_PROXY_FIX`, secure cookies, dual-stack bind |

## Resource profile and cost (Railway: RAM $10/GB-mo, vCPU $20/mo, volume $0.15/GB-mo)

| Service | Idle RAM | Typical RAM | Idle CPU | Typical CPU |
|---|---|---|---|---|
| superset (2 gunicorn workers) | 0.6 GB | 1.0–1.5 GB | 0.02 | 0.2–0.5 |
| superset-worker (4 procs, Chromium on demand) | 0.6 GB | 1.0–2.0 GB | 0.02 | 0.2–0.5 |
| superset-beat | 0.15 GB | 0.15 GB | 0.01 | 0.01 |
| superset-init | 0 (exits) | 0 | 0 | 0 |
| Postgres | 0.1 GB | 0.2 GB | 0.01 | 0.05 |
| Redis | 0.02 GB | 0.1 GB | 0 | 0.02 |
| **Total** | **~1.5 GB** | **~2.5–4 GB** | **~0.06 vCPU** | **~0.5–1.1 vCPU** |

Estimated monthly cost: **idle ≈ $17**; **typical team (dashboards used daily, a few scheduled reports) ≈ $40–60**; heavy SQL Lab / many reports ≈ $80+. Minimum plan: **Hobby** (worker image with Chromium and two gunicorn workers exceed Trial limits). Pro for >2 web replicas or large reports.

## Scaling

- Web: raise `superset` replicas (stateless; sessions are cookie-based, caches in Redis) or `SERVER_WORKER_AMOUNT`.
- Async queries / reports: raise `superset-worker` replicas or `SUPERSET_CELERY_CONCURRENCY`.
- Keep `superset-beat` at one replica (duplicate beats send duplicate reports).

## Pinning and upgrades

Pinned 2026-10-10: `apache/superset:6.1.0`, `psycopg2-binary 2.9.9`, `mysqlclient 2.2.8`, `clickhouse-connect 0.15.1`, `playwright 1.63.0`, `postgres-ssl:18`, `redis:8.2`. Upgrade: read `UPDATING.md` for the target release, change the `FROM` tag (and driver pins if extras changed), push; `superset-init` runs `superset db upgrade` + `superset init`, the others wait for the new schema head.

## Verification checklist

- [ ] `superset-init` logs: `db upgrade` done, admin created (or "already exists" on redeploy), `superset init` done, exit 0.
- [ ] `superset` healthy at `/health`; login with `SUPERSET_ADMIN_USERNAME` / `SUPERSET_ADMIN_PASSWORD`.
- [ ] Settings → Database Connections: connect a Postgres, a MySQL and a ClickHouse source (drivers listed in the dialog).
- [ ] SQL Lab: enable "Asynchronous query execution" on a database, run a query → executed by `superset-worker`, results returned.
- [ ] Create a chart and dashboard; reload → served from cache (Redis keys `superset_data_*`).
- [ ] Alerts & Reports: create a report with a dashboard screenshot; with SMTP set it is emailed, without SMTP the worker logs a dry-run with the screenshot step succeeding.
- [ ] Redeploy all services: dashboards, users and saved connections persist.

## Open questions

- Not deployed end-to-end here. Points to check on first deploy: `mysqlclient` build in the lean image (uses Superset's own `pip-install.sh --requires-build-essential`), Playwright `install-deps` on the trixie base, and that Railway passes `SUPERSET_INSTALL_BROWSER` as build ARG to the worker only.
- Listing copy says "on any SQL database": Superset supports any SQLAlchemy dialect, but this template ships three drivers; others need one line in the Dockerfile (documented). Wording kept; consider "on Postgres, MySQL, ClickHouse and more" if reviewers object.
- Building one Dockerfile four times (one per service) lengthens the first deploy; Railway caches layers per service afterwards.

## Deploy test findings (2026-10-11)

The web service waited for superset-init's migration and hit its healthcheck window before init (built later) finished. Fix: migration moved to a `migrate` role run as the web service's pre-deploy command; init now waits for the schema and only creates the admin and runs `superset init` (Alembic has no lock, so only one place migrates).
