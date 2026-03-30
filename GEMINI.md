# OpenClaw Multi-Agent Monitor

A comprehensive monitoring platform for OpenClaw instances, agents, and sessions. This project follows a distributed architecture where collectors deployed on OpenClaw machines report data to a central monitor server.

## Project Overview

- **Architecture:** Distributed Collector-Server model.
- **Backend:** FastAPI (Python 3.10+) with SQLAlchemy (Async) and SQLite.
- **Frontend:** Vue 3 with TypeScript, Vite, Element Plus, and ECharts.
- **Collector:** Lightweight Python script that wraps the OpenClaw CLI to gather metrics.
- **Key Features:** Dashboard overview, instance health tracking, agent status monitoring, session/token usage analytics.

## Directory Structure

- `server/`: FastAPI backend application.
- `web/`: Vue 3 frontend application.
- `collector/`: Python collector script and configuration.
- `deploy/`: Systemd service files and deployment scripts.

## Building and Running

### Backend (`server/`)
1. **Install Dependencies:** `pip install -r requirements.txt`
2. **Initialize Database:** `python init_db.py` (creates tables and default user `monitor`).
3. **Run Server:** `python run.py` (starts on port 9200).
4. **Environment Variables:** See `server/config.py` for `DATABASE_URL`, `SECRET_KEY`, `COLLECTOR_API_KEY`, etc.

### Frontend (`web/`)
1. **Install Dependencies:** `npm install`
2. **Development Mode:** `npm run dev` (starts on port 3000, proxies `/api` to port 9200).
3. **Build for Production:** `npm run build` (outputs to `web/dist/`).

### Collector (`collector/`)
1. **Install Dependencies:** `pip install -r requirements.txt`
2. **Configuration:** Edit `config.yaml` with your `server_url` and `api_key`.
3. **Run Collector:** `python collector.py`

## Development Conventions

- **Backend:**
  - Uses `FastAPI` with `asynccontextmanager` for lifespan management.
  - Database models are defined in `server/models.py`.
  - API routes are organized in `server/routers/`.
  - Follows PEP 8 for Python code styling.
- **Frontend:**
  - Uses Vue 3 Composition API with `<script setup>`.
  - Element Plus for UI components and ECharts for data visualization.
  - i18n support is available in `web/src/i18n/`.
  - Axios for API communication, configured in `web/src/api/index.ts`.
- **Collector:**
  - Communicates with OpenClaw via CLI commands (e.g., `openclaw sessions --json`).
  - Reports status via a heartbeat API to the central server.
  - Persists `instance_id` in a local `.instance_id` file.

## Deployment

- **Systemd:** Service files provided in `deploy/` for both server and collector.
- **Nginx:** Example configuration provided in `README_EN.md` for serving the frontend and proxying API requests.
- **Updates:** `deploy/update-server.sh` can be used to pull latest changes and restart services on the server.
