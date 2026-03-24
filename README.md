# OpenClaw Multi-Agent Monitor

OpenClaw 多实例、多智能体监控平台。用于跟踪分布式 OpenClaw 实例中的智能体活动、会话状态、Token 用量和系统健康状况。

## 项目架构

```
                        ┌──────────────────────────────────────┐
                        │          Monitor Server              │
                        │  ┌────────────┐  ┌───────────────┐   │
    浏览器 ───────────► │  │  Frontend   │  │   Backend     │   │
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
                   │ + 采集器 │   │ + 采集器 │  │ + 采集器 │
                   └─────────┘   └─────────┘  └─────────┘
```

项目由三个组件组成：

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| **web** | Vue 3 + TypeScript + Vite + Element Plus + ECharts | 前端监控面板 |
| **server** | FastAPI + SQLAlchemy + SQLite | 后端 API 服务，提供数据存储和认证 |
| **collector** | Python + Requests | 部署在每台 OpenClaw 机器上的数据采集器 |

## 目录结构

```
├── web/                    # 前端
│   └── src/
│       ├── views/          # 页面（Dashboard、Instances、TokenStats 等）
│       ├── components/     # 通用组件（StatusBadge、TokenChart）
│       ├── api/            # Axios API 封装
│       ├── router/         # 路由配置
│       └── i18n/           # 国际化（中文/英文）
├── server/                 # 后端
│   ├── main.py             # FastAPI 应用入口
│   ├── run.py              # 启动脚本
│   ├── config.py           # 配置（环境变量）
│   ├── models.py           # 数据库模型
│   ├── database.py         # 数据库连接
│   ├── auth.py             # JWT 认证
│   └── routers/            # API 路由模块
│       ├── dashboard.py
│       ├── instances.py
│       ├── agents.py
│       ├── sessions.py
│       ├── tokens.py
│       ├── collector.py
│       └── auth.py
└── collector/              # 采集器
    ├── collector.py         # 采集主程序
    ├── config.yaml          # 采集器配置
    └── requirements.txt     # Python 依赖
```

## 快速开始

### 前置条件

- Node.js >= 18
- Python >= 3.10

### 1. 启动后端服务

```bash
cd server
pip install -r requirements.txt

# 初始化数据库（创建表 + 生成默认用户，密码会打印在控制台）
python init_db.py

# 启动服务
python run.py
```

服务启动在 `http://localhost:9200`。如果跳过 `init_db.py`，首次启动时也会自动初始化。

### 2. 启动前端

```bash
cd web
npm install
npm run dev
```

开发服务器启动在 `http://localhost:3000`，API 请求自动代理到后端 `9200` 端口。

### 3. 部署采集器（每台 OpenClaw 机器）

```bash
cd collector
pip install -r requirements.txt
```

编辑 `config.yaml` 配置：

```yaml
server_url: "http://<monitor-server-ip>:9200"   # 监控服务端地址
api_key: "your-collector-api-key"                # API Key（需与服务端 COLLECTOR_API_KEY 一致）
instance_name: "prod-01"                         # 当前实例名称
collect_interval: 60                             # 采集间隔（秒）
openclaw_host: "127.0.0.1"                       # OpenClaw Gateway 地址
openclaw_port: 18789                             # OpenClaw Gateway 端口
openclaw_bin: "openclaw"                         # OpenClaw CLI 路径
```

启动采集器：

```bash
python collector.py
```

采集器会定期收集当前实例的智能体列表、会话信息和 Token 用量，并通过心跳接口上报到监控服务端。

## 后端配置

通过环境变量配置，均有默认值：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///monitor.db` | 数据库连接 |
| `HEARTBEAT_TIMEOUT_SECONDS` | `180` | 心跳超时时间（秒），超过则标记实例离线 |
| `STATUS_CHECK_INTERVAL` | `30` | 心跳状态检查间隔（秒） |
| `SERVER_PORT` | `9200` | 服务端口 |
| `SECRET_KEY` | 自动生成 | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Token 过期时间（小时） |
| `COLLECTOR_API_KEY` | 空（不校验） | Collector 心跳接口的 API Key，设置后采集器请求必须携带此 Key |

## API 接口

| 路由 | 说明 | 认证 |
|------|------|------|
| `POST /api/auth/login` | 登录 | 否 |
| `GET /api/auth/me` | 当前用户信息 | 是 |
| `POST /api/auth/change-password` | 修改密码 | 是 |
| `GET /api/dashboard` | 仪表盘概览数据 | 是 |
| `GET /api/instances` | 实例列表 | 是 |
| `GET /api/instances/{id}` | 实例详情（含智能体和会话） | 是 |
| `GET /api/agents` | 智能体列表 | 是 |
| `GET /api/agents/{id}/sessions` | 智能体的会话列表 | 是 |
| `GET /api/sessions` | 会话列表（支持筛选） | 是 |
| `GET /api/tokens/summary` | Token 用量汇总 | 是 |
| `GET /api/tokens/trend` | Token 用量趋势 | 是 |
| `POST /api/collector/heartbeat` | 采集器心跳上报 | API Key |
| `GET /healthz` | 健康检查 | 否 |

## 部署

### 生产环境构建前端

```bash
cd web
npm run build
```

构建产物在 `web/dist/` 目录，可通过 Nginx 等反向代理服务器托管静态文件。

