# ---------- builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
# Install production deps into a virtual-env we'll copy to the runtime stage.
# Strip pip/setuptools and __pycache__ to shrink the layer.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir . \
    && /opt/venv/bin/pip uninstall -y pip setuptools \
    && find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true \
    && find /opt/venv -name '*.pyc' -delete 2>/dev/null; true \
    && find /opt/venv -name '*.pyi' -delete 2>/dev/null; true \
    && find /opt/venv -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null; true \
    && find /opt/venv -type d -name tests -exec rm -rf {} + 2>/dev/null; true \
    && find /opt/venv -type d -name test -exec rm -rf {} + 2>/dev/null; true

# ---------- runtime ----------
FROM python:3.12-slim

# Non-root user
RUN groupadd --gid 1000 ckg \
    && useradd --uid 1000 --gid ckg --shell /bin/sh ckg

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
COPY app/ app/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"]

USER ckg

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
