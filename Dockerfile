FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json vite.config.js index.html ./
RUN npm install --no-audit --no-fund
COPY src/ ./src/
RUN npm run build

FROM python:3.12-slim
ENV DEPLOY_MODE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=frontend /app/dist/ ./dist/
COPY *.py BDRIS_MASTER_GEO.json ./
USER nobody
CMD ["python", "-u", "server.py"]
