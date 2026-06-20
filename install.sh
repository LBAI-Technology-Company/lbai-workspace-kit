#!/usr/bin/env sh
set -eu

REPO="LBAI-Technology-Company/lbai-workspace-kit"
INSTALLER_VERSION="1.4.8"
LBAI_HOME="${LBAI_HOME:-$HOME/.lbai}"
INSTALL_DIR="$LBAI_HOME/kit"
BIN_DIR="$LBAI_HOME/bin"
VENV_DIR="$LBAI_HOME/venv"
RELEASE_TAG=""

ST_GIT=""
ST_PYTHON=""
ST_CURL=""
ST_LBAI=""
ST_PYDEPS=""
ST_PATH=""
ST_CODEX_CLI=""
ST_CODEX_MP=""
ST_CODEX_PLUGIN=""
ST_BACKEND=""

info() {
  printf '%s\n' "$*"
}

set_st() {
  case "$1" in
    GIT) ST_GIT="${2}|${3}" ;;
    PYTHON) ST_PYTHON="${2}|${3}" ;;
    CURL) ST_CURL="${2}|${3}" ;;
    LBAI) ST_LBAI="${2}|${3}" ;;
    PYDEPS) ST_PYDEPS="${2}|${3}" ;;
    PATH) ST_PATH="${2}|${3}" ;;
    CODEX_CLI) ST_CODEX_CLI="${2}|${3}" ;;
    CODEX_MP) ST_CODEX_MP="${2}|${3}" ;;
    CODEX_PLUGIN) ST_CODEX_PLUGIN="${2}|${3}" ;;
    BACKEND) ST_BACKEND="${2}|${3}" ;;
  esac
}

summary_line() {
  label="$1"
  raw="${2:-|}"
  state="${raw%%|*}"
  detail="${raw#*|}"
  if [ "$detail" = "$raw" ]; then
    detail=""
  fi
  case "$state" in
    OK) mark="[OK]  " ;;
    FAILED) mark="[失败]" ;;
    SKIPPED) mark="[跳过]" ;;
    WARN) mark="[警告]" ;;
    *) mark="[ -- ]" ;;
  esac
  if [ -n "$detail" ]; then
    info "$(printf '%-28s %s %s' "$label" "$mark" "$detail")"
  else
    info "$(printf '%-28s %s' "$label" "$mark")"
  fi
}

print_install_summary() {
  info ""
  info "========== 安装结果汇总 =========="
  summary_line "Git" "$ST_GIT"
  summary_line "Python 3.10+" "$ST_PYTHON"
  summary_line "curl" "$ST_CURL"
  summary_line "LBAI CLI" "$ST_LBAI"
  summary_line "Python 依赖 (jsonschema)" "$ST_PYDEPS"
  summary_line "Shell PATH (lbai)" "$ST_PATH"
  summary_line "Codex CLI" "$ST_CODEX_CLI"
  summary_line "Codex marketplace" "$ST_CODEX_MP"
  summary_line "Codex 插件 (lbai-workspace)" "$ST_CODEX_PLUGIN"
  summary_line "后端登录 (可选)" "$ST_BACKEND"
  info "=================================="
  info "说明：一键安装包含 LBAI CLI、Codex CLI（macOS/Linux）和 lbai-workspace 插件。"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

detect_script_dir() {
  if [ -f "$0" ]; then
    CDPATH= cd -- "$(dirname -- "$0")" && pwd
    return 0
  fi
  return 1
}

fetch_latest_release_tag_soft() {
  if [ -n "${LBAI_VERSION:-}" ]; then
    printf '%s\n' "$LBAI_VERSION"
    return 0
  fi

  tag=""
  if command -v gh >/dev/null 2>&1; then
    tag="$(gh api "repos/$REPO/releases/latest" --jq '.tag_name' 2>/dev/null | tr -d '[:space:]')"
  fi

  if [ -z "$tag" ]; then
    for api_url in \
      "https://ghproxy.net/https://api.github.com/repos/$REPO/releases/latest" \
      "https://api.github.com/repos/$REPO/releases/latest"
    do
      response="$(curl -fsSL --connect-timeout 15 --max-time 30 "$api_url" 2>/dev/null || true)"
      tag="$(printf '%s\n' "$response" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
      if [ -n "$tag" ]; then
        break
      fi
    done
  fi

  if [ -z "$tag" ]; then
    location="$(curl -fsSI --connect-timeout 15 --max-time 30 "https://github.com/$REPO/releases/latest" 2>/dev/null \
      | awk 'tolower($1) == "location:" { print $2 }' | tr -d '\r' | tail -n 1)"
    if [ -n "$location" ]; then
      tag="${location##*/}"
    fi
  fi

  if [ -z "$tag" ]; then
    return 1
  fi

  printf '%s\n' "$tag"
}

