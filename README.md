# ScreenDrawing

Lightweight screen drawing tool for Linux (Wayland compatible).
Designed for simple on-screen annotation with pen, eraser, and undo.

## Features

* Screen overlay drawing (Pen)
* Eraser (pen strokes only)
* Undo (Ctrl + Z)
* Clear canvas (C key)
* Lightweight and fast
* Wayland compatible (GNOME tested)

## Environment

Tested on:

* Linux (Ubuntu)
* GNOME Wayland Session
* Python 3.x
  
X11 is not officially tested.

## Installation (Easy Method)

### 1. Download the file

Download `screendrawing.py`

### 2. Make it executable

```bash
chmod +x screendrawing.py
```

### 3. Install (No sudo, recommended)

```bash
chmod +x screendrawing.py
mkdir -p ~/.local/bin
mv screendrawing.py ~/.local/bin/screendrawing

```

Now you can run it from terminal:

```bash
screendrawing
```

If menu does not appear on GNOME Wayland:
QT_QPA_PLATFORM=wayland screendrawing

Save:
Saved image is transparent (drawing only).
Useful for overlay, editing, and presentations.

If you want full screen capture with drawings,
use external screenshot tools (GNOME Screenshot, Spectacle, etc.)


## Desktop Launcher (GUI 실행)

Create file:

```
~/.local/share/applications/screendrawing.desktop
```

Paste:

```
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

Then refresh:

```bash
update-desktop-database ~/.local/share/applications
```

Now it appears in application menu.

## Controls

| Key      | Function         |
| -------- | ---------------- |
| Mouse    | Draw             |
| Ctrl+Q,ESC   | Quit         |
| C        | Clear canvas     |
| Ctrl + Z | Undo             |
| Ctrl + S | Screen Save      |

## Notes

* Optimized for Wayland environments
* Minimal dependencies
* Designed for personal productivity and screen annotation

## License / 라이선스

This project is licensed under the **GPL-2.0-or-later**.  
이 프로젝트는 **GPL-2.0-or-later** 라이선스 하에 배포됩니다.  
For more information, please see the [LICENSE](LICENSE) file.
