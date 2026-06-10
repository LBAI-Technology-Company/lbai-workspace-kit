#!/usr/bin/env sh
set -eu

REPO="LBAI-Technology-Company/lbai-workspace-kit"
VERSION="${LBAI_VERSION:-v0.1.0}"
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

install_from_dir() {
  src="$1"
  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR" "$BIN_DIR"
  (cd "$src" && tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -cf - .) | (cd "$INSTALL_DIR" && tar -xf -)
}

download_and_install() {
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT INT TERM
  archive="$tmp/lbai-workspace-kit.tar.gz"
  url="https://github.com/$REPO/archive/refs/tags/$VERSION.tar.gz"
  info "Downloading $url"
  curl -fsSL "$url" -o "$archive" || fail "download failed"
  tar -xzf "$archive" -C "$tmp"
  src="$(find "$tmp" -maxdepth 1 -type d -name 'lbai-workspace-kit-*' | head -n 1)"
  [ -n "$src" ] || fail "downloaded archive did not contain lbai-workspace-kit"
  install_from_dir "$src"
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

info "LBAI Workspace Kit installed."
info "lbai path: $BIN_DIR/lbai"
info
info "Add this to PATH if needed:"
info "  export PATH=\"$BIN_DIR:\$PATH\""
info
info "Next steps:"
info "  lbai auth login"
info "  lbai init-workspace"
info
info "To repair or upgrade the installed CLI, rerun install.sh."
info "To remove the installed CLI later:"
info "  lbai uninstall"