resolve_latest_release_tag() {
  tag="$(fetch_latest_release_tag_soft || true)"
  if [ -z "$tag" ]; then
    fail "could not resolve latest release for $REPO"
  fi
  printf '%s\n' "$tag"
}

bootstrap_latest_installer() {
  if [ "${LBAI_INSTALL_BOOTSTRAP:-}" = "1" ]; then
    return 0
  fi

  script_dir="$(detect_script_dir || true)"
  if [ -n "$script_dir" ] && [ -f "$script_dir/lbai_core/lbai/cli.py" ] && [ -d "$script_dir/workspace_template" ]; then
    return 0
  fi

  if ! have_cmd curl; then
    return 0
  fi

  tag="$(fetch_latest_release_tag_soft || true)"
  if [ -z "$tag" ]; then
    info "WARNING: 无法解析最新 release tag，继续使用当前 install.sh。"
    return 0
  fi
  tmp="$(mktemp -d)"
  fetched=0
  for url in \
    "https://github.com/$REPO/releases/latest/download/install.sh" \
    "https://ghproxy.net/https://github.com/$REPO/releases/latest/download/install.sh" \
    "https://ghproxy.net/https://raw.githubusercontent.com/$REPO/$tag/install.sh" \
    "https://raw.githubusercontent.com/$REPO/$tag/install.sh"
  do
    if curl -fsSL --connect-timeout 20 --max-time 120 "$url" -o "$tmp/install.sh" 2>/dev/null \
      && grep -q 'print_install_summary' "$tmp/install.sh" 2>/dev/null
    then
      fetched=1
      break
    fi
    rm -f "$tmp/install.sh"
  done

  if [ "$fetched" -ne 1 ]; then
    rm -rf "$tmp"
    info "WARNING: 无法从 GitHub 拉取最新 install.sh，继续使用当前安装脚本。"
    return 0
  fi

  remote_version="$(sed -n 's/^INSTALLER_VERSION="\([^"]*\)".*/\1/p' "$tmp/install.sh" | head -n 1)"
  if [ -n "${INSTALLER_VERSION:-}" ] && [ -n "$remote_version" ] && [ "$remote_version" = "$INSTALLER_VERSION" ]; then
    rm -rf "$tmp"
    return 0
  fi

  info "正在从 GitHub 拉取最新 install.sh ($tag)..."
  chmod +x "$tmp/install.sh"
  export LBAI_INSTALL_BOOTSTRAP=1
  export LBAI_VERSION="$tag"
  exec /bin/sh "$tmp/install.sh" "$@"
}

bootstrap_latest_installer

resolve_python_bin() {
  if have_cmd python3 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    printf 'python3'
    return 0
  fi
  if have_cmd python; then
    python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1 || return 1
    printf 'python'
    return 0
  fi
  return 1
}

ensure_git_macos() {
  if have_cmd git && git --version >/dev/null 2>&1; then
    return 0
  fi
  if have_cmd brew; then
    info "未检测到 Git，正在通过 Homebrew 安装..."
    brew install git
    return 0
  fi
  info "未检测到 Git，正在打开系统安装窗口（Xcode 命令行工具）..."
  xcode-select --install >/dev/null 2>&1 || true
  fail "请先在弹出窗口中完成 Git 安装，然后重新运行本安装命令。"
}

ensure_python_macos() {
  if resolve_python_bin >/dev/null 2>&1; then
    return 0
  fi
  if have_cmd brew; then
    info "未检测到 Python 3.10+，正在通过 Homebrew 安装..."
    brew install python
    return 0
  fi
  fail "未检测到 Python 3.10+。请先打开 https://www.python.org/downloads/ 安装，或安装 Homebrew 后重试。"
}

ensure_prerequisites_macos() {
  ensure_git_macos
  ensure_python_macos
}

ensure_prerequisites_linux() {
  if have_cmd git && resolve_python_bin >/dev/null 2>&1; then
    return 0
  fi
  info "未检测到 Git 或 Python 3.10+，正在尝试自动安装..."
  if have_cmd apt-get; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-pip python3-venv curl ca-certificates
    return 0
  fi
  if have_cmd dnf; then
    sudo dnf install -y git python3 curl ca-certificates
    return 0
  fi
  if have_cmd yum; then
    sudo yum install -y git python3 curl ca-certificates
    return 0
  fi
  if have_cmd apk; then
    sudo apk add --no-cache git python3 curl ca-certificates
    return 0
  fi
  fail "请手动安装 git、Python 3.10+ 和 curl 后重试。"
}

ensure_prerequisites() {
  os="$(uname -s 2>/dev/null || true)"
  info "正在检查运行环境（Git、Python 3.10+）..."
  case "$os" in
    Darwin)
      ensure_prerequisites_macos
      ;;
    Linux)
      ensure_prerequisites_linux
      ;;
    MINGW*|MSYS*|CYGWIN*)
      fail "Windows 请改用 PowerShell 安装命令：irm https://cdn.jsdelivr.net/gh/$REPO@latest/install.ps1 | iex"
      ;;
    *)
      fail "当前系统暂不支持自动安装，请手动安装 Git 和 Python 3.10+。"
      ;;
  esac
  if ! have_cmd git; then
    fail "Git 仍未可用，请完成安装后重试。"
  fi
  if ! resolve_python_bin >/dev/null 2>&1; then
    fail "Python 3.10+ 仍未可用，请完成安装后重试。"
  fi
  if ! have_cmd curl; then
    fail "未检测到 curl，无法下载安装包。"
  fi
  set_st GIT OK "$(git --version 2>/dev/null | head -n 1)"
  set_st PYTHON OK "$($(resolve_python_bin) --version 2>/dev/null | head -n 1)"
  set_st CURL OK "$(curl --version 2>/dev/null | head -n 1 | cut -d' ' -f1-2)"
  info "环境检查通过：$(git --version 2>/dev/null | head -n 1)"
  info "环境检查通过：$($(resolve_python_bin) --version 2>/dev/null | head -n 1)"
}

