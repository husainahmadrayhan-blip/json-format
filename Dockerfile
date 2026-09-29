FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY . ./
RUN npm ci --no-audit --no-fund
# GitHub web uploads may flatten src/ into repository root.
RUN mkdir -p src && for file in main.jsx style.css office-logic.js office-presets.json source-groups.js; do \
      if [ -f "$file" ] && [ ! -f "src/$file" ]; then mv "$file" src/; fi; \
      if [ ! -f "src/$file" ]; then echo "MISSING FILE: $file (GitHub root or src/). Upload all files from the ZIP." >&2; exit 1; fi; \
    done
RUN npm run build

FROM python:3.12-slim
ENV DEPLOY_MODE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=frontend /app/dist/ ./dist/
COPY *.py BDRIS_MASTER_GEO.json ./
USER nobody
CMD ["python", "-u", "server.py"]
