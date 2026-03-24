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
    """采集会话数据 (含 Token 统计)

    openclaw sessions --json 可能输出：
    - 单个 JSON 对象 { sessions: [...] }
    - 多个 JSON 对象拼接 (多 agent store 时每个 store 输出一个 JSON 块)
    - JSON 块之间或末尾可能混入非 JSON 文本 (CLI log/warning 等)
    """
    output = run_cli_command(openclaw_bin, ["sessions", "--all-agents", "--json"], timeout=120, env=env)
    if not output:
        logger.info("Sessions command returned no output")
        return []

    all_sessions = []

    # 尝试逐块解析 (处理多个 JSON 块拼接的情况)
    decoder = json.JSONDecoder()
    text = output.strip()
    pos = 0
    while pos < len(text):
        # 跳过空白
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(text):
            break
        # 跳过非 JSON 内容 (找到下一个 '{' 或 '[')
        if text[pos] not in ('{', '['):
            next_obj = text.find('{', pos)
            next_arr = text.find('[', pos)
            candidates = [c for c in (next_obj, next_arr) if c != -1]
            if not candidates:
                # 剩余内容中没有 JSON 了
                if pos < len(text):
                    skipped = text[pos:pos + 200]
                    logger.warning(f"Skipping trailing non-JSON content at pos {pos}: {skipped!r}")
                break
            next_json = min(candidates)
            skipped = text[pos:next_json]
            logger.warning(f"Skipping non-JSON content at pos {pos}: {skipped!r}")
            pos = next_json

        try:
            data, end_pos = decoder.raw_decode(text, pos)
            pos = end_pos
            # 提取 sessions 数组
            if isinstance(data, dict) and "sessions" in data:
                all_sessions.extend(data["sessions"])
            elif isinstance(data, dict) and "items" in data:
                all_sessions.extend(data["items"])
            elif isinstance(data, list):
                all_sessions.extend(data)
            else:
                logger.warning(f"Unexpected JSON structure (keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__})")
        except json.JSONDecodeError as e:
            # 当前位置的 '{' 或 '[' 解析失败，跳过这个字符继续
            logger.warning(f"JSON decode failed at pos {pos}: {e}")
            pos += 1

    if all_sessions:
        logger.info(f"Collected {len(all_sessions)} sessions")
    else:
        logger.warning(f"No sessions parsed from output ({len(output)} bytes): {output[:500]!r}")
    return all_sessions


def collect_agents(openclaw_bin: str, env: dict | None = None) -> list[dict]:
    """采集 Agent 列表

    使用 `openclaw agents list --json`，返回 AgentSummary[] 数组，
    包含 id, name, isDefault, identityEmoji, identityName 等字段。
    输出可能包含多个 JSON 块拼接或混入非 JSON 文本。
    """
    output = run_cli_command(openclaw_bin, ["agents", "list", "--json"], env=env)
    if not output:
        logger.info("Agents command returned no output")
        return []

    all_agents = []
    decoder = json.JSONDecoder()
    text = output.strip()
    pos = 0
    while pos < len(text):
        # 跳过空白
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(text):
            break
        # 跳过非 JSON 内容
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

    if all_agents:
        logger.info(f"Collected {len(all_agents)} agents")
    else:
        logger.warning(f"No agents parsed from output ({len(output)} bytes)")
    return all_agents


def collect_version(openclaw_bin: str, env: dict | None = None) -> str:
    """获取 OpenClaw 版本"""
    output = run_cli_command(openclaw_bin, ["--version"], timeout=10, env=env)
    if output:
        return output.strip().split("\n")[0].strip()
    return ""