CODEX_CLI_INSTALL_URL="https://chatgpt.com/codex/install.sh"
CODEX_PLUGIN_MARKETPLACE="lbai-internal"

codex_cli_bin() {
  if have_cmd codex; then
    command -v codex
    return 0
  fi
  if [ -x "$HOME/.local/bin/codex" ]; then
    printf '%s\n' "$HOME/.local/bin/codex"
    return 0
  fi
  return 1
}

refresh_codex_path() {
  if [ -d "$HOME/.local/bin" ]; then
    case ":$PATH:" in
      *":$HOME/.local/bin:"*) ;;
      *) PATH="$HOME/.local/bin:$PATH"; export PATH ;;
    esac
  fi
}

ensure_codex_local_bin_path() {
  bin_dir="$HOME/.local/bin"
  profile=""
  case "$(uname -s 2>/dev/null || true):${SHELL:-}" in
    Darwin:*/zsh) profile="$HOME/.zprofile" ;;
    Darwin:*/bash) profile="$HOME/.bash_profile" ;;
    Linux:*/zsh) profile="$HOME/.zshrc" ;;
    Linux:*/bash) profile="$HOME/.bashrc" ;;
    *) profile="$HOME/.profile" ;;
  esac

  [ -n "$profile" ] || return 0
  path_line="export PATH=\"$bin_dir:\$PATH\""
  touch "$profile"
  if grep -qF "$bin_dir" "$profile" 2>/dev/null; then
    return 0
  fi
  {
    printf '\n# Added by LBAI installer for Codex CLI\n'
    printf '%s\n' "$path_line"
  } >> "$profile"
  info "Added Codex CLI to PATH in $profile"
}

codex_cli_available() {
  refresh_codex_path
  codex_cli_bin >/dev/null 2>&1 && codex --version >/dev/null 2>&1
}

install_codex_via_official_script() {
  CODEX_NON_INTERACTIVE=1 curl -fsSL --connect-timeout 20 --max-time 300 "$CODEX_CLI_INSTALL_URL" | sh
}

