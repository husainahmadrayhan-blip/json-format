FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY . .
# GitHub browser upload can flatten src/ into the repository root.
# Recreate src/ only when main.jsx is at the root.
RUN if [ ! -f src/main.jsx ]; then \
      mkdir -p src && \
      cp main.jsx style.css office-logic.js office-presets.json src/; \
    fi
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi
RUN npm run build

FROM python:3.12-slim
ENV DEPLOY_MODE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=frontend /app/dist/ ./dist/
COPY *.py BDRIS_MASTER_GEO.json ./
USER nobody
CMD ["python", "-u", "server.py"]
