# ScreenDrawing

Lightweight screen drawing tool for Linux (Wayland compatible).
Designed for simple on-screen annotation with pen, eraser, and undo.

## Features

* Screen overlay drawing (Pen)
* Eraser (pen strokes only)
* Undo (Ctrl + Z)
* Clear canvas (C key)
* Temporary eraser (Ctrl key)
* Straight line (Shift key)
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

### 3. Move to global path (run anywhere)

```bash
sudo mv screendrawing.py /usr/local/bin/screendrawing
```

Now you can run it from terminal:

```bash
screendrawing
```

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