install_codex_via_npm() {
  if ! have_cmd npm; then
    return 1
  fi
  info "  尝试 npm 全局安装 @openai/codex ..."
  npm install -g @openai/codex
}

resolve_codex_github_asset() {
  os="$(uname -s 2>/dev/null || true)"
  arch="$(uname -m 2>/dev/null || true)"
  case "$os:$arch" in
    Darwin:arm64|Darwin:aarch64) printf '%s\n' "codex-aarch64-apple-darwin.tar.gz" ;;
    Darwin:x86_64) printf '%s\n' "codex-x86_64-apple-darwin.tar.gz" ;;
    Linux:x86_64) printf '%s\n' "codex-x86_64-unknown-linux-musl.tar.gz" ;;
    Linux:aarch64|Linux:arm64) printf '%s\n' "codex-aarch64-unknown-linux-musl.tar.gz" ;;
    *) return 1 ;;
  esac
}

install_codex_via_github_binary() {
  asset="$(resolve_codex_github_asset || true)"
  if [ -z "$asset" ]; then
    return 1
  fi

  info "  尝试 GitHub release 二进制 ($asset) ..."
  tmp="$(mktemp -d)"
  mkdir -p "$HOME/.local/bin"
  for url in \
    "https://ghproxy.net/https://github.com/openai/codex/releases/latest/download/$asset" \
    "https://github.com/openai/codex/releases/latest/download/$asset"
  do
    if curl -fsSL --connect-timeout 20 --max-time 300 "$url" -o "$tmp/codex.tgz" 2>/dev/null \
      && tar -tzf "$tmp/codex.tgz" >/dev/null 2>&1
    then
      rm -rf "$tmp/extract"
      mkdir -p "$tmp/extract"
      tar -xzf "$tmp/codex.tgz" -C "$tmp/extract" 2>/dev/null || true
      codex_bin="$(find "$tmp/extract" -type f -name codex 2>/dev/null | head -n 1)"
      if [ -n "$codex_bin" ] && cp "$codex_bin" "$HOME/.local/bin/codex" 2>/dev/null; then
        chmod +x "$HOME/.local/bin/codex"
        ensure_codex_local_bin_path
        rm -rf "$tmp"
        return 0
      fi
    fi
    rm -f "$tmp/codex.tgz"
  done
  rm -rf "$tmp"
  return 1
}

ensure_codex_cli() {
  if [ "${LBAI_SKIP_CODEX_CLI:-}" = "1" ]; then
    info "跳过 Codex CLI 安装（LBAI_SKIP_CODEX_CLI=1）。"
    set_st CODEX_CLI SKIPPED "LBAI_SKIP_CODEX_CLI=1"
    return 0
  fi

  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin|Linux) ;;
    *)
      info "当前系统跳过 Codex CLI 自动安装。"
      set_st CODEX_CLI SKIPPED "当前系统不支持自动安装"
      return 0
      ;;
  esac

  if codex_cli_available; then
    version="$(codex --version 2>/dev/null | head -n 1)"
    info "环境检查通过：$version"
    set_st CODEX_CLI OK "$version"
    return 0
  fi

  if ! have_cmd curl; then
    info "WARNING: 未检测到 curl，跳过 Codex CLI 自动安装。"
    set_st CODEX_CLI FAILED "缺少 curl"
    return 0
  fi

  info "未检测到 Codex CLI，正在尝试多种安装方式..."
  if install_codex_via_official_script && codex_cli_available; then
    :
  elif install_codex_via_npm && codex_cli_available; then
    :
  elif install_codex_via_github_binary && codex_cli_available; then
    :
  else
    info "WARNING: Codex CLI 自动安装失败。LBAI CLI 已安装，可稍后手动运行："
    info "  curl -fsSL $CODEX_CLI_INSTALL_URL | sh"
    info "  npm install -g @openai/codex"
    info "  或从 https://github.com/openai/codex/releases 下载对应平台二进制到 ~/.local/bin"
    set_st CODEX_CLI FAILED "自动安装失败，见上方手动命令"
    return 0
  fi

  refresh_codex_path
  if codex_cli_available; then
    version="$(codex --version 2>/dev/null | head -n 1)"
    info "环境检查通过：$version"
    set_st CODEX_CLI OK "$version"
    return 0
  fi

  if [ -x "$HOME/.local/bin/codex" ]; then
    info "Codex CLI 已安装到 $HOME/.local/bin/codex。"
    info "若当前终端仍找不到 codex，请运行 source ~/.zprofile 或 source ~/.zshrc 后重试。"
    set_st CODEX_CLI WARN "已安装到 ~/.local/bin/codex，需 source shell 配置"
    return 0
  fi

  info "WARNING: Codex CLI 安装脚本已执行，但未检测到 codex 命令。"
  info "  请新开终端，或运行 source ~/.zprofile / source ~/.zshrc 后再试。"
  set_st CODEX_CLI WARN "安装脚本已执行，当前终端未检测到 codex"
  return 0
}

