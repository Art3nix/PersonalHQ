#!/usr/bin/env bash
# Run once after cloning to self-host all external assets.
# Requires: curl, node/npm (for Tailwind build)
set -e

STATIC="personalhq/static"
mkdir -p "$STATIC/fonts" "$STATIC/js"

echo "── Downloading Lucide icons ──────────────────────────────────────────"
LUCIDE_VERSION="0.383.0"
curl -fsSL "https://unpkg.com/lucide@${LUCIDE_VERSION}/dist/umd/lucide.min.js" \
     -o "$STATIC/js/lucide.min.js"
echo "  ✓ lucide.min.js ($(du -h "$STATIC/js/lucide.min.js" | cut -f1))"

echo "── Downloading Chart.js ──────────────────────────────────────────────"
curl -fsSL "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" \
     -o "$STATIC/js/chart.min.js"
echo "  ✓ chart.min.js"

echo "── Downloading SortableJS ────────────────────────────────────────────"
curl -fsSL "https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js" \
     -o "$STATIC/js/sortable.min.js"
echo "  ✓ sortable.min.js"

echo "── Downloading Plus Jakarta Sans ─────────────────────────────────────"
# Variable font from the official GitHub release (stable URL, no version in path)
curl -fsSL "https://fonts.gstatic.com/s/plusjakartasans/v8/LDIoaomQNQcsA88c7O9yZ4KMCoOg4Ko20yw.woff2" \
     -o "$STATIC/fonts/PlusJakartaSans-VariableFont_wght.woff2"

# Fallback: if GitHub raw fails, try the Google Fonts CSS API to find current URL
if [ ! -s "$STATIC/fonts/PlusJakartaSans-VariableFont_wght.woff2" ]; then
  echo "  GitHub failed, trying Google Fonts API..."
  URL=$(curl -sA "Mozilla/5.0" \
    "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" \
    | grep -o 'https://fonts.gstatic.com[^)]*woff2' | head -1)
  [ -n "$URL" ] && curl -fsSL "$URL" -o "$STATIC/fonts/PlusJakartaSans-VariableFont_wght.woff2"
fi
echo "  ✓ PlusJakartaSans-VariableFont_wght.woff2 ($(du -h "$STATIC/fonts/PlusJakartaSans-VariableFont_wght.woff2" | cut -f1))"

echo "── Downloading JetBrains Mono ────────────────────────────────────────"
# Directly from JetBrains' official GitHub release (no version-embedded gstatic URL)
JBMONO_VERSION="2.304"
curl -fsSL "https://github.com/JetBrains/JetBrainsMono/raw/v${JBMONO_VERSION}/fonts/webfonts/JetBrainsMono-Regular.woff2" \
     -o "$STATIC/fonts/JetBrainsMono-Regular.woff2"

# Fallback: try the Google Fonts CSS API
if [ ! -s "$STATIC/fonts/JetBrainsMono-Regular.woff2" ]; then
  echo "  GitHub failed, trying Google Fonts API..."
  URL=$(curl -sA "Mozilla/5.0" \
    "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" \
    | grep -o 'https://fonts.gstatic.com[^)]*woff2' | head -1)
  [ -n "$URL" ] && curl -fsSL "$URL" -o "$STATIC/fonts/JetBrainsMono-Regular.woff2"
fi
echo "  ✓ JetBrainsMono-Regular.woff2 ($(du -h "$STATIC/fonts/JetBrainsMono-Regular.woff2" | cut -f1))"

echo "── Building Tailwind CSS ─────────────────────────────────────────────"
npm install
npm run build:css
echo "  ✓ tailwind.css ($(du -h "$STATIC/css/tailwind.css" | cut -f1))"

echo ""
echo "All assets ready. Restart your server."
