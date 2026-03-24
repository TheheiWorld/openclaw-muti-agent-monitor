# OpenClaw Multi-Agent Monitor

A multi-instance, multi-agent monitoring platform for OpenClaw. Track agent activity, session status, token usage, and system health across distributed OpenClaw instances.

## Architecture

```
                        ┌──────────────────────────────────────┐
                        │          Monitor Server              │
                        │  ┌────────────┐  ┌───────────────┐   │
    Browser ──────────► │  │  Frontend   │  │   Backend     │   │
                        │  │  Vue 3      │  │   FastAPI     │   │
                        │  │  :3000      │  │   :9200       │   │
                        │  └────────────┘  └───────┬───────┘   │
                        │                          │ SQLite     │
                        └──────────────────────────┼───────────┘
                                                   ▲
                                  Heartbeat API    │
                        ┌──────────────────────────┤
                        │              │           │
                   ┌────┴────┐   ┌────┴────┐  ┌───┴─────┐
                   │OpenClaw │   │OpenClaw │  │OpenClaw │
                   │Instance │   │Instance │  │Instance │
                   │+Collector│   │+Collector│  │+Collector│
                   └─────────┘   └─────────┘  └─────────┘
```

The project consists of three components:

| Component | Tech Stack | Description |
|-----------|------------|-------------|
| **web** | Vue 3 + TypeScript + Vite + Element Plus + ECharts | Frontend monitoring dashboard |
| **server** | FastAPI + SQLAlchemy + SQLite | Backend API service with data storage and authentication |
| **collector** | Python + Requests | Lightweight data collector deployed on each OpenClaw machine |

## Directory Structure

```
├── web/                    # Frontend
│   └── src/
│       ├── views/          # Pages (Dashboard, Instances, TokenStats, etc.)
│       ├── components/     # Shared components (StatusBadge, TokenChart)
│       ├── api/            # Axios API wrapper
│       ├── router/         # Route configuration
│       └── i18n/           # Internationalization (Chinese / English)
├── server/                 # Backend
│   ├── main.py             # FastAPI application entry point
│   ├── run.py              # Startup script
│   ├── config.py           # Configuration (environment variables)
│   ├── models.py           # Database models
│   ├── database.py         # Database connection
│   ├── auth.py             # JWT authentication
│   └── routers/            # API route modules
│       ├── dashboard.py
│       ├── instances.py
│       ├── agents.py
│       ├── sessions.py
│       ├── tokens.py
│       ├── collector.py
│       └── auth.py
└── collector/              # Collector
    ├── collector.py         # Main collector program
    ├── config.yaml          # Collector configuration
    └── requirements.txt     # Python dependencies
```

## Getting Started

### Prerequisites

- Node.js >= 18
- Python >= 3.10

### 1. Start the Backend

```bash
cd server
pip install -r requirements.txt

# Initialize the database (create tables + default user, password printed to console)
python init_db.py

# Start the server
python run.py
```

The server starts at `http://localhost:9200`. If you skip `init_db.py`, the database will be initialized automatically on first startup.

### 2. Start the Frontend

```bash
cd web
npm install
npm run dev
```

The dev server starts at `http://localhost:3000`. API requests are automatically proxied to the backend on port `9200`.

### 3. Deploy the Collector (on each OpenClaw machine)

```bash
cd collector
pip install -r requirements.txt
```

Edit `config.yaml`:

```yaml
server_url: "http://<monitor-server-ip>:9200"   # Monitor server address
api_key: "your-collector-api-key"                # API Key (must match server's COLLECTOR_API_KEY)
instance_name: "prod-01"                         # Unique instance name
collect_interval: 60                             # Collection interval (seconds)
openclaw_host: "127.0.0.1"                       # OpenClaw Gateway host
openclaw_port: 18789                             # OpenClaw Gateway port
openclaw_bin: "openclaw"                         # OpenClaw CLI binary path
```

Start the collector:

```bash
python collector.py
```

The collector periodically gathers agent lists, session info, and token usage from the local OpenClaw instance, then reports them to the monitor server via the heartbeat API.

## Backend Configuration

All settings are configured via environment variables with sensible defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///monitor.db` | Database connection string |
| `HEARTBEAT_TIMEOUT_SECONDS` | `180` | Seconds before an instance is marked offline |
| `STATUS_CHECK_INTERVAL` | `30` | Heartbeat status check interval (seconds) |
| `SERVER_PORT` | `9200` | Server port |
| `SECRET_KEY` | Auto-generated | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | JWT token expiry (hours) |
| `COLLECTOR_API_KEY` | Empty (no check) | API Key for collector heartbeat endpoint; collectors must include this key when set |

## API Endpoints

| Route | Description | Auth |
|-------|-------------|------|
| `POST /api/auth/login` | Login | No |
| `GET /api/auth/me` | Current user info | Yes |
| `POST /api/auth/change-password` | Change password | Yes |
| `GET /api/dashboard` | Dashboard overview data | Yes |
| `GET /api/instances` | List instances | Yes |
| `GET /api/instances/{id}` | Instance details (with agents and sessions) | Yes |
| `GET /api/agents` | List agents | Yes |
| `GET /api/agents/{id}/sessions` | Sessions for a specific agent | Yes |
| `GET /api/sessions` | List sessions (with filters) | Yes |
| `GET /api/tokens/summary` | Token usage summary | Yes |
| `GET /api/tokens/trend` | Token usage trend | Yes |
| `POST /api/collector/heartbeat` | Collector heartbeat report | API Key |
| `GET /healthz` | Health check | No |

