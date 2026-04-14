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
import locale

def detect_language():
    try:
        candidates = []
        try:
            candidates.append(locale.getlocale()[0] or '')
        except Exception:
            pass
        try:
            candidates.append(locale.getdefaultlocale()[0] or '')
        except Exception:
            pass
        try:
            from ctypes import windll
            ui_lang = locale.windows_locale.get(windll.kernel32.GetUserDefaultUILanguage(), '')
            candidates.append(ui_lang)
        except Exception:
            pass
    except Exception:
        candidates = []

    for lang in candidates:
        text = str(lang).lower()
        if text.startswith('zh') or 'chinese' in text:
            return 'zh'
    return 'en'

APP_LANG = detect_language()

def pick_lang(zh_text, en_text):
    return zh_text if APP_LANG == 'zh' else en_text

try:
    import psutil
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        pick_lang('缺少依赖', 'Missing dependency'),
        pick_lang('请先运行 setup.bat 安装依赖，或手动执行：\npip install psutil',
                  'Run setup.bat first, or install manually:\npip install psutil'),
    )
    sys.exit(1)

try:
    from ctypes import windll, Structure, c_long, byref, create_unicode_buffer

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

STYLE_PRESETS = {
    'midnight': {
        "bg": "#1e1e2e",
        "bg_section": "#181825",
        "text": "#cdd6f4",
        "text_dim": "#6c7086",
        "accent": "#89b4fa",
        "border": "#313244",
        "btn_hover": "#45475a",
        "bar_bg": "#313244",
        "cpu_colors": ["#a6e3a1", "#f9e2af", "#fab387", "#f38ba8"],
        "ram_color": "#89b4fa",
        "disk_color": "#f9e2af",
        "net_up": "#a6e3a1",
        "net_down": "#74c7ec",
        "scroll_bg": "#181825",
        "scroll_trough": "#1e1e2e",
    },
    'forest': {
        "bg": "#16231d",
        "bg_section": "#122019",
        "text": "#d7e7da",
        "text_dim": "#6f8b79",
        "accent": "#8fd694",
        "border": "#294437",
        "btn_hover": "#274133",
        "bar_bg": "#294437",
        "cpu_colors": ["#8fd694", "#d9c97a", "#e8a96b", "#d96c75"],
        "ram_color": "#7cc6fe",
        "disk_color": "#d9c97a",
        "net_up": "#8fd694",
        "net_down": "#7cc6fe",
        "scroll_bg": "#122019",
        "scroll_trough": "#16231d",
    },
    'sunset': {
        "bg": "#2a1d1a",
        "bg_section": "#211613",
        "text": "#f3ddd2",
        "text_dim": "#b39487",
        "accent": "#ffb86c",
        "border": "#5a3b32",
        "btn_hover": "#4a312a",
        "bar_bg": "#5a3b32",
        "cpu_colors": ["#ffd166", "#ffb86c", "#ff8c61", "#ff5d73"],
        "ram_color": "#8be9fd",
        "disk_color": "#ffd166",
        "net_up": "#7ee787",
        "net_down": "#8be9fd",
        "scroll_bg": "#211613",
        "scroll_trough": "#2a1d1a",
    },
}

THEME = STYLE_PRESETS['midnight']

ICON_CHOICES = [
    '⌨️', '💻', '🖥️', '📁', '🌐', '⚙️', '🚀', '🎮', '🎨', '📐',
    '📏', '📝', '💬', '✦', '🤖', '🔧', '📊', '📌', '📂', '✨', '▸',
]

TRIGGER_MODE_CHOICES = ['always', 'desktop_only']
SCREEN_EDGE_CHOICES = ['right', 'left', 'top', 'top_left', 'top_right']
STYLE_PRESET_CHOICES = ['midnight', 'forest', 'sunset']
OPACITY_CHOICES = ['0.45', '0.55', '0.65', '0.75', '0.85', '0.95']

PEEK         = 4
ANIM_STEP    = 35
ANIM_MS      = 10
HIDE_DELAY   = 800
TRIGGER_ZONE = 10
EDGE_MARGIN_Y = 30
MAX_HEIGHT_RATIO = 0.84
LAUNCH_PANEL_HEIGHT = 210
TOP_MODE_MIN_WIDTH = 560
TOP_MODE_EXTRA_WIDTH = 180
TOP_MODE_MAX_HEIGHT = 214

I18N = {
    'zh': {
        'group_development': '开发',
        'group_design': '设计',
        'group_ai': 'AI',
        'group_shortcuts': '快捷启动',
        'status_bar_title': '状态栏',
        'system_monitor': '系统监控',
        'memory': '内存',
        'disk': '磁盘',
        'quick_launch': '快捷启动',
        'no_shortcuts': '暂无快捷启动项，点击右上角设置添加',
        'settings_title': '快捷启动设置',
        'settings_items': '快捷启动项',
        'edit_shortcuts': '编辑快捷启动',
        'settings_button': '设置',
        'trigger_mode': '触发模式',
        'trigger_mode_always': '随时响应',
        'trigger_mode_desktop_only': '仅桌面响应',
        'status_bar_settings': '状态栏设置',
        'feature_status': '仅桌面响应',
        'screen_edge': '停靠位置',
        'screen_edge_right': '右侧',
        'screen_edge_left': '左侧',
        'screen_edge_top': '上侧',
        'screen_edge_top_left': '左上',
        'screen_edge_top_right': '右上',
        'on': '是',
        'off': '否',
        'style_preset': '风格',
        'opacity_setting': '透明度',
        'style_midnight': '午夜蓝',
        'style_forest': '森林绿',
        'style_sunset': '落日橙',
        'add': '新增',
        'delete': '删除',
        'name': '名称',
        'icon': '图标',
        'type': '类型',
        'group': '分组',
        'target': '目标',
        'detect_name': '自动识别名',
        'browser': '浏览器',
        'browse': '浏览',
        'enabled_item': '启用此项',
        'hint': '目标填写示例:\n- executable: 程序 .exe 路径，或写 auto 交给自动识别\n- url: 网站地址，例如 https://chat.openai.com\n- command: 命令行，例如 cursor 或 opencode\n- system: 本地文件夹或文件路径',
        'save_current': '保存当前项',
        'save_close': '保存并关闭',
        'cancel': '取消',
        'disabled_suffix': ' [停用]',
        'unnamed': '未命名',
        'new_item': '新项目',
        'no_item_selected_title': '未选择项目',
        'no_item_selected_msg': '请先选择一个快捷启动项。',
        'name_required_title': '名称不能为空',
        'name_required_msg': '请填写快捷启动名称。',
        'target_required_title': '目标不能为空',
        'target_required_msg': '请填写网址、程序路径或命令。',
        'saved_title': '已保存',
        'saved_msg': '快捷启动配置已保存并立即生效。',
        'exe_files': '可执行文件',
        'all_files': '所有文件',
        'cores': '核',
    },
    'en': {
        'group_development': 'Development',
        'group_design': 'Design',
        'group_ai': 'AI',
        'group_shortcuts': 'Shortcuts',
        'status_bar_title': 'Status Bar',
        'system_monitor': 'System Monitor',
        'memory': 'Memory',
        'disk': 'Disk',
        'quick_launch': 'Quick Launch',
        'no_shortcuts': 'No shortcuts yet. Click the settings button to add one.',
        'settings_title': 'Quick Launch Settings',
        'settings_items': 'Shortcuts',
        'edit_shortcuts': 'Edit Shortcut',
        'settings_button': 'Settings',
        'trigger_mode': 'Trigger Mode',
        'trigger_mode_always': 'Always',
        'trigger_mode_desktop_only': 'Desktop only',
        'status_bar_settings': 'Bar Settings',
        'feature_status': 'Desktop only',
        'screen_edge': 'Screen Edge',
        'screen_edge_right': 'Right',
        'screen_edge_left': 'Left',
        'screen_edge_top': 'Top',
        'screen_edge_top_left': 'Top Left',
        'screen_edge_top_right': 'Top Right',
        'on': 'Yes',
        'off': 'No',
        'style_preset': 'Style',
        'opacity_setting': 'Opacity',
        'style_midnight': 'Midnight',
        'style_forest': 'Forest',
        'style_sunset': 'Sunset',
        'add': 'Add',
        'delete': 'Delete',
        'name': 'Name',
        'icon': 'Icon',
        'type': 'Type',
        'group': 'Group',
        'target': 'Target',
        'detect_name': 'Auto-detect Name',
        'browser': 'Browser',
        'browse': 'Browse',
        'enabled_item': 'Enable this shortcut',
        'hint': 'Target examples:\n- executable: an .exe path, or use auto for detection\n- url: a website like https://chat.openai.com\n- command: a CLI command like cursor or opencode\n- system: a local file or folder path',
        'save_current': 'Save Item',
        'save_close': 'Save and Close',
        'cancel': 'Cancel',
        'disabled_suffix': ' [Disabled]',
        'unnamed': 'Unnamed',
        'new_item': 'New Item',
        'no_item_selected_title': 'No item selected',
        'no_item_selected_msg': 'Please select a shortcut first.',
        'name_required_title': 'Name is required',
        'name_required_msg': 'Please enter a shortcut name.',
        'target_required_title': 'Target is required',
        'target_required_msg': 'Please enter a URL, path, or command.',
        'saved_title': 'Saved',
        'saved_msg': 'Shortcut settings were saved and applied.',
        'exe_files': 'Executable Files',
        'all_files': 'All Files',
        'cores': 'cores',
    },
}

