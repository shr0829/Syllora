FROM node:22-alpine AS frontend-builder

WORKDIR /app/apps/frontend

COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY apps/frontend ./
RUN npm run build


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/backend ./apps/backend
COPY content ./content
COPY config ./config
COPY README.md CHANGELOG.md ./
COPY --from=frontend-builder /app/apps/frontend/dist ./apps/frontend/dist

RUN mkdir -p /app/data/plans

EXPOSE 8000

CMD ["sh", "-c", "python apps/backend/main.py serve --host ${HOST:-0.0.0.0} --port ${PORT:-8000}"]