run_codex() {
  refresh_codex_path
  if have_cmd codex; then
    codex "$@"
    return $?
  fi
  if [ -x "$HOME/.local/bin/codex" ]; then
    "$HOME/.local/bin/codex" "$@"
    return $?
  fi
  return 127
}

codex_cli_ready() {
  run_codex --version >/dev/null 2>&1
}

ensure_codex_plugin() {
  plugin_tag="${LBAI_PLUGIN_REF:-${RELEASE_TAG:-}}"

  if [ "${LBAI_SKIP_CODEX_PLUGIN:-}" = "1" ] || [ "${LBAI_SKIP_CODEX_CLI:-}" = "1" ]; then
    info "跳过 Codex 插件安装（LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1）。"
    set_st CODEX_MP SKIPPED "LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1"
    set_st CODEX_PLUGIN SKIPPED "LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1"
    return 0
  fi

  if ! codex_cli_ready; then
    info "WARNING: codex 不可用，跳过 lbai-workspace 插件安装。"
    info "  请先 source ~/.zprofile 或 ~/.zshrc，然后重新运行 install.sh。"
    set_st CODEX_MP FAILED "codex 不可用"
    set_st CODEX_PLUGIN FAILED "codex 不可用，需先安装/配置 Codex CLI"
    return 0
  fi

  if [ -z "$plugin_tag" ] || [ "$plugin_tag" = "local" ]; then
    info "WARNING: 无法确定插件 release tag，跳过 Codex 插件自动安装。"
    set_st CODEX_MP FAILED "无法确定 release tag"
    set_st CODEX_PLUGIN FAILED "无法确定 release tag"
    return 0
  fi

  info "正在配置 LBAI Codex 插件 marketplace ($plugin_tag)..."
  marketplace_ok=0
  if run_codex plugin marketplace upgrade "$CODEX_PLUGIN_MARKETPLACE" >/dev/null 2>&1; then
    marketplace_ok=1
    info "已升级 Codex marketplace: $CODEX_PLUGIN_MARKETPLACE"
  else
    run_codex plugin marketplace remove "$CODEX_PLUGIN_MARKETPLACE" >/dev/null 2>&1 || true
    if run_codex plugin marketplace add "$REPO" --ref "$plugin_tag"; then
      marketplace_ok=1
      info "已添加 Codex marketplace: $CODEX_PLUGIN_MARKETPLACE"
    fi
  fi

  if [ "$marketplace_ok" -eq 0 ]; then
    info "WARNING: Codex marketplace 配置失败。请确认已登录 Codex 后手动运行："
    info "  codex plugin marketplace add $REPO --ref $plugin_tag"
    info "  codex plugin add lbai-workspace@$CODEX_PLUGIN_MARKETPLACE"
    set_st CODEX_MP FAILED "marketplace 配置失败，见上方手动命令"
    set_st CODEX_PLUGIN FAILED "依赖 marketplace，未安装"
    return 0
  fi

  set_st CODEX_MP OK "$CODEX_PLUGIN_MARKETPLACE ($plugin_tag)"

  info "正在安装 lbai-workspace 插件..."
  run_codex plugin remove lbai-workspace >/dev/null 2>&1 || true
  if run_codex plugin add "lbai-workspace@$CODEX_PLUGIN_MARKETPLACE"; then
    info "已安装 Codex 插件: lbai-workspace@$CODEX_PLUGIN_MARKETPLACE"
    info "请在 Codex 桌面 App 中开启新线程，使插件 Skills 生效。"
    set_st CODEX_PLUGIN OK "lbai-workspace@$CODEX_PLUGIN_MARKETPLACE"
    return 0
  fi

  info "WARNING: Codex 插件安装失败。请手动运行："
  info "  codex plugin add lbai-workspace@$CODEX_PLUGIN_MARKETPLACE"
  set_st CODEX_PLUGIN FAILED "插件安装失败，见上方手动命令"
  return 0
}

