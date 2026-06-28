#!/usr/bin/env sh
# LBAI 安装引导：依次尝试 GitHub 直连与国内镜像，任一成功即执行 install.sh。
set -eu

REPO="LBAI-Technology-Company/lbai-workspace-kit"

info() {
  printf '%s\n' "$*"
}

for url in \
  "https://ghproxy.net/https://github.com/$REPO/releases/latest/download/install.sh" \
  "https://github.com/$REPO/releases/latest/download/install.sh" \
  "https://gh-proxy.com/https://github.com/$REPO/releases/latest/download/install.sh"
do
  info "尝试: $url"
  if curl -fsSL --connect-timeout 20 --max-time 180 "$url" | sh; then
    exit 0
  fi
  info "  -> 失败，尝试下一个镜像..."
done

info ""
info "错误: 所有下载源均失败，请检查网络或代理后重试。"
info "也可下载后本地运行: bash install.sh"
exit 1
