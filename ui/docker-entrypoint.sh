#!/bin/sh
set -e

# Runtime injection of API_BASE_URL into the pre-built Next.js client bundle.
# NEXT_PUBLIC_* vars are inlined at build time; this replaces the baked-in
# default with the value of API_BASE_URL supplied at `docker run` time.
if [ -n "$API_BASE_URL" ]; then
  find /app/.next -name '*.js' -exec sed -i "s|http://localhost:8000|${API_BASE_URL}|g" {} + 2>/dev/null || true
fi

exec "$@"
