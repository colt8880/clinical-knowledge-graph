# Build context: repo root (docker build -t ckg-ui -f ui/Dockerfile .)
# The Eval tab statically imports fixture JSON from /evals, so the build
# context must include the repo root.

# ---------- deps ----------
FROM node:20-alpine AS deps

WORKDIR /app
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci --ignore-scripts

# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules

# Copy UI source
COPY ui/ ./

# Copy fixture JSON files referenced by the Eval tab's static imports
COPY evals/fixtures/ ../evals/fixtures/

# Build with standalone output (set in next.config.mjs)
RUN npm run build

# ---------- runner ----------
FROM node:20-alpine

RUN addgroup --system --gid 1001 ckg \
    && adduser --system --uid 1001 --ingroup ckg ckg

WORKDIR /app

# Copy standalone server and static assets (owned by ckg so the
# entrypoint can sed-replace API_BASE_URL at runtime)
COPY --from=builder --chown=ckg:ckg /app/.next/standalone ./
COPY --from=builder --chown=ckg:ckg /app/.next/static ./.next/static

# Copy entrypoint for runtime API_BASE_URL injection
COPY ui/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1

USER ckg

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["node", "server.js"]
