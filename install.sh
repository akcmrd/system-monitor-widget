#!/usr/bin/env bash
# System Monitor Widget installer
#   ./install.sh              check/install dependencies and add shortcuts
#   ./install.sh --uninstall  remove the shortcuts (keeps settings and this folder)
set -euo pipefail

APP_ID=system-monitor-widget
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

if [[ -t 1 ]]; then
    B=$'\033[1m'; DIM=$'\033[2m'; BLUE=$'\033[1;34m'; GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[1;31m'; R=$'\033[0m'
else
    B= DIM= BLUE= GREEN= YELLOW= RED= R=
fi
say()     { printf '%s==>%s %s\n' "$BLUE" "$R" "$*"; }
warn()    { printf '%s!!%s  %s\n' "$YELLOW" "$R" "$*"; }
heading() { printf '\n%s%s%s\n' "$B" "$*" "$R"; }
ask()     { local a; read -r -p "    $1 [Y/n] " a; [[ -z "$a" || "$a" =~ ^[Yy] ]]; }

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$APPS/$APP_ID.desktop" "$AUTOSTART/$APP_ID.desktop" "$DESKTOP_DIR/$APP_ID.desktop"
    say "Shortcuts removed (app menu, autostart, desktop icon)."
    say "Settings are still in ~/.config/$APP_ID and the app is still in $DIR; delete them by hand if you want."
    exit 0
fi

# ── Welcome ───────────────────────────────────────────────────
cat <<EOF

${BLUE}  ╭──────────────────────────────────────────────╮
  │  *      System Monitor Widget · installer    │   *
  ╰──────────────────────────────────────────────╯${R}

  A small desktop widget showing clock, CPU, memory, GPU, battery,
  storage, network and top processes. Everything is read locally;
  nothing is sent over the internet.

${B}This installer will:${R}
  1. Check the required packages and install any that are missing
     (only this step needs your password, and only if something is missing)
  2. Add "System Monitor Widget" to your app menu
  3. Ask whether to start it on login and add a desktop icon
  4. Offer to start the widget now

  The app runs from this folder: ${B}$DIR${R}
  Nothing is copied elsewhere, so keep this folder.

EOF
read -r -p "  Press Enter to continue, or Ctrl+C to cancel. " _

# ── 1. Dependencies ───────────────────────────────────────────
command -v python3 >/dev/null || { warn "Python 3 is not installed. Install it with your package manager, then run this again."; exit 1; }

if   command -v apt-get >/dev/null; then PM=apt
elif command -v dnf     >/dev/null; then PM=dnf
elif command -v pacman  >/dev/null; then PM=pacman
elif command -v zypper  >/dev/null; then PM=zypper
else PM=unknown
fi

# WebKit2GTK 4.1, or 4.0 on older releases (Ubuntu 20.04, Debian 11) that don't ship 4.1
WEBKIT_CHECK="import gi; v=[x for x in ('4.1','4.0') if x in gi.Repository.get_default().enumerate_versions('WebKit2')]; gi.require_version('WebKit2', v[0]); from gi.repository import WebKit2"
pkg_available() {
    case $PM in
        apt)    [[ -n "$(apt-cache policy "$1" 2>/dev/null | grep 'Candidate:' | grep -v '(none)')" ]];;
        dnf)    dnf -q info "$1" >/dev/null 2>&1;;
        pacman) pacman -Si "$1" >/dev/null 2>&1;;
        zypper) zypper -q info "$1" 2>/dev/null | grep -q '^Name';;
        *)      false;;
    esac
}
webkit_pkg() {
    local new old
    case $PM in
        apt)    new=gir1.2-webkit2-4.1      old=gir1.2-webkit2-4.0;;
        dnf)    new=webkit2gtk4.1           old=webkit2gtk4.0;;
        pacman) new=webkit2gtk-4.1          old=webkit2gtk;;
        zypper) new=typelib-1_0-WebKit2-4_1 old=typelib-1_0-WebKit2-4_0;;
    esac
    if pkg_available "$new"; then echo "$new"; else echo "$old"; fi
}

# name | why it is needed | python check | apt | dnf | pacman | zypper  (@webkit = picked by webkit_pkg)
DEPS=(
"PyGObject|Python bindings that let the app use GTK and WebKit|import gi|python3-gi|python3-gobject|python-gobject|python3-gobject"
"GTK 3|Creates the widget window (frameless, on every workspace)|import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk|gir1.2-gtk-3.0|gtk3|gtk3|typelib-1_0-Gtk-3_0"
"WebKit2GTK|Draws the widget's interface (widget.html) inside the window|$WEBKIT_CHECK|@webkit|@webkit|@webkit|@webkit"
"pycairo|Shapes the window for the click-through option|import gi, cairo; gi.require_foreign('cairo')|python3-gi-cairo|python3-cairo|python-cairo|python3-gobject-cairo"
"psutil|Reads CPU, memory, disk, battery, network and process stats|import psutil|python3-psutil|python3-psutil|python-psutil|python3-psutil"
)
# name | what it adds | command
OPTIONAL=(
"NetworkManager (nmcli)|Wi-Fi name, connection type and DNS in the Network section|nmcli"
"iproute2 (ip)|Active network interface and gateway|ip"
"NVIDIA driver (nvidia-smi)|GPU section (NVIDIA cards only)|nvidia-smi"
)

