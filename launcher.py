#!/usr/bin/env python3
"""System Monitor Desktop Widget — GTK3 + WebKit2"""

import gi, ipaddress, json, os, re, subprocess, threading, time
gi.require_version('Gtk',     '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib, Gdk


import psutil

# ── Position: bottom-right corner with 20px margin ──────────
WIDGET_W = 420
WIDGET_H = 860
MARGIN   = 20
ZOOM     = 1.15  # scales the whole widget; window auto-fits content

# ── User settings (changed from the ⚙ panel in the widget) ──
SETTINGS_PATH = os.path.expanduser('~/.config/system-monitor-widget/settings.json')
DEFAULT_SETTINGS = {
    'sections': {'clock': True, 'cpumem': True, 'storage': True,
                 'network': True, 'procs': True},
    'zoom':     ZOOM,
    'corner':   'bottom-right',
    'interval': 1,
    'theme':    'dark',
    'accent':   '#58a6ff',
    'opacity':  1.0,
    'drives':   ['/'],  # mount points shown in the Storage section
    'procs':    5,      # processes listed per column (1..MAX_PROCS)
}
MAX_PROCS = 10

CORNERS = ('bottom-right', 'bottom-left', 'top-right', 'top-left')
THEMES  = ('dark', 'midnight', 'graphite', 'black', 'light')

def _num(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return min(max(v, lo), hi) if v == v else default  # v != v for NaN

def clean_settings(new, base=DEFAULT_SETTINGS):
    """Merge untrusted settings (file or page) onto base, keeping only valid values."""
    if not isinstance(new, dict):
        new = {}
    s = json.loads(json.dumps(base))
    sections = new.get('sections')
    if isinstance(sections, dict):
        for k in s['sections']:
            if isinstance(sections.get(k), bool):
                s['sections'][k] = sections[k]
    if 'zoom' in new:
        s['zoom'] = _num(new['zoom'], 0.5, 2.0, s['zoom'])
    if 'interval' in new:
        s['interval'] = int(_num(new['interval'], 1, 60, s['interval']))
    if 'procs' in new:
        s['procs'] = int(_num(new['procs'], 1, MAX_PROCS, s['procs']))
    if 'opacity' in new:
        s['opacity'] = _num(new['opacity'], 0.4, 1.0, s['opacity'])
    if new.get('corner') in CORNERS:
        s['corner'] = new['corner']
    if new.get('theme') in THEMES:
        s['theme'] = new['theme']
    if isinstance(new.get('accent'), str) and re.fullmatch(r'#[0-9a-fA-F]{6}', new['accent']):
        s['accent'] = new['accent']
    if isinstance(new.get('drives'), list):
        s['drives'] = [d for d in new['drives']
                       if isinstance(d, str) and d.startswith('/') and len(d) < 256][:20]
    return s

def load_settings():
    try:
        with open(SETTINGS_PATH) as f:
            return clean_settings(json.load(f))
    except (OSError, ValueError):
        return clean_settings({})

def save_settings(s):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    tmp = SETTINGS_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, SETTINGS_PATH)

def screen_geometry():
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    geo = monitor.get_workarea()  # excludes panels/taskbar
    return geo.x, geo.y, geo.width, geo.height

# ── Collect real system data ─────────────────────────────────
_prev_net = psutil.net_io_counters()
_prev_net_time = time.time()
_prev_iface = None

# ── Active network details (refreshed every NET_INFO_TTL s) ──
NET_INFO_TTL = 5
_net_info = {'iface': None}
_net_info_time = 0

def _run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout.strip()
    except Exception:
        return ''

def net_info():
    global _net_info, _net_info_time
    if time.time() - _net_info_time < NET_INFO_TTL:
        return _net_info
    _net_info_time = time.time()

    info = {'iface': None, 'name': None, 'type': None, 'ip': None,
            'subnet': None, 'gateway': None, 'dns': []}
    # Default route -> active interface + gateway
    for line in _run('ip', 'route', 'show', 'default').splitlines():
        parts = line.split()
        if 'dev' in parts:
            info['iface'] = parts[parts.index('dev') + 1]
            if 'via' in parts:
                info['gateway'] = parts[parts.index('via') + 1]
            break
    if not info['iface']:
        _net_info = info
        return info

    # Connection name (Wi-Fi SSID / profile) and type from NetworkManager
    for line in _run('nmcli', '-t', '-f', 'NAME,DEVICE,TYPE', 'con', 'show', '--active').splitlines():
        f = line.split(':')
        if len(f) >= 3 and f[-2] == info['iface']:
            info['name'] = ':'.join(f[:-2]).replace('\\', '')
            t = f[-1]
            info['type'] = 'Wi-Fi' if 'wireless' in t else 'Ethernet' if 'ethernet' in t else t
            break
    if info['type'] == 'Wi-Fi':
        for line in _run('nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi', 'list', '--rescan', 'no').splitlines():
            if line.startswith('yes:'):
                info['name'] = line[4:].replace('\\', '') or info['name']
                break

    # IPv4 address + subnet
    for a in psutil.net_if_addrs().get(info['iface'], []):
        if a.family.name == 'AF_INET':
            info['ip'] = a.address
            if a.netmask:
                net = ipaddress.IPv4Network(f'{a.address}/{a.netmask}', strict=False)
                info['prefix'] = net.prefixlen
                info['subnet'] = f'{net.with_prefixlen} ({a.netmask})'
            break

    # DNS servers for this interface, fallback to resolv.conf
    dns = _run('nmcli', '-t', '-g', 'IP4.DNS', 'dev', 'show', info['iface'])
    info['dns'] = [d.strip() for d in dns.replace('|', '\n').splitlines() if d.strip()]
    if not info['dns']:
        try:
            with open('/etc/resolv.conf') as f:
                info['dns'] = [l.split()[1] for l in f if l.startswith('nameserver')]
        except OSError:
            pass

    _net_info = info
    return info

# ── Mounted drives (list refreshed every DRIVES_TTL s, usage every tick) ──
DRIVES_TTL = 10
_drives = []
_drives_time = 0

def drives():
    """Real mounted filesystems (no loop/snap mounts), one entry per device."""
    global _drives, _drives_time
    if time.time() - _drives_time >= DRIVES_TTL:
        _drives_time = time.time()
        seen, found = set(), []
        for p in psutil.disk_partitions(all=False):
            if p.device in seen or p.device.startswith('/dev/loop') or p.mountpoint.startswith('/snap/'):
                continue
            seen.add(p.device)
            found.append(p.mountpoint)
        _drives = sorted(found, key=lambda m: (m != '/', m))
    out = []
    for m in _drives:
        try:
            u = psutil.disk_usage(m)
        except OSError:
            continue  # unmounted since the last scan
        out.append({'mount': m, 'used': u.used / 1e9, 'total': u.total / 1e9})
    return out

def collect():
    global _prev_net, _prev_net_time, _prev_iface

    cpu_pct   = psutil.cpu_percent(interval=None)
    cpu_freq  = psutil.cpu_freq()
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_temp  = None
    try:
        temps = psutil.sensors_temperatures()
        for key in ('coretemp', 'k10temp', 'cpu_thermal', 'acpitz'):
            if key in temps and temps[key]:
                cpu_temp = max(e.current for e in temps[key])
                break
    except Exception:
        pass

    mem  = psutil.virtual_memory()

    # Network delta on the active interface only
    net      = net_info()
    now_net  = psutil.net_io_counters(pernic=True).get(net['iface']) or psutil.net_io_counters()
    now_time = time.time()
    dt       = max(now_time - _prev_net_time, 0.001)
    net_in_mbps  = (now_net.bytes_recv - _prev_net.bytes_recv) / dt / 125000
    net_out_mbps = (now_net.bytes_sent - _prev_net.bytes_sent) / dt / 125000
    if net['iface'] != _prev_iface:
        net_in_mbps = net_out_mbps = 0  # interface changed
    _prev_iface    = net['iface']
    _prev_net      = now_net
    _prev_net_time = now_time

    # Top processes: the 10 busiest by CPU plus the 10 largest by memory
    procs = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_info']):
        try:
            mi  = p.info['memory_info']
            mem_gb = mi.rss / 1e9 if mi else 0
            procs.append({
                'pid':  p.info['pid'],
                'name': p.info['name'] or '?',
                'cpu':  p.info['cpu_percent'] or 0,
                'mem':  mem_gb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top = {p['pid']: p for key in ('cpu', 'mem')
           for p in sorted(procs, key=lambda p: p[key], reverse=True)[:MAX_PROCS]}

    return {
        'cpu_pct':    cpu_pct,
        'cpu_freq':   cpu_freq.current / 1000 if cpu_freq else None,
        'cpu_cores':  cpu_cores,
        'cpu_temp':   cpu_temp,
        'mem_used':   mem.used    / 1e9,
        'mem_free':   mem.available / 1e9,
        'mem_total':  mem.total   / 1e9,
        'disks':      drives(),
        'net':        net,
        'net_in_mbps':  max(0, net_in_mbps),
        'net_out_mbps': max(0, net_out_mbps),
        'processes':  list(top.values()),
    }

# ── GTK window ───────────────────────────────────────────────
class Widget(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.sx, self.sy, self.sw, self.sh = screen_geometry()
        self.settings = load_settings()
        self.set_default_size(WIDGET_W, WIDGET_H)
        self.set_title('system-monitor-widget')

        # Frameless, no taskbar/pager entry, all workspaces
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()

        # Opaque window: a transparent (RGBA) window flickers on every
        # update with WebKitGTK 4.1 under KDE Wayland/XWayland.

        # WebView
        wv_settings = WebKit2.Settings()
        wv_settings.set_enable_javascript(True)
        wv_settings.set_hardware_acceleration_policy(
            WebKit2.HardwareAccelerationPolicy.NEVER)

        # Page -> Python messages (settings panel)
        ucm = WebKit2.UserContentManager()
        ucm.register_script_message_handler('widget')
        ucm.connect('script-message-received::widget', self._on_message)

        self.wv = WebKit2.WebView.new_with_user_content_manager(ucm)
        self.wv.set_settings(wv_settings)
        self.wv.set_background_color(Gdk.RGBA(13/255, 17/255, 23/255, 1))
        self.wv.set_zoom_level(self.settings['zoom'])
        self.wv.connect('load-changed', self._on_load)
        self.w, self.h = WIDGET_W, WIDGET_H

        html_path = os.path.join(os.path.dirname(__file__), 'widget.html')
        self.wv.load_uri('file://' + html_path)

        self.add(self.wv)
        self.show_all()
        # Transparency via compositor window opacity (not an RGBA visual,
        # which flickers with WebKitGTK 4.1)
        self.set_opacity(self.settings['opacity'])

        # Position in the chosen corner after the window is mapped
        self._reposition()
        GLib.idle_add(self._reposition)  # re-apply after compositor settles

        # Warm up psutil CPU measurement
        psutil.cpu_percent(interval=None)
        time.sleep(0.1)
        psutil.cpu_percent(interval=None)

        # Push real data every N seconds (settings: interval)
        self._push_id = GLib.timeout_add(int(self.settings['interval'] * 1000), self._push_data)
        # Keep the window fitted to the content as it changes (data arrives
        # after load, process names vary, network goes up/down)
        GLib.timeout_add(2000, self._fit_periodic)

    def _reposition(self):
        corner = self.settings.get('corner', 'bottom-right')
        x = self.sx + MARGIN if 'left' in corner else self.sx + self.sw - self.w - MARGIN
        y = self.sy + MARGIN if 'top' in corner else self.sy + self.sh - self.h - MARGIN
        self.move(x, y)
        return False  # run once

    def _on_message(self, ucm, js_result):
        try:
            msg = json.loads(js_result.get_js_value().to_string())
        except Exception as e:
            print(f"[widget] bad message: {e}")
            return
        if not isinstance(msg, dict):
            return
        action = msg.get('action')
        if action == 'fit':
            GLib.timeout_add(50, self._fit)
        elif action == 'bg':
            rgba = Gdk.RGBA()
            if rgba.parse(str(msg.get('color', ''))):
                self.wv.set_background_color(rgba)
        elif action == 'opacity':  # live preview while dragging the slider
            self.set_opacity(_num(msg.get('value'), 0.4, 1.0, self.settings['opacity']))
        elif action == 'quit':
            Gtk.main_quit()
        elif action == 'save':
            old = self.settings
            self.settings = clean_settings(msg.get('settings'), old)
            save_settings(self.settings)
            self.set_opacity(self.settings['opacity'])
            if self.settings['zoom'] != old['zoom']:
                self.wv.set_zoom_level(self.settings['zoom'])
            if self.settings['interval'] != old['interval']:
                GLib.source_remove(self._push_id)
                self._push_id = GLib.timeout_add(int(self.settings['interval'] * 1000), self._push_data)
            self._reposition()
            GLib.timeout_add(50, self._fit)

    def _on_load(self, wv, event):
        if event == WebKit2.LoadEvent.FINISHED:
            self.wv.run_javascript(f"applySettings({json.dumps(self.settings)});", None, None, None)
            # Measure again once real data (process list) has rendered
            for ms in (100, 1500):
                GLib.timeout_add(ms, self._fit)

    def _fit_periodic(self):
        self._fit()
        return True  # keep repeating

    def _fit(self):
        js = ("(() => { const r = document.querySelector('.widget')"
              ".getBoundingClientRect(); return JSON.stringify([r.width, r.height, innerWidth]); })()")
        self.wv.run_javascript(js, None, self._fit_done, None)
        return False

    def _fit_done(self, wv, res, _):
        try:
            w, h, vw = json.loads(wv.run_javascript_finish(res).get_js_value().to_string())
        except Exception as e:
            print(f"[widget] fit error: {e}")
            return
        # Real CSS-px -> window-px ratio (ZOOM x any desktop scaling WebKit applies)
        scale = wv.get_allocated_width() / vw if vw else ZOOM
        self.w = min(int(w * scale + 0.999), self.sw - 2 * MARGIN)
        self.h = min(int(h * scale + 0.999), self.sh - 2 * MARGIN)
        if abs(wv.get_allocated_width() - self.w) <= 1 and abs(wv.get_allocated_height() - self.h) <= 1:
            return  # already fits
        GLib.timeout_add(200, self._fit)  # re-check once the resize lands
        self.set_size_request(self.w, self.h)
        self.resize(self.w, self.h)
        self._reposition()

    def _push_data(self):
        try:
            data = collect()
            js   = f"window.SYSDATA = {json.dumps(data)};"
            self.wv.run_javascript(js, None, None, None)
        except Exception as e:
            print(f"[widget] collect error: {e}")
        return True  # keep repeating


def main():
    win = Widget()
    win.connect('destroy', Gtk.main_quit)
    Gtk.main()

if __name__ == '__main__':
    main()
