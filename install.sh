#!/usr/bin/env bash
# System Monitor Widget installer
#   ./install.sh              install dependencies and add shortcuts
#   ./install.sh --uninstall  remove the shortcuts (keeps settings and this folder)
set -euo pipefail

APP_ID=system-monitor-widget
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
ask()  { local a; read -r -p "$1 [Y/n] " a; [[ -z "$a" || "$a" =~ ^[Yy] ]]; }

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$APPS/$APP_ID.desktop" "$AUTOSTART/$APP_ID.desktop" "$DESKTOP_DIR/$APP_ID.desktop"
    say "Shortcuts removed. Settings are still in ~/.config/$APP_ID; delete that folder to remove them too."
    exit 0
fi

# ── 1. Dependencies ───────────────────────────────────────────
deps_ok() {
    python3 - <<'EOF' 2>/dev/null
import gi, cairo, psutil
gi.require_version('Gtk', '3.0'); gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2
EOF
}

if deps_ok; then
    say "Dependencies already installed."
else
    if   command -v apt-get >/dev/null; then
        cmd=(sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 python3-psutil)
    elif command -v dnf >/dev/null; then
        cmd=(sudo dnf install -y python3-gobject python3-cairo gtk3 webkit2gtk4.1 python3-psutil)
    elif command -v pacman >/dev/null; then
        cmd=(sudo pacman -S --needed --noconfirm python-gobject python-cairo gtk3 webkit2gtk-4.1 python-psutil)
    elif command -v zypper >/dev/null; then
        cmd=(sudo zypper install -y python3-gobject python3-gobject-cairo typelib-1_0-Gtk-3_0 typelib-1_0-WebKit2-4_1 python3-psutil)
    else
        warn "Unknown package manager. Install manually: Python 3 GObject + cairo bindings, GTK 3, WebKit2GTK 4.1, psutil."
        exit 1
    fi
    say "Installing dependencies (needs your password):"
    echo "    ${cmd[*]}"
    "${cmd[@]}"
    deps_ok || { warn "Dependencies still missing after install; see the messages above."; exit 1; }
fi
command -v nmcli >/dev/null || warn "nmcli (NetworkManager) not found: the network section will show less detail."

# ── 2. Shortcuts ──────────────────────────────────────────────
chmod +x "$DIR/launcher.py"
entry() {
    cat <<EOF
[Desktop Entry]
Type=Application
Name=System Monitor Widget
Comment=Desktop system monitor (clock, CPU, RAM, GPU, battery, disk, network, processes)
Exec=env GDK_BACKEND=x11 python3 "$DIR/launcher.py"
Icon=utilities-system-monitor
Terminal=false
Categories=System;Monitor;
X-GNOME-Autostart-enabled=true
EOF
}

mkdir -p "$APPS"
entry > "$APPS/$APP_ID.desktop"
say "Added to the app menu (search for \"System Monitor Widget\")."

if ask "Start the widget automatically when you log in?"; then
    mkdir -p "$AUTOSTART"
    entry > "$AUTOSTART/$APP_ID.desktop"
    say "Autostart enabled."
fi

if [[ -d "$DESKTOP_DIR" ]] && ask "Add an icon to your desktop?"; then
    entry > "$DESKTOP_DIR/$APP_ID.desktop"
    chmod +x "$DESKTOP_DIR/$APP_ID.desktop"
    gio set "$DESKTOP_DIR/$APP_ID.desktop" metadata::trusted true 2>/dev/null || true
    say "Desktop icon added."
fi

command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true

# ── 3. Start it ───────────────────────────────────────────────
if ! pgrep -f "$DIR/launcher.py" >/dev/null && ask "Start the widget now?"; then
    (GDK_BACKEND=x11 setsid python3 "$DIR/launcher.py" >/dev/null 2>&1 &)
    say "Started. Click ⚙ on the widget for settings."
fi
say "Done. To remove the shortcuts later: ./install.sh --uninstall"
