"""
Main Window for ScaleXPro CV-Modifier:
Friendly, Simple & Premium Lavender/Purple SaaS Desktop Experience:
- Left Sidebar (240px) with rich vertical purple gradient (#6B5FB5 to #7B6CC4),
  white ScaleXPro logo card, rounded lavender active pill (#DDD6F7 with #3B2D7C text),
  real-time badge counters, botanical plant illustration (data/assets/sidebar_art.png),
  and 'Offline & secure' security chip.
- Top Bar (White rounded 20px card) with Page Title, rounded pill search box with circular purple button,
  Help guided tour trigger, Notification Bell with pink badge, and User profile avatar with soft gradient ring.
- Page transition animation (fade + subtle slide) using OutCubic easing.
- Guided Tour for first-run walkthrough.
- Floating non-intrusive Toast notifications.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
    QMenu,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QColor, QKeySequence, QShortcut, QCursor
import qtawesome as qta

from app.ui.styles import (
    SCALEXPRO_SAAS_STYLE,
    apply_scalexpro_palette,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_PURPLE_DARK,
    COLOR_PURPLE_DEEP,
    COLOR_LAVENDER,
    COLOR_LAVENDER_LIGHT,
    COLOR_CTA,
    COLOR_CTA_HOVER,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_APP,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)
from app.ui.dashboard_tab import DashboardTab
from app.ui.main_tab import CVRedactionTab
from app.ui.history_tab import HistoryTab
from app.ui.clients_tab import ClientsTab
from app.ui.templates_tab import TemplatesTab
from app.ui.settings_tab import SettingsTab
from app.ui.widgets import ToastNotification, CardWidget
from app.ui.login_view import LoginView
from app.ui.tour import GuidedTourDialog
from app.ui.animations import animate_page_transition, is_animations_enabled
from app.config import ASSETS_DIR, DB_PATH
from app.database import init_db, get_all_settings, get_dashboard_metrics, get_all_clients, get_submissions
from app.logger import logger


class ClickableFrame(QFrame):
    """QFrame that emits a clicked signal on left mouse click."""
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Primary ScaleXPro SaaS Window hosting Login, Sidebar, Top Bar, Stacked Pages, and Guided Tour."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScaleXPro CV-Modifier - Friendly, Secure & Branded")
        self.current_user: Optional[dict] = None

        # Window sizing: centered at 1440x900, min 1200x750
        self.resize(1440, 900)
        self.setMinimumSize(1200, 750)
        self._center_on_screen()

        # Set App Window Icon
        icon_path = ASSETS_DIR / "app_icon.ico"
        if not icon_path.exists():
            icon_path = ASSETS_DIR / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Apply Global Palette & Stylesheet
        app_inst = QApplication.instance()
        if app_inst:
            apply_scalexpro_palette(app_inst)
        init_db()
        self.setStyleSheet(SCALEXPRO_SAAS_STYLE)

        self._setup_ui()
        self.setMenuBar(None)
        self.setStatusBar(None)
        self._setup_shortcuts()
        self._refresh_user_chip()
        self._update_sidebar_counts()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - 1440) // 2
            y = (screen_geo.height() - 900) // 2
            self.move(max(0, x), max(0, y))

    def _setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("AppRoot")
        self.setCentralWidget(central_widget)

        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Master Window Stack: Page 0 = LoginView, Page 1 = Main SaaS App
        self.window_stack = QStackedWidget()
        central_layout.addWidget(self.window_stack)

        # -------------------------------------------------------------
        # Page 0: Login View
        # -------------------------------------------------------------
        self.login_view = LoginView()
        self.login_view.login_successful.connect(self._on_login_successful)
        self.window_stack.addWidget(self.login_view)

        # -------------------------------------------------------------
        # Page 1: Main Application Container
        # -------------------------------------------------------------
        self.main_app_widget = QWidget()
        root_layout = QHBoxLayout(self.main_app_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.window_stack.addWidget(self.main_app_widget)

        # -------------------------------------------------------------
        # 1. Left Sidebar (240px, Purple Gradient #6B5FB5 -> #7B6CC4)
        # -------------------------------------------------------------
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("SidebarFrame")
        self.sidebar_frame.setFixedWidth(240)
        self.sidebar_frame.setStyleSheet("""
            QFrame#SidebarFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6B5FB5, stop:1 #7B6CC4);
                border: none;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(16, 18, 16, 16)
        sidebar_layout.setSpacing(14)

        # White Rounded Card containing ScaleXPro Logo
        self._build_sidebar_logo(sidebar_layout)

        # Section Heading "DASHBOARD"
        lbl_heading = QLabel("DASHBOARD")
        lbl_heading.setObjectName("SidebarSectionHeading")
        lbl_heading.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px; font-weight: 700; letter-spacing: 1px; padding-left: 6px;")
        sidebar_layout.addWidget(lbl_heading)

        # Navigation Items List
        self.nav_buttons: List[QPushButton] = []
        self.nav_badges: Dict[int, QLabel] = {}

        self.nav_items_meta = [
            ("Home", "fa5s.th-large", 0, None),
            ("Process CV", "fa5s.magic", 1, "queue"),
            ("Submissions", "fa5s.paper-plane", 2, "subs"),
            ("Clients", "fa5s.building", 3, "clients"),
            ("Templates", "fa5s.envelope-open-text", 4, None),
            ("Edit CV", "fa5s.pen", 6, "New"),
            ("Settings", "fa5s.cog", 5, None),
        ]

        nav_box = QVBoxLayout()
        nav_box.setSpacing(5)

        for idx, (label_text, icon_name, page_idx, badge_type) in enumerate(self.nav_items_meta):
            btn_frame = QFrame()
            btn_frame.setStyleSheet("background: transparent;")
            bf_l = QHBoxLayout(btn_frame)
            bf_l.setContentsMargins(0, 0, 0, 0)
            bf_l.setSpacing(0)

            btn = QPushButton(f"  {label_text}")
            btn.setIcon(qta.icon(icon_name, color="#FFFFFF"))
            btn.setIconSize(QSize(17, 17))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("nav_index", idx)
            btn.setProperty("target_page", page_idx)
            btn.clicked.connect(lambda _, p=page_idx: self._on_nav_clicked(p))
            bf_l.addWidget(btn, stretch=1)
            self.nav_buttons.append(btn)

            # Badge container if applicable
            if badge_type:
                badge_lbl = QLabel("")
                badge_lbl.setObjectName("NavBadge")
                badge_lbl.setAlignment(Qt.AlignCenter)
                badge_lbl.setStyleSheet("""
                    background-color: rgba(255, 255, 255, 0.22);
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: 700;
                    border-radius: 9px;
                    padding: 2px 7px;
                    min-width: 14px;
                """)
                bf_l.addWidget(badge_lbl)
                self.nav_badges[idx] = badge_lbl
                if badge_type == "New":
                    badge_lbl.setText("New")
                    badge_lbl.setStyleSheet(f"""
                        background-color: {COLOR_CTA};
                        color: #FFFFFF;
                        font-size: 10px;
                        font-weight: 800;
                        border-radius: 8px;
                        padding: 1px 6px;
                    """)

            nav_box.addWidget(btn_frame)

        sidebar_layout.addLayout(nav_box)
        sidebar_layout.addStretch()

        # Botanical Illustration (data/assets/sidebar_art.png)
        art_path = str(ASSETS_DIR / "sidebar_art.png")
        if os.path.exists(art_path):
            pix = QPixmap(art_path)
            if not pix.isNull():
                art_lbl = QLabel()
                art_lbl.setAlignment(Qt.AlignCenter)
                scaled_art = pix.scaledToWidth(140, Qt.SmoothTransformation)
                art_lbl.setPixmap(scaled_art)
                sidebar_layout.addWidget(art_lbl, alignment=Qt.AlignCenter)

        # "Offline & secure" Chip in Sidebar
        secure_chip = QFrame()
        secure_chip.setObjectName("SidebarSecureChip")
        secure_chip.setStyleSheet("""
            QFrame#SidebarSecureChip {
                background-color: rgba(255, 255, 255, 0.16);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 12px;
                padding: 6px 10px;
            }
        """)
        sc_l = QHBoxLayout(secure_chip)
        sc_l.setContentsMargins(4, 2, 4, 2)
        sc_l.setSpacing(6)

        lock_ico = QLabel()
        lock_ico.setPixmap(qta.icon("fa5s.shield-alt", color="#3DBE7A").pixmap(14, 14))
        sc_l.addWidget(lock_ico)

        sc_txt = QLabel("Offline & secure")
        sc_txt.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600; border: none;")
        sc_l.addWidget(sc_txt, stretch=1)

        v_lbl = QLabel("v2.6")
        v_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px; font-weight: 500;")
        sc_l.addWidget(v_lbl)

        sidebar_layout.addWidget(secure_chip)

        root_layout.addWidget(self.sidebar_frame)

        # -------------------------------------------------------------
        # 2. Main Content Area (Top Bar + QStackedWidget)
        # -------------------------------------------------------------
        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        # Top Bar (White Rounded 20px Card)
        self._build_top_bar(main_layout)

        # Page Stack
        self.stack = QStackedWidget()
        self.page_dashboard = DashboardTab()
        self.page_process = CVRedactionTab()
        self.page_submissions = HistoryTab()
        self.page_clients = ClientsTab()
        self.page_templates = TemplatesTab()
        self.page_settings = SettingsTab()

        self.stack.addWidget(self.page_dashboard)    # Index 0
        self.stack.addWidget(self.page_process)      # Index 1
        self.stack.addWidget(self.page_submissions)  # Index 2
        self.stack.addWidget(self.page_clients)      # Index 3
        self.stack.addWidget(self.page_templates)    # Index 4
        self.stack.addWidget(self.page_settings)     # Index 5

        main_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(main_content, stretch=1)

        # -------------------------------------------------------------
        # 3. Inter-Page Connections & Signals
        # -------------------------------------------------------------
        self.page_dashboard.navigate_to_tab.connect(self.switch_page)
        self.page_dashboard.files_selected_signal.connect(self._on_dashboard_files_dropped)
        self.page_dashboard.show_toast_signal.connect(self.show_toast)

        self.page_templates.show_toast_signal.connect(self.show_toast)
        self.page_settings.show_toast_signal.connect(self.show_toast)
        self.page_settings.settings_saved_signal.connect(self._on_settings_saved)

        self.page_process.status_signal.connect(self._on_process_status)
        self.page_process.navigate_to_tab.connect(self.switch_page)

        # -------------------------------------------------------------
        # 4. Floating Toast Notification & Guided Tour
        # -------------------------------------------------------------
        self.toast = ToastNotification(self)
        self.tour_dialog = GuidedTourDialog(self)

        # Check remembered login or auto-continue for offline convenience
        from app.database import get_setting, get_user_by_username
        remembered = get_setting("remembered_username", "")
        if remembered:
            u = get_user_by_username(remembered)
            if u:
                self.bypass_login(dict(u))
            else:
                self.window_stack.setCurrentIndex(0)
                self.switch_page(0)
        else:
            self.window_stack.setCurrentIndex(0)
            self.switch_page(0)

    # -----------------------------------------------------------------
    # Top Bar Component (White Rounded 20px Card)
    # -----------------------------------------------------------------
    def _build_top_bar(self, parent_layout: QVBoxLayout):
        top_bar_card = CardWidget(radius=20, enable_shadow=True, enable_hover_lift=False)
        top_bar_card.setFixedHeight(64)
        top_bar_layout = QHBoxLayout(top_bar_card)
        top_bar_layout.setContentsMargins(22, 10, 22, 10)
        top_bar_layout.setSpacing(16)

        # Page Title in Bold Deep Navy
        self.lbl_page_title = QLabel("Dashboard")
        self.lbl_page_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 800; border: none;")
        top_bar_layout.addWidget(self.lbl_page_title)

        top_bar_layout.addSpacing(16)

        # Search Bar Pill with Circular Purple Button (from Reference)
        search_frame = QFrame()
        search_frame.setObjectName("TopSearchBar")
        search_frame.setFixedWidth(340)
        sf_layout = QHBoxLayout(search_frame)
        sf_layout.setContentsMargins(12, 2, 4, 2)
        sf_layout.setSpacing(8)

        self.global_search = QLineEdit()
        self.global_search.setObjectName("SearchBox")
        self.global_search.setPlaceholderText("Search candidates, clients, CVs...")
        self.global_search.returnPressed.connect(self._on_global_search)
        sf_layout.addWidget(self.global_search, stretch=1)

        btn_search_circle = QPushButton()
        btn_search_circle.setObjectName("SearchCircleBtn")
        btn_search_circle.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        btn_search_circle.setIconSize(QSize(13, 13))
        btn_search_circle.setCursor(Qt.PointingHandCursor)
        btn_search_circle.clicked.connect(self._on_global_search)
        sf_layout.addWidget(btn_search_circle)

        top_bar_layout.addWidget(search_frame)
        top_bar_layout.addStretch()

        # "Help" button to trigger the Guided Tour
        self.btn_help = QPushButton()
        self.btn_help.setObjectName("TopBarHelp")
        self.btn_help.setIcon(qta.icon("fa5s.question-circle", color=COLOR_PRIMARY))
        self.btn_help.setIconSize(QSize(16, 16))
        self.btn_help.setFixedSize(36, 36)
        self.btn_help.setToolTip("Open Guided Tour & Tips")
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                border: 1px solid #DDD6F7;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
            }}
        """)
        self.btn_help.clicked.connect(self._on_help_clicked)
        top_bar_layout.addWidget(self.btn_help)

        # Notification Bell with pink notification dot
        self.btn_bell = QPushButton()
        self.btn_bell.setIcon(qta.icon("fa5s.bell", color="#6C5CB8"))
        self.btn_bell.setIconSize(QSize(16, 16))
        self.btn_bell.setFixedSize(36, 36)
        self.btn_bell.setToolTip("Recent notifications")
        self.btn_bell.setCursor(Qt.PointingHandCursor)
        self.btn_bell.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                border: 1px solid #DDD6F7;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
            }}
        """)
        self.btn_bell.clicked.connect(self._on_bell_clicked)
        top_bar_layout.addWidget(self.btn_bell)

        # User Profile Avatar Pill with Gradient Ring
        self.user_chip = ClickableFrame()
        self.user_chip.setObjectName("UserChipFrame")
        self.user_chip.setCursor(Qt.PointingHandCursor)
        self.user_chip.clicked.connect(self._show_user_menu)
        uc_layout = QHBoxLayout(self.user_chip)
        uc_layout.setContentsMargins(4, 2, 12, 2)
        uc_layout.setSpacing(10)

        # Avatar with soft gradient aura
        avatar_circle = QFrame()
        avatar_circle.setFixedSize(32, 32)
        avatar_circle.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #E4E0FA, stop:1 #DDD6F7);
                border-radius: 16px;
                border: 1.5px solid #6C5CB8;
            }
        """)
        av_l = QVBoxLayout(avatar_circle)
        av_l.setContentsMargins(0, 0, 0, 0)
        self.avatar_lbl = QLabel("KN")
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet(f"color: {COLOR_PURPLE_DEEP}; font-size: 12px; font-weight: 700; border: none;")
        av_l.addWidget(self.avatar_lbl)
        uc_layout.addWidget(avatar_circle)

        # Name and Role
        u_text = QVBoxLayout()
        u_text.setSpacing(1)
        u_text.setContentsMargins(0, 0, 0, 0)

        self.lbl_user_name = QLabel("Kashish Niranjan")
        self.lbl_user_name.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 700; font-size: 12.5px; border: none;")
        u_text.addWidget(self.lbl_user_name)

        self.lbl_user_role = QLabel("Talent Operations")
        self.lbl_user_role.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; border: none;")
        u_text.addWidget(self.lbl_user_role)
        uc_layout.addLayout(u_text)

        top_bar_layout.addWidget(self.user_chip)
        parent_layout.addWidget(top_bar_card)

    # -----------------------------------------------------------------
    # Sidebar Logo Component
    # -----------------------------------------------------------------
    def _build_sidebar_logo(self, parent_layout: QVBoxLayout):
        logo_card = QFrame()
        logo_card.setObjectName("SidebarLogoCard")
        logo_card.setStyleSheet("""
            QFrame#SidebarLogoCard {
                background-color: #FFFFFF;
                border-radius: 16px;
                padding: 6px 10px;
            }
        """)
        lc_l = QHBoxLayout(logo_card)
        lc_l.setContentsMargins(4, 4, 4, 4)
        lc_l.setAlignment(Qt.AlignCenter)

        logo_path = str(ASSETS_DIR / "scalexpro_logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                lbl_logo = QLabel()
                lbl_logo.setAlignment(Qt.AlignCenter)
                scaled_pix = pix.scaledToWidth(170, Qt.SmoothTransformation)
                lbl_logo.setPixmap(scaled_pix)
                lc_l.addWidget(lbl_logo)
            else:
                lbl_text = QLabel("ScaleXPro")
                lbl_text.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 20px; font-weight: 800;")
                lc_l.addWidget(lbl_text)
        else:
            lbl_text = QLabel("ScaleXPro")
            lbl_text.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 20px; font-weight: 800;")
            lc_l.addWidget(lbl_text)

        parent_layout.addWidget(logo_card)

    # -----------------------------------------------------------------
    # Shortcuts
    # -----------------------------------------------------------------
    def _setup_shortcuts(self):
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self._on_shortcut_open)

        shortcut_send = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_send.activated.connect(self._on_shortcut_send)

    def _on_shortcut_open(self):
        if self.stack.currentIndex() != 1:
            self.switch_page(1)
        self.page_process._on_browse_clicked()

    def _on_shortcut_send(self):
        if self.stack.currentIndex() == 1:
            self.page_process._on_send_clicked()

    # -----------------------------------------------------------------
    # Navigation & Page Transitions
    # -----------------------------------------------------------------
    def _on_nav_clicked(self, page_idx: int):
        if page_idx == 6:
            # Edit CV mode: Switch to Process CV in Review mode
            self.switch_page(1)
            # If the process tab has an edit mode toggle, trigger it
            if hasattr(self.page_process, "preview_widget"):
                self.page_process.preview_widget.enter_edit_mode()
        else:
            self.switch_page(page_idx)

    def switch_page(self, index: int):
        """Switches the active page in QStackedWidget and updates sidebar highlights."""
        if index < 0 or index >= self.stack.count():
            return

        # Animate transition smoothly
        animate_page_transition(self.stack, index)

        page_titles = [
            ("Dashboard", "Overview & pipeline"),
            ("Process CV", "Redact contacts & apply adaptive brand"),
            ("Submissions History", "Client delivery logs & tracking"),
            ("Client Management", "Recipients and hiring contacts"),
            ("Email Templates", "Dispatch copy and placeholders"),
            ("Settings", "Branding, SMTP & preferences"),
        ]
        title, _ = page_titles[index]
        self.lbl_page_title.setText(title)

        # Update sidebar visual state
        for btn in self.nav_buttons:
            target = btn.property("target_page")
            is_active = (target == index) or (index == 1 and target == 6)

            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_LAVENDER};
                        color: {COLOR_PURPLE_DEEP};
                        border: none;
                        border-radius: 12px;
                        font-size: 13.5px;
                        font-weight: 700;
                        text-align: left;
                        padding: 10px 14px;
                    }}
                """)
                # Set icon color to deep purple
                idx_meta = btn.property("nav_index")
                icon_name = self.nav_items_meta[idx_meta][1]
                btn.setIcon(qta.icon(icon_name, color=COLOR_PURPLE_DEEP))
            else:
                btn.setStyleSheet("""
                    QPushButton {{
                        background-color: transparent;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 12px;
                        font-size: 13.5px;
                        font-weight: 500;
                        text-align: left;
                        padding: 10px 14px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.15);
                        color: #FFFFFF;
                    }}
                """)
                idx_meta = btn.property("nav_index")
                icon_name = self.nav_items_meta[idx_meta][1]
                btn.setIcon(qta.icon(icon_name, color="#FFFFFF"))

        self._update_sidebar_counts()

        # Data refreshes
        if index == 0:
            self.page_dashboard.refresh_dashboard()
        elif index == 1:
            self.page_process.reload_clients_dropdown()
        elif index == 2:
            self.page_submissions.refresh_history()
        elif index == 3:
            self.page_clients.refresh_clients()
        elif index == 4:
            self.page_templates.load_templates()
        elif index == 5:
            self.page_settings.load_settings()

    def _update_sidebar_counts(self):
        try:
            metrics = get_dashboard_metrics()
            clients = get_all_clients()

            # Process CV count (queue)
            if 1 in self.nav_badges:
                self.nav_badges[1].setText(str(metrics.get("cvs_processed", 0)))

            # Submissions count
            if 2 in self.nav_badges:
                self.nav_badges[2].setText(str(metrics.get("sent_count", 0)))

            # Clients count
            if 3 in self.nav_badges:
                self.nav_badges[3].setText(str(len(clients)))
        except Exception as e:
            logger.debug(f"Error updating sidebar badge counts: {e}")

    def _on_dashboard_files_dropped(self, files: list):
        self.page_process.load_multiple_files(files)
        self.show_toast(f"Imported {len(files)} CV(s) for automated processing.", "success", "Files Ready")

    def _on_process_status(self, message: str, status_type: str):
        self.show_toast(message, status_type)

    def show_toast(self, message: str, status_type: str = "info", title: Optional[str] = None):
        self.toast.show_message(message, status_type, title)

    def _refresh_user_chip(self):
        if self.current_user:
            name = self.current_user.get("full_name") or self.current_user.get("username", "Kashish Niranjan")
            role = self.current_user.get("role", "Talent Operations")
        else:
            settings = get_all_settings()
            name = settings.get("recruiter_name", "Kashish Niranjan")
            role = settings.get("recruiter_role", "Talent Operations")

        self.lbl_user_name.setText(name)
        self.lbl_user_role.setText(role)
        initials = "".join([part[0] for part in name.split()[:2]]).upper() if name else "KN"
        self.avatar_lbl.setText(initials)

    def _on_settings_saved(self):
        self._refresh_user_chip()
        self.page_dashboard.refresh_dashboard()
        self._update_sidebar_counts()

    def _on_login_successful(self, user: dict):
        self.current_user = user
        self._refresh_user_chip()
        if hasattr(self.page_settings, "set_current_user"):
            self.page_settings.set_current_user(user)
        self.window_stack.setCurrentIndex(1)
        self.switch_page(0)
        self.show_toast(f"Welcome back, {user.get('full_name', 'Recruiter')}!", "success", "Signed In")

    def _on_global_search(self):
        query = self.global_search.text().strip()
        if not query:
            return
        self.switch_page(2)
        if hasattr(self.page_submissions, "search_input"):
            self.page_submissions.search_input.setText(query)
            self.page_submissions._on_search_changed(query)

    def _on_help_clicked(self):
        self.tour_dialog.show_tour(self)

    def _on_bell_clicked(self):
        self.show_toast("All background safety checks & redactions are running normally.", "info", "Notifications")

    def _show_user_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 18px;
                border-radius: 8px;
                color: {COLOR_NAVY};
                font-size: 13px;
                font-weight: 500;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_LAVENDER_LIGHT};
                color: {COLOR_PURPLE_DEEP};
            }}
        """)
        act_prof = menu.addAction(qta.icon("fa5s.user-cog", color=COLOR_PRIMARY), "Edit Profile & Settings")
        act_tour = menu.addAction(qta.icon("fa5s.map-signs", color=COLOR_PRIMARY), "Replay Guided Tour")
        menu.addSeparator()
        act_logout = menu.addAction(qta.icon("fa5s.sign-out-alt", color=COLOR_DANGER), "Log Out")

        action = menu.exec(QCursor.pos())
        if action == act_prof:
            self.switch_page(5)
        elif action == act_tour:
            self.tour_dialog.show_tour(self)
        elif action == act_logout:
            self.current_user = None
            self.window_stack.setCurrentIndex(0)
            self.show_toast("Logged out successfully.", "info", "Signed Out")

    def bypass_login(self, user: dict):
        """Bypasses login view for screenshot verification scripts."""
        self._on_login_successful(user)
