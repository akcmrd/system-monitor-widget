# System Monitor Widget

A small always-on-desktop system monitor for Linux, built with GTK3 + WebKit2GTK.

It shows a clock, CPU usage/frequency/temperature, memory, disk usage, the active
network connection (name, IP, gateway, DNS, live up/down speed) and the top
processes by CPU and memory, plus optional GPU (NVIDIA) and battery sections.
A ⚙ panel lets you choose and reorder sections, theme, units, clock style and more.

## Install

Works on Linux desktops (KDE, GNOME, XFCE, …) with apt, dnf, pacman or zypper.

```bash
git clone https://github.com/akcmrd/system-monitor-widget.git ~/system-monitor-widget
cd ~/system-monitor-widget
./install.sh
```

The installer:

1. installs the dependencies (Python GObject + cairo bindings, GTK 3, WebKit2GTK 4.1, psutil), asking for your password only if something is missing
2. adds **System Monitor Widget** to your app menu
3. asks whether to start it on login, add a desktop icon, and start it now

The widget runs from the folder you cloned, so keep that folder. To update later:

```bash
cd ~/system-monitor-widget && git pull
```

then close the widget (⚙ → Close widget) and start it again from the app menu.

To remove the shortcuts: `./install.sh --uninstall` (your settings and the folder stay; delete them by hand if you want).

NetworkManager (`nmcli`) is optional; without it the network section shows less detail.

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
