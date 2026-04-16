#!/bin/sh
set -e

# Wait for Neo4j to become reachable before starting the app.
# NEO4J_URI defaults to bolt://localhost:7687 — extract host:port.
NEO4J_HOST="${NEO4J_URI#bolt://}"
NEO4J_HOST="${NEO4J_HOST#neo4j://}"
NEO4J_HOST_ONLY="${NEO4J_HOST%%:*}"
NEO4J_PORT="${NEO4J_HOST##*:}"
NEO4J_PORT="${NEO4J_PORT:-7687}"

MAX_WAIT=30
elapsed=0

echo "Waiting for Neo4j at ${NEO4J_HOST_ONLY}:${NEO4J_PORT} ..."
while ! python -c "
import socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('${NEO4J_HOST_ONLY}', ${NEO4J_PORT}))
    s.close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    elapsed=$((elapsed + 1))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "Neo4j not reachable after ${MAX_WAIT}s — starting anyway."
        break
    fi
    sleep 1
done

exec "$@"
