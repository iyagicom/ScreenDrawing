# ScreenDrawing

Lightweight screen drawing tool for Linux (Wayland optimized).  
Designed for simple on-screen annotation with pen, eraser, undo, and transparent overlay.

---

## ✨ Features

- Screen overlay drawing (Pen)
- Eraser (pen strokes only)
- Undo (Ctrl + Z)
- Clear canvas (C key)
- Transparent drawing overlay (PNG save)
- Lightweight & fast
- Wayland compatible (GNOME tested)

---

## 🖥️ Environment

Tested on:

- Ubuntu 24.04
- GNOME Wayland Session
- Python 3.x
- PyQt5

> X11 is not officially tested.

---

## 📥 Installation (No sudo, Recommended)

### 1. Download

Download the file:

screendrawing.py

### 2. Make executable

chmod +x screendrawing.py

### 3. Install to user PATH (best method)

mkdir -p ~/.local/bin
mv screendrawing.py ~/.local/bin/screendrawing
chmod +x ~/.local/bin/screendrawing

Now you can run it from anywhere:

screendrawing

---

## ⚠️ Wayland (GNOME) Notes

If the menu does not appear on GNOME Wayland, run:

QT_QPA_PLATFORM=wayland screendrawing

ScreenDrawing is primarily developed and tested on GNOME Wayland.

---

## 💾 Save Behavior (Important)

Saved images are transparent (drawing only).  
This is intentional and useful for:

- Overlay editing
- Presentations
- Video annotation
- Tutorials / lectures
- Image compositing

If you want a full screen capture with drawings,
use external screenshot tools such as:

- GNOME Screenshot
- Spectacle
- Flameshot

---

## 🚀 Desktop Launcher (GUI 실행)

Create this file:

~/.local/share/applications/screendrawing.desktop

Paste:

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

Then refresh:

update-desktop-database ~/.local/share/applications

Now ScreenDrawing will appear in the application menu.

---

## 🎮 Controls

| Key      | Function                |
|----------|--------------------------|
| Mouse    | Draw                     |
| Ctrl + Z | Undo                     |
| C        | Clear canvas             |
| Ctrl + S | Save (Transparent PNG)   |
| ESC      | Exit                     |
| Ctrl + Q | Exit                     |

---

## 📌 Notes

- Optimized for Wayland environments
- Minimal dependencies (PyQt5 only)
- Runs as fullscreen transparent overlay
- Designed for real-time screen annotation
- Lightweight alternative to heavy annotation tools

---

## 👤 Author

Jeong SeongYong  
Email: iyagicom@gmail.com  

---

## 📜 License / 라이선스

This project is licensed under the GPL-2.0-or-later.  
이 프로젝트는 GPL-2.0-or-later 라이선스 하에 배포됩니다.

You are free to use, modify, and redistribute under GPL terms.