GROUP_ALIASES = {
    '开发': 'group_development',
    'Development': 'group_development',
    '设计': 'group_design',
    'Design': 'group_design',
    'AI': 'group_ai',
    '快捷启动': 'group_shortcuts',
    'Shortcuts': 'group_shortcuts',
}

def tr(key):
    return I18N.get(APP_LANG, I18N['en']).get(key, key)

def group_label(key):
    return tr(f'group_{key}')

def display_group(group):
    return tr(GROUP_ALIASES.get(group, '')) if group in GROUP_ALIASES else group

def default_shortcuts():
    return [
        {"id": "opencode", "name": "OpenCode", "icon": "⌨️", "kind": "command",
         "target": "opencode", "group": group_label('development'), "enabled": True},
        {"id": "sketchup", "name": "SketchUp", "icon": "📐", "kind": "executable",
         "target": "auto", "detect": "SketchUp", "group": group_label('design'), "enabled": True},
        {"id": "autocad", "name": "AutoCAD", "icon": "📏", "kind": "executable",
         "target": "auto", "detect": "AutoCAD", "group": group_label('design'), "enabled": True},
        {"id": "photoshop", "name": "Photoshop", "icon": "🎨", "kind": "executable",
         "target": "auto", "detect": "Photoshop", "group": group_label('design'), "enabled": True},
        {"id": "gemini", "name": "Gemini", "icon": "✦", "kind": "url",
         "target": "https://gemini.google.com", "browser": "chrome", "group": group_label('ai'), "enabled": True},
        {"id": "chatgpt", "name": "ChatGPT", "icon": "💬", "kind": "url",
         "target": "https://chatgpt.com", "browser": "chrome", "group": group_label('ai'), "enabled": True},
        {"id": "godot", "name": "Godot", "icon": "🎮", "kind": "executable",
         "target": "D:\\下载\\Godot_v4.6.1-stable_win64.exe\\Godot_v4.6.1-stable_win64.exe",
         "group": group_label('development'), "enabled": True},
    ]

def default_group_choices():
    return [
        group_label('development'),
        group_label('design'),
        group_label('ai'),
        group_label('shortcuts'),
    ]

def trigger_mode_label(mode):
    return tr(f'trigger_mode_{mode}')

def trigger_mode_choices():
    return [trigger_mode_label(mode) for mode in TRIGGER_MODE_CHOICES]

def screen_edge_label(edge):
    return tr(f'screen_edge_{edge}')

def screen_edge_choices():
    return [screen_edge_label(edge) for edge in SCREEN_EDGE_CHOICES]

def normalize_screen_edge(value):
    if value in SCREEN_EDGE_CHOICES:
        return value
    for edge in SCREEN_EDGE_CHOICES:
        if value == screen_edge_label(edge):
            return edge
    return 'right'

def style_preset_label(style_id):
    return tr(f'style_{style_id}')

def style_preset_choices():
    return [style_preset_label(style_id) for style_id in STYLE_PRESET_CHOICES]

def normalize_style_preset(value):
    if value in STYLE_PRESET_CHOICES:
        return value
    for style_id in STYLE_PRESET_CHOICES:
        if value == style_preset_label(style_id):
            return style_id
    return 'midnight'

def get_theme(style_id):
    return dict(STYLE_PRESETS.get(normalize_style_preset(style_id), STYLE_PRESETS['midnight']))

def normalize_opacity(value):
    try:
        opacity = float(value)
    except (TypeError, ValueError):
        return 0.65
    return max(0.2, min(1.0, opacity))

def normalize_trigger_mode(value):
    if value in TRIGGER_MODE_CHOICES:
        return value
    for mode in TRIGGER_MODE_CHOICES:
        if value == trigger_mode_label(mode):
            return mode
    return 'always'

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
            'group': item.get('group', group_label('shortcuts')),
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
    shortcut['group'] = shortcut.get('group', group_label('shortcuts'))
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
        "trigger_mode": "always",
        "screen_edge": "right",
        "style_preset": "midnight",
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
        "opacity": normalize_opacity(cfg.get("opacity", 0.65)),
        "width": cfg.get("width", 186),
        "update_interval_ms": cfg.get("update_interval_ms", 1500),
        "trigger_mode": normalize_trigger_mode(cfg.get("trigger_mode", "always")),
        "screen_edge": normalize_screen_edge(cfg.get("screen_edge", "right")),
        "style_preset": normalize_style_preset(cfg.get("style_preset", "midnight")),
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

def cpu_color(pct, theme):
    c = theme['cpu_colors']
    if pct < 30: return c[0]
    if pct < 60: return c[1]
    if pct < 85: return c[2]
    return c[3]

def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r,
           x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return cv.create_polygon(pts, smooth=True, **kw)

def compute_window_width(base_width, top_center_mode=False):
    if top_center_mode:
        return max(TOP_MODE_MIN_WIDTH, base_width * 2 + TOP_MODE_EXTRA_WIDTH)
    return base_width

def build_shortcut_grid_rows(items, columns=2):
    rows = []
    row = []
    for item in items:
        row.append(item)
        if len(row) == columns:
            rows.append(tuple(row))
            row = []
    if row:
        row.extend([None] * (columns - len(row)))
        rows.append(tuple(row))
    return rows

def truncate_text(text, max_chars):
    if max_chars is None or max_chars < 4 or len(text) <= max_chars:
        return text
    return f"{text[:max_chars - 3]}..."

def format_shortcut_text(icon, name, max_name_chars=None):
    return f" {icon}  {truncate_text(name, max_name_chars)}"

def compute_available_height(screen_height, top_center_mode=False):
    available_h = max(220, min(screen_height - EDGE_MARGIN_Y * 2, int(screen_height * MAX_HEIGHT_RATIO)))
    if top_center_mode:
        return min(available_h, TOP_MODE_MAX_HEIGHT)
    return available_h

def get_stat_row_layout(top_center_mode=False):
    if top_center_mode:
        return {
            'inline': True,
            'row_pady': 1,
            'canvas_height': 8,
            'bar_padx': (8, 8),
            'value_width': 7,
        }
    return {
        'inline': False,
        'row_pady': 3,
        'canvas_height': 10,
        'bar_padx': (0, 0),
        'value_width': 0,
    }

def get_launch_spacing(top_center_mode=False):
    if top_center_mode:
        return {
            'section_pady': 1,
            'header_pady': 2,
            'wrap_top_pady': 1,
            'group_top_pady': 2,
            'group_bottom_pady': 1,
            'button_pady': 1,
            'footer_spacer_height': 10,
        }
    return {
        'section_pady': 2,
        'header_pady': 4,
        'wrap_top_pady': 4,
        'group_top_pady': 6,
        'group_bottom_pady': 2,
        'button_pady': 1,
        'footer_spacer_height': 28,
    }

def compute_top_launch_height(available_height, header_height, launch_header_height, desired_launch_height):
    max_launch_height = max(110, available_height - header_height - launch_header_height - 8)
    return min(desired_launch_height, max_launch_height)

