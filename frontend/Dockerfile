# ===== Multi-Agent Data Platform — Frontend Dockerfile =====
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies (with registry mirror for network resilience)
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

# Copy source code
COPY . .

# Build-time API URL — same-origin /api routes through Nginx
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# Prune devDependencies for smaller production image
RUN npm prune --production

# ── Production image ──
FROM node:22-alpine AS runner

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts
COPY --from=builder /app/tsconfig.json ./tsconfig.json

EXPOSE 3000

CMD ["npm", "start"]
