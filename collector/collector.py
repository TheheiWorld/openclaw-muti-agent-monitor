#!/usr/bin/env python3
"""
OpenClaw Monitor Collector
部署在每台 OpenClaw 机器上，定期采集实例状态并上报到中心后端。
"""

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("collector")

# 持久化 instance_id，确保重启后标识不变
INSTANCE_ID_FILE = Path(__file__).parent / ".instance_id"


def get_or_create_instance_id() -> str:
    if INSTANCE_ID_FILE.exists():
        return INSTANCE_ID_FILE.read_text().strip()
    instance_id = str(uuid.uuid4())[:12]
    INSTANCE_ID_FILE.write_text(instance_id)
    return instance_id


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def check_health(host: str, port: int) -> dict:
    """检查 OpenClaw Gateway 健康状态"""
    result = {"live": False, "ready": False}
    try:
        resp = requests.get(f"http://{host}:{port}/healthz", timeout=5)
        if resp.status_code == 200:
            result["live"] = True
    except Exception as e:
        logger.warning(f"Health check /healthz failed: {e}")

    try:
        resp = requests.get(f"http://{host}:{port}/readyz", timeout=5)
        if resp.status_code == 200:
            result["ready"] = True
    except Exception as e:
        logger.warning(f"Health check /readyz failed: {e}")

    return result


def run_cli_command(openclaw_bin: str, args: list[str], timeout: int = 30, env: dict | None = None) -> str | None:
    """执行 OpenClaw CLI 命令并返回 stdout"""
    cmd = [openclaw_bin] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env,
        )
        if result.returncode != 0:
            logger.warning(f"CLI command failed: {' '.join(cmd)}\nstderr: {result.stderr[:500]}")
            return None
        return result.stdout
    except FileNotFoundError:
        logger.error(f"OpenClaw CLI not found: {openclaw_bin}")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"CLI command timed out ({timeout}s): {' '.join(cmd)}")
        return None
    except Exception as e:
        logger.warning(f"CLI command error: {e}")
        return None


def collect_sessions(openclaw_bin: str, env: dict | None = None) -> list[dict]:
    """采集会话数据 (含 Token 统计)"""
    output = run_cli_command(openclaw_bin, ["sessions", "--all-agents", "--json"], timeout=120, env=env)
    if not output:
        logger.info("Sessions command returned no output")
        return []

    all_sessions = []
    decoder = json.JSONDecoder()
    text = output.strip()
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(text):
            break
        if text[pos] not in ('{', '['):
            next_obj = text.find('{', pos)
            next_arr = text.find('[', pos)
            candidates = [c for c in (next_obj, next_arr) if c != -1]
            if not candidates:
                break
            pos = min(candidates)

        try:
            data, end_pos = decoder.raw_decode(text, pos)
            pos = end_pos
            if isinstance(data, dict) and "sessions" in data:
                all_sessions.extend(data["sessions"])
            elif isinstance(data, dict) and "items" in data:
                all_sessions.extend(data["items"])
            elif isinstance(data, list):
                all_sessions.extend(data)
        except json.JSONDecodeError:
            pos += 1

    return all_sessions


def collect_agents(openclaw_bin: str, env: dict | None = None) -> list[dict]:
    """采集 Agent 列表"""
    output = run_cli_command(openclaw_bin, ["agents", "list", "--json"], timeout=120, env=env)
    if not output:
        logger.info("Agents command returned no output")
        return []

    all_agents = []
    decoder = json.JSONDecoder()
    text = output.strip()
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(text):
            break
        if text[pos] not in ('{', '['):
            next_obj = text.find('{', pos)
            next_arr = text.find('[', pos)
            candidates = [c for c in (next_obj, next_arr) if c != -1]
            if not candidates:
                break
            pos = min(candidates)

        try:
            data, end_pos = decoder.raw_decode(text, pos)
            pos = end_pos
            if isinstance(data, list):
                all_agents.extend(data)
            elif isinstance(data, dict) and "agents" in data:
                all_agents.extend(data["agents"])
            elif isinstance(data, dict):
                all_agents.append(data)
        except json.JSONDecodeError:
            pos += 1

    return all_agents


