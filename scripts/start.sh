#!/usr/bin/env bash
#
# Start the full Clinical Knowledge Graph stack locally.
#
# What it does:
#   1. Kills anything on ports 3000, 8000 (UI, API).
#   2. Starts Neo4j (Docker) if not already running.
#   3. Loads constraints + seed data (idempotent).
#   4. Starts the API (FastAPI on :8000).
#   5. Starts the UI (Next.js on :3000).
#   6. Opens the Explore tab in your browser.
#
# Usage: ./scripts/start.sh
#   --no-seed     Skip seed loading (faster restart).
#   --no-browser  Don't open the browser.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEO4J_CONTAINER="ckg-neo4j"
NEO4J_PASSWORD="password123"
NEO4J_BOLT="bolt://localhost:7687"
API_PORT=8000
UI_PORT=3000

NO_SEED=false
NO_BROWSER=false
for arg in "$@"; do
  case "$arg" in
    --no-seed)    NO_SEED=true ;;
    --no-browser) NO_BROWSER=true ;;
  esac
done

# ── Helpers ────────────────────────────────────────────────────────

log()  { printf "\033[1;34m=> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m=> %s\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m=> %s\033[0m\n" "$*"; }

kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "Killing processes on port $port (PIDs: $pids)"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

wait_for() {
  local url=$1
  local label=$2
  local max_attempts=30
  local attempt=0
  while ! curl -sf "$url" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "ERROR: $label did not start within ${max_attempts}s" >&2
      exit 1
    fi
    sleep 1
  done
}

# ── 1. Stop existing services on our ports ─────────────────────────

log "Clearing ports $UI_PORT and $API_PORT..."
kill_port $UI_PORT
kill_port $API_PORT

# ── 2. Start Neo4j ────────────────────────────────────────────────

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${NEO4J_CONTAINER}$"; then
  ok "Neo4j already running ($NEO4J_CONTAINER)"
else
  # Check if container exists but is stopped.
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${NEO4J_CONTAINER}$"; then
    log "Starting stopped Neo4j container..."
    docker start "$NEO4J_CONTAINER"
  else
    log "Creating Neo4j container..."
    docker run -d \
      --name "$NEO4J_CONTAINER" \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH="neo4j/${NEO4J_PASSWORD}" \
      neo4j:5-community
  fi

  log "Waiting for Neo4j to be ready..."
  wait_for "http://localhost:7474" "Neo4j"
  ok "Neo4j is up"
fi

# ── 3. Load seed data ─────────────────────────────────────────────

if [ "$NO_SEED" = false ]; then
  log "Loading constraints..."
  docker exec -i "$NEO4J_CONTAINER" cypher-shell \
    -u neo4j -p "$NEO4J_PASSWORD" \
    < "$ROOT/graph/constraints.cypher"

  log "Loading statin seed..."
  docker exec -i "$NEO4J_CONTAINER" cypher-shell \
    -u neo4j -p "$NEO4J_PASSWORD" \
    < "$ROOT/graph/seeds/statins.cypher"

  ok "Seed data loaded"
else
  warn "Skipping seed (--no-seed)"
fi

# ── 4. Start API ──────────────────────────────────────────────────

log "Starting API on :$API_PORT..."
cd "$ROOT/api"
.venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 --port "$API_PORT" \
  --log-level warning \
  > /tmp/ckg-api.log 2>&1 &
API_PID=$!

wait_for "http://localhost:$API_PORT/healthz" "API"
ok "API is up (PID $API_PID, log: /tmp/ckg-api.log)"

# ── 5. Start UI ───────────────────────────────────────────────────

log "Starting UI on :$UI_PORT..."
cd "$ROOT/ui"
npm run dev > /tmp/ckg-ui.log 2>&1 &
UI_PID=$!

wait_for "http://localhost:$UI_PORT" "UI"
ok "UI is up (PID $UI_PID, log: /tmp/ckg-ui.log)"

# ── 6. Open browser ───────────────────────────────────────────────

if [ "$NO_BROWSER" = false ]; then
  log "Opening browser..."
  open "http://localhost:$UI_PORT/explore"
fi

# ── Summary ───────────────────────────────────────────────────────

echo ""
ok "All services running:"
echo "   Neo4j:  http://localhost:7474  (container: $NEO4J_CONTAINER)"
echo "   API:    http://localhost:$API_PORT  (PID $API_PID)"
echo "   UI:     http://localhost:$UI_PORT  (PID $UI_PID)"
echo ""
echo "   Explore: http://localhost:$UI_PORT/explore"
echo ""
echo "   Stop: kill $API_PID $UI_PID"
echo "   Logs: tail -f /tmp/ckg-api.log /tmp/ckg-ui.log"
