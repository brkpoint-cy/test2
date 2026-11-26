#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "错误：未找到 Docker。请先在 Ubuntu 上安装 Docker Engine 和 Compose 插件。" >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "错误：Docker 不可用。请确认 Docker 服务已启动，且当前用户有访问权限。" >&2
    echo "可尝试：sudo systemctl enable --now docker" >&2
    echo "然后加入 docker 组并重新登录：sudo usermod -aG docker $USER" >&2
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "错误：未找到 Docker Compose 插件，请安装 docker-compose-plugin。" >&2
    exit 1
fi

mkdir -p data/demo data/raw artifacts/demo artifacts/web-configs artifacts/web-runs

echo "正在构建 AeriScope 镜像（首次构建需要下载 Python 和 Node.js 依赖）..."
docker compose build "$@"

echo
echo "安装完成。启动前后端服务："
echo "  ./scripts/start_ubuntu_docker.sh"
echo "默认访问地址：http://localhost:8000"
