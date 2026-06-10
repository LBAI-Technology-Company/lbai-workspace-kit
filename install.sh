#!/usr/bin/env sh
set -eu

REPO="LBAI-Technology-Company/lbai-workspace-kit"
VERSION="${LBAI_VERSION:-v0.1.5}"
LBAI_HOME="${LBAI_HOME:-$HOME/.lbai}"
INSTALL_DIR="$LBAI_HOME/kit"
BIN_DIR="$LBAI_HOME/bin"

info() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
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

install_from_dir() {
  src="$1"
  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR" "$BIN_DIR"
  (cd "$src" && tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -cf - .) | (cd "$INSTALL_DIR" && tar -xf -)
}

download_archive() {
  archive="$1"
  archive_dir="$(dirname "$archive")"

  info "Downloading LBAI Workspace Kit $VERSION..."
  for url in \
    "https://ghproxy.net/https://github.com/$REPO/archive/refs/tags/$VERSION.tar.gz" \
    "https://github.com/$REPO/archive/refs/tags/$VERSION.tar.gz" \
    "https://gh-proxy.com/https://github.com/$REPO/archive/refs/tags/$VERSION.tar.gz"
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
    if gh release download "$VERSION" --repo "$REPO" --archive=tar.gz --dir "$archive_dir" >/dev/null 2>&1; then
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
    if git clone --depth 1 --branch "$VERSION" "$git_url" "$clone_dir" >/dev/null 2>&1; then
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

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/lbai_core/lbai/cli.py" ] && [ -d "$SCRIPT_DIR/workspace_template" ]; then
  info "Installing from local checkout: $SCRIPT_DIR"
  install_from_dir "$SCRIPT_DIR"
else
  download_and_install
fi

chmod +x "$INSTALL_DIR/lbai_core/bin/lbai"
cat > "$BIN_DIR/lbai" <<EOF
#!/usr/bin/env sh
set -eu
export LBAI_KIT_ROOT="$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR/lbai_core\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m lbai.cli "\$@"
EOF
chmod +x "$BIN_DIR/lbai"
ensure_shell_path

info "LBAI Workspace Kit installed."
info "lbai path: $BIN_DIR/lbai"
info
shell_rc="$(detect_shell_rc || true)"
info "Next steps:"
if [ -n "$shell_rc" ]; then
  info "  source $shell_rc"
fi
info "  lbai auth login"
info "  lbai init-workspace"
info
info "To repair or upgrade the installed CLI, rerun install.sh."
info "To remove the installed CLI later:"
info "  lbai uninstall"
