FROM node:24.17.0-bookworm-slim@sha256:862263c612aa437e3037674b85419622a9d93bff80aa1eee5398dfe686375532 AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm install -g npm@11.18.0 --no-audit --no-fund \
    && test "$(node --version)" = "v24.17.0" \
    && test "$(npm --version)" = "11.18.0" \
    && npm ci --ignore-scripts --no-audit --no-fund

FROM deps AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
COPY apps/web .
RUN npm run build

FROM node:24.17.0-bookworm-slim@sha256:862263c612aa437e3037674b85419622a9d93bff80aa1eee5398dfe686375532 AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
