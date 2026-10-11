# Apache Superset for Railway: official lean image + metadata/DB drivers + config.
# One image for all roles (web, worker, beat, init); the start command picks the role.
FROM apache/superset:6.1.0

USER root
# Make uv target the image's virtualenv explicitly.
ENV VIRTUAL_ENV=/app/.venv

# Database drivers (versions inside Superset 6.1.0's own extras ranges):
#   psycopg2-binary   Postgres (metadata DB and Postgres sources)
#   mysqlclient       MySQL / MariaDB sources (mysql:// URIs)
#   clickhouse-connect ClickHouse sources (clickhousedb:// URIs)
RUN /app/docker/apt-install.sh default-libmysqlclient-dev pkg-config \
 && /app/docker/pip-install.sh --requires-build-essential --no-cache \
      psycopg2-binary==2.9.9 \
      mysqlclient==2.2.8 \
      clickhouse-connect==0.15.1

# Headless Chromium for Alerts & Reports screenshots. Only the worker needs it:
# set the service variable SUPERSET_INSTALL_BROWSER=true on that service
# (Railway passes service variables to matching build ARGs).
ARG SUPERSET_INSTALL_BROWSER=false
RUN if [ "${SUPERSET_INSTALL_BROWSER}" = "true" ]; then \
      uv pip install --no-cache-dir playwright==1.63.0 \
      && playwright install-deps chromium \
      && playwright install chromium \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "Skipping headless browser (SUPERSET_INSTALL_BROWSER=${SUPERSET_INSTALL_BROWSER})"; \
    fi

COPY --chown=superset:superset superset_config.py /app/pythonpath/superset_config.py
COPY --chmod=755 superset-railway /usr/local/bin/superset-railway

USER superset

# Dual-stack bind for gunicorn (IPv4 + IPv6 private network); see run-server.sh.
ENV SUPERSET_BIND_ADDRESS="[::]"

CMD ["/usr/local/bin/superset-railway", "web"]
