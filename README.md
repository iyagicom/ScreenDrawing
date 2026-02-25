# ScreenDrawing

Lightweight screen drawing tool for Linux and Windows.  
Designed for real-time on-screen annotation with pen, shapes, text, highlighter, eraser, and undo.

---

## ✨ Features

### Drawing Tools
- **Pen** — freehand drawing
- **Rectangle** — drag to draw a rectangle
- **Ellipse** — drag to draw an ellipse
- **Line** — drag to draw a straight line
- **Arrow** — drag to draw an arrow
- **Text** — click to place inline text
  - Enter → Line break
  - Ctrl+Enter → Confirm text (draw on canvas)
  - Escape → Cancel

### Options
- **Fill** — fill rectangle / ellipse / arrow with color
- **Highlight** — semi-transparent overlay (pen, line, rect, ellipse, arrow)
- **Eraser** — remove strokes by brush or shape area (pen, rect, ellipse, line, arrow)

### Drawing / Mouse Mode
- **Drawing mode** — canvas is active, all tools available
- **Mouse passthrough mode** — canvas hides so the mouse interacts freely with windows below; your drawing remains visible as a static overlay
  - **Single click** the Drawing button → clear canvas and switch to mouse mode
  - **Double click** the Drawing button → keep drawing and switch to mouse mode

### Convenience
- **Color picker** — choose any pen color
- **Stroke width** — adjustable thickness (shared with eraser size)
- **Font selector** — choose font family and size
- **Quick size buttons** — 10 / 16 / 24 / 36 (applies to both stroke width and font size)
- **Undo** — up to 50 steps
- **Clear All** — wipe the entire canvas
- **Save** — export drawing layer as transparent PNG

### Settings Auto-save
Tool selection, color, stroke width, fill, highlight mode, and font are automatically saved on exit and restored on next launch.  
Settings are stored at:
- **Linux:** `~/.local/share/screendrawing/settings.json`
- **Windows:** `%APPDATA%\screendrawing\settings.json`

### Keyboard Shortcuts
- **Hold Ctrl** — temporary eraser (releases back to previous tool)
- **Hold Shift** — temporary straight line (releases back to previous tool)

### Other
- Auto language detection (Korean / English based on system locale)
- Lightweight — PyQt5 only, no extra dependencies

---

## 🖥️ Environment

Tested on:

- Linux (Ubuntu 24.04) — X11 and Wayland
- Windows 11
- Python 3.x + PyQt5

---

## 📦 Requirements

**Linux:**
```bash
pip install PyQt5
```

**Windows:**
```bash
pip install PyQt5 pywin32
```

---

## 🚀 Installation

### ✅ Option 1 — Windows EXE (No Python required)

