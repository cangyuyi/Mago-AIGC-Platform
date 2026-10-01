# Deps stage
FROM node:26-alpine AS deps
WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY apps/web/package.json ./apps/web/package.json

RUN corepack pnpm@9.15.0 install --frozen-lockfile

# Build stage
FROM node:26-alpine AS builder
WORKDIR /app

ARG API_GATEWAY_URL=http://api-gateway:8080
ARG AGENT_URL=http://agent:8000
# next.config.mjs resolves rewrites while building the standalone server.
ENV API_GATEWAY_URL=${API_GATEWAY_URL}
ENV AGENT_URL=${AGENT_URL}

RUN corepack enable

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages
COPY . .

RUN cd apps/web && corepack pnpm@9.15.0 build

# Runtime stage
FROM node:26-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Keep the standalone root intact: apps/web/node_modules contains relative
# links into the root node_modules/.pnpm directory.
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone/ ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "apps/web/server.js"]
