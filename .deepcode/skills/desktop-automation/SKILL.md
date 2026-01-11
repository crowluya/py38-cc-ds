---
name: desktop-automation
description: Automate desktop tasks using screenshot, OCR, and mouse/keyboard control. Use when users ask to interact with desktop applications, click buttons, type text, or read screen content.
allowed-tools: Read, Write, Bash
model: sonnet
color: green
---

# Desktop Automation Skill

Automate desktop interactions using the desktop MCP server.

## Available Tools

| Tool | Description |
|------|-------------|
| `screenshot` | Capture screen or region, returns base64 PNG |
| `ocr_screen` | OCR the screen, returns text with positions |
| `find_text` | Find text on screen, returns coordinates |
| `click` | Click at coordinates |
| `double_click` | Double click at coordinates |
| `right_click` | Right click at coordinates |
| `move_mouse` | Move mouse to coordinates |
| `drag` | Drag from start to end coordinates |
| `type_text` | Type text string |
| `hotkey` | Press keyboard shortcut |
| `scroll` | Scroll mouse wheel |
| `get_screen_size` | Get screen dimensions |
| `get_mouse_position` | Get current mouse position |

## Usage Patterns

### Click on Text
```
1. Use find_text to locate the text
2. Use click with the returned coordinates
```

### Fill Form Field
```
1. Use find_text to locate the field label
2. Use click to focus the field
3. Use type_text to enter the value
```

### Navigate Menu
```
1. Use click on menu item
2. Wait briefly for menu to open
3. Use click on submenu item
```

### Keyboard Shortcuts
```
- Copy: hotkey(["ctrl", "c"]) or hotkey(["cmd", "c"]) on Mac
- Paste: hotkey(["ctrl", "v"]) or hotkey(["cmd", "v"]) on Mac
- Save: hotkey(["ctrl", "s"]) or hotkey(["cmd", "s"]) on Mac
```

## Best Practices

1. **Always screenshot first** - Understand the current screen state
2. **Use OCR for verification** - Confirm actions completed successfully
3. **Add small delays** - Allow UI to respond between actions
4. **Handle errors gracefully** - Check if text was found before clicking

## Language Support

For Chinese OCR, use `lang: "chi_sim"` parameter:
```
ocr_screen(lang="chi_sim")
find_text(text="确定", lang="chi_sim")
```

## Platform Notes

- **Windows 7**: Uses PIL.ImageGrab for screenshots (more reliable)
- **macOS**: Uses pyautogui for all operations
- **Tesseract**: Must be installed on the system for OCR
