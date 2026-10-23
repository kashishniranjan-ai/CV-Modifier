"""
Script to capture high-definition screenshots of every page in CV-Modifier.
Saves to screenshots/ directory and prints status.
"""

import os
import sys
import time

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

from app.ui.styles import apply_scalexpro_palette
from app.config import ASSETS_DIR
apply_scalexpro_palette(app)

from app.ui.main_window import MainWindow

os.makedirs("screenshots", exist_ok=True)

# 1. Capture Splash Screen
splash_img_path = ASSETS_DIR / "splash_screen.png"
if splash_img_path.exists():
    splash_pix = QPixmap(str(splash_img_path))
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()
    splash.showMessage(
        "   ScaleXPro CV-Modifier • Loading system & offline modules...",
        Qt.AlignBottom | Qt.AlignLeft,
        QColor("#F28A1E"),
    )
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    splash_grab = splash.grab()
    splash_grab.save("screenshots/splash.png")
    print(f"Captured Startup Splash Screen -> screenshots/splash.png ({splash_grab.width()}x{splash_grab.height()})")
    splash.close()

win = MainWindow()
win.resize(1440, 900)
win.show()

# Allow Qt to process events
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)

# Capture Login View
pix_login = win.grab()
pix_login.save("screenshots/login.png")
print(f"Captured Login Screen -> screenshots/login.png ({pix_login.width()}x{pix_login.height()})")

# Bypass login to capture main workspace
win.bypass_login({
    "id": 1,
    "username": "recruiter",
    "full_name": "Kashish Niranjan",
    "role": "Talent Operations",
    "email": "kashish@scalexpro.com",
})

for _ in range(10):
    app.processEvents()
    time.sleep(0.02)

pages = [
    (0, "dashboard", "Dashboard Page"),
    (1, "process_cv_hero", "Process CV (Upload Hero State)"),
    (2, "submissions", "Submissions Page"),
    (3, "clients", "Clients Page"),
    (4, "templates", "Templates Page"),
    (5, "settings", "Settings Page"),
]

for idx, slug, name in pages:
    win.switch_page(idx)
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    pix = win.grab()
    out_file = f"screenshots/{slug}.png"
    pix.save(out_file)
    print(f"Captured {name} -> {out_file} ({pix.width()}x{pix.height()})")

# Now test and capture Process CV with loaded sample CV
win.switch_page(1)
win.page_process._load_sample_cv()
# Wait for worker thread to finish
if hasattr(win.page_process, "worker") and win.page_process.worker:
    win.page_process.worker.wait(10000)

for _ in range(15):
    app.processEvents()
    time.sleep(0.05)

pix_loaded = win.grab()
pix_loaded.save("screenshots/process_cv_loaded.png")
pix_loaded.save("screenshots/process_cv.png")
print(f"Captured Process CV (Loaded & Anonymized) -> screenshots/process_cv_loaded.png ({pix_loaded.width()}x{pix_loaded.height()})")

print("All screenshots successfully captured!")
sys.exit(0)
