# Pick Helper, hosted: the Python app in hosted mode (accounts, community notes). Caddy in front does HTTPS and passes
# the visitor's address (docker-compose.yml). Data and logs live on volumes; see docs/hosting.md.
FROM python:3.13.15-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --home-dir /app app
WORKDIR /app

COPY *.py ./
COPY web/dist web/dist
# a starting point for the data volume, copied there on first start only (docker/entrypoint.sh)
COPY data/pickhelper.db seed/pickhelper.db
COPY data/reddit seed/reddit
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN mkdir data logs && chown app:app data logs && chmod 0755 /usr/local/bin/entrypoint

USER app
VOLUME ["/app/data", "/app/logs"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/meta', timeout=4)"]
ENTRYPOINT ["entrypoint"]
CMD ["python", "webapp.py", "--hosted", "--behind-proxy", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]
