# Desktop MCP Server

A Model Context Protocol (MCP) server that provides desktop automation capabilities including screenshot, OCR, and mouse/keyboard control.

## Features

- **Screenshot**: Capture full screen or specific regions
- **OCR**: Extract text from screen using EasyOCR with image preprocessing
- **Find Text**: Locate text on screen and get coordinates
- **Mouse Control**: Click, move, drag operations
- **Keyboard Control**: Type text, press hotkeys

## Requirements

- Python 3.8.10+
- EasyOCR (no system dependencies required)

## Installation

```bash
cd desktop-mcp-server

# Windows 7
pip install pyautogui==0.9.53 easyocr opencv-python-headless numpy Pillow==9.5.0

# macOS
pip install pyautogui easyocr opencv-python-headless numpy Pillow
```

## Usage

### As MCP Server (stdio)

```bash
python -m desktop_mcp
```

### DeepCode Configuration

Add to `.deepcode/mcp.json`:

```json
{
  "mcpServers": {
    "desktop": {
      "command": "python",
      "args": ["-m", "desktop_mcp"],
      "cwd": "/path/to/desktop-mcp-server"
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `screenshot` | Capture screen or region, returns base64 image |
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

## OCR Language Support

EasyOCR supports multiple languages. Use the `lang` parameter:

| Language | Code |
|----------|------|
| English | `eng` or `en` |
| Simplified Chinese | `chi_sim` or `ch_sim` |
| Traditional Chinese | `chi_tra` or `ch_tra` |
| Japanese | `jpn` or `ja` |
| Korean | `kor` or `ko` |

Example:
```json
{"name": "ocr_screen", "arguments": {"lang": "chi_sim"}}
{"name": "find_text", "arguments": {"text": "确定", "lang": "chi_sim"}}
```

## Image Preprocessing

OCR includes automatic preprocessing to improve accuracy:
- Grayscale conversion
- CLAHE contrast enhancement
- Noise reduction (fastNlMeansDenoising)
- Sharpening

## Platform Support

| Feature | Windows 7 | macOS |
|---------|-----------|-------|
| Screenshot | PIL.ImageGrab | pyautogui |
| OCR | EasyOCR | EasyOCR |
| Mouse/Keyboard | pyautogui | pyautogui |

## License

MIT
