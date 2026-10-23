import os
import re
import sys

os.environ["QT_API"] = "pyside6"
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import qtawesome as qta

files = [
    "app/ui/dashboard_tab.py",
    "app/ui/main_window.py",
    "app/ui/main_tab.py",
    "app/ui/history_tab.py",
    "app/ui/clients_tab.py",
    "app/ui/templates_tab.py",
    "app/ui/settings_tab.py",
    "app/ui/widgets.py",
]

all_icons = set()
for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
            for match in re.finditer(r'qta\.icon\(["\']([^"\']+)["\']', content):
                all_icons.add((match.group(1), fpath))

for icon, fpath in sorted(all_icons):
    try:
        qta.icon(icon)
        print(f"OK: {icon} (in {fpath})")
    except Exception as e:
        print(f"FAILED: {icon} (in {fpath}) -> {e}")
