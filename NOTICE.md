# NOTICE — Apache Superset template

This is a community template. It is not affiliated with or endorsed by the Apache Software Foundation. Apache Superset, Superset and the Superset logo are trademarks of the Apache Software Foundation.

## Upstream sources checked (2026-10-10)

| Source | Version / path | License | Use |
|---|---|---|---|
| apache/superset | `6.1.0`: `Dockerfile` (lean target, `/app/.venv`, `PYTHONPATH=/app/pythonpath`) | Apache-2.0 | Base image layout |
| apache/superset | `6.1.0`: `docker/entrypoints/run-server.sh`, `docker/pip-install.sh`, `docker/apt-install.sh` | Apache-2.0 | Used unmodified inside the image (gunicorn launch, package install helpers) |
| apache/superset | `6.1.0`: `docker/docker-init.sh`, `docker/docker-bootstrap.sh` | Apache-2.0 | Init sequence (db upgrade → create-admin → init) and Celery worker/beat commands, re-implemented in `superset-railway` |
| apache/superset | `6.1.0`: `docker/pythonpath_dev/superset_config.py`, `superset/config.py` | Apache-2.0 | Celery imports and beat schedule (`reports.scheduler`, `reports.prune_log`) follow the upstream example; the rest of `superset_config.py` was written for this template |
| apache/superset | `6.1.0`: `pyproject.toml` extras (`postgres`, `mysql`, `clickhouse`, `playwright`) | Apache-2.0 | Driver version ranges |
| Superset docs | `docs/admin_docs/installation/docker-builds.mdx` | Apache-2.0 | Recommended way to extend the lean image |
| Railway docs | Dockerfiles: build-time variables via `ARG` | — | `SUPERSET_INSTALL_BROWSER` build switch |

## Market templates and repos reviewed

| Code / repo | License | Use |
|---|---|---|
| `superset` (image-based, inline base64 config) | n/a | Service split (web/worker/beat) kept; implementation replaced |
| `S7TBaH` → github.com/ju-li/apache-superset-railway | none (all rights reserved) | Read only; nothing copied |
| `c0hqeB` → github.com/leonardochappuis/superset-railway-image | none (all rights reserved) | Read only; nothing copied |

## Railway base services

`Postgres` and `Redis` definitions are copied from `templates/_railway-base/postgres.json` and `redis.json`.

## Third-party packages installed at build time

`psycopg2-binary` (LGPL-3.0 with exceptions), `mysqlclient` (GPL-2.0), `clickhouse-connect` (Apache-2.0), `playwright` (Apache-2.0) and Chromium (BSD-style, via Playwright) — installed from PyPI / Playwright CDN, unmodified.