def _get_local_ip() -> str:
    """获取本机局域网 IP（非 127.0.0.1）"""
    try:
        # 通过 UDP 连接外部地址来获取本机出口 IP，不会实际发送数据
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    # fallback: gethostbyname
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def build_heartbeat(config: dict, instance_id: str) -> dict:
    """构建完整心跳数据"""
    host = config["openclaw_host"]
    port = config["openclaw_port"]
    openclaw_bin = config["openclaw_bin"]

    # 构造子进程环境变量，指定 HOME 目录使 openclaw CLI 读取正确的数据
    cli_env = None
    openclaw_home = config.get("openclaw_home", "")
    if openclaw_home:
        cli_env = os.environ.copy()
        cli_env["HOME"] = openclaw_home

    health = check_health(host, port)
    sessions_raw = collect_sessions(openclaw_bin, env=cli_env) if health["live"] else []
    agents_raw = collect_agents(openclaw_bin, env=cli_env) if health["live"] else []
    version = collect_version(openclaw_bin, env=cli_env) if health["live"] else ""

    # 规范化 agent 数据
    # openclaw agents list --json 返回字段:
    #   id, name, isDefault, identityEmoji, identityName, identitySource, model, workspace, ...
    agents = []
    for ag in agents_raw:
        identity = ag.get("identity", {}) or {}
        agents.append({
            "id": ag.get("id", ""),
            "name": ag.get("identityName", "") or ag.get("name", "") or identity.get("name", ""),
            "identity": {
                "emoji": ag.get("identityEmoji", "") or identity.get("emoji", ""),
                "theme": identity.get("theme", ""),
            },
        })

    # 规范化 session 数据
    sessions = []
    for sess in sessions_raw:
        sessions.append({
            "key": sess.get("key", ""),
            "sessionId": sess.get("sessionId", sess.get("session_id", "")),
            "agentId": sess.get("agentId", sess.get("agent_id", "")),
            "channel": sess.get("channel", ""),
            "displayName": sess.get("displayName", sess.get("display_name", "")),
            "status": sess.get("status", ""),
            "inputTokens": sess.get("inputTokens", sess.get("input_tokens", 0)) or 0,
            "outputTokens": sess.get("outputTokens", sess.get("output_tokens", 0)) or 0,
            "totalTokens": sess.get("totalTokens", sess.get("total_tokens", 0)) or 0,
            "contextTokens": sess.get("contextTokens", sess.get("context_tokens", 0)) or 0,
            "estimatedCostUsd": sess.get("estimatedCostUsd", sess.get("estimated_cost_usd", 0)) or 0,
            "modelProvider": sess.get("modelProvider", sess.get("model_provider", "")),
            "model": sess.get("model", ""),
            "startedAt": sess.get("startedAt", sess.get("started_at")),
            "endedAt": sess.get("endedAt", sess.get("ended_at")),
            "updatedAt": sess.get("updatedAt", sess.get("updated_at")),
        })

    # 获取本机 IP
    machine_host = config.get("advertise_host", "")
    if not machine_host:
        machine_host = _get_local_ip()

    # 获取机器名称
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    return {
        "instance_id": instance_id,
        "instance_name": config["instance_name"],
        "hostname": hostname,
        "host": machine_host,
        "port": port,
        "version": version,
        "health": health,
        "agents": agents,
        "sessions": sessions,
        "timestamp": int(time.time()),
    }


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
        else:
            logger.warning(f"Server returned {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.ConnectionError:
        logger.warning(f"Cannot connect to server: {server_url}")
        return False
    except Exception as e:
        logger.warning(f"Send heartbeat error: {e}")
        return False


def main():
    config = load_config()
    instance_id = get_or_create_instance_id()
    interval = config.get("collect_interval", 60)
    api_key = config.get("api_key", "")

    logger.info(f"OpenClaw Monitor Collector started")
    logger.info(f"  Instance ID: {instance_id}")
    logger.info(f"  Instance Name: {config['instance_name']}")
    logger.info(f"  Server URL: {config['server_url']}")
    logger.info(f"  Collect Interval: {interval}s")
    logger.info(f"  OpenClaw: {config['openclaw_host']}:{config['openclaw_port']}")

    running = True

    def handle_signal(signum, frame):
        nonlocal running
        logger.info("Shutting down...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        try:
            heartbeat = build_heartbeat(config, instance_id)
            agent_count = len(heartbeat["agents"])
            session_count = len(heartbeat["sessions"])
            total_tokens = sum(s.get("totalTokens", 0) for s in heartbeat["sessions"])

            ok = send_heartbeat(config["server_url"], heartbeat, api_key)
            if ok:
                logger.info(
                    f"Heartbeat sent: status={heartbeat['health']}, "
                    f"agents={agent_count}, sessions={session_count}, "
                    f"tokens={total_tokens}"
                )
            else:
                logger.warning("Heartbeat send failed")
        except Exception as e:
            logger.error(f"Collect error: {e}")

        # 可中断的 sleep
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    logger.info("Collector stopped")


if __name__ == "__main__":
    main()
