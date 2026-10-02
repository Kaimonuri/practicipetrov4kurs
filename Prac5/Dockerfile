# syntax=docker/dockerfile:1

FROM node:24-alpine AS dependencies
WORKDIR /app

# Зависимости устанавливаются отдельным слоем для повторного использования кеша.
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --prod --frozen-lockfile

FROM alpine:3.22 AS production
ENV NODE_ENV=production \
    PORT=3000 \
    DB_PATH=/app/data/dev.db

COPY --from=dependencies /usr/local/bin/node /usr/local/bin/node
RUN apk add --no-cache libstdc++ \
    && addgroup -S app \
    && adduser -S -G app app \
    && mkdir -p /app/data /app/public/uploads \
    && chown -R app:app /app
WORKDIR /app

COPY --from=dependencies --chown=app:app /app/node_modules ./node_modules
COPY --chown=app:app package.json ./
COPY --chown=app:app server.js db.js views.js ./
COPY --chown=app:app pages ./pages
COPY --chown=app:app public ./public
COPY --chown=app:app dev.db ./seed/dev.db
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# sed защищает entrypoint от CRLF после редактирования проекта в Windows.
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

USER app
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:3000/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["node", "server.js"]