Download `screendrawing.exe` from the [Releases](https://github.com/iyagicom/ScreenDrawing/releases) page and run it directly. No installation needed.

### ✅ Option 2 — pip install (Linux & Windows)

**Linux:**
```bash
pip install screendrawing --break-system-packages
```

**Windows:**
```bash
pip install screendrawing[windows]
```

Then run from anywhere:

```bash
screendrawing
```

### ✅ Option 3 — Manual (Linux)

#### 1. Download

Download `screendrawing.py` from this repository.

#### 2. Make executable

```bash
chmod +x screendrawing.py
```

#### 3. Install to user PATH

![Screenshot](ScreenDrawing.png)

```bash
mkdir -p ~/.local/bin
mv screendrawing.py ~/.local/bin/screendrawing
chmod +x ~/.local/bin/screendrawing
```

Make sure `~/.local/bin` is in your PATH. Add to `~/.bashrc` or `~/.zshrc` if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Now you can run it from anywhere:

```bash
screendrawing
```

---

## 💾 Save Behavior

The **Save** button exports the drawing layer only as a transparent PNG (`~/drawing_YYYYMMDD_HHMMSS.png`).

This is intentional and useful for:

- Overlay editing in image editors
- Presentation slides
- Video annotation
- Tutorial / lecture materials
- Image compositing

To capture the full screen including the background and your drawings, use an external screenshot tool **while ScreenDrawing is running**:

- **GNOME Screenshot** (`gnome-screenshot`)
- **Spectacle** (KDE)
- **Flameshot**

---

## 🚀 Desktop Launcher

To add ScreenDrawing to the application menu, create a `.desktop` file:

```bash
nano ~/.local/share/applications/screendrawing.desktop
```

Paste the following:

```ini
[Desktop Entry]
Encoding=UTF-8
Exec=screendrawing
Icon=applications-graphics
Type=Application
Terminal=false
Name=ScreenDrawing
GenericName=Screen Drawing Tool
Comment=Lightweight screen drawing overlay
StartupNotify=false
Categories=Utility;
```

Then refresh the application database:

```bash
update-desktop-database ~/.local/share/applications
```

ScreenDrawing will now appear in your application menu.

---

## 🎮 Controls

### Keyboard Shortcuts

| Key            | Function                                       |
|----------------|------------------------------------------------|
| `Ctrl + Z`     | Undo                                           |
| `Ctrl + S`     | Save (transparent PNG)                         |
| `Ctrl + Q`     | Exit                                           |
| `C`            | Clear canvas                                   |
| `ESC`          | Exit (or cancel text input if active)          |
| Hold `Ctrl`    | Temporary eraser (restores on release)         |
| Hold `Shift`   | Temporary straight line (restores on release)  |
| `Ctrl + Enter` | Confirm text (draw on canvas)                  |

### Toolbar Buttons

| Button         | Function                                                  |
|----------------|-----------------------------------------------------------|
| Pen            | Freehand drawing                                          |
| Rect           | Rectangle                                                 |
| Ellipse        | Ellipse / circle                                          |
| Line           | Straight line                                             |
| Arrow          | Draw an arrow                                             |
| Text           | Inline text input (on canvas)                             |
|                | • Enter → Line break                                      |
|                | • Ctrl+Enter → Confirm text (draw on canvas)              |
|                | • Escape → Cancel                                         |
| Color          | Open color picker                                         |
| W + Spinner    | Stroke width (also controls eraser size)                  |
| Font           | Open font selector                                        |
| 10/16/24/36    | Quick size preset (stroke width + font size)              |
| Fill           | Toggle fill for rectangle / ellipse / arrow               |
| Highlight      | Toggle semi-transparent highlight mode                    |
| Eraser         | Toggle eraser mode                                        |
| Undo           | Undo last action (up to 50 steps)                         |
| Save           | Save drawing as transparent PNG                           |
| Clear All      | Clear entire canvas                                       |
| Drawing ✎      | Single click → clear canvas + switch to mouse mode        |
|                | Double click → keep drawing + switch to mouse mode        |
| Exit           | Save settings and close the application                   |

---

## 📌 Notes

- Runs as a fullscreen transparent overlay
- Eraser size is shared with the stroke width setting
- Highlight mode works on pen (freehand), line, rectangle, ellipse, and arrow
- Eraser mode works on pen (freehand), line, rectangle, ellipse, and arrow
- Holding `Ctrl` or `Shift` temporarily switches tools and restores them on release
- In mouse passthrough mode, the toolbar remains fully clickable
- All drawing is non-destructive to the desktop — only the overlay canvas is affected
- Settings (tool, color, width, font, fill, highlight) are auto-saved on exit

---

## 👤 Author

Jeong SeongYong  
Email: iyagicom@gmail.com  
GitHub: [iyagicom](https://github.com/iyagicom)

---

## 📜 License

This project is licensed under the **GPL-2.0-or-later**.  
이 프로젝트는 GPL-2.0-or-later 라이선스 하에 배포됩니다.

You are free to use, modify, and redistribute under GPL terms.  
See [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) for details.
