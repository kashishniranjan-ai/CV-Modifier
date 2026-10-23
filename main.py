"""
CV-Modifier: Enterprise Candidate Anonymizer & Brander (Offline Desktop Application)
Entry point of the application.
"""

import os
import sys
import traceback

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt

from app.config import ensure_directories, ASSETS_DIR
from app.logger import logger
from app.ui.styles import apply_scalexpro_palette
from app.ui.main_window import MainWindow
from app.ui.splash import ScaleXProSplashScreen


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log uncaught errors."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Uncaught Exception:\n{err_str}")
    try:
        QMessageBox.critical(
            None,
            "Critical Error",
            f"An unexpected error occurred:\n\n{exc_value}\n\nPlease check the log file.",
        )
    except Exception:
        pass


def run_cli_test_redact(args):
    """CLI mode to test redaction directly from the executable without launching full GUI."""
    import ctypes
    # Attach to parent console if available so stdout is visible in CMD/PowerShell
    try:
        if ctypes.windll.kernel32.AttachConsole(-1):
            if sys.stdout is None or not hasattr(sys.stdout, "write"):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            if sys.stderr is None or not hasattr(sys.stderr, "write"):
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    except Exception:
        pass

    from pathlib import Path
    from app.core.pdf_redactor import redact_and_brand_pdf
    from app.core.validator import validate_clean_pdf
    from app.config import EXPORTS_DIR, BASE_DIR

    input_pdf = args[1] if len(args) > 1 else str(BASE_DIR / "sample_data" / "sample_cv_john_doe.pdf")
    output_pdf = args[2] if len(args) > 2 else str(EXPORTS_DIR / "CAND-9999_Test_Redacted.pdf")
    scalexpro = BASE_DIR / "data" / "assets" / "scalexpro_logo.png"
    logo_path = str(scalexpro) if scalexpro.exists() else str(BASE_DIR / "sample_data" / "scalexpro_logo.png")

    print("\n" + "=" * 60)
    print("CV-MODIFIER: Running Standalone Redaction Test")
    print(f"Input CV:    {input_pdf}")
    print(f"Output PDF:  {output_pdf}")
    print(f"Logo Banner: {logo_path}")
    print("=" * 60)

    if not Path(input_pdf).exists():
        print(f"ERROR: Input file not found: {input_pdf}")
        logger.error(f"Input file not found: {input_pdf}")
        sys.exit(1)

    res = redact_and_brand_pdf(
        input_path=input_pdf,
        output_path=output_pdf,
        logo_path=logo_path,
        redaction_color="white",
        redact_email=True,
        redact_phone=True,
        redact_urls=True,
        redact_address=True,
        redact_metadata=True,
        add_logo=True,
    )

    if not res.success:
        print(f"ERROR: Redaction failed: {res.error_message}")
        logger.error(f"Redaction failed: {res.error_message}")
        sys.exit(1)

    print(f"SUCCESS: Redacted {len(res.redactions_applied)} sensitive items permanently.")
    for item in res.redactions_applied:
        print(f"  * [Page {item.get('page', 1)}] {item['category']}: {item['value']}")

    print("\nRunning post-redaction safety scan...")
    is_clean, violations = validate_clean_pdf(output_pdf)
    if not is_clean:
        print(f"SECURITY BLOCK: {len(violations)} violations still detected!")
        for v in violations:
            print(f"  ✖ {v['description']}")
        sys.exit(1)

    print("VALIDATION PASSED: 0 residual sensitive items detected in output PDF.")
    print(f"Branded output PDF successfully generated at:\n{output_pdf}")
    print("=" * 60 + "\n")
    logger.info("Standalone CLI redaction test completed successfully.")
    sys.exit(0)


def main():
    # Ensure all data and log directories exist
    ensure_directories()
    sys.excepthook = handle_exception

    # Check for CLI test-redact argument
    if len(sys.argv) > 1 and sys.argv[1] == "--test-redact":
        run_cli_test_redact(sys.argv[1:])
        return

    logger.info("Starting ScaleXPro CV-Modifier Desktop Application...")

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ScaleXPro CV-Modifier")
    app.setOrganizationName("ScaleXPro")

    # Apply central light palette
    apply_scalexpro_palette(app)

    # Set application icon
    icon_path = ASSETS_DIR / "app_icon.ico"
    if not icon_path.exists():
        icon_path = ASSETS_DIR / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Display branded startup splash screen (Screen 10)
    splash = ScaleXProSplashScreen()
    splash.show()
    app.processEvents()

    from app.database import get_setting
    from app.ui.animations import set_animations_enabled
    reduce_anim = get_setting("reduce_animations", False)
    set_animations_enabled(not bool(reduce_anim))

    window = MainWindow()

    if splash:
        splash.finish(window)

    window.show()

    exit_code = app.exec()
    logger.info(f"ScaleXPro CV-Modifier Application exited with code {exit_code}")
    sys.exit(exit_code)



if __name__ == "__main__":
    main()