heading "Step 1 of 4 · Required packages"
missing=() any_missing=no
for d in "${DEPS[@]}"; do
    IFS='|' read -r name why check apt dnf pacman zypper <<<"$d"
    if python3 -c "$check" >/dev/null 2>&1; then
        mark="${GREEN}✔ installed${R}"
    else
        mark="${RED}✘ missing  ${R}"
        any_missing=yes
        case $PM in apt) pkg=$apt;; dnf) pkg=$dnf;; pacman) pkg=$pacman;; zypper) pkg=$zypper;; *) pkg=;; esac
        [[ $pkg == @webkit ]] && pkg=$(webkit_pkg)
        [[ -n $pkg ]] && missing+=("$pkg")
    fi
    printf '  %s  %-15s %s%s%s\n' "$mark" "$name" "$DIM" "$why" "$R"
done

heading "Optional tools (not installed by this script)"
for o in "${OPTIONAL[@]}"; do
    IFS='|' read -r name why cmd <<<"$o"
    if command -v "$cmd" >/dev/null; then mark="${GREEN}✔ found  ${R}"; else mark="${YELLOW}– not found${R}"; fi
    printf '  %s  %-26s %s%s%s\n' "$mark" "$name" "$DIM" "$why" "$R"
done
echo

if [[ $any_missing == no ]]; then
    say "All required packages are installed."
else
    case $PM in
        apt)    cmd=(sudo apt-get install -y "${missing[@]}");;
        dnf)    cmd=(sudo dnf install -y "${missing[@]}");;
        pacman) cmd=(sudo pacman -S --needed --noconfirm "${missing[@]}");;
        zypper) cmd=(sudo zypper install -y "${missing[@]}");;
        *)      warn "Unknown package manager: install the missing packages above by hand, then run this again."; exit 1;;
    esac
    say "This command installs the missing packages:"
    echo "      ${cmd[*]}"
    ask "Run it now?" || { warn "Cancelled. Install them by hand, then run this again."; exit 1; }
    "${cmd[@]}"
    for d in "${DEPS[@]}"; do
        IFS='|' read -r name _ check _ <<<"$d"
        python3 -c "$check" >/dev/null 2>&1 || { warn "$name is still missing; see the messages above."; exit 1; }
    done
    say "Required packages installed."
fi

# ── 2. App menu ───────────────────────────────────────────────
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

heading "Step 2 of 4 · App menu"
mkdir -p "$APPS"
entry > "$APPS/$APP_ID.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
say "Added. Search your app menu for \"System Monitor Widget\"."

# ── 3. Autostart and desktop icon ─────────────────────────────
heading "Step 3 of 4 · Shortcuts"
autostart=no desktop=no
if ask "Start the widget automatically when you log in?"; then
    mkdir -p "$AUTOSTART"
    entry > "$AUTOSTART/$APP_ID.desktop"
    autostart=yes
    say "Autostart enabled."
fi
if [[ -d "$DESKTOP_DIR" ]] && ask "Add an icon to your desktop?"; then
    entry > "$DESKTOP_DIR/$APP_ID.desktop"
    chmod +x "$DESKTOP_DIR/$APP_ID.desktop"
    gio set "$DESKTOP_DIR/$APP_ID.desktop" metadata::trusted true 2>/dev/null || true
    desktop=yes
    say "Desktop icon added."
fi

# ── 4. Start ──────────────────────────────────────────────────
heading "Step 4 of 4 · Start"
if pgrep -f "$DIR/launcher.py" >/dev/null; then
    say "The widget is already running."
elif ask "Start the widget now?"; then
    (GDK_BACKEND=x11 setsid python3 "$DIR/launcher.py" >/dev/null 2>&1 &)
    say "Started."
fi

cat <<EOF

${GREEN}  ✔ All done${R}
    App menu entry : yes
    Start on login : $autostart
    Desktop icon   : $desktop

  Click ${B}⚙${R} on the widget for settings (sections, theme, units, position, …).
  Update later   : cd "$DIR" && git pull   (then restart the widget)
  Remove shortcuts: ./install.sh --uninstall

EOF
