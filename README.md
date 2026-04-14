# Desktop Status Bar

A lightweight Windows desktop sidebar built with Tkinter. It stays on the right edge of the screen, shows real-time system stats, and includes a customizable quick-launch panel for apps, commands, websites, and local paths.

## Features

- Real-time CPU, memory, disk, network, and battery monitoring
- Auto-hide sidebar on the right edge of the screen
- Pin button to keep the sidebar visible
- Semi-transparent floating UI
- Smooth scrolling quick-launch panel
- Built-in settings panel for adding and editing shortcuts
- Config saved in `config.json`

## Requirements

- Windows
- Python 3
- `psutil`

## Install

1. Run `setup.bat`
2. The script installs `psutil`
3. The sidebar is added to Windows startup
4. The app launches immediately

If you prefer manual install:

```powershell
pip install psutil
pythonw status_bar.pyw
```

## Usage

- Move the mouse to the right edge of the screen to reveal the sidebar
- Click `📌` to pin or unpin it
- Click `⚙` to open the shortcut settings panel
- Click `✕` to close the app

## Recent Progress

- Improved the shortcut settings panel to preserve in-progress form edits when switching selection
- Reworked the left settings list into custom rows so selection updates feel lighter and less flickery
- Added themed scrollbar rendering and smoother wheel scrolling for the left shortcut list
- Added a `Status Bar Settings` section with desktop-only trigger mode, style presets, and opacity control
- Updated the shortcut list behavior so `Add` and `Delete` stay below the visible shortcut items and pin above `Status Bar Settings` only when the list overflows
- Added automatic scrolling to newly created shortcut items so they are selected and brought into view more reliably

## Known Issue

- When the shortcut list is already full, a newly added item may still fail to appear immediately in the visible area until the list is saved or reopened; the item is usually created successfully, but the live visibility behavior still needs refinement

## Manage Shortcuts

Use the settings panel to add, edit, remove, enable, or disable shortcuts.

Supported shortcut types:

- `executable`: launch a local `.exe`
- `url`: open a website
- `command`: run a CLI command
- `system`: open a local folder or file

Examples:

- `executable` target: `C:\Program Files\App\App.exe`
- `url` target: `https://chatgpt.com`
- `command` target: `cursor`
- `system` target: `D:\Projects`

## Config File

Shortcuts are stored in `config.json` under `shortcuts`.

Example:

```json
{
  "id": "notion",
  "name": "Notion",
  "icon": "📝",
  "kind": "url",
  "target": "https://www.notion.so",
  "browser": "chrome",
  "group": "Work",
  "enabled": true
}
```

Common fields:

- `id`: unique shortcut id
- `name`: display name
- `icon`: icon or emoji shown in the sidebar
- `kind`: `executable`, `url`, `command`, or `system`
- `target`: path, URL, or command
- `group`: section label in the sidebar
- `enabled`: whether the item is shown
- `detect`: optional app name used when `target` is `auto`
- `browser`: browser preference for URLs

## Files

- `status_bar.pyw`: main application
- `config.json`: user configuration
- `setup.bat`: install and startup setup
- `uninstall.bat`: remove startup entry

## Notes

- Some applications can be auto-detected from common install paths or the Windows registry
- You can still edit `config.json` directly if you prefer not to use the settings panel

## License

No license file is included yet. Add one before reusing this project in other distributions.
