# Frontend Dockerfile -- Next.js 15 multi-stage build
# Stage 1: Install dependencies + build
# Stage 2: Production runtime with standalone output

# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app

# NEXT_PUBLIC_API_URL must be set at BUILD time (Next.js bakes it into client JS)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Copy package files first for layer caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Ensure public/ exists (may not exist in all projects)
RUN mkdir -p public

# Build Next.js (standalone output mode)
RUN npm run build

# ---- Stage 2: Production runtime ----
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone output from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Copy public/ (created/ensured in builder stage)
COPY --from=builder /app/public ./public

# Set ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -q --spider http://0.0.0.0:3000 || exit 1

CMD ["node", "server.js"]