def collect_version(openclaw_bin: str, env: dict | None = None) -> str:
    """获取 OpenClaw 版本"""
    output = run_cli_command(openclaw_bin, ["--version"], timeout=10, env=env)
    if output:
        return output.strip().split("\n")[0].strip()
    return ""


def _get_local_ip() -> str:
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def calculate_daily_usage(agents: list[dict]) -> list[dict]:
    """统计昨日的 Token 消耗 (用于长期存档)"""
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_date = yesterday.date()
    yesterday_str = yesterday_date.strftime("%Y-%m-%d")

    results = []

    for ag in agents:
        agent_dir = ag.get("agentDir", "")
        if not agent_dir or not os.path.isdir(agent_dir):
            continue

        parent_dir = os.path.dirname(agent_dir)
        sessions_dir = os.path.join(parent_dir, "sessions")

        if not os.path.isdir(sessions_dir):
            continue

        usage_total = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}

        try:
            for fname in os.listdir(sessions_dir):
                if ".jsonl" not in fname:
                    continue
                fpath = os.path.join(sessions_dir, fname)
                mtime = os.path.getmtime(fpath)
                mdate = datetime.fromtimestamp(mtime).date()

                if mdate == yesterday_date:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            if '"usage":' in line:
                                try:
                                    data = json.loads(line)
                                    msg = data.get("message", {})
                                    usage = msg.get("usage") if isinstance(msg, dict) else data.get("usage")
                                    if usage and isinstance(usage, dict):
                                        usage_total["input"] += usage.get("input", 0)
                                        usage_total["output"] += usage.get("output", 0)
                                        usage_total["cache_read"] += usage.get("cacheRead", 0)
                                        usage_total["cache_write"] += usage.get("cacheWrite", 0)
                                        usage_total["total"] += usage.get("totalTokens", 0)
                                except Exception:
                                    continue
        except Exception as e:
            logger.error(f"Error scanning sessions for agent {ag['id']}: {e}")
            continue

        if usage_total["total"] > 0:
            results.append({
                "agent_id": ag["id"], "date": yesterday_str,
                **usage_total
            })

    return results


def calculate_hourly_usage(agents: list[dict]) -> list[dict]:
    """统计今日的小时级 Token 消耗 (用于 Dashboard 实时趋势)"""
    today_date = datetime.now().date()
    results = []

    for ag in agents:
        agent_dir = ag.get("agentDir", "")
        if not agent_dir or not os.path.isdir(agent_dir):
            continue

        parent_dir = os.path.dirname(agent_dir)
        sessions_dir = os.path.join(parent_dir, "sessions")

        if not os.path.isdir(sessions_dir):
            continue

        # key: "YYYY-MM-DD HH:00:00", value: usage_dict
        hourly_map = {}

        try:
            for fname in os.listdir(sessions_dir):
                if ".jsonl" not in fname:
                    continue
                fpath = os.path.join(sessions_dir, fname)
                mtime = os.path.getmtime(fpath)
                mdate = datetime.fromtimestamp(mtime).date()

                # 仅处理今日修改过的文件
                if mdate == today_date:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            if '"usage":' in line:
                                try:
                                    data = json.loads(line)
                                    ts_str = data.get("timestamp")
                                    if not ts_str:
                                        continue
                                    
                                    # 解析 timestamp 确定小时
                                    # 格式通常为: 2026-03-22T14:32:24.395Z
                                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                    if dt.date() != today_date:
                                        continue
                                    
                                    hour_str = dt.strftime("%Y-%m-%d %H:00:00")
                                    
                                    msg = data.get("message", {})
                                    usage = msg.get("usage") if isinstance(msg, dict) else data.get("usage")
                                    
                                    if usage and isinstance(usage, dict):
                                        if hour_str not in hourly_map:
                                            hourly_map[hour_str] = {"input": 0, "output": 0, "total": 0}
                                        
                                        hourly_map[hour_str]["input"] += usage.get("input", 0)
                                        hourly_map[hour_str]["output"] += usage.get("output", 0)
                                        hourly_map[hour_str]["total"] += usage.get("totalTokens", 0)
                                except Exception:
                                    continue
        except Exception as e:
            logger.error(f"Error scanning hourly sessions for agent {ag['id']}: {e}")
            continue

        for hour_str, usage in hourly_map.items():
            results.append({
                "agent_id": ag["id"],
                "hour": hour_str,
                **usage
            })

    return results