PATH_MARKER="# LBAI Workspace Kit CLI"

detect_shell_rc() {
  shell_name="$(basename "${SHELL:-}")"
  if [ "$shell_name" = "zsh" ] || [ -n "${ZSH_VERSION:-}" ]; then
    printf '%s\n' "$HOME/.zshrc"
    return 0
  fi
  if [ "$shell_name" = "bash" ] || [ -n "${BASH_VERSION:-}" ]; then
    if [ -f "$HOME/.bash_profile" ]; then
      printf '%s\n' "$HOME/.bash_profile"
    else
      printf '%s\n' "$HOME/.bashrc"
    fi
    return 0
  fi
  return 1
}

ensure_shell_path() {
  shell_rc="$(detect_shell_rc || true)"
  path_export="export PATH=\"$BIN_DIR:\$PATH\""

  if [ -z "$shell_rc" ]; then
    info "Could not detect a shell rc file. Add lbai to PATH manually:"
    info "  $path_export"
    set_st PATH WARN "未检测到 shell 配置文件，需手动加入 PATH"
    return 0
  fi

  touch "$shell_rc"
  if grep -qF "$PATH_MARKER" "$shell_rc" 2>/dev/null || grep -qF "$BIN_DIR" "$shell_rc" 2>/dev/null; then
    info "PATH already configured in $shell_rc"
    set_st PATH OK "已配置 ($shell_rc)"
    return 0
  fi

  {
    printf '\n%s\n' "$PATH_MARKER"
    printf '%s\n' "$path_export"
  } >> "$shell_rc"
  info "Added lbai to PATH in $shell_rc"
  info "Run: source $shell_rc"
  set_st PATH OK "已写入 ($shell_rc)"
}

read_kit_version() {
  if [ -f "$INSTALL_DIR/VERSION" ]; then
    tr -d '[:space:]' < "$INSTALL_DIR/VERSION"
  else
    printf 'unknown'
  fi
}

create_python_runtime() {
  rm -rf "$VENV_DIR"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR" >/dev/null 2>&1; then
    fail "could not create Python runtime at $VENV_DIR. Install Python venv support and rerun install.sh."
  fi

  venv_python="$VENV_DIR/bin/python"
  if [ ! -x "$venv_python" ]; then
    fail "Python runtime was created but $venv_python is not executable"
  fi

  if ! "$venv_python" -m pip install --quiet --disable-pip-version-check -r "$INSTALL_DIR/lbai_core/requirements.txt"; then
    fail "could not install Python dependencies into $VENV_DIR. Check network or pip configuration, then rerun install.sh."
  fi

  printf '%s\n' "$venv_python"
}

install_from_dir() {
  src="$1"
  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR" "$BIN_DIR"
  (cd "$src" && tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -cf - .) | (cd "$INSTALL_DIR" && tar -xf -)
}

