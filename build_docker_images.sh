#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MODE="all"
VERSION="v1.14.1"
ARM_IMAGE=""
AMD_IMAGE=""
IMAGE_PREFIX="registry.cn-hangzhou.aliyuncs.com/pubg/archery"
ARM_BASE_IMAGE="hhyo/archery-base:arm64-local"
AMD_BASE_IMAGE="hhyo/archery-base:amd64-local"
PYTHON_BASE_IMAGE="docker.m.daocloud.io/library/python:3.11-bullseye"
HTTP_PROXY_ARG="${HTTP_PROXY:-}"
HTTPS_PROXY_ARG="${HTTPS_PROXY:-}"
SKIP_AMD_BASE="false"
PUSH="false"
DRY_RUN="false"

usage() {
  cat <<EOF
用法:
  ./build_docker_images.sh [选项]

选项:
  -m <all|arm|amd>             构建模式，默认 all
  -v <tag>                     版本标签，默认 v1.14.1
  --arm-image <image:tag>      arm64 目标镜像
  --amd-image <image:tag>      amd64 目标镜像
  --arm-base-image <image:tag> arm64 构建时使用的基础镜像，默认 hhyo/archery-base:arm64-local
  --amd-base-image <image:tag> amd64 构建时使用的基础镜像，默认 hhyo/archery-base:amd64-local
  --python-base-image <image>  Dockerfile-base 的 Python 基础镜像，默认 library/python:3.11-bullseye
  --http-proxy <url>           传递 HTTP_PROXY 给 Dockerfile-base
  --https-proxy <url>          传递 HTTPS_PROXY 给 Dockerfile-base
  --skip-amd-base              跳过 amd64 基础镜像构建
  --push                       构建后推送镜像
  --dry-run                    仅打印命令，不执行
  -h, --help                   显示帮助

示例:
  ./build_docker_images.sh -m all -v v1.14.1 \\
    --arm-image registry.cn-hangzhou.aliyuncs.com/pubg/archery:v1.14.1-arm64 \\
    --amd-image registry.cn-hangzhou.aliyuncs.com/pubg/archery:v1.14.1
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m)
      MODE="$2"
      shift 2
      ;;
    -v)
      VERSION="$2"
      shift 2
      ;;
    --arm-image)
      ARM_IMAGE="$2"
      shift 2
      ;;
    --amd-image)
      AMD_IMAGE="$2"
      shift 2
      ;;
    --arm-base-image)
      ARM_BASE_IMAGE="$2"
      shift 2
      ;;
    --amd-base-image)
      AMD_BASE_IMAGE="$2"
      shift 2
      ;;
    --python-base-image)
      PYTHON_BASE_IMAGE="$2"
      shift 2
      ;;
    --http-proxy)
      HTTP_PROXY_ARG="$2"
      shift 2
      ;;
    --https-proxy)
      HTTPS_PROXY_ARG="$2"
      shift 2
      ;;
    --skip-amd-base)
      SKIP_AMD_BASE="true"
      shift
      ;;
    --push)
      PUSH="true"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "all" && "$MODE" != "arm" && "$MODE" != "amd" ]]; then
  echo "mode 仅支持 all|arm|amd"
  exit 1
fi

if [[ -z "$ARM_IMAGE" ]]; then
  ARM_IMAGE="${IMAGE_PREFIX}:${VERSION}-arm64"
fi
if [[ -z "$AMD_IMAGE" ]]; then
  AMD_IMAGE="${IMAGE_PREFIX}:${VERSION}"
fi

run_cmd() {
  echo "+ $*"
  if [[ "$DRY_RUN" == "false" ]]; then
    "$@"
  fi
}

build_arm() {
  run_cmd docker build --platform linux/arm64 -f src/docker/Dockerfile-base \
    --build-arg "PYTHON_BASE_IMAGE=$PYTHON_BASE_IMAGE" \
    --build-arg "HTTP_PROXY=$HTTP_PROXY_ARG" \
    --build-arg "HTTPS_PROXY=$HTTPS_PROXY_ARG" \
    -t "$ARM_BASE_IMAGE" .
  run_cmd docker build --platform linux/arm64 -f src/docker/Dockerfile --build-arg "BASE_IMAGE=$ARM_BASE_IMAGE" -t "$ARM_IMAGE" .
  if [[ "$PUSH" == "true" ]]; then
    run_cmd docker push "$ARM_IMAGE"
  fi
}

build_amd() {
  if [[ "$SKIP_AMD_BASE" == "false" ]]; then
    run_cmd docker build --platform linux/amd64 -f src/docker/Dockerfile-base \
      --build-arg "PYTHON_BASE_IMAGE=$PYTHON_BASE_IMAGE" \
      --build-arg "HTTP_PROXY=$HTTP_PROXY_ARG" \
      --build-arg "HTTPS_PROXY=$HTTPS_PROXY_ARG" \
      -t "$AMD_BASE_IMAGE" .
  fi
  run_cmd docker build --platform linux/amd64 -f src/docker/Dockerfile --build-arg "BASE_IMAGE=$AMD_BASE_IMAGE" -t "$AMD_IMAGE" .
  if [[ "$PUSH" == "true" ]]; then
    run_cmd docker push "$AMD_IMAGE"
  fi
}

if [[ "$MODE" == "all" || "$MODE" == "arm" ]]; then
  build_arm
fi

if [[ "$MODE" == "all" || "$MODE" == "amd" ]]; then
  build_amd
fi

echo "构建完成"