### Nginx 参考配置

```nginx
server {
    listen 80;
    server_name monitor.example.com;

    # 前端静态文件
    location / {
        root /path/to/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:9200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 健康检查
    location /healthz {
        proxy_pass http://127.0.0.1:9200;
    }
}
```

### 后端服务部署（systemd）

#### 1. 准备服务器环境

```bash
# 创建系统用户
sudo useradd -r -s /sbin/nologin openclaw-monitor

# 创建部署目录
sudo mkdir -p /opt/openclaw-monitor
sudo chown openclaw-monitor:openclaw-monitor /opt/openclaw-monitor
```

#### 2. 部署代码

```bash
# 拷贝项目到部署目录
sudo cp -r server/ collector/ /opt/openclaw-monitor/
sudo chown -R openclaw-monitor:openclaw-monitor /opt/openclaw-monitor

# 创建 Python 虚拟环境并安装依赖
sudo -u openclaw-monitor python3 -m venv /opt/openclaw-monitor/venv
sudo -u openclaw-monitor /opt/openclaw-monitor/venv/bin/pip install -r /opt/openclaw-monitor/server/requirements.txt
```

#### 3. 配置环境变量

```bash
# 从模板创建环境变量文件
sudo cp deploy/env.example /opt/openclaw-monitor/.env

# 生成并填写密钥
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
COLLECTOR_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")

sudo tee /opt/openclaw-monitor/.env > /dev/null <<EOF
SECRET_KEY=${SECRET_KEY}
COLLECTOR_API_KEY=${COLLECTOR_API_KEY}
EOF

sudo chown openclaw-monitor:openclaw-monitor /opt/openclaw-monitor/.env
sudo chmod 600 /opt/openclaw-monitor/.env
```

#### 4. 初始化数据库

```bash
cd /opt/openclaw-monitor
sudo -u openclaw-monitor bash -c 'set -a; source .env; set +a; venv/bin/python -m server.init_db'
```

该命令会创建所有数据库表并生成默认用户 `monitor`，密码打印在控制台输出中，请妥善保存。

> 如果跳过此步骤，服务首次启动时也会自动初始化数据库，密码会输出到 journalctl 日志中。

#### 5. 安装并启动 systemd 服务

```bash
# 安装服务文件
sudo cp deploy/openclaw-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# 启动并设置开机自启
sudo systemctl enable --now openclaw-monitor

# 查看状态
sudo systemctl status openclaw-monitor

# 查看日志
sudo journalctl -u openclaw-monitor -f
```

#### 6. 常用运维命令

```bash
sudo systemctl start openclaw-monitor     # 启动
sudo systemctl stop openclaw-monitor      # 停止
sudo systemctl restart openclaw-monitor   # 重启
sudo systemctl status openclaw-monitor    # 状态
sudo journalctl -u openclaw-monitor -n 100 --no-pager  # 最近 100 行日志
```

### 采集器部署（systemd）

在每台 OpenClaw 实例机器上：

#### 1. 部署采集器

```bash
# 创建用户和目录（如果与 server 同机器则复用）
sudo useradd -r -s /sbin/nologin openclaw-monitor 2>/dev/null || true
sudo mkdir -p /opt/openclaw-monitor
sudo cp -r collector/ /opt/openclaw-monitor/
sudo chown -R openclaw-monitor:openclaw-monitor /opt/openclaw-monitor

# 安装依赖（如果虚拟环境已存在则复用）
sudo -u openclaw-monitor python3 -m venv /opt/openclaw-monitor/venv 2>/dev/null || true
sudo -u openclaw-monitor /opt/openclaw-monitor/venv/bin/pip install -r /opt/openclaw-monitor/collector/requirements.txt
```

#### 2. 修改配置

编辑 `/opt/openclaw-monitor/collector/config.yaml`：

```yaml
server_url: "http://<monitor-server-ip>:9200"   # 指向监控服务端
api_key: "your-collector-api-key"                # 与服务端 COLLECTOR_API_KEY 一致
instance_name: "prod-01"                         # 当前实例唯一标识
collect_interval: 60
openclaw_host: "127.0.0.1"
openclaw_port: 18789
openclaw_bin: "openclaw"
```

#### 3. 安装并启动服务

```bash
sudo cp deploy/openclaw-collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-collector

# 查看日志
sudo journalctl -u openclaw-collector -f
```

## 数据库

使用 SQLite，自动创建，包含以下表：

- **instances** — OpenClaw 实例信息和心跳状态
- **agents** — 智能体信息
- **sessions** — 会话记录（含 Token 用量、费用、模型信息）
- **token_usage_hourly** — 按小时聚合的 Token 用量统计
- **users** — 系统用户

## 功能概览

- **仪表盘** — 实例总数、智能体数量、Token 用量、告警数、24h 趋势图
- **实例管理** — 查看所有实例的在线/离线状态，进入实例查看详细信息
- **智能体监控** — 查看各实例下的智能体列表和运行状态
- **会话追踪** — 按实例、智能体、频道筛选会话，查看 Token 消耗明细
- **Token 分析** — 按实例/智能体维度的用量汇总，支持 24h/7d/30d 趋势图
- **国际化** — 支持中文和英文界面切换
- **JWT 认证** — 登录认证，保护管理接口
