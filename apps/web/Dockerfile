# syntax=docker/dockerfile:1
# Phoenix web — multi-stage build. Build context: repository root.

FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.15.1 --activate
WORKDIR /app

# --- dependencies (cached until the lockfile changes) ---
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json ./apps/web/
COPY packages/ ./packages/
RUN pnpm install --frozen-lockfile

# --- development (used by docker-compose.dev.yml) ---
FROM deps AS dev
COPY apps/web/ ./apps/web/
WORKDIR /app/apps/web
EXPOSE 23000
CMD ["pnpm", "exec", "next", "dev", "-p", "23000", "-H", "0.0.0.0"]

# --- production build ---
FROM deps AS build
COPY apps/web/ ./apps/web/
# NEXT_PUBLIC_* values are inlined at build time, not read at runtime
ARG NEXT_PUBLIC_API_URL=http://localhost:28000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
WORKDIR /app/apps/web
RUN mkdir -p public && pnpm build

# --- production runtime: standalone server only, non-root ---
FROM node:20-alpine AS runner
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=23000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S phoenix && adduser -S phoenix -G phoenix
COPY --from=build --chown=phoenix:phoenix /app/apps/web/.next/standalone ./
COPY --from=build --chown=phoenix:phoenix /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=phoenix:phoenix /app/apps/web/public ./apps/web/public
USER phoenix
EXPOSE 23000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD wget -qO- http://127.0.0.1:23000/ >/dev/null || exit 1
CMD ["node", "apps/web/server.js"]