class ThemedScrollbar(tk.Canvas):
    def __init__(self, parent, theme, command, width=8):
        super().__init__(
            parent,
            width=width,
            highlightthickness=0,
            bd=0,
            relief='flat',
            bg=theme['scroll_trough'],
            cursor='hand2',
        )
        self.theme = theme
        self.command = command
        self.thumb_margin = 1
        self.min_thumb = 24
        self.first = 0.0
        self.last = 1.0
        self._dragging = False
        self._drag_offset = 0
        self._thumb_bounds = (0, 0, width, 0)
        self.bind('<Configure>', self._redraw)
        self.bind('<Button-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)

    def set(self, first, last):
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))
        self._redraw()

    def _redraw(self, _event=None):
        self.delete('all')
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.create_rectangle(0, 0, width, height, fill=self.theme['scroll_trough'], outline='')
        if self.first <= 0.0 and self.last >= 1.0:
            self._thumb_bounds = (0, 0, width, 0)
            return

        travel = max(1, height - self.thumb_margin * 2)
        thumb_h = max(self.min_thumb, int(travel * (self.last - self.first)))
        thumb_h = min(travel, thumb_h)
        top = self.thumb_margin + int((travel - thumb_h) * self.first)
        bottom = top + thumb_h
        left = self.thumb_margin
        right = width - self.thumb_margin
        self._thumb_bounds = (left, top, right, bottom)
        radius = max(2, min((right - left) // 2, (bottom - top) // 2))
        round_rect(self, left, top, right, bottom, radius, fill=self.theme['scroll_bg'], outline='')

    def _move_to(self, top):
        height = max(1, self.winfo_height())
        thumb_h = max(1, self._thumb_bounds[3] - self._thumb_bounds[1])
        travel = max(1, height - self.thumb_margin * 2 - thumb_h)
        frac = (top - self.thumb_margin) / travel if travel else 0.0
        frac = max(0.0, min(1.0, frac))
        self.command('moveto', frac)

    def _on_press(self, event):
        left, top, right, bottom = self._thumb_bounds
        if top <= event.y <= bottom:
            self._dragging = True
            self._drag_offset = event.y - top
            return
        thumb_h = max(1, bottom - top)
        self._move_to(event.y - thumb_h / 2)

    def _on_drag(self, event):
        if not self._dragging:
            return
        self._move_to(event.y - self._drag_offset)

    def _on_release(self, _event):
        self._dragging = False

# ═══════════════════════ Main Application ═══════════════════════

class StatusBar:
    def __init__(self):
        self.cfg = load_config()
        self.mon = SysMonitor()
        self.t = get_theme(self.cfg.get('style_preset', 'midnight'))

        self.root = tk.Tk()
        self.root.withdraw()

        self._is_shown = False
        self._animating = False
        self._hide_job = None
        self._pinned = False
        self._settings_window = None
        self._settings_items = []
        self._settings_selected_index = None
        self._settings_view = 'shortcut'
        self._preview_job = None
        self._shortcut_save_job = None
        self._loading_settings_form = False
        self._refreshing_main_ui = False

        self._setup_window()
        self._build_ui()
        self._update_dock_positions()
        self._place_hidden()

        self.root.deiconify()
        self._tick_stats()
        self._poll_mouse()

    # ──────── Window ────────

    def _setup_window(self):
        r = self.root
        r.title(tr('status_bar_title'))
        r.overrideredirect(True)
        r.attributes('-topmost', True)
        r.attributes('-alpha', normalize_opacity(self.cfg.get('opacity', 0.65)))
        r.configure(bg=TRANSPARENT_KEY)
        r.attributes('-transparentcolor', TRANSPARENT_KEY)

        self._base_w = self.cfg.get('width', 186)
        self.W = self._base_w

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

    def _screen_edge(self):
        return normalize_screen_edge(self.cfg.get('screen_edge', 'right'))

    def _is_top_center_mode(self):
        return self._screen_edge() == 'top'

    def _update_dock_positions(self):
        edge = self._screen_edge()
        if edge == 'left':
            self._x_shown = 0
            self._x_hidden = -(self.W - PEEK)
            self._y_shown = self._win_y
            self._y_hidden = self._win_y
        elif edge in ('top', 'top_left', 'top_right'):
            if edge == 'top_left':
                self._x_shown = 0
            elif edge == 'top_right':
                self._x_shown = self.scr_w - self.W
            else:
                self._x_shown = max(0, (self.scr_w - self.W) // 2)
            self._x_hidden = self._x_shown
            self._y_shown = self.scr_top
            self._y_hidden = self.scr_top - self._win_h + PEEK
        else:
            self._x_shown = self.scr_w - self.W
            self._x_hidden = self.scr_w - PEEK
            self._y_shown = self._win_y
            self._y_hidden = self._win_y

    def _place_hidden(self):
        self.root.geometry(f'+{self._x_hidden}+{self._y_hidden}')

    def _place_current(self):
        x = self._x_shown if (self._is_shown or self._pinned) else self._x_hidden
        y = self._y_shown if (self._is_shown or self._pinned) else self._y_hidden
        self.root.geometry(f'{self.W}x{self._win_h}+{x}+{y}')

    # ──────── Auto-hide ────────

    def _mouse_in_trigger_band(self, mx, my, wy, wh):
        edge = self._screen_edge()
        if edge == 'left':
            return (mx <= TRIGGER_ZONE) and (wy <= my <= wy + wh)
        if edge in ('top', 'top_left', 'top_right'):
            return (my <= self.scr_top + TRIGGER_ZONE) and (self._x_shown <= mx <= self._x_shown + self.W)
        return (mx >= self.scr_w - TRIGGER_ZONE) and (wy <= my <= wy + wh)

    def _is_desktop_foreground(self):
        if not HAS_CTYPES:
            return True
        try:
            hwnd = windll.user32.GetForegroundWindow()
            if not hwnd:
                return False
            class_name = create_unicode_buffer(256)
            windll.user32.GetClassNameW(hwnd, class_name, 256)
            return class_name.value in ('Progman', 'WorkerW')
        except Exception:
            return True

    def _can_trigger_show(self):
        mode = normalize_trigger_mode(self.cfg.get('trigger_mode', 'always'))
        if mode == 'desktop_only':
            return self._is_desktop_foreground()
        return True

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
            wy = self.root.winfo_y()
            wh = self._win_h

            mouse_at_edge = self._mouse_in_trigger_band(mx, my, wy, wh)
            mouse_in_bar = self._is_shown and (wx <= mx <= wx + self.W) and (wy <= my <= wy + wh)
            allow_trigger = self._can_trigger_show()

            if ((mouse_at_edge and allow_trigger) or mouse_in_bar) and not self._is_shown:
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
        self._animate_to(self._x_shown, self._y_shown)

    def _slide_hide(self):
        if not self._is_shown and not self._animating:
            return
        self._is_shown = False
        self._animate_to(self._x_hidden, self._y_hidden)

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
            wy = self.root.winfo_y()
            mouse_at_edge = self._mouse_in_trigger_band(mx, my, wy, self._win_h)
            mouse_in_bar = (wx <= mx <= wx + self.W) and \
                           (wy <= my <= wy + self._win_h)
            if mouse_at_edge or mouse_in_bar:
                return
        except Exception:
            pass
        self._slide_hide()

    def _cancel_hide(self):
        if self._hide_job is not None:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None

    def _animate_to(self, target_x, target_y):
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        dist_x = target_x - current_x
        dist_y = target_y - current_y

        if abs(dist_x) <= 2 and abs(dist_y) <= 2:
            self.root.geometry(f'+{target_x}+{target_y}')
            self._animating = False
            return

        self._animating = True
        if abs(dist_y) > 0:
            step_y = ANIM_STEP if dist_y > 0 else -ANIM_STEP
            if abs(dist_y) < ANIM_STEP * 3:
                step_y = max(2, abs(dist_y) // 3) * (1 if dist_y > 0 else -1)
            new_y = current_y + step_y
            new_y = min(new_y, target_y) if step_y > 0 else max(new_y, target_y)
            new_x = target_x
        else:
            step_x = ANIM_STEP if dist_x > 0 else -ANIM_STEP
            if abs(dist_x) < ANIM_STEP * 3:
                step_x = max(2, abs(dist_x) // 3) * (1 if dist_x > 0 else -1)
            new_x = current_x + step_x
            new_x = min(new_x, target_x) if step_x > 0 else max(new_x, target_x)
            new_y = target_y

        self.root.geometry(f'+{new_x}+{new_y}')
        self.root.after(ANIM_MS, lambda: self._animate_to(target_x, target_y))

    # ──────── Build UI ────────

    def _build_ui(self):
        t = self.t
        TK = TRANSPARENT_KEY
        top_center_mode = self._is_top_center_mode()
        launch_spacing = get_launch_spacing(top_center_mode)
        self.W = compute_window_width(self._base_w, top_center_mode)

        canvas = tk.Canvas(self.root, bg=TK, highlightthickness=0, bd=0)
        canvas.pack(fill='both', expand=True)
        self._canvas = canvas

        main = tk.Frame(canvas, bg=TK)
        self._main_frame = main
        canvas.create_window((0, 0), window=main, anchor='nw', width=self.W)

        # ── Header ──
        hdr = tk.Frame(main, bg=t['bg_section'], pady=4 if top_center_mode else 6)
        hdr.pack(fill='x', pady=(0, 1 if top_center_mode else 2))

        hdr_in = tk.Frame(hdr, bg=t['bg_section'])
        hdr_in.pack(fill='x', padx=10)

        tk.Label(hdr_in, text=f"⚡ {tr('system_monitor')}", font=('Microsoft YaHei UI', 9, 'bold'),
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

        settings_btn = tk.Label(
            hdr_in,
            text='⚙',
            font=('Segoe UI Emoji', 9),
            fg=t['text_dim'],
            bg=t['bg_section'],
            cursor='hand2',
            padx=4,
        )
        settings_btn.pack(side='right', padx=(0, 6))
        settings_btn.bind('<Button-1>', self._open_settings_panel)
        settings_btn.bind('<Enter>', lambda e: settings_btn.config(fg=t['accent']))
        settings_btn.bind('<Leave>', lambda e: settings_btn.config(fg=t['text_dim']))

        body = tk.Frame(main, bg=TK)
        body.pack(fill='both', expand=True)
        if top_center_mode:
            body.grid_columnconfigure(0, weight=1, uniform='top_body')
            body.grid_columnconfigure(1, weight=1, uniform='top_body')

        # ── Stats panel ──
        sf = tk.Frame(body, bg=t['bg'], pady=2 if top_center_mode else 4)
        if top_center_mode:
            sf.grid(row=0, column=0, sticky='nsew', padx=(0, 3), pady=1)
        else:
            sf.pack(fill='x', pady=2)

        self.cpu_bar = self._stat_row(sf, 'CPU', compact=top_center_mode)
        self.ram_bar = self._stat_row(sf, tr('memory'), compact=top_center_mode)
        self.disk_bar = self._stat_row(sf, tr('disk'), compact=top_center_mode)

        self.freq_label = tk.Label(sf, text='', font=('Consolas', 7),
                                   fg=t['text_dim'], bg=t['bg'])
        self.freq_label.pack(fill='x', padx=12, pady=(1 if top_center_mode else 0, 0))

        nf = tk.Frame(sf, bg=t['bg'], pady=1 if top_center_mode else 2)
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
        lf = tk.Frame(body, bg=t['bg'], pady=launch_spacing['section_pady'])
        if top_center_mode:
            lf.grid(row=0, column=1, sticky='nsew', padx=(3, 0), pady=1)
        else:
            lf.pack(fill='x', pady=2)

        lh = tk.Frame(lf, bg=t['bg_section'], pady=launch_spacing['header_pady'])
        lh.pack(fill='x')
        tk.Label(lh, text=f"🚀 {tr('quick_launch')}", font=('Microsoft YaHei UI', 9, 'bold'),
                 fg=t['accent'], bg=t['bg_section']).pack(padx=10, anchor='w')

        launch_wrap = tk.Frame(lf, bg=t['bg'])
        launch_wrap.pack(fill='both', expand=True, padx=2, pady=(launch_spacing['wrap_top_pady'], 0))

        launch_canvas = tk.Canvas(
            launch_wrap,
            bg=t['bg'],
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        launch_scroll = self._make_scrollbar(launch_wrap, launch_canvas.yview)
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
        available_h = compute_available_height(self.scr_h, top_center_mode)
        if top_center_mode:
            body_h = max(120, available_h - hdr.winfo_reqheight() - 1)
            body.configure(height=body_h)
            body.pack_propagate(False)
            sf.configure(height=body_h)
            sf.grid_propagate(False)
            lf.configure(height=body_h)
            lf.grid_propagate(False)
            launch_wrap_h = max(110, body_h - lh.winfo_reqheight() - launch_spacing['wrap_top_pady'])
            launch_wrap.configure(height=launch_wrap_h)
            launch_wrap.pack_propagate(False)
            body_h = max(sf.winfo_reqheight(), lf.winfo_reqheight())
            desired_launch_h = max(110, body_h - lh.winfo_reqheight() - 8)
            launch_h = compute_top_launch_height(
                available_height=available_h,
                header_height=hdr.winfo_reqheight(),
                launch_header_height=lh.winfo_reqheight(),
                desired_launch_height=desired_launch_h,
            )
        else:
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
        if top_center_mode:
            self._win_y = self.scr_top
        else:
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

    def _make_scrollbar(self, parent, command):
        return ThemedScrollbar(parent, self.t, command, width=8)

    def _render_shortcuts(self):
        if not hasattr(self, '_launch_list'):
            return
        for child in self._launch_list.winfo_children():
            child.destroy()

        grouped = {}
        group_order = []
        visible = False
        for app in self.cfg.get('shortcuts', []):
            if not app.get('enabled', True):
                continue
            group = app.get('group', group_label('shortcuts'))
            if group not in grouped:
                grouped[group] = []
                group_order.append(group)
            grouped[group].append(app)
            visible = True

        for group in group_order:
            self._group_label(self._launch_list, display_group(group))
            if self._is_top_center_mode():
                group_frame = tk.Frame(self._launch_list, bg=self.t['bg'])
                group_frame.pack(fill='x', padx=2, pady=(0, 2))
                group_frame.grid_columnconfigure(0, weight=1, uniform='shortcut_cols')
                group_frame.grid_columnconfigure(1, weight=1, uniform='shortcut_cols')
                for row_idx, row_items in enumerate(build_shortcut_grid_rows(grouped[group], columns=2)):
                    for col_idx, app in enumerate(row_items):
                        cell = tk.Frame(group_frame, bg=self.t['bg'])
                        pad_x = (0, 4) if col_idx == 0 else (4, 0)
                        cell.grid(row=row_idx, column=col_idx, sticky='ew', padx=pad_x, pady=1)
                        if app is not None:
                            self._app_btn(cell, app, compact=True)
            else:
                for app in grouped[group]:
                    self._app_btn(self._launch_list, app)

        if not visible:
            tk.Label(
                self._launch_list,
                text=f" {tr('no_shortcuts')}",
                font=('Microsoft YaHei UI', 8),
                fg=self.t['text_dim'],
                bg=self.t['bg'],
                anchor='w',
            ).pack(fill='x', padx=8, pady=8)

        tk.Frame(
            self._launch_list,
            bg=self.t['bg'],
            height=get_launch_spacing(self._is_top_center_mode())['footer_spacer_height'],
        ).pack(fill='x')
        self._refresh_launch_scroll()

    def _open_settings_panel(self, _e=None):
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        self._settings_items = [dict(item) for item in self.cfg.get('shortcuts', [])]
        self._settings_selected_index = None
        self._settings_view = 'shortcut'

        win = tk.Toplevel(self.root)
        self._settings_window = win
        win.title(tr('settings_title'))
        win.geometry('860x500')
        win.minsize(820, 460)
        win.configure(bg=self.t['bg'])
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', self._close_settings_panel)

        left = tk.Frame(win, bg=self.t['bg_section'], width=220)
        left.pack(side='left', fill='y')
        left.pack_propagate(False)
        right = tk.Frame(win, bg=self.t['bg'])
        right.pack(side='right', fill='both', expand=True)

        left_top = tk.Frame(left, bg=self.t['bg_section'])
        left_top.pack(side='top', fill='both', expand=True)

        self._shortcuts_header = tk.Label(left_top, text=tr('settings_items'), font=('Microsoft YaHei UI', 10, 'bold'),
                                          fg=self.t['accent'], bg=self.t['bg_section'])
        self._shortcuts_header.pack(anchor='w', padx=12, pady=(6, 6))

        self._shortcuts_panel = tk.Frame(left_top, bg=self.t['bg_section'])
        self._shortcuts_panel.pack(fill='both', expand=True, padx=10, pady=(0, 10), anchor='n')

        list_wrap = tk.Frame(self._shortcuts_panel, bg=self.t['bg_section'])
        list_wrap.pack(fill='both', expand=True)
        self._shortcuts_list_wrap = list_wrap
        self._settings_list_canvas = tk.Canvas(list_wrap, bg=self.t['bg_section'], highlightthickness=0, bd=0)
        list_scroll = self._make_scrollbar(list_wrap, self._settings_list_canvas.yview)
        self._settings_list_canvas.configure(yscrollcommand=list_scroll.set)
        self._settings_list_canvas.pack(side='left', fill='both', expand=True)
        list_scroll.pack(side='right', fill='y')
        self._settings_list_frame = tk.Frame(self._settings_list_canvas, bg=self.t['bg_section'])
        self._settings_list_window = self._settings_list_canvas.create_window((0, 0), window=self._settings_list_frame, anchor='nw')
        self._settings_item_rows = []
        self._settings_list_canvas.bind('<Configure>', self._refresh_settings_list_layout)
        self._settings_list_frame.bind('<Configure>', self._refresh_settings_list_layout)
        for widget in (self._settings_list_canvas, self._settings_list_frame):
            widget.bind('<MouseWheel>', self._on_settings_list_wheel)
            widget.bind('<Button-4>', self._on_settings_list_wheel)
            widget.bind('<Button-5>', self._on_settings_list_wheel)

        self._shortcuts_action_row = tk.Frame(self._shortcuts_panel, bg=self.t['bg_section'])
        self._populate_settings_action_row(self._shortcuts_action_row)
        self._shortcuts_action_row.pack(fill='x', pady=(8, 2), side='bottom')

        left_top.bind('<Configure>', lambda _e: self._refresh_settings_list())

        self._settings_mode_btn = tk.Button(
            left,
            text=tr('status_bar_settings'),
            command=self._show_trigger_settings,
            bg=self.t['bg'],
            fg=self.t['text'],
            activebackground=self.t['btn_hover'],
            activeforeground=self.t['accent'],
            relief='flat',
            bd=0,
            padx=8,
            pady=6,
            anchor='w',
            cursor='hand2',
        )
        self._settings_mode_btn.pack(fill='x', padx=10, pady=(10, 12), side='bottom')

        self._settings_vars = {
            'name': tk.StringVar(),
            'icon': tk.StringVar(),
            'kind': tk.StringVar(value='executable'),
            'target': tk.StringVar(),
            'group': tk.StringVar(value=group_label('shortcuts')),
            'detect': tk.StringVar(),
            'browser': tk.StringVar(value='chrome'),
            'enabled': tk.BooleanVar(value=True),
            'trigger_mode': tk.StringVar(value=tr('off')),
            'screen_edge': tk.StringVar(value=screen_edge_label(normalize_screen_edge(self.cfg.get('screen_edge', 'right')))),
            'style_preset': tk.StringVar(value=style_preset_label(normalize_style_preset(self.cfg.get('style_preset', 'midnight')))),
            'opacity': tk.StringVar(value=f"{normalize_opacity(self.cfg.get('opacity', 0.65)):.2f}"),
        }
        for key in ('name', 'icon', 'kind', 'target', 'group', 'detect', 'browser', 'enabled'):
            self._settings_vars[key].trace_add('write', self._queue_shortcut_autosave)
        self._settings_vars['trigger_mode'].trace_add('write', self._queue_live_preview)
        self._settings_vars['screen_edge'].trace_add('write', self._queue_live_preview)
        self._settings_vars['style_preset'].trace_add('write', self._queue_live_preview)
        self._settings_vars['opacity'].trace_add('write', self._queue_live_preview)

        self._settings_title_label = tk.Label(right, text=tr('edit_shortcuts'), font=('Microsoft YaHei UI', 10, 'bold'),
                                              fg=self.t['accent'], bg=self.t['bg'])
        self._settings_title_label.pack(anchor='w', padx=14, pady=(12, 8))

        content_wrap = tk.Frame(right, bg=self.t['bg'])
        content_wrap.pack(fill='both', expand=True, padx=14)

        form = tk.Frame(content_wrap, bg=self.t['bg'])
        form.grid(row=0, column=0, sticky='nsew')
        form.grid_columnconfigure(0, minsize=120)
        form.grid_columnconfigure(1, weight=1)
        content_wrap.grid_columnconfigure(0, weight=1)
        content_wrap.grid_rowconfigure(0, weight=1)
        self._shortcut_form = form

        self._settings_entry(form, tr('name'), self._settings_vars['name'], 0)
        self._settings_option(form, tr('icon'), self._settings_vars['icon'], ICON_CHOICES, 1)
        self._settings_option(form, tr('type'), self._settings_vars['kind'], ['executable', 'url', 'command', 'system'], 2)
        self._settings_option(form, tr('group'), self._settings_vars['group'], default_group_choices(), 3)
        self._settings_entry(form, tr('target'), self._settings_vars['target'], 4, with_browse=True)
        self._settings_entry(form, tr('detect_name'), self._settings_vars['detect'], 5)
        self._settings_option(form, tr('browser'), self._settings_vars['browser'], ['chrome', 'default'], 6)
        tk.Checkbutton(
            form,
            text=tr('enabled_item'),
            variable=self._settings_vars['enabled'],
            bg=self.t['bg'],
            fg=self.t['text'],
            selectcolor=self.t['bg_section'],
            activebackground=self.t['bg'],
            activeforeground=self.t['text'],
        ).grid(row=7, column=1, sticky='w', pady=(8, 0))

        hint = tr('hint')
        tk.Label(form, text=hint, justify='left', font=('Microsoft YaHei UI', 8),
                 fg=self.t['text_dim'], bg=self.t['bg']).grid(row=8, column=0, columnspan=3, sticky='w', pady=(12, 0))

        trigger_form = tk.Frame(content_wrap, bg=self.t['bg'])
        trigger_form.grid(row=0, column=0, sticky='nsew')
        trigger_form.grid_columnconfigure(0, minsize=120)
        trigger_form.grid_columnconfigure(1, weight=1)
        self._trigger_form = trigger_form
        self._settings_option(trigger_form, tr('feature_status'), self._settings_vars['trigger_mode'], [tr('off'), tr('on')], 0)
        self._settings_option(trigger_form, tr('screen_edge'), self._settings_vars['screen_edge'], screen_edge_choices(), 1)
        self._settings_option(trigger_form, tr('style_preset'), self._settings_vars['style_preset'], style_preset_choices(), 2)
        self._settings_option(trigger_form, tr('opacity_setting'), self._settings_vars['opacity'], OPACITY_CHOICES, 3)

        self._refresh_settings_list()
        self._load_bar_settings_form()
        if self._settings_items:
            self._on_settings_select(0)
        else:
            self._settings_add_item()

    def _close_settings_panel(self):
        if self._shortcut_save_job is not None:
            self.root.after_cancel(self._shortcut_save_job)
            self._shortcut_save_job = None
            if self._settings_view == 'shortcut' and self._settings_selected_index is not None:
                self._settings_store_current_draft(refresh_list=False)
                self._persist_shortcuts()
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.destroy()
        self._settings_window = None
        self._settings_selected_index = None
        self._settings_view = 'shortcut'
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
            self._preview_job = None
        self._shortcut_save_job = None

    def _load_bar_settings_form(self):
        mode = normalize_trigger_mode(self.cfg.get('trigger_mode', 'always'))
        self._settings_vars['trigger_mode'].set(tr('on') if mode == 'desktop_only' else tr('off'))
        self._settings_vars['screen_edge'].set(screen_edge_label(normalize_screen_edge(self.cfg.get('screen_edge', 'right'))))
        self._settings_vars['style_preset'].set(style_preset_label(normalize_style_preset(self.cfg.get('style_preset', 'midnight'))))
        self._settings_vars['opacity'].set(f"{normalize_opacity(self.cfg.get('opacity', 0.65)):.2f}")

    def _apply_bar_settings(self):
        self.cfg['trigger_mode'] = 'desktop_only' if self._settings_vars['trigger_mode'].get() == tr('on') else 'always'
        self.cfg['screen_edge'] = normalize_screen_edge(self._settings_vars['screen_edge'].get())
        self.cfg['style_preset'] = normalize_style_preset(self._settings_vars['style_preset'].get())
        self.cfg['opacity'] = normalize_opacity(self._settings_vars['opacity'].get())

    def _persist_shortcuts(self):
        self.cfg['shortcuts'] = normalize_shortcuts(self._settings_items)
        save_config(self.cfg)
        self._render_shortcuts()

    def _queue_shortcut_autosave(self, *_args):
        if self._loading_settings_form or self._settings_view != 'shortcut':
            return
        if self._settings_selected_index is None:
            return
        if self._shortcut_save_job is not None:
            self.root.after_cancel(self._shortcut_save_job)
        self._shortcut_save_job = self.root.after(120, self._apply_shortcut_autosave)

    def _apply_shortcut_autosave(self):
        self._shortcut_save_job = None
        if self._loading_settings_form or self._settings_view != 'shortcut':
            return
        if self._settings_selected_index is None:
            return
        self._settings_store_current_draft(refresh_list=False)
        self._persist_shortcuts()

    def _queue_live_preview(self, *_args):
        if self._settings_view != 'trigger':
            return
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(60, self._apply_live_preview)

    def _apply_live_preview(self):
        self._preview_job = None
        if self._refreshing_main_ui:
            return
        if self._settings_window is None or not self._settings_window.winfo_exists():
            return
        self._apply_bar_settings()
        save_config(self.cfg)
        self._refresh_main_ui()

    def _refresh_main_ui(self):
        if self._refreshing_main_ui:
            return
        self._refreshing_main_ui = True
        self.t = get_theme(self.cfg.get('style_preset', 'midnight'))
        self.root.attributes('-alpha', normalize_opacity(self.cfg.get('opacity', 0.65)))
        self.root.unbind_all('<MouseWheel>')
        self.root.unbind_all('<Button-4>')
        self.root.unbind_all('<Button-5>')
        try:
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    continue
                child.destroy()
            self._build_ui()
            self._update_dock_positions()
            self._place_current()
        finally:
            self._refreshing_main_ui = False

    def _update_settings_nav_state(self):
        if getattr(self, '_settings_mode_btn', None):
            is_trigger = self._settings_view == 'trigger'
            self._settings_mode_btn.config(
                bg=self.t['btn_hover'] if is_trigger else self.t['bg'],
                fg=self.t['accent'] if is_trigger else self.t['text'],
            )

    def _show_shortcut_settings(self):
        self._settings_view = 'shortcut'
        self._settings_title_label.config(text=tr('edit_shortcuts'))
        self._trigger_form.grid_remove()
        self._shortcut_form.grid()
        self._update_settings_nav_state()

    def _show_trigger_settings(self):
        if getattr(self, '_settings_selected_index', None) is not None:
            self._settings_store_current_draft(refresh_list=False)
            self._persist_shortcuts()
        self._settings_view = 'trigger'
        self._load_bar_settings_form()
        self._settings_title_label.config(text=tr('status_bar_settings'))
        self._shortcut_form.grid_remove()
        self._trigger_form.grid()
        self._update_settings_nav_state()

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
                 fg=self.t['text'], bg=self.t['bg'], width=14, anchor='w').grid(
                     row=row, column=0, sticky='w', pady=5, padx=(0, 8)
                 )
        entry = tk.Entry(parent, textvariable=var, bg=self.t['bg_section'], fg=self.t['text'],
                         insertbackground=self.t['text'], relief='flat')
        entry.grid(row=row, column=1, sticky='ew', pady=5)
        if with_browse:
            tk.Button(parent, text=tr('browse'), command=self._settings_browse_target,
                      bg=self.t['bg_section'], fg=self.t['text'],
                      activebackground=self.t['btn_hover'], activeforeground=self.t['accent'],
                      relief='flat', bd=0, padx=8, pady=4, cursor='hand2').grid(row=row, column=2, padx=(8, 0), pady=5)
    def _settings_option(self, parent, label, var, values, row):
        tk.Label(parent, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                 fg=self.t['text'], bg=self.t['bg'], width=14, anchor='w').grid(
                     row=row, column=0, sticky='w', pady=5, padx=(0, 8)
                 )
        menu = tk.OptionMenu(parent, var, *values)
        menu.config(bg=self.t['bg_section'], fg=self.t['text'], activebackground=self.t['btn_hover'],
                    activeforeground=self.t['accent'], relief='flat', highlightthickness=0,
                    width=18, anchor='w')
        menu['menu'].config(bg=self.t['bg_section'], fg=self.t['text'],
                            activebackground=self.t['btn_hover'], activeforeground=self.t['accent'])
        menu.grid(row=row, column=1, sticky='w', pady=5)

    def _refresh_settings_list_layout(self, _e=None):
        if not getattr(self, '_settings_list_canvas', None):
            return
        self._settings_list_frame.update_idletasks()
        cw = max(1, self._settings_list_canvas.winfo_width())
        ch = self._settings_list_frame.winfo_reqheight()
        self._settings_list_canvas.itemconfigure(self._settings_list_window, width=cw)
        bbox = self._settings_list_canvas.bbox('all')
        if bbox is not None:
            self._settings_list_canvas.configure(scrollregion=bbox)
        else:
            self._settings_list_canvas.configure(scrollregion=(0, 0, cw, ch))

    def _on_settings_list_wheel(self, event):
        if not getattr(self, '_settings_list_canvas', None):
            return 'break'
        start, end = self._settings_list_canvas.yview()
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

        if not hasattr(self, '_settings_scroll_velocity'):
            self._settings_scroll_velocity = 0.0
            self._settings_scroll_animating = False

        self._settings_scroll_velocity += impulse
        cap = 400.0
        if self._settings_scroll_velocity > cap:
            self._settings_scroll_velocity = cap
        elif self._settings_scroll_velocity < -cap:
            self._settings_scroll_velocity = -cap

        if not self._settings_scroll_animating:
            self._settings_scroll_animating = True
            self._smooth_settings_scroll_tick()
        return 'break'

    def _smooth_settings_scroll_tick(self):
        if not hasattr(self, '_settings_list_canvas'):
            self._settings_scroll_animating = False
            return

        v = getattr(self, '_settings_scroll_velocity', 0.0)
        if abs(v) < 1.0:
            self._settings_scroll_velocity = 0.0
            self._settings_scroll_animating = False
            return

        self._settings_list_frame.update_idletasks()
        content_h = self._settings_list_frame.winfo_reqheight()
        view_h = self._settings_list_canvas.winfo_height()
        if content_h <= view_h or content_h < 1:
            self._settings_scroll_velocity = 0.0
            self._settings_scroll_animating = False
            return

        pixel_step = v * 0.12
        frac_step = pixel_step / content_h
        cur_start, cur_end = self._settings_list_canvas.yview()
        new_start = cur_start + frac_step

        if new_start < 0:
            new_start = 0
            self._settings_scroll_velocity = 0.0
        elif new_start > 1.0 - (cur_end - cur_start):
            new_start = 1.0 - (cur_end - cur_start)
            self._settings_scroll_velocity = 0.0

        self._settings_list_canvas.yview_moveto(new_start)
        self._settings_scroll_velocity *= 0.85
        self.root.after(12, self._smooth_settings_scroll_tick)

    def _settings_row_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.t['bg'],
            fg=self.t['text'],
            activebackground=self.t['btn_hover'],
            activeforeground=self.t['accent'],
            relief='flat',
            bd=0,
            padx=8,
            pady=6,
            anchor='w',
            cursor='hand2',
        )

    def _populate_settings_action_row(self, parent):
        for child in parent.winfo_children():
            child.destroy()
        self._settings_row_button(parent, tr('add'), self._settings_add_item).pack(side='left', expand=True, fill='x')
        self._settings_row_button(parent, tr('delete'), self._settings_delete_item).pack(side='left', expand=True, fill='x', padx=6)

    def _settings_row_text(self, idx):
        item = self._settings_items[idx]
        status = '' if item.get('enabled', True) else tr('disabled_suffix')
        group = display_group(item.get('group', group_label('shortcuts')))
        return f"{group} / {item.get('name', tr('unnamed'))}{status}"

    def _bind_settings_row_widgets(self, row, lbl, idx):
        for sequence in ('<Button-1>', '<MouseWheel>', '<Button-4>', '<Button-5>'):
            row.unbind(sequence)
            lbl.unbind(sequence)
        row.bind('<Button-1>', lambda _e, i=idx: self._on_settings_select(i))
        lbl.bind('<Button-1>', lambda _e, i=idx: self._on_settings_select(i))
        for widget in (row, lbl):
            widget.bind('<MouseWheel>', self._on_settings_list_wheel)
            widget.bind('<Button-4>', self._on_settings_list_wheel)
            widget.bind('<Button-5>', self._on_settings_list_wheel)

    def _create_settings_item_row(self, idx, before=None):
        selected = idx == self._settings_selected_index
        bg = self.t['btn_hover'] if selected else self.t['bg']
        fg = self.t['accent'] if selected else self.t['text']
        row = tk.Frame(self._settings_list_frame, bg=bg, padx=6, pady=2, cursor='hand2')
        pack_kwargs = {'fill': 'x', 'pady': (0, 4)}
        if before is not None:
            pack_kwargs['before'] = before
        row.pack(**pack_kwargs)
        lbl = tk.Label(row, text=self._settings_row_text(idx), font=('Microsoft YaHei UI', 9), fg=fg,
                       bg=row.cget('bg'), anchor='w', padx=4)
        lbl.pack(fill='x')
        self._bind_settings_row_widgets(row, lbl, idx)
        return row, lbl

    def _reindex_settings_rows(self, start=0):
        for idx in range(start, len(self._settings_item_widgets)):
            row, lbl = self._settings_item_widgets[idx]
            self._bind_settings_row_widgets(row, lbl, idx)
            lbl.config(text=self._settings_row_text(idx))
        self._update_settings_row_styles()

    def _sync_settings_action_rows(self):
        if not getattr(self, '_inline_actions_row', None):
            return
        self._refresh_settings_list_layout()
        self._settings_window.update_idletasks()
        overflow = self._settings_list_frame.winfo_reqheight() > self._settings_list_canvas.winfo_height()
        if overflow:
            if self._inline_actions_row.winfo_manager():
                self._inline_actions_row.pack_forget()
            if not self._shortcuts_action_row.winfo_manager():
                self._shortcuts_action_row.pack(fill='x', pady=(8, 2), side='bottom')
        else:
            if not self._inline_actions_row.winfo_manager():
                self._inline_actions_row.pack(fill='x', pady=(4, 2))
            if self._shortcuts_action_row.winfo_manager():
                self._shortcuts_action_row.pack_forget()
        self._refresh_settings_list_layout()

    def _scroll_settings_item_into_view(self, idx):
        if not hasattr(self, '_settings_list_canvas') or not hasattr(self, '_settings_item_rows'):
            return
        if idx < 0 or idx >= len(self._settings_item_rows):
            return
        self._settings_list_frame.update_idletasks()
        row = self._settings_item_rows[idx]
        content_h = self._settings_list_frame.winfo_reqheight()
        view_h = self._settings_list_canvas.winfo_height()
        if content_h <= view_h or content_h <= 0:
            return

        max_top = max(0, content_h - view_h)
        if idx == len(self._settings_item_rows) - 1:
            self._settings_list_canvas.yview_moveto(max_top / content_h)
            return

        row_top = row.winfo_y()
        row_bottom = row_top + row.winfo_height()
        cur_start, cur_end = self._settings_list_canvas.yview()
        view_top = cur_start * content_h
        view_bottom = cur_end * content_h

        if row_top >= view_top and row_bottom <= view_bottom:
            return

        if row_bottom > view_bottom:
            new_top = row_bottom - view_h + 8
        else:
            new_top = max(0, row_top - 8)

        new_top = max(0, min(max_top, new_top))
        self._settings_list_canvas.yview_moveto(new_top / content_h)

    def _ensure_settings_item_visible(self, idx):
        if not hasattr(self, '_settings_list_canvas'):
            return
        self._refresh_settings_list_layout()
        self.root.update_idletasks()
        self._scroll_settings_item_into_view(idx)

    def _schedule_settings_item_visible(self, idx):
        self.root.after_idle(lambda i=idx: self._ensure_settings_item_visible(i))
        self.root.after(30, lambda i=idx: self._ensure_settings_item_visible(i))
        self.root.after(80, lambda i=idx: self._ensure_settings_item_visible(i))

    def _refresh_settings_list(self):
        if not getattr(self, '_settings_list_frame', None):
            return
        for child in self._settings_list_frame.winfo_children():
            child.destroy()

        self._settings_item_rows = []
        self._settings_item_widgets = []
        for idx, item in enumerate(self._settings_items):
            row, lbl = self._create_settings_item_row(idx)
            self._settings_item_rows.append(row)
            self._settings_item_widgets.append((row, lbl))
        self._inline_actions_row = tk.Frame(self._settings_list_frame, bg=self.t['bg_section'])
        self._populate_settings_action_row(self._inline_actions_row)
        self._reindex_settings_rows()
        self._inline_actions_row.pack(fill='x', pady=(4, 2))
        self._sync_settings_action_rows()

    def _update_settings_row_styles(self):
        if not hasattr(self, '_settings_item_widgets'):
            return
        for idx, widgets in enumerate(self._settings_item_widgets):
            row, lbl = widgets
            selected = idx == self._settings_selected_index
            bg = self.t['btn_hover'] if selected else self.t['bg']
            fg = self.t['accent'] if selected else self.t['text']
            row.config(bg=bg)
            lbl.config(bg=bg, fg=fg)

    def _update_settings_row_text(self, idx):
        if not hasattr(self, '_settings_item_widgets'):
            return
        if idx < 0 or idx >= len(self._settings_item_widgets):
            return
        item = self._settings_items[idx]
        status = '' if item.get('enabled', True) else tr('disabled_suffix')
        group = display_group(item.get('group', group_label('shortcuts')))
        self._settings_item_widgets[idx][1].config(text=f"{group} / {item.get('name', tr('unnamed'))}{status}")

    def _select_settings_item_local(self, idx, ensure_visible=False):
        if idx is None or idx < 0 or idx >= len(self._settings_items):
            return
        self._settings_selected_index = idx
        self._show_shortcut_settings()
        self._settings_load_form(self._settings_items[idx])
        self._update_settings_row_styles()
        if ensure_visible:
            self._schedule_settings_item_visible(idx)

    def _settings_collect_form(self):
        shortcut = {
            'id': self._settings_vars['name'].get().strip().lower().replace(' ', '_') or 'shortcut',
            'name': self._settings_vars['name'].get().strip(),
            'icon': self._settings_vars['icon'].get().strip() or '▸',
            'kind': self._settings_vars['kind'].get().strip() or 'executable',
            'target': self._settings_vars['target'].get().strip(),
            'group': self._settings_vars['group'].get().strip() or group_label('shortcuts'),
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

    def _settings_store_current_draft(self, refresh_list=True):
        idx = self._settings_selected_index
        if idx is None:
            return False
        if idx < 0 or idx >= len(self._settings_items):
            return False
        updated = normalize_shortcut(self._settings_collect_form())
        changed = updated != self._settings_items[idx]
        self._settings_items[idx] = updated
        if refresh_list and changed:
            self._refresh_settings_list()
        elif changed:
            self._update_settings_row_text(idx)
        return changed

    def _settings_load_form(self, item):
        self._loading_settings_form = True
        try:
            self._settings_vars['name'].set(item.get('name', ''))
            self._settings_vars['icon'].set(item.get('icon', ''))
            self._settings_vars['kind'].set(item.get('kind', 'executable'))
            self._settings_vars['target'].set(item.get('target', ''))
            self._settings_vars['group'].set(item.get('group', group_label('shortcuts')))
            self._settings_vars['detect'].set(item.get('detect', ''))
            self._settings_vars['browser'].set(item.get('browser', 'chrome'))
            self._settings_vars['enabled'].set(bool(item.get('enabled', True)))
        finally:
            self._loading_settings_form = False

    def _on_settings_select(self, idx=None, ensure_visible=False, skip_store=False, _e=None):
        if idx is None:
            return
        prev_idx = self._settings_selected_index
        if idx is None or idx < 0 or idx >= len(self._settings_items):
            return
        if idx == prev_idx and self._settings_view == 'shortcut':
            return
        if (not skip_store) and prev_idx is not None and prev_idx < len(self._settings_items):
            self._settings_store_current_draft(refresh_list=False)
            self._persist_shortcuts()
        self._settings_selected_index = idx
        self._show_shortcut_settings()
        self._settings_load_form(self._settings_items[idx])
        self._update_settings_row_styles()
        if ensure_visible:
            self._scroll_settings_item_into_view(idx)

    def _settings_add_item(self):
        self._settings_store_current_draft(refresh_list=False)
        item = normalize_shortcut({
            'name': tr('new_item'),
            'icon': '✨',
            'kind': 'url',
            'target': 'https://',
            'group': group_label('shortcuts'),
            'enabled': True,
        })
        self._settings_items.append(item)
        idx = len(self._settings_items) - 1
        before = None
        if getattr(self, '_inline_actions_row', None) and self._inline_actions_row.winfo_exists() and self._inline_actions_row.winfo_manager():
            before = self._inline_actions_row
        row, lbl = self._create_settings_item_row(idx, before=before)
        self._settings_item_rows.append(row)
        self._settings_item_widgets.append((row, lbl))
        self._reindex_settings_rows(idx)
        self._sync_settings_action_rows()
        self._select_settings_item_local(idx, ensure_visible=True)
        self._persist_shortcuts()
        self.root.after_idle(lambda: self._settings_list_canvas.yview_moveto(1.0))
        self.root.after(30, lambda: self._settings_list_canvas.yview_moveto(1.0))
        self.root.after(80, lambda: self._settings_list_canvas.yview_moveto(1.0))

    def _settings_delete_item(self):
        if self._settings_selected_index is None:
            return
        delete_idx = self._settings_selected_index
        del self._settings_items[self._settings_selected_index]
        if self._settings_items:
            idx = max(0, delete_idx - 1)
            if 0 <= delete_idx < len(self._settings_item_widgets):
                row, _lbl = self._settings_item_widgets.pop(delete_idx)
                self._settings_item_rows.pop(delete_idx)
                row.destroy()
            self._reindex_settings_rows(delete_idx)
            self._sync_settings_action_rows()
            self._select_settings_item_local(idx, ensure_visible=True)
            self._persist_shortcuts()
        else:
            self._settings_selected_index = None
            self._refresh_settings_list()
            self._settings_vars['name'].set('')
            self._settings_vars['icon'].set('')
            self._settings_vars['kind'].set('executable')
            self._settings_vars['target'].set('')
            self._settings_vars['group'].set(group_label('shortcuts'))
            self._settings_vars['detect'].set('')
            self._settings_vars['browser'].set('chrome')
            self._settings_vars['enabled'].set(True)
            self._persist_shortcuts()

    def _settings_apply_form(self):
        if self._settings_view == 'trigger':
            self._apply_bar_settings()
            save_config(self.cfg)
            self._refresh_main_ui()
            return True
        if self._settings_selected_index is None:
            messagebox.showwarning(tr('no_item_selected_title'), tr('no_item_selected_msg'))
            return False
        shortcut = self._settings_collect_form()
        if not shortcut.get('name'):
            messagebox.showwarning(tr('name_required_title'), tr('name_required_msg'))
            return False
        if not shortcut.get('target'):
            messagebox.showwarning(tr('target_required_title'), tr('target_required_msg'))
            return False
        self._settings_items[self._settings_selected_index] = normalize_shortcut(shortcut)
        self._refresh_settings_list()
        return True

    def _settings_save_all(self):
        is_trigger_view = self._settings_view == 'trigger'
        if self._settings_view != 'trigger':
            self._settings_store_current_draft()
        if not self._settings_apply_form():
            return
        if not is_trigger_view:
            self._apply_bar_settings()
            self.cfg['shortcuts'] = normalize_shortcuts(self._settings_items)
            save_config(self.cfg)
            self._refresh_main_ui()
        self._close_settings_panel()
        messagebox.showinfo(tr('saved_title'), tr('saved_msg'))

    def _settings_browse_target(self):
        kind = self._settings_vars['kind'].get()
        if kind == 'url':
            return
        if kind == 'system':
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=[(tr('exe_files'), '*.exe'), (tr('all_files'), '*.*')])
        if path:
            self._settings_vars['target'].set(path)

    def _stat_row(self, parent, label, compact=False):
        t = self.t
        layout = get_stat_row_layout(compact)
        row = tk.Frame(parent, bg=t['bg'], pady=layout['row_pady'])
        row.pack(fill='x', padx=10)

        if layout['inline']:
            tk.Label(row, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                     fg=t['text'], bg=t['bg'], width=5, anchor='w').pack(side='left')
            cv = tk.Canvas(row, height=layout['canvas_height'], bg=t['bar_bg'], highlightthickness=0, bd=0)
            cv.pack(side='left', fill='x', expand=True, padx=layout['bar_padx'], pady=1)
            val = tk.Label(row, text='0%', font=('Consolas', 8),
                           fg=t['text_dim'], bg=t['bg'], width=layout['value_width'], anchor='e')
            val.pack(side='right')
        else:
            top = tk.Frame(row, bg=t['bg'])
            top.pack(fill='x')
            tk.Label(top, text=label, font=('Microsoft YaHei UI', 8, 'bold'),
                     fg=t['text'], bg=t['bg']).pack(side='left')
            val = tk.Label(top, text='0%', font=('Consolas', 8),
                           fg=t['text_dim'], bg=t['bg'])
            val.pack(side='right')

            cv = tk.Canvas(row, height=layout['canvas_height'], bg=t['bar_bg'], highlightthickness=0, bd=0)
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
        spacing = get_launch_spacing(self._is_top_center_mode())
        tk.Label(
            parent,
            text=f' {text}',
            font=('Microsoft YaHei UI', 8, 'bold'),
            fg=self.t['text_dim'],
            bg=self.t['bg'],
            anchor='w',
        ).pack(fill='x', padx=8, pady=(spacing['group_top_pady'], spacing['group_bottom_pady']))

    def _top_shortcut_name_limit(self):
        usable_width = max(160, (self.W - 48) // 2)
        return max(10, min(18, (usable_width - 42) // 9))

    def _app_btn(self, parent, app_cfg, compact=False):
        t = self.t
        spacing = get_launch_spacing(compact)
        fr = tk.Frame(parent, bg=t['bg'], padx=6, pady=5, cursor='hand2')
        fr.pack(fill='x', expand=compact, padx=0 if compact else 2, pady=spacing['button_pady'])

        icon = app_cfg.get('icon', '▸')
        name = app_cfg.get('name', 'App')
        text = format_shortcut_text(icon, name, self._top_shortcut_name_limit() if compact else None)
        lbl = tk.Label(fr, text=text, font=('Microsoft YaHei UI', 9),
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

            self._draw_bar(self.cpu_bar, s['cpu'], cpu_color(s['cpu'], self.t))

            ram_txt = f"{s['ram_used']:.1f}/{s['ram_total']:.0f}G"
            self._draw_bar(self.ram_bar, s['ram_pct'], self.t['ram_color'], ram_txt)

            disk_txt = f"{s['disk_used']:.0f}/{s['disk_total']:.0f}G"
            self._draw_bar(self.disk_bar, s['disk_pct'], self.t['disk_color'], disk_txt)

            if s['cpu_freq']:
                self.freq_label.config(text=f"  {s['cpu_freq']:.0f} MHz · {psutil.cpu_count()} {tr('cores')}")

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
