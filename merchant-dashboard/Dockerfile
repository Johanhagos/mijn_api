# Next.js dashboard for Railway (standalone output). Build root = merchant-dashboard/.
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* must be present at build time: they are inlined into the client bundle.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_BUY_APIUSD_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_BUY_APIUSD_URL=$NEXT_PUBLIC_BUY_APIUSD_URL
ENV NODE_ENV=production
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
# Railway provides $PORT; Next's standalone server honours it.
EXPOSE 3000
CMD ["node", "server.js"]
