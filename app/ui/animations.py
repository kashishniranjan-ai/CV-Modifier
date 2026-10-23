"""
Animation Engine for ScaleXPro CV-Modifier:
Provides smooth 60fps animations with OutCubic easing:
- Page transitions (fade + subtle horizontal slide)
- Staggered card entrance (fade-in + 12px rise with 60ms delay per card)
- Animated stat counters (counting up from 0 to target value)
- Confetti particle burst effect for success celebrations
- Card hover elevation (2px rise and soft shadow expansion)
- Respects the "Reduce animations" setting globally to preserve CPU on slow PCs
"""

import math
import random
from typing import Optional, List, Callable
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QStackedWidget,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    QTimer,
    QObject,
    Property,
)
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

# Global flag: reduced animations
_ANIMATIONS_ENABLED = True


def set_animations_enabled(enabled: bool):
    global _ANIMATIONS_ENABLED
    _ANIMATIONS_ENABLED = enabled


def is_animations_enabled() -> bool:
    return _ANIMATIONS_ENABLED


# -----------------------------------------------------------------------------
# 1. Number Counter Animation
# -----------------------------------------------------------------------------
class NumberCounterAnimator(QObject):
    """Smoothly counts an integer value from 0 to target_val on a QLabel."""
    def __init__(
        self,
        label: QLabel,
        target_value: int,
        duration_ms: int = 500,
        prefix: str = "",
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent or label)
        self.label = label
        self.target = target_value
        self.duration = duration_ms
        self.prefix = prefix
        self.suffix = suffix
        self._current: float = 0.0

        if not is_animations_enabled():
            self.label.setText(f"{self.prefix}{self.target}{self.suffix}")
            return

        self._anim = QPropertyAnimation(self, b"counterValue", self)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(target_value))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def get_counter_value(self) -> float:
        return self._current

    def set_counter_value(self, val: float):
        self._current = val
        self.label.setText(f"{self.prefix}{int(round(val))}{self.suffix}")

    counterValue = Property(float, get_counter_value, set_counter_value)


def animate_number(label: QLabel, target_val: int, prefix: str = "", suffix: str = "", duration_ms: int = 500):
    NumberCounterAnimator(label, target_val, duration_ms, prefix, suffix)


# -----------------------------------------------------------------------------
# 2. Staggered Card Entrance Animation
# -----------------------------------------------------------------------------
def animate_card_entrance(widget: QWidget, delay_ms: int = 0, duration_ms: int = 350):
    """Fades in and rises a card slightly by 10px."""
    if not is_animations_enabled():
        return

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    orig_pos = widget.pos()
    start_pos = QPoint(orig_pos.x(), orig_pos.y() + 10)
    widget.move(start_pos)

    def _start_anim():
        group = QParallelAnimationGroup(widget)

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(duration_ms)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        rise = QPropertyAnimation(widget, b"pos")
        rise.setDuration(duration_ms)
        rise.setStartValue(start_pos)
        rise.setEndValue(orig_pos)
        rise.setEasingCurve(QEasingCurve.OutCubic)

        group.addAnimation(fade)
        group.addAnimation(rise)
        group.start(QPropertyAnimation.DeleteWhenStopped)

    if delay_ms > 0:
        QTimer.singleShot(delay_ms, _start_anim)
    else:
        _start_anim()


# -----------------------------------------------------------------------------
# 3. Page Transition Animation
# -----------------------------------------------------------------------------
def animate_page_transition(stack: QStackedWidget, next_idx: int, duration_ms: int = 200):
    """Performs a smooth, non-blocking fade-in transition when switching pages."""
    curr_idx = stack.currentIndex()
    if curr_idx == next_idx:
        return
    if not is_animations_enabled():
        stack.setCurrentIndex(next_idx)
        return

    # Cancel any in-flight page transition animation
    if hasattr(stack, "_page_anim") and stack._page_anim:
        try:
            stack._page_anim.stop()
        except Exception:
            pass
        stack._page_anim = None

    # Reset any lingering graphics effects across all pages
    for i in range(stack.count()):
        w = stack.widget(i)
        if w and w.graphicsEffect():
            w.setGraphicsEffect(None)

    next_widget = stack.widget(next_idx)
    if not next_widget:
        stack.setCurrentIndex(next_idx)
        return

    stack.setCurrentIndex(next_idx)

    # Fade in next widget cleanly
    effect = QGraphicsOpacityEffect(next_widget)
    next_widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    anim = QPropertyAnimation(effect, b"opacity", stack)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def _cleanup():
        next_widget.setGraphicsEffect(None)
        stack._page_anim = None
        next_widget.update()

    anim.finished.connect(_cleanup)
    stack._page_anim = anim
    anim.start(QPropertyAnimation.DeleteWhenStopped)


# -----------------------------------------------------------------------------
# 4. Confetti Burst Particle Canvas
# -----------------------------------------------------------------------------
class Particle:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 9)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2.5
        self.size = random.uniform(5, 9)
        self.color = random.choice([
            QColor("#6C5CB8"),  # Purple
            QColor("#F28A1E"),  # Orange
            QColor("#3DBE7A"),  # Green
            QColor("#FBE4F3"),  # Pink
            QColor("#DDD6F7"),  # Lavender
            QColor("#DCE8FB"),  # Blue
            QColor("#FBBF24"),  # Gold
        ])
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-8, 8)
        self.alpha = 255


class ConfettiBurstWidget(QWidget):
    """Full-bleed transparent overlay widget providing a 1.2s confetti particle burst."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.particles: List[Particle] = []
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._step)
        self.hide()

    def burst(self, center_x: Optional[int] = None, center_y: Optional[int] = None, count: int = 60):
        if not is_animations_enabled():
            return
        w = self.parentWidget().width() if self.parentWidget() else 400
        h = self.parentWidget().height() if self.parentWidget() else 300
        self.resize(w, h)
        cx = center_x if center_x is not None else w // 2
        cy = center_y if center_y is not None else h // 2

        self.particles = [Particle(cx, cy) for _ in range(count)]
        self.show()
        self.raise_()
        self._timer.start()

    def _step(self):
        alive = False
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.22  # gravity
            p.vx *= 0.98  # drag
            p.rotation += p.rot_speed
            p.alpha = max(0, p.alpha - 5)
            if p.alpha > 0:
                alive = True

        self.update()
        if not alive:
            self._timer.stop()
            self.hide()

    def paintEvent(self, event):
        if not self.particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for p in self.particles:
            if p.alpha <= 0:
                continue
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rotation)
            col = QColor(p.color)
            col.setAlpha(p.alpha)
            painter.setBrush(QBrush(col))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(
                QRectF(-p.size / 2, -p.size / 2, p.size, p.size * 0.7),
                2, 2
            )
            painter.restore()
        painter.end()
