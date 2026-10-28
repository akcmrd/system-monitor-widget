# System Monitor Widget

A small always-on-desktop system monitor for Linux, built with GTK3 + WebKit2GTK.

It shows a clock, CPU usage/frequency/temperature, memory, disk usage, the active
network connection (name, IP, gateway, DNS, live up/down speed) and the top
processes by CPU and memory, plus optional GPU (NVIDIA) and battery sections.
A ⚙ panel lets you choose and reorder sections, theme, units, clock style and more.

## Supported systems

| Distro | Installer | Status |
|---|---|---|
| Debian 12+, Ubuntu 22.04+, Linux Mint 21+, Pop!_OS, Zorin, elementary | ✅ apt | Tested on Debian 13 |
| Ubuntu 20.04, Debian 11 and other older releases | ✅ apt | Uses WebKit2GTK 4.0 automatically |
| Fedora | ✅ dnf | Should work, not yet tested |
| Arch, Manjaro, EndeavourOS | ✅ pacman | Should work, not yet tested |
| openSUSE | ⚠️ zypper | Package names not verified |
| RHEL, Rocky, AlmaLinux | ⚠️ dnf | WebKit2GTK may need EPEL or extra repos |
| Alpine, Void, Gentoo, NixOS, Solus, … | ❌ | Install the [dependencies](#manual-install) by hand |
| Fedora Silverblue/Kinoite, SteamOS (immutable) | ❌ | Packages can't be installed the usual way |

**Desktops:** KDE Plasma, XFCE, Cinnamon and MATE are fully supported. On GNOME the widget works,
but GNOME shows no desktop icons by default (so the installer's desktop-icon option has no effect)
and "keep below other windows" may behave differently. Wayland sessions work through XWayland,
which is installed by default almost everywhere.

## Install

```bash
git clone https://github.com/akcmrd/system-monitor-widget.git ~/system-monitor-widget
cd ~/system-monitor-widget
./install.sh
```

The installer:

1. installs the dependencies (Python GObject + cairo bindings, GTK 3, WebKit2GTK 4.1 or 4.0, psutil), asking for your password only if something is missing
2. adds **System Monitor Widget** to your app menu
3. asks whether to start it on login, add a desktop icon, and start it now

The widget runs from the folder you cloned, so keep that folder. To update later:

```bash
cd ~/system-monitor-widget && git pull
```

then close the widget (⚙ → Close widget) and start it again from the app menu.

To remove the shortcuts: `./install.sh --uninstall` (your settings and the folder stay; delete them by hand if you want).

### Manual install

If the installer doesn't support your distro, install these with your package manager, then run
`GDK_BACKEND=x11 python3 launcher.py` from this folder (or `./install.sh` just for the shortcuts once they're present):

- Python 3 with **PyGObject** (GObject introspection bindings) and **pycairo** with its GObject integration
- **GTK 3** introspection data
- **WebKit2GTK 4.1** (or 4.0) introspection data
- **psutil**

Optional: NetworkManager (`nmcli`) for Wi-Fi name and DNS, `ip` (iproute2) for the gateway,
`nvidia-smi` for the GPU section.

## Settings

Click ⚙ in the top-right corner. Changes are saved to `~/.config/system-monitor-widget/settings.json`.

- **Layout:** show, hide and reorder sections (Clock, CPU & Memory, GPU, Battery, Storage, Network, Top processes); pick storage drives
- **Look:** theme, accent colour, opacity, size, normal/compact density; 12/24-hour clock, seconds, date
- **Data:** processes shown (1–10), process columns, update interval, red-alert threshold, GB/GiB, Mbps/MB/s, °C/°F, network details, network speed graph
- **Window:** corner, keep below other windows, click-through (only ⚙ stays clickable), reset to defaults

The GPU section reads NVIDIA cards through `nvidia-smi`; it is off by default.

## Notes

- The storage section shows `/` by default; pick other mounted drives under ⚙ → Storage drives.
- Nothing is sent over the network; all data is read locally with psutil, `ip` and `nmcli`.