DOC_FILES = ["SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md", "TOOLS.md"]


def sync_agent_docs(config: dict, instance_id: str, agents: list[dict], api_key: str) -> bool:
    """读取每个 agent 的文档文件并同步到 server"""
    docs_payload = []
    for ag in agents:
        workspace = ag.get("workspace", "")
        if not workspace or not os.path.isdir(workspace):
            continue

        files = {}
        for fname in DOC_FILES:
            fpath = os.path.join(workspace, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        files[fname] = f.read()
                except Exception as e:
                    logger.warning(f"Read {fpath} failed: {e}")
        if files:
            docs_payload.append({"agentId": ag["id"], "files": files})

    if not docs_payload:
        return True

    payload = {"instance_id": instance_id, "agents": docs_payload}
    url = f"{config['server_url']}/api/collector/agent-docs"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Agent docs sync error: {e}")
        return False


def send_heartbeat(server_url: str, heartbeat: dict, api_key: str = "") -> bool:
    """将心跳数据上报到中心后端"""
    url = f"{server_url}/api/collector/heartbeat"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.post(url, json=heartbeat, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("ok", False)
        return False
    except Exception as e:
        logger.warning(f"Send heartbeat error: {e}")
        return False


def send_daily_usage(server_url: str, payload: dict, api_key: str = "") -> bool:
    """上报每日统计数据"""
    url = f"{server_url}/api/collector/daily-usage"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Send daily usage error: {e}")
        return False


def main():
    config = load_config()
    instance_id = get_or_create_instance_id()

    heartbeat_interval = config.get("heartbeat_interval", config.get("collect_interval", 60))
    agents_interval = config.get("agents_interval", config.get("collect_interval", 120))
    sessions_interval = config.get("sessions_interval", config.get("collect_interval", 60))
    doc_sync_interval = config.get("doc_sync_interval", 3600)
    api_key = config.get("api_key", "")

    logger.info(f"OpenClaw Monitor Collector started")
    logger.info(f"  Instance ID: {instance_id}")
    logger.info(f"  Intervals: Heartbeat={heartbeat_interval}s, Agents={agents_interval}s, Sessions={sessions_interval}s, DocSync={doc_sync_interval}s")

    running = True

    # 数据缓存
    cached_agents = []
    cached_sessions = []
    cached_hourly_usage = []
    cached_health = {"live": False, "ready": False}
    cached_version = ""

    # 上次执行时间
    last_heartbeat = 0
    last_agents = 0
    last_sessions = 0
    last_doc_sync = 0
    last_daily_stats_date = ""

    def handle_signal(signum, frame):
        nonlocal running
        logger.info("Shutting down...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    host = config["openclaw_host"]
    port = config["openclaw_port"]
    openclaw_bin = config["openclaw_bin"]
    openclaw_home = config.get("openclaw_home", "")
    cli_env = None
    if openclaw_home:
        cli_env = os.environ.copy()
        cli_env["HOME"] = openclaw_home

    machine_host = config.get("advertise_host", "")
    if not machine_host:
        machine_host = _get_local_ip()
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    while running:
        now = time.time()
        now_dt = datetime.now()
        should_send = False

        try:
            # 1. 检查 Heartbeat / Health
            if now - last_heartbeat >= heartbeat_interval:
                cached_health = check_health(host, port)
                if cached_health["live"] and not cached_version:
                    cached_version = collect_version(openclaw_bin, env=cli_env)
                last_heartbeat = now
                should_send = True

            # 2. 检查 Agents
            if now - last_agents >= agents_interval:
                if cached_health["live"]:
                    agents_raw = collect_agents(openclaw_bin, env=cli_env)
                    new_agents = []
                    for ag in agents_raw:
                        identity = ag.get("identity", {}) or {}
                        new_agents.append({
                            "id": ag.get("id", ""),
                            "name": ag.get("identityName", "") or ag.get("name", "") or identity.get("name", ""),
                            "identity": {"emoji": ag.get("identityEmoji", "") or identity.get("emoji", ""), "theme": identity.get("theme", "")},
                            "workspace": ag.get("workspace", ""),
                            "agentDir": ag.get("agentDir", ""),
                            "model": ag.get("model", ""),
                        })
                    cached_agents = new_agents
                last_agents = now
                should_send = True

            # 3. 检查 Sessions (同时计算今日小时级 Token)
            if now - last_sessions >= sessions_interval:
                if cached_health["live"]:
                    sessions_raw = collect_sessions(openclaw_bin, env=cli_env)
                    new_sessions = []
                    for sess in sessions_raw:
                        new_sessions.append({
                            "key": sess.get("key", ""),
                            "sessionId": sess.get("sessionId", sess.get("session_id", "")),
                            "agentId": sess.get("agentId", sess.get("agent_id", "")),
                            "channel": sess.get("channel", ""),
                            "displayName": sess.get("displayName", sess.get("display_name", "")),
                            "status": sess.get("status", ""),
                            "inputTokens": sess.get("inputTokens", sess.get("input_tokens", 0)) or 0,
                            "outputTokens": sess.get("outputTokens", sess.get("output_tokens", 0)) or 0,
                            "cacheReadTokens": sess.get("cacheReadTokens", sess.get("cache_read_tokens", 0)) or 0,
                            "cacheWriteTokens": sess.get("cacheWriteTokens", sess.get("cache_write_tokens", 0)) or 0,
                            "totalTokens": sess.get("totalTokens", sess.get("total_tokens", 0)) or 0,
                            "contextTokens": sess.get("contextTokens", sess.get("context_tokens", 0)) or 0,
                            "estimatedCostUsd": sess.get("estimatedCostUsd", sess.get("estimated_cost_usd", 0)) or 0,
                            "modelProvider": sess.get("modelProvider", sess.get("model_provider", "")),
                            "model": sess.get("model", ""),
                            "startedAt": sess.get("startedAt", sess.get("started_at")),
                            "endedAt": sess.get("endedAt", sess.get("ended_at")),
                            "updatedAt": sess.get("updatedAt", sess.get("updated_at")),
                        })
                    cached_sessions = new_sessions
                    
                    # 分析今日小时级数据
                    if cached_agents:
                        cached_hourly_usage = calculate_hourly_usage(cached_agents)

                last_sessions = now
                should_send = True

            # 4. 发送数据
            if should_send:
                heartbeat_payload = {
                    "instance_id": instance_id,
                    "instance_name": config["instance_name"],
                    "hostname": hostname, "host": machine_host, "port": port,
                    "version": cached_version, "health": cached_health,
                    "agents": cached_agents,
                    "sessions": cached_sessions,
                    "hourly_usage": cached_hourly_usage,
                    "timestamp": int(now),
                }
                if send_heartbeat(config["server_url"], heartbeat_payload, api_key):
                    logger.info(
                        f"Heartbeat sent: agents={len(cached_agents)}, "
                        f"sessions={len(cached_sessions)}, hourly_records={len(cached_hourly_usage)}"
                    )
                else:
                    logger.warning("Heartbeat send failed")

            # 5. 同步 agent 文档
            if now - last_doc_sync >= doc_sync_interval:
                if cached_agents and sync_agent_docs(config, instance_id, cached_agents, api_key):
                    logger.info(f"Agent docs synced: {len(cached_agents)} agents")
                    last_doc_sync = now

            # 6. 每日凌晨 1 点统计昨日 Token 消耗
            current_date_str = now_dt.strftime("%Y-%m-%d")
            if now_dt.hour == 1 and last_daily_stats_date != current_date_str:
                if cached_agents:
                    logger.info("Starting daily token usage calculation...")
                    stats = calculate_daily_usage(cached_agents)
                    if stats:
                        payload = {"instance_id": instance_id, "items": stats}
                        if send_daily_usage(config["server_url"], payload, api_key):
                            logger.info(f"Daily usage reported: {len(stats)} agents")
                            last_daily_stats_date = current_date_str
                        else:
                            logger.warning("Daily usage report failed, will retry")
                    else:
                        logger.info("No token usage found for yesterday")
                        last_daily_stats_date = current_date_str
        except Exception as e:
            logger.error(f"Loop error: {e}")

        time.sleep(1)
        if not running:
            break

    logger.info("Collector stopped")


if __name__ == "__main__":
    main()
