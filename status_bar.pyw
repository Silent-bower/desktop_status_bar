"""桌面状态栏 — 实时系统监控 + 快捷启动
Auto-hide on right edge, slides out on mouse hover.
"""

import tkinter as tk
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

def load_config():
    defaults = {
        "opacity": 0.65,
        "width": 186,
        "update_interval_ms": 1500,
        "apps": [
            {"name": "OpenCode",  "icon": "⌨️", "type": "cli", "command": "opencode"},
            {"name": "SketchUp",  "icon": "📐", "type": "exe", "path": "auto"},
            {"name": "Photoshop", "icon": "🎨", "type": "exe", "path": "auto"},
            {"name": "Gemini",    "icon": "✦",  "type": "url", "url": "https://gemini.google.com"},
            {"name": "ChatGPT",   "icon": "💬", "type": "url", "url": "https://chatgpt.com"},
            {"name": "Godot",     "icon": "🎮", "type": "exe", "path": "D:\\下载\\Godot_v4.6.1-stable_win64.exe\\Godot_v4.6.1-stable_win64.exe"},
        ]
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user = json.load(f)
            defaults.update(user)
        except Exception:
            pass
    else:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(defaults, f, indent=2, ensure_ascii=False)
    return defaults

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

    @classmethod
    def find_app(cls, name):
        nl = name.lower()
        if 'sketchup' in nl:
            return (cls._find_in_dirs(['SketchUp'], ['SketchUp.exe', r'SketchUp\SketchUp.exe'])
                    or shutil.which('SketchUp'))
        if 'photoshop' in nl:
            return (cls._find_in_dirs(['Adobe'], ['Photoshop.exe'])
                    or shutil.which('Photoshop'))
        return shutil.which(name)

    @classmethod
    def launch(cls, cfg):
        t = cfg.get('type', 'exe')
        try:
            if t == 'cli':
                cmd = cfg.get('command', '')
                subprocess.Popen(f'start "" {cmd}', shell=True)
            elif t == 'url':
                url = cfg['url']
                ch = cls.chrome()
                if ch:
                    subprocess.Popen([ch, url])
                else:
                    os.startfile(url)
            elif t == 'exe':
                path = cfg.get('path', 'auto')
                if path == 'auto':
                    path = cls.find_app(cfg.get('name', ''))
                if path and os.path.exists(path):
                    subprocess.Popen([path])
                else:
                    subprocess.Popen(f'start "" "{cfg.get("name", "")}"', shell=True)
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
        self._launch_window = launch_canvas.create_window((0, 0), window=launch_list, anchor='nw')

        launch_canvas.bind('<Configure>', self._refresh_launch_scroll)
        launch_list.bind('<Configure>', self._refresh_launch_scroll)
        launch_canvas.bind('<MouseWheel>', self._on_launch_mousewheel)
        launch_list.bind('<MouseWheel>', self._on_launch_mousewheel)

        for app in self.cfg.get('apps', []):
            self._app_btn(launch_list, app)

        # Fit to content and prioritize a tall launcher area over scrolling.
        self.root.update_idletasks()
        other_h = hdr.winfo_reqheight() + sf.winfo_reqheight() + lh.winfo_reqheight() + 24
        launch_content_h = launch_list.winfo_reqheight()
        launch_max_h = max(110, self.scr_h - other_h - 12)
        launch_h = min(launch_content_h, launch_max_h)
        launch_canvas.configure(height=launch_h)
        self._refresh_launch_scroll()

        self.root.update_idletasks()
        full_h = self.scr_h
        launch_h = max(launch_h, full_h - other_h - 12)
        launch_canvas.configure(height=launch_h)
        self._refresh_launch_scroll()

        self.root.update_idletasks()
        ch = min(max(main.winfo_reqheight(), full_h), full_h)
        self._content_h = ch
        self._win_h = ch
        self._win_y = self.scr_top
        self.root.geometry(f'{self.W}x{ch}')
        canvas.config(scrollregion=(0, 0, self.W, ch))

    def _toggle_pin(self, _e=None):
        self._pinned = not self._pinned
        t = self.t
        if self._pinned:
            self._pin_btn.config(fg=t['accent'])
            self._cancel_hide()
            self._slide_show()
        else:
            self._pin_btn.config(fg=t['text_dim'])

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
            w.bind('<MouseWheel>', self._on_launch_mousewheel, add='+')

    def _refresh_launch_scroll(self, _e=None):
        if not hasattr(self, '_launch_canvas'):
            return
        self._launch_canvas.configure(scrollregion=self._launch_canvas.bbox('all'))
        self._launch_canvas.itemconfigure(self._launch_window, width=max(1, self._launch_canvas.winfo_width()))

    def _on_launch_mousewheel(self, event):
        if not hasattr(self, '_launch_canvas'):
            return
        start, end = self._launch_canvas.yview()
        if start == 0.0 and end == 1.0:
            return 'break'
        direction = -1 if event.delta > 0 else 1
        self._launch_canvas.yview_scroll(direction, 'units')
        return 'break'

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
