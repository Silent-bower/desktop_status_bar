"""桌面状态栏 — 实时系统监控 + 快捷启动
Auto-hide on right edge, slides out on mouse hover.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys
import json
import shutil
import time
import threading

try:
    import psutil
except ImportError:
    root = tk.Tk()
    root.withdraw()
    from tkinter import messagebox
    messagebox.showerror('缺少依赖', '请先运行 setup.bat 安装依赖，或手动执行：\npip install psutil')
    sys.exit(1)

try:
    from ctypes import windll, Structure, c_long, byref

    class RECT(Structure):
        _fields_ = [("left", c_long), ("top", c_long),
                     ("right", c_long), ("bottom", c_long)]

    HAS_CTYPES = True
except Exception:
    HAS_CTYPES = False

# ═══════════════════════ Configuration ═══════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')

TRANSPARENT_KEY = '#010101'

THEME = {
    "bg":         "#1e1e2e",
    "bg_section": "#181825",
    "text":       "#cdd6f4",
    "text_dim":   "#6c7086",
    "accent":     "#cba6f7",
    "border":     "#313244",
    "btn_hover":  "#45475a",
    "bar_bg":     "#313244",
    "cpu_colors": ["#a6e3a1", "#f9e2af", "#fab387", "#f38ba8"],
    "ram_color":  "#89b4fa",
    "disk_color": "#f9e2af",
    "net_up":     "#a6e3a1",
    "net_down":   "#89b4fa",
}

PEEK         = 4
ANIM_STEP    = 35
ANIM_MS      = 10
HIDE_DELAY   = 800
TRIGGER_ZONE = 10
EDGE_MARGIN_Y = 30
MAX_HEIGHT_RATIO = 0.84
LAUNCH_PANEL_HEIGHT = 210

def default_shortcuts():
    return [
        {"id": "opencode", "name": "OpenCode", "icon": "⌨️", "kind": "command",
         "target": "opencode", "group": "开发", "enabled": True},
        {"id": "sketchup", "name": "SketchUp", "icon": "📐", "kind": "executable",
         "target": "auto", "detect": "SketchUp", "group": "设计", "enabled": True},
        {"id": "autocad", "name": "AutoCAD", "icon": "📏", "kind": "executable",
         "target": "auto", "detect": "AutoCAD", "group": "设计", "enabled": True},
        {"id": "photoshop", "name": "Photoshop", "icon": "🎨", "kind": "executable",
         "target": "auto", "detect": "Photoshop", "group": "设计", "enabled": True},
        {"id": "gemini", "name": "Gemini", "icon": "✦", "kind": "url",
         "target": "https://gemini.google.com", "browser": "chrome", "group": "AI", "enabled": True},
        {"id": "chatgpt", "name": "ChatGPT", "icon": "💬", "kind": "url",
         "target": "https://chatgpt.com", "browser": "chrome", "group": "AI", "enabled": True},
        {"id": "godot", "name": "Godot", "icon": "🎮", "kind": "executable",
         "target": "D:\\下载\\Godot_v4.6.1-stable_win64.exe\\Godot_v4.6.1-stable_win64.exe",
         "group": "开发", "enabled": True},
    ]

def normalize_shortcut(item):
    if not isinstance(item, dict):
        return None

    if 'kind' in item or 'target' in item:
        shortcut = dict(item)
    else:
        legacy_type = item.get('type', 'exe')
        shortcut = {
            'id': item.get('id') or item.get('name', '').strip().lower().replace(' ', '_'),
            'name': item.get('name', 'App'),
            'icon': item.get('icon', '▸'),
            'group': item.get('group', '快捷启动'),
            'enabled': item.get('enabled', True),
        }
        if legacy_type == 'cli':
            shortcut['kind'] = 'command'
            shortcut['target'] = item.get('command', '')
        elif legacy_type == 'url':
            shortcut['kind'] = 'url'
            shortcut['target'] = item.get('url', '')
            shortcut['browser'] = item.get('browser', 'chrome')
        else:
            shortcut['kind'] = 'executable'
            shortcut['target'] = item.get('path', 'auto')
            shortcut['detect'] = item.get('detect', item.get('name', ''))

    shortcut['id'] = shortcut.get('id') or shortcut.get('name', 'item').strip().lower().replace(' ', '_')
    shortcut['name'] = shortcut.get('name', 'App')
    shortcut['icon'] = shortcut.get('icon', '▸')
    shortcut['group'] = shortcut.get('group', '快捷启动')
    shortcut['enabled'] = bool(shortcut.get('enabled', True))
    shortcut['kind'] = shortcut.get('kind', 'executable')
    shortcut['target'] = shortcut.get('target', '')
    if shortcut['kind'] == 'url':
        shortcut['browser'] = shortcut.get('browser', 'chrome')
    if shortcut['kind'] == 'executable':
        shortcut['detect'] = shortcut.get('detect', shortcut.get('name', ''))
    return shortcut

def normalize_shortcuts(items):
    shortcuts = []
    for item in items or []:
        shortcut = normalize_shortcut(item)
        if shortcut:
            shortcuts.append(shortcut)
    return shortcuts

def load_config():
    defaults = {
        "opacity": 0.65,
        "width": 186,
        "update_interval_ms": 1500,
        "shortcuts": default_shortcuts(),
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user = json.load(f)
            for key, value in user.items():
                if key not in ('apps', 'shortcuts'):
                    defaults[key] = value
            defaults['shortcuts'] = normalize_shortcuts(
                user.get('shortcuts', user.get('apps', defaults['shortcuts']))
            ) or default_shortcuts()
        except Exception:
            pass
    else:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(defaults, f, indent=2, ensure_ascii=False)
    return defaults

def save_config(cfg):
    data = {
        "opacity": cfg.get("opacity", 0.65),
        "width": cfg.get("width", 186),
        "update_interval_ms": cfg.get("update_interval_ms", 1500),
        "shortcuts": normalize_shortcuts(cfg.get("shortcuts", [])),
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ═══════════════════════ System Monitor ═══════════════════════

class SysMonitor:
    def __init__(self):
        self._prev_net = psutil.net_io_counters()
        self._prev_t = time.time()
        psutil.cpu_percent(interval=None)

    def snapshot(self):
        s = {}
        s['cpu'] = psutil.cpu_percent(interval=None)
        s['cpu_freq'] = getattr(psutil.cpu_freq(), 'current', 0)

        mem = psutil.virtual_memory()
        s['ram_pct'] = mem.percent
        s['ram_used'] = mem.used / (1024 ** 3)
        s['ram_total'] = mem.total / (1024 ** 3)

        dsk = psutil.disk_usage('C:\\')
        s['disk_pct'] = dsk.percent
        s['disk_used'] = dsk.used / (1024 ** 3)
        s['disk_total'] = dsk.total / (1024 ** 3)

        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - self._prev_t, 0.1)
        s['net_up'] = (net.bytes_sent - self._prev_net.bytes_sent) / dt
        s['net_down'] = (net.bytes_recv - self._prev_net.bytes_recv) / dt
        self._prev_net = net
        self._prev_t = now

        try:
            bat = psutil.sensors_battery()
            s['battery'] = bat.percent if bat else None
            s['charging'] = bat.power_plugged if bat else False
        except Exception:
            s['battery'] = None

        return s

# ═══════════════════════ App Launcher ═══════════════════════

class Launcher:
    _chrome = None

    @classmethod
    def chrome(cls):
        if cls._chrome and os.path.exists(cls._chrome):
            return cls._chrome
        for p in [
            os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
        ]:
            if os.path.exists(p):
                cls._chrome = p
                return p
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe')
            val = winreg.QueryValue(key, None)
            winreg.CloseKey(key)
            if val and os.path.exists(val):
                cls._chrome = val
                return val
        except Exception:
            pass
        w = shutil.which('chrome')
        if w:
            cls._chrome = w
        return w

    @staticmethod
    def _find_in_dirs(base_names, sub_patterns):
        bases = [os.environ.get('ProgramFiles', r'C:\Program Files'),
                 os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')]
        for base in bases:
            for bname in base_names:
                d = os.path.join(base, bname)
                if not os.path.isdir(d):
                    continue
                try:
                    for entry in sorted(os.listdir(d), reverse=True):
                        for pat in sub_patterns:
                            exe = os.path.join(d, entry, pat)
                            if os.path.exists(exe):
                                return exe
                except OSError:
                    pass
        return None

    @staticmethod
    def _find_in_registry(app_paths, uninstall_names):
        try:
            import winreg
        except Exception:
            return None

        app_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths'),
        ]
        for root, base in app_roots:
            for exe_name in app_paths:
                try:
                    key = winreg.OpenKey(root, fr'{base}\{exe_name}')
                    val = winreg.QueryValue(key, None)
                    winreg.CloseKey(key)
                    if val and os.path.exists(val):
                        return val
                except OSError:
                    pass

        uninstall_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]
        uninstall_names = [name.lower() for name in uninstall_names]
        for root, base in uninstall_roots:
            try:
                key = winreg.OpenKey(root, base)
            except OSError:
                continue
            try:
                count = winreg.QueryInfoKey(key)[0]
                for idx in range(count):
                    try:
                        sub_name = winreg.EnumKey(key, idx)
                        sub_key = winreg.OpenKey(key, sub_name)
                    except OSError:
                        continue
                    try:
                        try:
                            display_name = (winreg.QueryValueEx(sub_key, 'DisplayName')[0] or '').lower()
                        except OSError:
                            display_name = ''
                        try:
                            install_loc = winreg.QueryValueEx(sub_key, 'InstallLocation')[0]
                        except OSError:
                            install_loc = ''
                        try:
                            display_icon = winreg.QueryValueEx(sub_key, 'DisplayIcon')[0]
                        except OSError:
                            display_icon = ''
                    finally:
                        winreg.CloseKey(sub_key)

                    if not any(name in display_name for name in uninstall_names):
                        continue

                    for candidate in (display_icon, install_loc):
                        if not candidate:
                            continue
                        cleaned = candidate.split(',')[0].strip().strip('"')
                        if os.path.isfile(cleaned):
                            return cleaned
                        if os.path.isdir(cleaned):
                            for exe_name in app_paths:
                                exe = os.path.join(cleaned, exe_name)
                                if os.path.exists(exe):
                                    return exe
            finally:
                winreg.CloseKey(key)
        return None

    @classmethod
    def find_app(cls, name):
        nl = name.lower()
        if 'sketchup' in nl:
            return (
                cls._find_in_registry(['SketchUp.exe'], ['sketchup'])
                or cls._find_in_dirs(['SketchUp'], ['SketchUp.exe', r'SketchUp\SketchUp.exe'])
                or shutil.which('SketchUp')
                or shutil.which('SketchUp.exe')
            )
        if 'photoshop' in nl:
            return (
                cls._find_in_registry(['Photoshop.exe'], ['photoshop', 'adobe photoshop'])
                or cls._find_in_dirs(['Adobe'], ['Photoshop.exe'])
                or shutil.which('Photoshop')
                or shutil.which('Photoshop.exe')
            )
        if 'autocad' in nl or nl == 'cad' or ' cad' in nl:
            return (
                cls._find_in_registry(
                    ['acad.exe', 'acadlt.exe', 'AutoCAD.exe'],
                    ['autocad', 'autocad lt', 'autodesk autocad'],
                )
                or cls._find_in_dirs(['Autodesk'], ['acad.exe', 'acadlt.exe', 'AutoCAD.exe'])
                or shutil.which('acad')
                or shutil.which('acad.exe')
                or shutil.which('acadlt')
                or shutil.which('acadlt.exe')
            )
        return shutil.which(name)

    @staticmethod
    def _normalize_args(args):
        if not args:
            return []
        if isinstance(args, list):
            return [str(arg) for arg in args if str(arg).strip()]
        return [str(args)]

    @classmethod
    def launch(cls, cfg):
        kind = cfg.get('kind')
        if not kind:
            legacy_type = cfg.get('type', 'exe')
            kind = {'cli': 'command', 'url': 'url', 'exe': 'executable'}.get(legacy_type, legacy_type)
        try:
            if kind == 'command':
                cmd = cfg.get('target') or cfg.get('command', '')
                subprocess.Popen(f'start "" {cmd}', shell=True)
            elif kind == 'url':
                url = cfg.get('target') or cfg.get('url', '')
                browser = cfg.get('browser', 'chrome')
                if browser == 'chrome':
                    ch = cls.chrome()
                else:
                    ch = None
                if ch and url:
                    subprocess.Popen([ch, url])
                else:
                    os.startfile(url)
            elif kind == 'executable':
                path = cfg.get('target', cfg.get('path', 'auto'))
                if path == 'auto':
                    path = cls.find_app(cfg.get('detect', cfg.get('name', '')))
                args = cls._normalize_args(cfg.get('args'))
                if path and os.path.exists(path):
                    subprocess.Popen([path, *args])
                else:
                    subprocess.Popen(f'start "" "{cfg.get("name", "")}"', shell=True)
            elif kind == 'system':
                target = cfg.get('target', '')
                if target:
                    os.startfile(target)
            return True, ''
        except Exception as e:
            return False, str(e)

# ═══════════════════════ UI Helpers ═══════════════════════

def fmt_speed(bps):
    if bps < 1024:
        return f'{bps:.0f} B/s'
    if bps < 1048576:
        return f'{bps / 1024:.1f} K/s'
    return f'{bps / 1048576:.1f} M/s'

def cpu_color(pct):
    c = THEME['cpu_colors']
    if pct < 30: return c[0]
    if pct < 60: return c[1]
    if pct < 85: return c[2]
    return c[3]

def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r,
           x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return cv.create_polygon(pts, smooth=True, **kw)

# ═══════════════════════ Main Application ═══════════════════════

class StatusBar:
    def __init__(self):
        self.cfg = load_config()
        self.mon = SysMonitor()
        self.t = THEME

        self.root = tk.Tk()
        self.root.withdraw()

        self._is_shown = False
        self._animating = False
        self._hide_job = None
        self._pinned = False
        self._settings_window = None
        self._settings_items = []
        self._settings_selected_index = None

        self._setup_window()
        self._build_ui()

        self._x_shown = self.scr_w - self.W
        self._x_hidden = self.scr_w - PEEK
        self.root.geometry(f'+{self._x_hidden}+{self._win_y}')

        self.root.deiconify()
        self._tick_stats()
        self._poll_mouse()

    # ──────── Window ────────

    def _setup_window(self):
        r = self.root
        r.title('状态栏')
        r.overrideredirect(True)
        r.attributes('-topmost', True)
        r.attributes('-alpha', self.cfg.get('opacity', 0.65))
        r.configure(bg=TRANSPARENT_KEY)
        r.attributes('-transparentcolor', TRANSPARENT_KEY)

        self.W = self.cfg.get('width', 186)

        if HAS_CTYPES:
            rect = RECT()
            windll.user32.SystemParametersInfoW(48, 0, byref(rect), 0)
            self.scr_w = rect.right
            self.scr_h = rect.bottom - rect.top
            self.scr_top = rect.top
        else:
            self.scr_w = r.winfo_screenwidth()
            self.scr_h = r.winfo_screenheight() - 48
            self.scr_top = 0

        self._win_y = self.scr_top

    # ──────── Auto-hide ────────

    def _poll_mouse(self):
        try:
            if self._settings_window is not None and self._settings_window.winfo_exists():
                self._cancel_hide()
                if not self._is_shown:
                    self._slide_show()
                self.root.after(80, self._poll_mouse)
                return

            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            wx = self.root.winfo_x()
            wy = self._win_y
            wh = self._win_h

            mouse_at_edge = mx >= self.scr_w - TRIGGER_ZONE
            mouse_in_bar = (wx <= mx <= wx + self.W) and (wy <= my <= wy + wh)

            if (mouse_at_edge or mouse_in_bar) and not self._is_shown:
                self._cancel_hide()
                self._slide_show()
            elif not mouse_at_edge and not mouse_in_bar and self._is_shown and not self._pinned:
                self._schedule_hide()
        except Exception:
            pass

        self.root.after(80, self._poll_mouse)

    def _slide_show(self):
        if self._is_shown and not self._animating:
            return
        self._is_shown = True
        self._animate_to(self._x_shown)

    def _slide_hide(self):
        if not self._is_shown and not self._animating:
            return
        self._is_shown = False
        self._animate_to(self._x_hidden)

    def _schedule_hide(self):
        if self._pinned:
            return
        if self._hide_job is None:
            self._hide_job = self.root.after(HIDE_DELAY, self._do_hide)

    def _do_hide(self):
        self._hide_job = None
        if self._pinned:
            return
        try:
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            wx = self.root.winfo_x()
            mouse_at_edge = mx >= self.scr_w - TRIGGER_ZONE
            mouse_in_bar = (wx <= mx <= wx + self.W) and \
                           (self._win_y <= my <= self._win_y + self._win_h)
            if mouse_at_edge or mouse_in_bar:
                return
        except Exception:
            pass
        self._slide_hide()

    def _cancel_hide(self):
        if self._hide_job is not None:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None

    def _animate_to(self, target_x):
        current_x = self.root.winfo_x()
        dist = target_x - current_x

        if abs(dist) <= 2:
            self.root.geometry(f'+{target_x}+{self._win_y}')
            self._animating = False
            return

        self._animating = True
        step = ANIM_STEP if dist > 0 else -ANIM_STEP
        if abs(dist) < ANIM_STEP * 3:
            step = max(2, abs(dist) // 3) * (1 if dist > 0 else -1)

        new_x = current_x + step
        new_x = min(new_x, target_x) if step > 0 else max(new_x, target_x)

        self.root.geometry(f'+{new_x}+{self._win_y}')
        self.root.after(ANIM_MS, lambda: self._animate_to(target_x))

    # ──────── Build UI ────────

    def _build_ui(self):
        t = self.t
        TK = TRANSPARENT_KEY

        canvas = tk.Canvas(self.root, bg=TK, highlightthickness=0, bd=0)
        canvas.pack(fill='both', expand=True)
        self._canvas = canvas

        main = tk.Frame(canvas, bg=TK)
        self._main_frame = main
        canvas.create_window((0, 0), window=main, anchor='nw', width=self.W)

        # ── Header ──
        hdr = tk.Frame(main, bg=t['bg_section'], pady=6)
        hdr.pack(fill='x', pady=(0, 2))

        hdr_in = tk.Frame(hdr, bg=t['bg_section'])
        hdr_in.pack(fill='x', padx=10)

        tk.Label(hdr_in, text='⚡ 系统监控', font=('Microsoft YaHei UI', 9, 'bold'),
                 fg=t['accent'], bg=t['bg_section']).pack(side='left')

        close = tk.Label(hdr_in, text='✕', font=('Consolas', 10),
                         fg=t['text_dim'], bg=t['bg_section'], cursor='hand2')
        close.pack(side='right')
        close.bind('<Button-1>', lambda e: self.root.destroy())
        close.bind('<Enter>', lambda e: close.config(fg='#f38ba8'))
        close.bind('<Leave>', lambda e: close.config(fg=t['text_dim']))

        self._pin_btn = tk.Label(hdr_in, text='📌', font=('Segoe UI Emoji', 9),
                                 fg=t['text_dim'], bg=t['bg_section'], cursor='hand2')
        self._pin_btn.pack(side='right', padx=(0, 6))
        self._pin_btn.bind('<Button-1>', self._toggle_pin)
        self._pin_btn.bind('<Enter>', lambda e: self._pin_btn.config(fg=t['accent']))
        self._pin_btn.bind('<Leave>', lambda e: self._pin_btn.config(
            fg=t['accent'] if self._pinned else t['text_dim']))

        settings_btn = tk.Label(hdr_in, text='⚙', font=('Segoe UI Emoji', 9),
                                fg=t['text_dim'], bg=t['bg_section'], cursor='hand2')
        settings_btn.pack(side='right', padx=(0, 6))
        settings_btn.bind('<Button-1>', self._open_settings_panel)
        settings_btn.bind('<Enter>', lambda e: settings_btn.config(fg=t['accent']))
        settings_btn.bind('<Leave>', lambda e: settings_btn.config(fg=t['text_dim']))

        # ── Stats panel ──
        sf = tk.Frame(main, bg=t['bg'], pady=4)
        sf.pack(fill='x', pady=2)

        self.cpu_bar = self._stat_row(sf, 'CPU')
        self.ram_bar = self._stat_row(sf, '内存')
        self.disk_bar = self._stat_row(sf, '磁盘')

        self.freq_label = tk.Label(sf, text='', font=('Consolas', 7),
                                   fg=t['text_dim'], bg=t['bg'])
        self.freq_label.pack(fill='x', padx=12)

        nf = tk.Frame(sf, bg=t['bg'], pady=2)
        nf.pack(fill='x', padx=12)
        self.net_up_lbl = tk.Label(nf, text='↑ 0 B/s', font=('Consolas', 8),
                                   fg=t['net_up'], bg=t['bg'])
        self.net_up_lbl.pack(anchor='w')
        self.net_dn_lbl = tk.Label(nf, text='↓ 0 B/s', font=('Consolas', 8),
                                   fg=t['net_down'], bg=t['bg'])
        self.net_dn_lbl.pack(anchor='w')

        self.bat_frame = tk.Frame(sf, bg=t['bg'])
        self.bat_lbl = tk.Label(self.bat_frame, font=('Microsoft YaHei UI', 8),
                                fg=t['text_dim'], bg=t['bg'])
        self.bat_lbl.pack(fill='x', padx=12)

        # ── Launch panel ──
        lf = tk.Frame(main, bg=t['bg'], pady=2)
        lf.pack(fill='x', pady=2)

        lh = tk.Frame(lf, bg=t['bg_section'], pady=4)
        lh.pack(fill='x')
        tk.Label(lh, text='🚀 快捷启动', font=('Microsoft YaHei UI', 9, 'bold'),
                 fg=t['accent'], bg=t['bg_section']).pack(padx=10, anchor='w')

        launch_wrap = tk.Frame(lf, bg=t['bg'])
        launch_wrap.pack(fill='both', expand=True, padx=2, pady=(2, 0))

        launch_canvas = tk.Canvas(
            launch_wrap,
            bg=t['bg'],
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        launch_scroll = tk.Scrollbar(
            launch_wrap,
            orient='vertical',
            command=launch_canvas.yview,
            troughcolor=t['bg'],
            activebackground=t['btn_hover'],
            bg=t['bg_section'],
            width=10,
        )
        launch_canvas.configure(yscrollcommand=launch_scroll.set)
        launch_canvas.pack(side='left', fill='both', expand=True)
        launch_scroll.pack(side='right', fill='y')

        launch_list = tk.Frame(launch_canvas, bg=t['bg'])
        self._launch_canvas = launch_canvas
        self._launch_list = launch_list
        self._launch_scroll = launch_scroll
        self._launch_window = launch_canvas.create_window((0, 0), window=launch_list, anchor='nw')

        launch_canvas.bind('<Configure>', self._refresh_launch_scroll)
        launch_list.bind('<Configure>', self._refresh_launch_scroll)

        self._render_shortcuts()

        self.root.bind_all('<MouseWheel>', self._on_global_mousewheel, add='+')
        self.root.bind_all('<Button-4>', self._on_global_mousewheel, add='+')
        self.root.bind_all('<Button-5>', self._on_global_mousewheel, add='+')

        # Keep the launcher area at a fixed height so it scrolls reliably.
        self.root.update_idletasks()
        available_h = max(220, min(self.scr_h - EDGE_MARGIN_Y * 2, int(self.scr_h * MAX_HEIGHT_RATIO)))
        other_h = hdr.winfo_reqheight() + sf.winfo_reqheight() + lh.winfo_reqheight() + 24
        launch_max_h = max(110, available_h - other_h - 12)
        launch_h = min(LAUNCH_PANEL_HEIGHT, launch_max_h)
        launch_canvas.configure(height=launch_h)

        self.root.update_idletasks()
        self._refresh_launch_scroll()

        self.root.update_idletasks()
        ch = min(main.winfo_reqheight(), available_h)
        self._content_h = ch
        self._win_h = ch
        self._win_y = self.scr_top + max(EDGE_MARGIN_Y, (self.scr_h - ch) // 2)
        self.root.geometry(f'{self.W}x{ch}')
        canvas.config(scrollregion=(0, 0, self.W, ch))

        self.root.after(100, self._refresh_launch_scroll)

    def _toggle_pin(self, _e=None):
        self._pinned = not self._pinned
        t = self.t
        if self._pinned:
            self._pin_btn.config(fg=t['accent'])
            self._cancel_hide()
            self._slide_show()
        else:
            self._pin_btn.config(fg=t['text_dim'])

    def _render_shortcuts(self):
        if not hasattr(self, '_launch_list'):
            return
        for child in self._launch_list.winfo_children():
            child.destroy()

        current_group = None
        visible = False
        for app in self.cfg.get('shortcuts', []):
            if not app.get('enabled', True):
                continue
            group = app.get('group', '快捷启动')
            if group != current_group:
                self._group_label(self._launch_list, group)
                current_group = group
            self._app_btn(self._launch_list, app)
            visible = True

        if not visible:
            tk.Label(
                self._launch_list,
                text=' 暂无快捷启动项，点击右上角设置添加',
                font=('Microsoft YaHei UI', 8),
                fg=self.t['text_dim'],
                bg=self.t['bg'],
                anchor='w',
            ).pack(fill='x', padx=8, pady=8)

        tk.Frame(self._launch_list, bg=self.t['bg'], height=28).pack(fill='x')
        self._refresh_launch_scroll()

    def _open_settings_panel(self, _e=None):
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        self._settings_items = [dict(item) for item in self.cfg.get('shortcuts', [])]
        self._settings_selected_index = None

        win = tk.Toplevel(self.root)
        self._settings_window = win
        win.title('快捷启动设置')
        win.geometry('860x500')
        win.minsize(820, 460)
        win.configure(bg=self.t['bg'])
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', self._close_settings_panel)

        left = tk.Frame(win, bg=self.t['bg_section'], width=220)
        left.pack(side='left', fill='y')
        right = tk.Frame(win, bg=self.t['bg'])
        right.pack(side='right', fill='both', expand=True)

        tk.Label(left, text='快捷启动项', font=('Microsoft YaHei UI', 10, 'bold'),
                 fg=self.t['accent'], bg=self.t['bg_section']).pack(anchor='w', padx=12, pady=(12, 6))

        list_wrap = tk.Frame(left, bg=self.t['bg_section'])
        list_wrap.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self._settings_listbox = tk.Listbox(
            list_wrap,
            bg=self.t['bg'],
            fg=self.t['text'],
            selectbackground=self.t['btn_hover'],
            selectforeground=self.t['accent'],
            relief='flat',
            highlightthickness=0,
            activestyle='none',
        )
        list_scroll = tk.Scrollbar(list_wrap, orient='vertical', command=self._settings_listbox.yview)
        self._settings_listbox.configure(yscrollcommand=list_scroll.set)
        self._settings_listbox.pack(side='left', fill='both', expand=True)
        list_scroll.pack(side='right', fill='y')
        self._settings_listbox.bind('<<ListboxSelect>>', self._on_settings_select)

        btn_row = tk.Frame(left, bg=self.t['bg_section'])
        btn_row.pack(fill='x', padx=10, pady=(0, 12))
        self._settings_action_btn(btn_row, '新增', self._settings_add_item).pack(side='left', expand=True, fill='x')
        self._settings_action_btn(btn_row, '删除', self._settings_delete_item).pack(side='left', expand=True, fill='x', padx=6)

        tk.Label(right, text='编辑快捷启动', font=('Microsoft YaHei UI', 10, 'bold'),
                 fg=self.t['accent'], bg=self.t['bg']).pack(anchor='w', padx=14, pady=(12, 8))

        self._settings_vars = {
            'name': tk.StringVar(),
            'icon': tk.StringVar(),
            'kind': tk.StringVar(value='executable'),
            'target': tk.StringVar(),
            'group': tk.StringVar(value='快捷启动'),
            'detect': tk.StringVar(),
            'browser': tk.StringVar(value='chrome'),
            'enabled': tk.BooleanVar(value=True),
        }

        form = tk.Frame(right, bg=self.t['bg'])
        form.pack(fill='both', expand=True, padx=14)

        self._settings_entry(form, '名称', self._settings_vars['name'], 0)
        self._settings_entry(form, '图标', self._settings_vars['icon'], 1)
        self._settings_option(form, '类型', self._settings_vars['kind'], ['executable', 'url', 'command', 'system'], 2)
        self._settings_entry(form, '分组', self._settings_vars['group'], 3)
        self._settings_entry(form, '目标', self._settings_vars['target'], 4, with_browse=True)
        self._settings_entry(form, '自动识别名', self._settings_vars['detect'], 5)
        self._settings_option(form, '浏览器', self._settings_vars['browser'], ['chrome', 'default'], 6)
        tk.Checkbutton(
            form,
            text='启用此项',
            variable=self._settings_vars['enabled'],
            bg=self.t['bg'],
            fg=self.t['text'],
            selectcolor=self.t['bg_section'],
            activebackground=self.t['bg'],
            activeforeground=self.t['text'],
        ).grid(row=7, column=1, sticky='w', pady=(8, 0))

        hint = (
            '目标填写示例:\n'
            '- executable: 程序 .exe 路径，或写 auto 交给自动识别\n'
            '- url: 网站地址，例如 https://chat.openai.com\n'
            '- command: 命令行，例如 cursor 或 opencode\n'
            '- system: 本地文件夹或文件路径'
        )
        tk.Label(form, text=hint, justify='left', font=('Microsoft YaHei UI', 8),
                 fg=self.t['text_dim'], bg=self.t['bg']).grid(row=8, column=0, columnspan=3, sticky='w', pady=(12, 0))

        action_row = tk.Frame(right, bg=self.t['bg'])
        action_row.pack(fill='x', padx=14, pady=14)
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        action_row.grid_columnconfigure(2, weight=1)
        self._settings_action_btn(action_row, '保存当前项', self._settings_apply_form).grid(
            row=0, column=0, sticky='ew'
        )
        self._settings_action_btn(action_row, '保存并关闭', self._settings_save_all).grid(
            row=0, column=1, sticky='ew', padx=8
        )
        self._settings_action_btn(action_row, '取消', self._close_settings_panel).grid(
            row=0, column=2, sticky='ew'
        )

        self._refresh_settings_list()
        if self._settings_items:
            self._settings_listbox.selection_set(0)
            self._on_settings_select()
        else:
            self._settings_add_item()

    def _close_settings_panel(self):
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.destroy()
        self._settings_window = None
        self._settings_selected_index = None

    def _settings_action_btn(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.t['bg_section'],
            fg=self.t['text'],
            activebackground=self.t['btn_hover'],
            activeforeground=self.t['accent'],
            relief='flat',
            bd=0,
            padx=10,
            pady=6,
            cursor='hand2',
        )

    def _settings_entry(self, parent, label, var, row, with_browse=False):
        tk.Label(parent, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                 fg=self.t['text'], bg=self.t['bg']).grid(row=row, column=0, sticky='w', pady=5, padx=(0, 8))
        entry = tk.Entry(parent, textvariable=var, bg=self.t['bg_section'], fg=self.t['text'],
                         insertbackground=self.t['text'], relief='flat')
        entry.grid(row=row, column=1, sticky='ew', pady=5)
        if with_browse:
            tk.Button(parent, text='浏览', command=self._settings_browse_target,
                      bg=self.t['bg_section'], fg=self.t['text'],
                      activebackground=self.t['btn_hover'], activeforeground=self.t['accent'],
                      relief='flat', bd=0, padx=8, pady=4, cursor='hand2').grid(row=row, column=2, padx=(8, 0), pady=5)
        parent.grid_columnconfigure(1, weight=1)

    def _settings_option(self, parent, label, var, values, row):
        tk.Label(parent, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                 fg=self.t['text'], bg=self.t['bg']).grid(row=row, column=0, sticky='w', pady=5, padx=(0, 8))
        menu = tk.OptionMenu(parent, var, *values)
        menu.config(bg=self.t['bg_section'], fg=self.t['text'], activebackground=self.t['btn_hover'],
                    activeforeground=self.t['accent'], relief='flat', highlightthickness=0)
        menu['menu'].config(bg=self.t['bg_section'], fg=self.t['text'],
                            activebackground=self.t['btn_hover'], activeforeground=self.t['accent'])
        menu.grid(row=row, column=1, sticky='w', pady=5)

    def _refresh_settings_list(self):
        if not getattr(self, '_settings_listbox', None):
            return
        self._settings_listbox.delete(0, 'end')
        for item in self._settings_items:
            status = '' if item.get('enabled', True) else ' [停用]'
            group = item.get('group', '快捷启动')
            self._settings_listbox.insert('end', f"{group} / {item.get('name', '未命名')}{status}")

    def _settings_collect_form(self):
        shortcut = {
            'id': self._settings_vars['name'].get().strip().lower().replace(' ', '_') or 'shortcut',
            'name': self._settings_vars['name'].get().strip(),
            'icon': self._settings_vars['icon'].get().strip() or '▸',
            'kind': self._settings_vars['kind'].get().strip() or 'executable',
            'target': self._settings_vars['target'].get().strip(),
            'group': self._settings_vars['group'].get().strip() or '快捷启动',
            'enabled': bool(self._settings_vars['enabled'].get()),
        }
        detect = self._settings_vars['detect'].get().strip()
        browser = self._settings_vars['browser'].get().strip() or 'chrome'
        if shortcut['kind'] == 'executable':
            shortcut['detect'] = detect or shortcut['name']
            if not shortcut['target']:
                shortcut['target'] = 'auto'
        elif shortcut['kind'] == 'url':
            shortcut['browser'] = browser
        return shortcut

    def _settings_load_form(self, item):
        self._settings_vars['name'].set(item.get('name', ''))
        self._settings_vars['icon'].set(item.get('icon', ''))
        self._settings_vars['kind'].set(item.get('kind', 'executable'))
        self._settings_vars['target'].set(item.get('target', ''))
        self._settings_vars['group'].set(item.get('group', '快捷启动'))
        self._settings_vars['detect'].set(item.get('detect', ''))
        self._settings_vars['browser'].set(item.get('browser', 'chrome'))
        self._settings_vars['enabled'].set(bool(item.get('enabled', True)))

    def _on_settings_select(self, _e=None):
        if not getattr(self, '_settings_listbox', None):
            return
        selection = self._settings_listbox.curselection()
        if not selection:
            self._settings_selected_index = None
            return
        idx = selection[0]
        self._settings_selected_index = idx
        self._settings_load_form(self._settings_items[idx])

    def _settings_add_item(self):
        item = normalize_shortcut({
            'name': '新项目',
            'icon': '✨',
            'kind': 'url',
            'target': 'https://',
            'group': '快捷启动',
            'enabled': True,
        })
        self._settings_items.append(item)
        self._refresh_settings_list()
        idx = len(self._settings_items) - 1
        self._settings_listbox.selection_clear(0, 'end')
        self._settings_listbox.selection_set(idx)
        self._settings_listbox.see(idx)
        self._on_settings_select()

    def _settings_delete_item(self):
        if self._settings_selected_index is None:
            return
        del self._settings_items[self._settings_selected_index]
        self._refresh_settings_list()
        if self._settings_items:
            idx = min(self._settings_selected_index, len(self._settings_items) - 1)
            self._settings_listbox.selection_set(idx)
            self._on_settings_select()
        else:
            self._settings_selected_index = None
            self._settings_vars['name'].set('')
            self._settings_vars['icon'].set('')
            self._settings_vars['kind'].set('executable')
            self._settings_vars['target'].set('')
            self._settings_vars['group'].set('快捷启动')
            self._settings_vars['detect'].set('')
            self._settings_vars['browser'].set('chrome')
            self._settings_vars['enabled'].set(True)

    def _settings_apply_form(self):
        if self._settings_selected_index is None:
            messagebox.showwarning('未选择项目', '请先选择一个快捷启动项。')
            return False
        shortcut = self._settings_collect_form()
        if not shortcut.get('name'):
            messagebox.showwarning('名称不能为空', '请填写快捷启动名称。')
            return False
        if not shortcut.get('target'):
            messagebox.showwarning('目标不能为空', '请填写网址、程序路径或命令。')
            return False
        self._settings_items[self._settings_selected_index] = normalize_shortcut(shortcut)
        self._refresh_settings_list()
        self._settings_listbox.selection_clear(0, 'end')
        self._settings_listbox.selection_set(self._settings_selected_index)
        self._settings_listbox.see(self._settings_selected_index)
        return True

    def _settings_save_all(self):
        if self._settings_selected_index is not None and not self._settings_apply_form():
            return
        self.cfg['shortcuts'] = normalize_shortcuts(self._settings_items)
        save_config(self.cfg)
        self._render_shortcuts()
        self._close_settings_panel()
        messagebox.showinfo('已保存', '快捷启动配置已保存并立即生效。')

    def _settings_browse_target(self):
        kind = self._settings_vars['kind'].get()
        if kind == 'url':
            return
        if kind == 'system':
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')])
        if path:
            self._settings_vars['target'].set(path)

    def _stat_row(self, parent, label):
        t = self.t
        row = tk.Frame(parent, bg=t['bg'], pady=3)
        row.pack(fill='x', padx=10)

        top = tk.Frame(row, bg=t['bg'])
        top.pack(fill='x')
        tk.Label(top, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                 fg=t['text'], bg=t['bg']).pack(side='left')
        val = tk.Label(top, text='0%', font=('Consolas', 8),
                       fg=t['text_dim'], bg=t['bg'])
        val.pack(side='right')

        cv = tk.Canvas(row, height=10, bg=t['bar_bg'], highlightthickness=0, bd=0)
        cv.pack(fill='x', pady=(2, 0))

        return {'cv': cv, 'val': val}

    def _draw_bar(self, bar, pct, color, txt=None):
        cv = bar['cv']
        cv.delete('all')
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 2:
            return
        r = h // 2
        round_rect(cv, 0, 0, w, h, r, fill=self.t['bar_bg'], outline='')
        fw = max(r * 2, int(w * pct / 100))
        if pct > 0:
            round_rect(cv, 0, 0, min(fw, w), h, r, fill=color, outline='')
        bar['val'].config(text=txt or f'{pct:.0f}%')

    def _group_label(self, parent, text):
        tk.Label(
            parent,
            text=f' {text}',
            font=('Microsoft YaHei UI', 8, 'bold'),
            fg=self.t['text_dim'],
            bg=self.t['bg'],
            anchor='w',
        ).pack(fill='x', padx=8, pady=(6, 2))

    def _app_btn(self, parent, app_cfg):
        t = self.t
        fr = tk.Frame(parent, bg=t['bg'], padx=6, pady=5, cursor='hand2')
        fr.pack(fill='x', padx=2, pady=1)

        icon = app_cfg.get('icon', '▸')
        name = app_cfg.get('name', 'App')
        lbl = tk.Label(fr, text=f' {icon}  {name}', font=('Microsoft YaHei UI', 9),
                       fg=t['text'], bg=t['bg'], anchor='w')
        lbl.pack(fill='x')

        def enter(e):
            fr.config(bg=t['btn_hover'])
            lbl.config(bg=t['btn_hover'], fg=t['accent'])

        def leave(e):
            fr.config(bg=t['bg'])
            lbl.config(bg=t['bg'], fg=t['text'])

        def click(e):
            lbl.config(fg='#a6e3a1')
            fr.after(400, lambda: lbl.config(fg=t['text']))
            threading.Thread(target=Launcher.launch, args=(app_cfg,), daemon=True).start()

        for w in (fr, lbl):
            w.bind('<Enter>', enter)
            w.bind('<Leave>', leave)
            w.bind('<Button-1>', click)

    def _refresh_launch_scroll(self, _e=None):
        if not hasattr(self, '_launch_canvas'):
            return
        self._launch_list.update_idletasks()
        content_h = self._launch_list.winfo_reqheight() + 8
        cw = max(1, self._launch_canvas.winfo_width())
        self._launch_canvas.configure(scrollregion=(0, 0, cw, content_h))
        self._launch_canvas.itemconfigure(self._launch_window, width=cw)

    def _pointer_in_launch_area(self):
        if not hasattr(self, '_launch_canvas'):
            return False
        try:
            widget = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
        except Exception:
            return False
        while widget is not None:
            if widget in (self._launch_canvas, self._launch_list, self._launch_scroll):
                return True
            widget = widget.master
        return False

    def _on_global_mousewheel(self, event):
        if not self._pointer_in_launch_area():
            return
        if not hasattr(self, '_launch_canvas'):
            return
        start, end = self._launch_canvas.yview()
        if start == 0.0 and end == 1.0:
            return 'break'

        if getattr(event, 'num', None) == 4:
            impulse = -80
        elif getattr(event, 'num', None) == 5:
            impulse = 80
        else:
            delta = getattr(event, 'delta', 0)
            if delta == 0:
                return 'break'
            impulse = -delta * 0.6

        if not hasattr(self, '_scroll_velocity'):
            self._scroll_velocity = 0.0
            self._scroll_animating = False

        self._scroll_velocity += impulse
        cap = 400.0
        if self._scroll_velocity > cap:
            self._scroll_velocity = cap
        elif self._scroll_velocity < -cap:
            self._scroll_velocity = -cap

        if not self._scroll_animating:
            self._scroll_animating = True
            self._smooth_scroll_tick()

        return 'break'

    def _smooth_scroll_tick(self):
        if not hasattr(self, '_launch_canvas'):
            self._scroll_animating = False
            return

        v = self._scroll_velocity
        if abs(v) < 1.0:
            self._scroll_velocity = 0.0
            self._scroll_animating = False
            return

        self._launch_list.update_idletasks()
        content_h = self._launch_list.winfo_reqheight()
        view_h = self._launch_canvas.winfo_height()
        if content_h <= view_h or content_h < 1:
            self._scroll_animating = False
            return

        pixel_step = v * 0.12
        frac_step = pixel_step / content_h
        cur_start, cur_end = self._launch_canvas.yview()
        new_start = cur_start + frac_step

        if new_start < 0:
            new_start = 0
            self._scroll_velocity = 0.0
        elif new_start > 1.0 - (cur_end - cur_start):
            new_start = 1.0 - (cur_end - cur_start)
            self._scroll_velocity = 0.0

        self._launch_canvas.yview_moveto(new_start)
        self._scroll_velocity *= 0.85

        self.root.after(12, self._smooth_scroll_tick)

    # ──────── Ticks ────────

    def _tick_stats(self):
        try:
            s = self.mon.snapshot()

            self._draw_bar(self.cpu_bar, s['cpu'], cpu_color(s['cpu']))

            ram_txt = f"{s['ram_used']:.1f}/{s['ram_total']:.0f}G"
            self._draw_bar(self.ram_bar, s['ram_pct'], self.t['ram_color'], ram_txt)

            disk_txt = f"{s['disk_used']:.0f}/{s['disk_total']:.0f}G"
            self._draw_bar(self.disk_bar, s['disk_pct'], self.t['disk_color'], disk_txt)

            if s['cpu_freq']:
                self.freq_label.config(text=f"  {s['cpu_freq']:.0f} MHz · {psutil.cpu_count()}核")

            self.net_up_lbl.config(text=f"↑ {fmt_speed(s['net_up'])}")
            self.net_dn_lbl.config(text=f"↓ {fmt_speed(s['net_down'])}")

            if s['battery'] is not None:
                self.bat_frame.pack(fill='x', padx=0, before=self.net_up_lbl.master)
                icon = '⚡' if s['charging'] else '🔋'
                self.bat_lbl.config(text=f" {icon} {s['battery']:.0f}%")
        except Exception as e:
            print(f'stats error: {e}')

        self.root.after(self.cfg.get('update_interval_ms', 1500), self._tick_stats)

    def run(self):
        self.root.mainloop()

# ═══════════════════════ Entry ═══════════════════════

if __name__ == '__main__':
    StatusBar().run()
