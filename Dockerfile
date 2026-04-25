# ── Stage 1: Build CSS & Fetch Assets ─────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /build

# 1. Install curl
RUN apt-get update && apt-get install -y curl

# 2. Setup Node
COPY package.json ./
RUN npm install

# 3. Create static directories
RUN mkdir -p personalhq/static/js personalhq/static/fonts

# 4. Download missing assets manually so we don't get 404s!
RUN curl -fsSL "https://unpkg.com/lucide@0.383.0/dist/umd/lucide.min.js" -o personalhq/static/js/lucide.min.js
RUN curl -fsSL "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" -o personalhq/static/js/chart.min.js
RUN curl -fsSL "https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js" -o personalhq/static/js/sortable.min.js
RUN curl -fsSL "https://fonts.gstatic.com/s/plusjakartasans/v8/LDIoaomQNQcsA88c7O9yZ4KMCoOg4Ko20yw.woff2" -o personalhq/static/fonts/PlusJakartaSans-VariableFont_wght.woff2

# 5. Copy the rest of your UI files
COPY tailwind.config.js ./
COPY personalhq/static/css/input.css personalhq/static/css/input.css
COPY personalhq/templates personalhq/templates
COPY personalhq/static/js personalhq/static/js

# 6. Explicit npx command (without --minify to prevent freezing)
RUN npx tailwindcss \
      -i personalhq/static/css/input.css \
      -o personalhq/static/css/tailwind.css

# ── Stage 2: Python app ───────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy everything we generated in Stage 1 into the final image
COPY --from=builder /build/personalhq/static/css/tailwind.css personalhq/static/css/tailwind.css
COPY --from=builder /build/personalhq/static/js/lucide.min.js personalhq/static/js/lucide.min.js
COPY --from=builder /build/personalhq/static/js/chart.min.js personalhq/static/js/chart.min.js
COPY --from=builder /build/personalhq/static/js/sortable.min.js personalhq/static/js/sortable.min.js
COPY --from=builder /build/personalhq/static/fonts personalhq/static/fonts

EXPOSE 8000