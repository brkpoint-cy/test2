#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT="${AERISCOPE_PORT:-8000}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((PORT < 1 || PORT > 65535)); then
    echo "错误：AERISCOPE_PORT 必须是 1 到 65535 之间的整数。" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "错误：Docker 不可用，请先运行 ./scripts/install_ubuntu_docker.sh 查看检查结果。" >&2
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "错误：未找到 Docker Compose 插件。" >&2
    exit 1
fi

mkdir -p data/demo data/raw artifacts/demo artifacts/web-configs artifacts/web-runs
docker compose up -d "$@"

CONTAINER_ID="$(docker compose ps -q app)"
if [[ -z "$CONTAINER_ID" ]]; then
    echo "错误：服务容器未创建。" >&2
    exit 1
fi

echo "正在等待 AeriScope 健康检查通过..."
for ((attempt = 1; attempt <= 60; attempt++)); do
    STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER_ID" 2>/dev/null || true)"
    case "$STATUS" in
        healthy)
            echo
            echo "AeriScope 已启动：http://localhost:${PORT}"
            echo "API 文档：http://localhost:${PORT}/docs"
            echo "查看日志：docker compose logs -f app"
            echo "停止服务：docker compose down"
            exit 0
            ;;
        unhealthy|exited|dead)
            echo
            echo "错误：服务启动失败（状态：${STATUS}）。最近日志如下：" >&2
            docker compose logs --tail=50 app >&2
            exit 1
            ;;
    esac
    sleep 2
done

echo "错误：等待服务就绪超时。最近日志如下：" >&2
docker compose logs --tail=50 app >&2
exit 1
