# Frontend Dockerfile - Multi-stage build

# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Development command with hot reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage with nginx (security hardened)
FROM nginx:alpine AS production

# OCI Image Labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
LABEL org.opencontainers.image.title="CaeliCrawler Frontend"
LABEL org.opencontainers.image.description="Vue.js frontend for CaeliCrawler municipal data platform"
LABEL org.opencontainers.image.vendor="CaeliCrawler"
LABEL org.opencontainers.image.licenses="Proprietary"
LABEL org.opencontainers.image.source="https://github.com/caelichrawler/caelichrawler"
LABEL org.opencontainers.image.base.name="nginx:alpine"

# Create non-root user for security
RUN addgroup -g 1001 -S nginx-user && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-user nginx-user && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-user /var/run/nginx.pid

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ensure correct permissions
RUN chown -R nginx-user:nginx-user /usr/share/nginx/html

EXPOSE 80

# Switch to non-root user
USER nginx-user

CMD ["nginx", "-g", "daemon off;"]
