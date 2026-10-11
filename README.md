# Deploy and Host Apache Superset with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/apache-superset-6-bi-dashboards?referralCode=20H68q)

Apache Superset is an open-source business intelligence platform for exploring data, writing SQL and building interactive dashboards. This community template runs Superset 6 on Railway with a Postgres metadata database, Redis caching, Celery workers for asynchronous queries and scheduled reports, and drivers for Postgres, MySQL and ClickHouse.

## About Hosting Apache Superset

A production Superset setup is more than the web app. Superset keeps its own metadata (users, charts, dashboards, saved queries) in a SQL database, uses Redis for caching and as the Celery broker, runs Celery workers for asynchronous SQL Lab queries, thumbnails and Alerts & Reports, and needs a single Celery beat process to trigger scheduled reports. This template wires those pieces together on Railway's private network. A one-shot init service migrates the metadata database, creates an admin with a generated password and sets up roles. The image extends the official lean image with database drivers and a configuration file driven entirely by Railway variables, and runs as a non-root user.

## Common Use Cases

- Self-service dashboards on top of your product's Postgres or MySQL database (use a read-only user).
- Fast analytics on event data stored in ClickHouse.
- SQL Lab as a shared, browser-based SQL editor with saved queries and access control.
- Scheduled email reports and threshold alerts for KPIs.
- Replacing per-seat BI licences with a self-hosted tool your team controls.

## Dependencies for Apache Superset Hosting

- Apache Superset 6 (`apache/superset` lean image plus drivers)
- PostgreSQL (metadata database)
- Redis (Celery broker, result backend and caches)
- Optional: an SMTP server for alerts and email reports

### Deployment Dependencies

- Superset documentation: https://superset.apache.org/docs/intro
- Docker builds and custom images: https://superset.apache.org/docs/installation/docker-builds
- Configuring Superset: https://superset.apache.org/docs/configuration/configuring-superset
- Connecting to databases: https://superset.apache.org/docs/databases
- Alerts and reports: https://superset.apache.org/docs/configuration/alerts-reports
- Releases: https://github.com/apache/superset/releases

### Implementation Details

| Service | Role | Public |
|---|---|---|
| `superset` | Web UI and REST API (gunicorn) | HTTPS domain |
| `superset-worker` | Celery worker: async SQL Lab, reports (with headless Chromium), thumbnails, cache warm-up | — |
| `superset-beat` | Celery beat: triggers scheduled reports and housekeeping | — |
| `superset-init` | One-shot: `superset db upgrade`, admin user, `superset init` | — |
| `Postgres` | Metadata database | — |
| `Redis` | Broker, results and caches | — |

All Superset services build the same image (`FROM apache/superset:6.1.0`) and differ only by start command.

**First login.** Wait for `superset-init` to finish, open the `superset` domain and sign in with `SUPERSET_ADMIN_USERNAME` (default `admin`) and the generated `SUPERSET_ADMIN_PASSWORD` from the `superset` service's Variables tab. Then add a data source under Settings → Database Connections, for example `postgresql://readonly:password@my-db.railway.internal:5432/app` for a database in the same Railway project, or `clickhousedb://user:password@clickhouse.railway.internal:8123/default`.

**Email reports.** Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_MAIL_FROM` to `superset` and `superset-worker`. Until then, reports run in dry-run mode. Outbound SMTP requires Railway's Pro plan; Slack notifications work on every plan.

**Scaling.** Add replicas to `superset` for more concurrent users and to `superset-worker` for more async queries and reports. Keep `superset-beat` at exactly one replica.

**Pinning and upgrades.** The Superset version is the `FROM` line in `services/superset/Dockerfile`; driver versions are pinned next to it. To upgrade, check Superset's `UPDATING.md`, change the tag and push. `superset-init` applies migrations and the other services wait for the new schema.

### Why Deploy Apache Superset on Railway?

Railway keeps Superset, its metadata database, Redis and workers on one private network next to the databases you want to analyse, so dashboards query your data without exposing it publicly. Scaling web and worker capacity is a replica setting, and you pay for actual usage rather than per-seat BI pricing.