download_archive() {
  archive="$1"
  archive_dir="$(dirname "$archive")"

  info "Downloading LBAI Workspace Kit $RELEASE_TAG..."
  for url in \
    "https://ghproxy.net/https://github.com/$REPO/archive/refs/tags/$RELEASE_TAG.tar.gz" \
    "https://github.com/$REPO/archive/refs/tags/$RELEASE_TAG.tar.gz" \
    "https://gh-proxy.com/https://github.com/$REPO/archive/refs/tags/$RELEASE_TAG.tar.gz"
  do
    if curl -fsSL --connect-timeout 20 --max-time 600 --retry 2 --retry-delay 2 "$url" -o "$archive" 2>/dev/null \
      && tar -tzf "$archive" >/dev/null 2>&1
    then
      return 0
    fi
    rm -f "$archive"
  done

  if command -v gh >/dev/null 2>&1; then
    rm -f "$archive"
    if gh release download "$RELEASE_TAG" --repo "$REPO" --archive=tar.gz --dir "$archive_dir" >/dev/null 2>&1; then
      candidate="$(find "$archive_dir" -maxdepth 1 -name '*.tar.gz' | head -n 1)"
      if [ -n "$candidate" ] && tar -tzf "$candidate" >/dev/null 2>&1; then
        mv "$candidate" "$archive"
        return 0
      fi
    fi
    rm -f "$archive_dir"/*.tar.gz 2>/dev/null || true
  fi

  return 1
}

clone_and_install() {
  tmp="$1"
  for git_url in \
    "https://ghproxy.net/https://github.com/$REPO.git" \
    "https://github.com/$REPO.git"
  do
    clone_dir="$tmp/git-clone"
    rm -rf "$clone_dir"
    if git clone --depth 1 --branch "$RELEASE_TAG" "$git_url" "$clone_dir" >/dev/null 2>&1; then
      install_from_dir "$clone_dir"
      return 0
    fi
  done
  return 1
}

download_and_install() {
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT INT TERM
  archive="$tmp/lbai-workspace-kit.tar.gz"

  if download_archive "$archive"; then
    tar -xzf "$archive" -C "$tmp"
    src="$(find "$tmp" -maxdepth 1 -type d -name 'lbai-workspace-kit-*' | head -n 1)"
    [ -n "$src" ] || fail "downloaded archive did not contain lbai-workspace-kit"
    install_from_dir "$src"
    return 0
  fi

  clone_and_install "$tmp" || fail "download failed; check network and retry"
}

ensure_prerequisites

PYTHON_BIN="$(resolve_python_bin)"
[ -n "$PYTHON_BIN" ] || fail "Python 3.10+ is required"

SCRIPT_DIR="$(detect_script_dir || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/lbai_core/lbai/cli.py" ] && [ -d "$SCRIPT_DIR/workspace_template" ]; then
  info "Installing from local checkout: $SCRIPT_DIR"
  install_from_dir "$SCRIPT_DIR"
  if [ -f "$SCRIPT_DIR/VERSION" ]; then
    RELEASE_TAG="v$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"
  else
    RELEASE_TAG="local"
  fi
else
  RELEASE_TAG="$(resolve_latest_release_tag)"
  info "Latest release: $RELEASE_TAG"
  download_and_install
fi

chmod +x "$INSTALL_DIR/lbai_core/bin/lbai"
RUNTIME_PYTHON="$(create_python_runtime)"
cat > "$BIN_DIR/lbai" <<EOF
#!/usr/bin/env sh
set -eu
export LBAI_HOME="$LBAI_HOME"
export LBAI_KIT_ROOT="$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR/lbai_core\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$RUNTIME_PYTHON" -m lbai.cli "\$@"
EOF
chmod +x "$BIN_DIR/lbai"
ensure_shell_path
ensure_codex_cli
ensure_codex_plugin

set_st PYDEPS OK "jsonschema 等 ($VENV_DIR)"
info "Installed Python runtime and dependencies (jsonschema)."

if [ -t 0 ] && [ "${LBAI_SKIP_BACKEND_AUTH:-}" != "1" ]; then
  info "Optional backend knowledge service setup."
  if "$BIN_DIR/lbai" auth backend-login --optional; then
    set_st BACKEND OK "已完成或已跳过"
  else
    set_st BACKEND WARN "未完成，可稍后运行 lbai auth backend-login"
  fi
else
  set_st BACKEND SKIPPED "非交互环境或 LBAI_SKIP_BACKEND_AUTH=1"
fi

kit_version="$(read_kit_version)"
set_st LBAI OK "v$kit_version ($BIN_DIR/lbai)"

print_install_summary

info "Release: $RELEASE_TAG"
info
shell_rc="$(detect_shell_rc || true)"
info "Next steps:"
if [ -n "$shell_rc" ]; then
  info "  source $shell_rc"
fi
if [ "$(uname -s 2>/dev/null || true)" = "Darwin" ] && [ -f "$HOME/.zprofile" ]; then
  info "  source ~/.zprofile   # Codex CLI PATH（macOS 常见）"
fi
info "  lbai auth login"
info "  lbai auth doctor"
info "  lbai auth backend-login"
info "  lbai init-workspace"
if ! codex_cli_ready && { codex_cli_bin >/dev/null 2>&1 || [ -x "$HOME/.local/bin/codex" ]; }; then
  info "  source ~/.zprofile   # 然后 codex --version"
  info "  重新运行 install.sh 以自动安装 lbai-workspace 插件"
fi
info
info "To repair or upgrade the installed CLI, rerun install.sh."
info "To remove the installed CLI later:"
info "  lbai uninstall"
