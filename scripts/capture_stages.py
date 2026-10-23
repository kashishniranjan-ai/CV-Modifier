"""
Screenshot capture utility for ScaleXPro CV-Modifier design board verification.
Captures each screen at high resolution and saves to screenshots/
"""

import os
import sys
import time
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from app.config import ensure_directories
from app.database import init_db, get_user_count, create_user
from app.ui.styles import apply_scalexpro_palette
from app.ui.main_window import MainWindow

def wait_ui(app, ms: int = 350):
    """Processes Qt events while waiting for animations and layouts to settle."""
    start = time.time()
    while (time.time() - start) * 1000 < ms:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()

def capture_screens():
    ensure_directories()
    init_db()

    shots_dir = ROOT_DIR / "screenshots"
    shots_dir.mkdir(exist_ok=True)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    apply_scalexpro_palette(app)

    window = MainWindow()
    window.resize(1440, 900)
    window.show()
    wait_ui(app, 300)

    # 1. Screen 1: Login Screen (Sign In mode)
    window.window_stack.setCurrentIndex(0)
    window.login_view.form_stack.setCurrentIndex(0)
    window.login_view.txt_username.setText("admin@scalexpro.com")
    window.login_view.chk_remember.setChecked(True)
    wait_ui(app, 300)
    pix = window.grab()
    pix.save(str(shots_dir / "01_login_signin.png"))
    print(f"Captured: {shots_dir / '01_login_signin.png'}")

    # 2. Screen 1b: First-run Admin Account Setup Wizard
    window.login_view.form_stack.setCurrentIndex(1)
    wait_ui(app, 300)
    pix = window.grab()
    pix.save(str(shots_dir / "01b_login_create_admin.png"))
    print(f"Captured: {shots_dir / '01b_login_create_admin.png'}")

    # 3. Bypass login to capture Inner App Screens
    admin_user = {
        "id": 1,
        "username": "admin",
        "full_name": "Kashish Niranjan",
        "email": "kashish@scalexpro.com",
        "role": "Admin",
    }
    window.bypass_login(admin_user)
    wait_ui(app, 300)

    # Screen 2: Dashboard
    window.switch_page(0)
    wait_ui(app, 400)
    pix = window.grab()
    pix.save(str(shots_dir / "02_dashboard.png"))
    print(f"Captured: {shots_dir / '02_dashboard.png'}")

    # Screen 3: Process CV
    window.switch_page(1)
    sample_pdf = ROOT_DIR / "sample_data" / "sample_cv_john_doe.pdf"
    if sample_pdf.exists():
        window.page_process.start_batch_processing([str(sample_pdf)])
        # Wait for processing thread
        for _ in range(60):
            app.processEvents()
            time.sleep(0.05)
            if not window.page_process.worker or not window.page_process.worker.isRunning():
                break
        wait_ui(app, 500)

    pix = window.grab()
    pix.save(str(shots_dir / "03_process_cv.png"))
    print(f"Captured: {shots_dir / '03_process_cv.png'}")

    # Screen 4: Process CV Loading Dialog
    from app.ui.process_dialogs import ProcessLoadingDialog, ProcessSuccessDialog
    dlg_loading = ProcessLoadingDialog(window)
    dlg_loading.resize(window.size())
    dlg_loading.move(window.pos())
    dlg_loading.show()
    wait_ui(app, 400)
    pix = dlg_loading.grab()
    pix.save(str(shots_dir / "04_process_loading.png"))
    dlg_loading.close()
    print(f"Captured: {shots_dir / '04_process_loading.png'}")

    # Screen 5: Process CV Success Dialog
    dlg_success = ProcessSuccessDialog(
        client_name="Acme Foods Pvt Ltd",
        client_email="client@acmefoods.com",
        candidate_id="CAND-1042",
        sent_time="22 Oct 2025, 10:24 AM",
        parent=window,
    )
    dlg_success.resize(window.size())
    dlg_success.move(window.pos())
    dlg_success.show()
    wait_ui(app, 400)
    pix = dlg_success.grab()
    pix.save(str(shots_dir / "05_process_success.png"))
    dlg_success.close()
    print(f"Captured: {shots_dir / '05_process_success.png'}")

    # Screen 6: Submissions History
    window.switch_page(2)
    wait_ui(app, 400)
    pix = window.grab()
    pix.save(str(shots_dir / "06_submissions.png"))
    print(f"Captured: {shots_dir / '06_submissions.png'}")

    # Screen 7: Clients
    window.switch_page(3)
    wait_ui(app, 400)
    pix = window.grab()
    pix.save(str(shots_dir / "07_clients.png"))
    print(f"Captured: {shots_dir / '07_clients.png'}")

    # Screen 7b: Add Client Modal
    from app.ui.clients_tab import ClientDialog
    dlg_client = ClientDialog(parent=window)
    dlg_client.company_edit.setText("Acme Foods Pvt Ltd")
    dlg_client.email_edit.setText("client@acmefoods.com")
    dlg_client.name_edit.setText("John Doe (Hiring VP)")
    dlg_client.show()
    wait_ui(app, 300)
    pix = dlg_client.grab()
    pix.save(str(shots_dir / "07b_clients_add_modal.png"))
    dlg_client.close()
    print(f"Captured: {shots_dir / '07b_clients_add_modal.png'}")

    # Screen 8: Templates
    window.switch_page(4)
    wait_ui(app, 400)
    pix = window.grab()
    pix.save(str(shots_dir / "08_templates.png"))
    print(f"Captured: {shots_dir / '08_templates.png'}")

    # Screen 9: Settings
    window.switch_page(5)
    wait_ui(app, 400)
    pix = window.grab()
    pix.save(str(shots_dir / "09_settings.png"))
    print(f"Captured: {shots_dir / '09_settings.png'}")

    # Screen 9b: Settings User Management (scrolled)
    if hasattr(window, "page_settings"):
        window.page_settings.set_current_user({"username": "admin", "role": "Admin", "full_name": "Admin User"})
        if hasattr(window.page_settings, "scroll"):
            vbar = window.page_settings.scroll.verticalScrollBar()
            vbar.setValue(vbar.maximum())
            wait_ui(app, 400)
            pix = window.grab()
            pix.save(str(shots_dir / "09b_settings_user_management.png"))
            print(f"Captured: {shots_dir / '09b_settings_user_management.png'}")

    # Screen 10: Splash Screen
    from app.ui.splash import ScaleXProSplashScreen
    splash = ScaleXProSplashScreen()
    splash.show()
    wait_ui(app, 400)
    pix = splash.grab()
    pix.save(str(shots_dir / "10_splash.png"))
    splash.close()
    print(f"Captured: {shots_dir / '10_splash.png'}")

    # Screen 11: App Icon
    import shutil
    icon_src = ROOT_DIR / "data" / "assets" / "app_icon.png"
    if icon_src.exists():
        shutil.copy2(icon_src, shots_dir / "11_app_icon.png")
        print(f"Captured: {shots_dir / '11_app_icon.png'}")

    # Screen 12: First-run Guided Tour
    window.switch_page(0)
    wait_ui(app, 300)
    window.tour_dialog.show_tour(center_on_widget=window)
    wait_ui(app, 300)
    pix = window.grab()
    pix.save(str(shots_dir / "12_guided_tour.png"))
    window.tour_dialog.hide()
    print(f"Captured: {shots_dir / '12_guided_tour.png'}")

    print("All initial screens captured successfully!")
    window.close()

if __name__ == "__main__":
    capture_screens()
