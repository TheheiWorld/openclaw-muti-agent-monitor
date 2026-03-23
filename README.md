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
python run.py
```

服务启动在 `http://localhost:9200`。首次运行会自动创建数据库并生成默认用户 `monitor`，密码会打印在控制台日志中。

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
| `POST /api/collector/heartbeat` | 采集器心跳上报 | 否 |
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

### 后端生产部署

```bash
cd server
pip install -r requirements.txt
# 使用 uvicorn 直接启动
uvicorn server.main:app --host 0.0.0.0 --port 9200
```

建议使用 systemd 或 supervisor 管理后端进程，确保服务持续运行。

### 采集器生产部署

在每台 OpenClaw 实例机器上：

1. 拷贝 `collector/` 目录到目标机器
2. 修改 `config.yaml` 中的 `server_url` 指向监控服务端
3. 修改 `instance_name` 为当前实例的唯一标识
4. 使用 systemd 或 supervisor 管理采集器进程

#### systemd 服务示例（采集器）

```ini
[Unit]
Description=OpenClaw Monitor Collector
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/openclaw-monitor/collector
ExecStart=/usr/bin/python3 collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
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