## Deployment

### Build the Frontend for Production

```bash
cd web
npm run build
```

The build output is in `web/dist/`. Serve it with Nginx or any static file server.

### Nginx Configuration Example

```nginx
server {
    listen 80;
    server_name monitor.example.com;

    # Frontend static files
    location / {
        root /path/to/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://127.0.0.1:9200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check
    location /healthz {
        proxy_pass http://127.0.0.1:9200;
    }
}
```

### Backend Deployment (systemd)

#### 1. Prepare the Server

```bash
# Create a system user
sudo useradd -r -s /sbin/nologin openclaw-monitor

# Create the deployment directory
sudo mkdir -p /opt/openclaw-monitor
sudo chown openclaw-monitor:openclaw-monitor /opt/openclaw-monitor
```

#### 2. Deploy the Code

```bash
# Copy the project to the deployment directory
sudo cp -r server/ collector/ /opt/openclaw-monitor/
sudo chown -R openclaw-monitor:openclaw-monitor /opt/openclaw-monitor

# Create a Python virtual environment and install dependencies
sudo -u openclaw-monitor python3 -m venv /opt/openclaw-monitor/venv
sudo -u openclaw-monitor /opt/openclaw-monitor/venv/bin/pip install -r /opt/openclaw-monitor/server/requirements.txt
```

#### 3. Configure Environment Variables

```bash
# Create environment file from template
sudo cp deploy/env.example /opt/openclaw-monitor/.env

# Generate and fill in secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
COLLECTOR_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")

sudo tee /opt/openclaw-monitor/.env > /dev/null <<EOF
SECRET_KEY=${SECRET_KEY}
COLLECTOR_API_KEY=${COLLECTOR_API_KEY}
EOF

sudo chown openclaw-monitor:openclaw-monitor /opt/openclaw-monitor/.env
sudo chmod 600 /opt/openclaw-monitor/.env
```

#### 4. Initialize the Database

```bash
cd /opt/openclaw-monitor
sudo -u openclaw-monitor bash -c 'set -a; source .env; set +a; venv/bin/python -m server.init_db'
```

This creates all database tables and generates a default user `monitor` — the password is printed to the console. Save it securely.

> If you skip this step, the database will be initialized automatically on first service startup. The password will appear in the journalctl logs.

#### 5. Install and Start the systemd Service

```bash
# Install the service file
sudo cp deploy/openclaw-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable --now openclaw-monitor

# Check status
sudo systemctl status openclaw-monitor

# View logs
sudo journalctl -u openclaw-monitor -f
```

#### 6. Common Operations

```bash
sudo systemctl start openclaw-monitor     # Start
sudo systemctl stop openclaw-monitor      # Stop
sudo systemctl restart openclaw-monitor   # Restart
sudo systemctl status openclaw-monitor    # Status
sudo journalctl -u openclaw-monitor -n 100 --no-pager  # Last 100 log lines
```

### Collector Deployment (systemd)

On each OpenClaw instance machine:

#### 1. Deploy the Collector

```bash
# Create user and directory (reuse if already on the same machine as server)
sudo useradd -r -s /sbin/nologin openclaw-monitor 2>/dev/null || true
sudo mkdir -p /opt/openclaw-monitor
sudo cp -r collector/ /opt/openclaw-monitor/
sudo chown -R openclaw-monitor:openclaw-monitor /opt/openclaw-monitor

# Install dependencies (reuse venv if it already exists)
sudo -u openclaw-monitor python3 -m venv /opt/openclaw-monitor/venv 2>/dev/null || true
sudo -u openclaw-monitor /opt/openclaw-monitor/venv/bin/pip install -r /opt/openclaw-monitor/collector/requirements.txt
```

#### 2. Update Configuration

Edit `/opt/openclaw-monitor/collector/config.yaml`:

```yaml
server_url: "http://<monitor-server-ip>:9200"   # Point to the monitor server
api_key: "your-collector-api-key"                # Must match server's COLLECTOR_API_KEY
instance_name: "prod-01"                         # Unique identifier for this instance
collect_interval: 60
openclaw_host: "127.0.0.1"
openclaw_port: 18789
openclaw_bin: "openclaw"
```

#### 3. Install and Start the Service

```bash
sudo cp deploy/openclaw-collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-collector

# View logs
sudo journalctl -u openclaw-collector -f
```

## Database

Uses SQLite, auto-created on first run. Tables:

- **instances** — OpenClaw instance info and heartbeat status
- **agents** — Agent information
- **sessions** — Session records (token usage, cost, model info)
- **token_usage_hourly** — Hourly aggregated token usage statistics
- **users** — System users

## Features

- **Dashboard** — Instance count, agent count, token usage, alerts, 24h trend chart
- **Instance Management** — View online/offline status of all instances with drill-down details
- **Agent Monitoring** — View agent lists and running status per instance
- **Session Tracking** — Filter sessions by instance, agent, or channel; view token consumption details
- **Token Analytics** — Usage summary by instance/agent, with 24h/7d/30d trend charts
- **Internationalization** — Chinese and English UI
- **JWT Authentication** — Login-based access control for management endpoints
