# ── Stage 1: Build CSS ────────────────────────────────────────────────────
FROM node:20-slim AS css-builder

WORKDIR /build

COPY package.json ./
RUN npm install

COPY tailwind.config.js ./
COPY personalhq/static/css/input.css personalhq/static/css/input.css
COPY personalhq/templates personalhq/templates

RUN npx tailwindcss \
      -i personalhq/static/css/input.css \
      -o personalhq/static/css/tailwind.css

# ── Stage 2: Python app ───────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY --from=css-builder /build/personalhq/static/css/tailwind.css \
                         personalhq/static/css/tailwind.css

EXPOSE 8000
