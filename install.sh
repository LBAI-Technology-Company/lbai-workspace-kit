#!/usr/bin/env sh
set -eu

REPO="LBAI-Technology-Company/lbai-workspace-kit"
LBAI_HOME="${LBAI_HOME:-$HOME/.lbai}"
INSTALL_DIR="$LBAI_HOME/kit"
BIN_DIR="$LBAI_HOME/bin"
VENV_DIR="$LBAI_HOME/venv"
RELEASE_TAG=""

info() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

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
  info "环境检查通过：$(git --version 2>/dev/null | head -n 1)"
  info "环境检查通过：$($(resolve_python_bin) --version 2>/dev/null | head -n 1)"
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
    return 0
  fi

  touch "$shell_rc"
  if grep -qF "$PATH_MARKER" "$shell_rc" 2>/dev/null || grep -qF "$BIN_DIR" "$shell_rc" 2>/dev/null; then
    info "PATH already configured in $shell_rc"
    return 0
  fi

  {
    printf '\n%s\n' "$PATH_MARKER"
    printf '%s\n' "$path_export"
  } >> "$shell_rc"
  info "Added lbai to PATH in $shell_rc"
  info "Run: source $shell_rc"
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

detect_script_dir() {
  if [ -f "$0" ]; then
    CDPATH= cd -- "$(dirname -- "$0")" && pwd
    return 0
  fi
  return 1
}

resolve_latest_release_tag() {
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
    fail "could not resolve latest release for $REPO"
  fi

  printf '%s\n' "$tag"
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

info "Installed Python runtime and dependencies (jsonschema)."

if [ -t 0 ] && [ "${LBAI_SKIP_BACKEND_AUTH:-}" != "1" ]; then
  info "Optional backend knowledge service setup."
  "$BIN_DIR/lbai" auth backend-login --optional || true
fi

kit_version="$(read_kit_version)"
info "LBAI Workspace Kit installed."
info "已安装版本: $kit_version"
info "Release: $RELEASE_TAG"
info "lbai path: $BIN_DIR/lbai"
info
shell_rc="$(detect_shell_rc || true)"
info "Next steps:"
if [ -n "$shell_rc" ]; then
  info "  source $shell_rc"
fi
info "  lbai auth login"
info "  lbai auth doctor"
info "  lbai auth backend-login"
info "  lbai init-workspace"
info
info "To repair or upgrade the installed CLI, rerun install.sh."
info "To remove the installed CLI later:"
info "  lbai uninstall"
