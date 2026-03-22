# Dashboard
## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Download & build frontend assets (one-time)
```bash
bash scripts/download_assets.sh
```
This downloads Lucide icons, Plus Jakarta Sans, JetBrains Mono, and builds the
Tailwind CSS bundle. Without this step the app will load but look unstyled.

### 3. Run locally
```bash
docker-compose up
```
Or without Docker:
```bash
flask --app personalhq db upgrade
flask --app personalhq run
```
