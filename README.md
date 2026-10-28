# System Monitor Widget

A small always-on-desktop system monitor for Linux, built with GTK3 + WebKit2GTK.

It shows a clock, CPU usage/frequency/temperature, memory, disk usage, the active
network connection (name, IP, gateway, DNS, live up/down speed) and the top
processes by CPU and memory. A ⚙ panel lets you pick sections, theme, accent
colour, size, corner, opacity and update interval.

## Requirements

- Python 3
- GTK 3 and WebKit2GTK 4.1 with Python bindings
- [psutil](https://pypi.org/project/psutil/)
- pycairo (`python3-gi-cairo` on Debian/Ubuntu), for click-through
- NetworkManager (`nmcli`) and `iproute2` (`ip`) for network details

On Debian/Ubuntu:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 python3-psutil network-manager iproute2
```

## Install

```bash
mkdir -p ~/.local/share/system-monitor-widget
cp launcher.py widget.html ~/.local/share/system-monitor-widget/
python3 ~/.local/share/system-monitor-widget/launcher.py
```

To start it on login, copy the desktop entry and replace `%h` with your home directory:

```bash
sed "s|%h|$HOME|" system-monitor-widget.desktop > ~/.config/autostart/system-monitor-widget.desktop
```

`GDK_BACKEND=x11` in the desktop entry lets the widget position itself on Wayland sessions.

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
