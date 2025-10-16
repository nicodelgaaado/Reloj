"""PySide6 front end for the chronograph clock."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .engine import ChronographEngine, ChronographSnapshot


@dataclass(frozen=True)
class WatchSkin:
    """Palette that describes how the chronograph should be rendered."""

    name: str
    background_gradient: tuple[str, str, str]
    case_gradient: tuple[str, str, str]
    dial_gradient: tuple[str, str, str]
    highlight_color: str
    accent_text_color: str
    major_marker_color: str
    minor_marker_color: str
    minute_dot_color: str
    inner_ring_color: str
    numeral_color: str
    hour_hand_color: str
    minute_hand_color: str
    second_hand_color: str
    second_counter_weight_color: str
    center_cap_border_color: str
    center_cap_base_color: str
    center_cap_fill_color: str
    time_background_rgba: str
    time_text_color: str
    ui_accent_color: str
    ui_accent_text_color: str
    frame_image_path: Optional[str] = None


ASSET_ROOT = Path(__file__).resolve().parent / "assets"
FRAME_ASSET_ROOT = ASSET_ROOT / "frames"


MODE_BUTTON_IDLE_BACKGROUND = "rgba(15, 23, 42, 160)"
FRAME_DIAMETER_RATIO = 0.85
DIAL_RADIUS_RATIO = 0.33

WATCH_SKIN_PRESETS = [
    WatchSkin(
        name="Audemars Piguet",
        background_gradient=("#0f172a", "#111b2c", "#1f2937"),
        case_gradient=("#1f2937", "#101828", "#0b1120"),
        dial_gradient=("#f8fafc", "#e2e8f0", "#cbd5f5"),
        highlight_color="#38bdf8",
        accent_text_color="#0f172a",
        major_marker_color="#38bdf8",
        minor_marker_color="#1f2937",
        minute_dot_color="#94a3b8",
        inner_ring_color="#d1d9e6",
        numeral_color="#0f172a",
        hour_hand_color="#1f2937",
        minute_hand_color="#0f172a",
        second_hand_color="#38bdf8",
        second_counter_weight_color="#0ea5e9",
        center_cap_border_color="#38bdf8",
        center_cap_base_color="#0f172a",
        center_cap_fill_color="#38bdf8",
        time_background_rgba="rgba(15, 23, 42, 140)",
        time_text_color="#e2e8f0",
        ui_accent_color="#38bdf8",
        ui_accent_text_color="#0f172a",
        frame_image_path="audemars_piguet.png",
    ),
]

WATCH_SKINS = {skin.name: skin for skin in WATCH_SKIN_PRESETS}
DEFAULT_WATCH_SKIN = WATCH_SKIN_PRESETS[0]


class AnalogChronographWidget(QWidget):
    """Widget that renders an analog chronograph face."""

    def __init__(
        self,
        engine: Optional[ChronographEngine] = None,
        skin: Optional[WatchSkin] = None,
        refresh_interval_ms: int = 16,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine or ChronographEngine()
        self._skin = skin or DEFAULT_WATCH_SKIN
        self._snapshot = self._engine.snapshot()
        self._frame_pixmap: Optional[QPixmap] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(refresh_interval_ms)
        self.setMinimumSize(360, 360)
        self.setAutoFillBackground(False)
        self._load_frame_pixmap(self._skin)

    def _on_tick(self) -> None:
        self._snapshot = self._engine.snapshot()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._draw_background(painter)

        size = min(self.width(), self.height())
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        radius = size * DIAL_RADIUS_RATIO

        painter.translate(center_x, center_y)

        self._draw_frame(painter, size)
        self._draw_face(painter, radius)
        self._draw_hands(painter, radius * 0.9, self._snapshot)
        self._draw_center_cap(painter)

    def set_skin(self, skin: WatchSkin) -> None:
        """Update the rendering palette for the analog widget."""
        if self._skin == skin:
            return
        self._skin = skin
        self._load_frame_pixmap(skin)
        self.update()

    def _load_frame_pixmap(self, skin: WatchSkin) -> None:
        """Refresh cached frame artwork for the current skin."""
        frame_path = skin.frame_image_path
        if not frame_path:
            self._frame_pixmap = None
            return
        candidate = FRAME_ASSET_ROOT / frame_path
        if not candidate.exists():
            self._frame_pixmap = None
            return
        pixmap = QPixmap(str(candidate))
        self._frame_pixmap = pixmap if not pixmap.isNull() else None

    def _draw_background(self, painter: QPainter) -> None:
        painter.save()
        gradient = QLinearGradient(0, 0, 0, self.height())
        top, mid, bottom = self._skin.background_gradient
        gradient.setColorAt(0.0, QColor(top))
        gradient.setColorAt(0.45, QColor(mid))
        gradient.setColorAt(1.0, QColor(bottom))
        painter.fillRect(self.rect(), gradient)

        vignette = QRadialGradient(QPointF(self.width() / 2.0, self.height() / 2.0), max(self.width(), self.height()) * 0.65)
        vignette.setColorAt(0.0, QColor(255, 255, 255, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 90))
        painter.fillRect(self.rect(), vignette)
        painter.restore()

    def _draw_frame(self, painter: QPainter, size: float) -> None:
        if not self._frame_pixmap or self._frame_pixmap.isNull():
            return
        painter.save()
        frame_diameter = int(size * FRAME_DIAMETER_RATIO)
        if frame_diameter <= 0:
            painter.restore()
            return
        scaled = self._frame_pixmap.scaled(
            frame_diameter,
            frame_diameter,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(
            int(-scaled.width() / 2),
            int(-scaled.height() / 2),
            scaled,
        )
        painter.restore()

    def _draw_face(self, painter: QPainter, radius: float) -> None:
        painter.save()
        case_gradient = QRadialGradient(QPointF(0, 0), radius * 1.05)
        outer, mid, inner = self._skin.case_gradient
        case_gradient.setColorAt(0.0, QColor(outer))
        case_gradient.setColorAt(0.55, QColor(mid))
        case_gradient.setColorAt(1.0, QColor(inner))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(case_gradient)
        painter.drawEllipse(QRectF(-radius, -radius, radius * 2, radius * 2))

        dial_radius = radius * 0.9
        dial_rect = QRectF(-dial_radius, -dial_radius, dial_radius * 2, dial_radius * 2)
        dial_gradient = QRadialGradient(QPointF(0, 0), dial_radius)
        center, mid_tone, edge = self._skin.dial_gradient
        dial_gradient.setColorAt(0.0, QColor(center))
        dial_gradient.setColorAt(0.65, QColor(mid_tone))
        dial_gradient.setColorAt(1.0, QColor(edge))
        painter.setBrush(dial_gradient)
        painter.drawEllipse(dial_rect)

        highlight_pen = QPen(QColor(self._skin.highlight_color))
        highlight_pen.setWidthF(radius * 0.012)
        highlight_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(highlight_pen)
        painter.drawEllipse(QRectF(-radius * 0.78, -radius * 0.78, radius * 1.56, radius * 1.56))

        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(12):
            painter.save()
            painter.rotate(index * 30.0)
            marker_length = radius * (0.16 if index % 3 == 0 else 0.1)
            marker_width = radius * (0.035 if index % 3 == 0 else 0.018)
            color = QColor(self._skin.major_marker_color if index % 3 == 0 else self._skin.minor_marker_color)
            painter.setBrush(color)
            rect = QRectF(-marker_width / 2.0, -(radius * 0.78), marker_width, marker_length)
            painter.drawRoundedRect(rect, marker_width * 0.4, marker_width * 0.4)
            painter.restore()

        painter.setBrush(QColor(self._skin.minute_dot_color))
        dot_radius = radius * 0.01
        for index in range(60):
            if index % 5 != 0:
                point = self._point_on_circle(radius * 0.78, index * 6.0)
                painter.drawEllipse(
                    QRectF(point.x() - dot_radius, point.y() - dot_radius, dot_radius * 2, dot_radius * 2)
                )

        inner_ring_pen = QPen(QColor(self._skin.inner_ring_color))
        inner_ring_pen.setWidthF(radius * 0.006)
        painter.setPen(inner_ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(-radius * 0.46, -radius * 0.46, radius * 0.92, radius * 0.92))

        painter.setPen(QPen(QColor(self._skin.numeral_color)))
        font = painter.font()
        font.setFamily("Segoe UI")
        font.setPointSizeF(radius * 0.16)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        numeral_box = radius * 0.17
        for hour in range(1, 13):
            angle = hour * 30.0
            position = self._point_on_circle(radius * 0.54, angle)
            rect = QRectF(
                position.x() - numeral_box,
                position.y() - numeral_box,
                numeral_box * 2,
                numeral_box * 2,
            )
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(hour))

        painter.restore()

    def _draw_hands(self, painter: QPainter, max_radius: float, snapshot: ChronographSnapshot) -> None:
        painter.save()

        painter.setPen(Qt.PenStyle.NoPen)

        painter.save()
        painter.rotate(snapshot.hours_angle)
        hour_path = QPainterPath()
        hour_path.moveTo(-max_radius * 0.045, max_radius * 0.08)
        hour_path.lineTo(max_radius * 0.045, max_radius * 0.08)
        hour_path.lineTo(max_radius * 0.022, -max_radius * 0.4)
        hour_path.quadTo(0.0, -max_radius * 0.52, -max_radius * 0.022, -max_radius * 0.4)
        hour_path.closeSubpath()
        painter.setBrush(QColor(self._skin.hour_hand_color))
        painter.drawPath(hour_path)
        painter.restore()

        painter.save()
        painter.rotate(snapshot.minutes_angle)
        minute_path = QPainterPath()
        minute_path.moveTo(-max_radius * 0.032, max_radius * 0.1)
        minute_path.lineTo(max_radius * 0.032, max_radius * 0.1)
        minute_path.lineTo(max_radius * 0.016, -max_radius * 0.64)
        minute_path.quadTo(0.0, -max_radius * 0.75, -max_radius * 0.016, -max_radius * 0.64)
        minute_path.closeSubpath()
        painter.setBrush(QColor(self._skin.minute_hand_color))
        painter.drawPath(minute_path)
        painter.restore()

        painter.save()
        painter.rotate(snapshot.seconds_angle)
        painter.setBrush(QColor(self._skin.second_hand_color))
        second_path = QPainterPath()
        second_path.moveTo(-max_radius * 0.012, max_radius * 0.14)
        second_path.lineTo(max_radius * 0.012, max_radius * 0.14)
        second_path.lineTo(max_radius * 0.007, -max_radius * 0.82)
        second_path.lineTo(-max_radius * 0.007, -max_radius * 0.82)
        second_path.closeSubpath()
        painter.drawPath(second_path)

        pointer_radius = max_radius * 0.03
        painter.drawEllipse(QRectF(-pointer_radius, -max_radius * 0.82 - pointer_radius, pointer_radius * 2, pointer_radius * 2))

        counter_weight_radius = max_radius * 0.05
        painter.setBrush(QColor(self._skin.second_counter_weight_color))
        painter.drawEllipse(QRectF(-counter_weight_radius, max_radius * 0.08, counter_weight_radius * 2, counter_weight_radius))
        painter.restore()

        painter.restore()

    def _draw_center_cap(self, painter: QPainter) -> None:
        painter.save()
        base_radius = min(self.width(), self.height()) * 0.032
        painter.setPen(QPen(QColor(self._skin.center_cap_border_color), base_radius * 0.18))
        painter.setBrush(QColor(self._skin.center_cap_base_color))
        painter.drawEllipse(QRectF(-base_radius, -base_radius, base_radius * 2, base_radius * 2))

        cap_radius = base_radius * 0.55
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._skin.center_cap_fill_color))
        painter.drawEllipse(QRectF(-cap_radius, -cap_radius, cap_radius * 2, cap_radius * 2))
        painter.restore()

    @staticmethod
    def _point_on_circle(radius: float, angle_degrees: float) -> QPointF:
        radians = math.radians(angle_degrees - 90.0)
        x = radius * math.cos(radians)
        y = radius * math.sin(radians)
        return QPointF(x, y)


class ChronographWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chronograph Clock")
        self._engine = ChronographEngine()
        self._available_skins = list(WATCH_SKINS.values())
        self._active_skin = DEFAULT_WATCH_SKIN
        self._analog_widget = AnalogChronographWidget(engine=self._engine, skin=self._active_skin)
        self._analog_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self._mode_clock_button = QPushButton("Clock")
        self._mode_clock_button.setCheckable(True)
        self._mode_stopwatch_button = QPushButton("Stopwatch")
        self._mode_stopwatch_button.setCheckable(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self._mode_clock_button, 0)
        self._mode_group.addButton(self._mode_stopwatch_button, 1)
        self._mode_clock_button.setChecked(True)
        self._mode_group.idClicked.connect(self._on_mode_selected)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)
        mode_layout.addStretch(1)
        mode_layout.addWidget(self._mode_clock_button)
        mode_layout.addWidget(self._mode_stopwatch_button)
        mode_layout.addStretch(1)
        layout.addLayout(mode_layout)

        self._skin_label = QLabel("Watch Skin")
        self._skin_selector = QComboBox()
        for skin in self._available_skins:
            self._skin_selector.addItem(skin.name)
        self._skin_selector.setCurrentText(self._active_skin.name)
        self._skin_selector.currentTextChanged.connect(self._on_skin_selected)

        skin_layout = QHBoxLayout()
        skin_layout.setSpacing(8)
        skin_layout.addStretch(1)
        skin_layout.addWidget(self._skin_label)
        skin_layout.addWidget(self._skin_selector)
        skin_layout.addStretch(1)
        layout.addLayout(skin_layout)

        self._time_display = QLabel("00:00:00")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = self._time_display.font()
        time_font.setPointSize(22)
        time_font.setFamily("Segoe UI")
        time_font.setWeight(QFont.Weight.Medium)
        self._time_display.setFont(time_font)
        layout.addWidget(self._time_display)

        layout.addWidget(self._analog_widget, stretch=1)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.addStretch(1)

        self._start_button = QPushButton("Start")
        self._stop_button = QPushButton("Stop")
        self._reset_button = QPushButton("Reset")

        self._start_button.clicked.connect(self._handle_start)
        self._stop_button.clicked.connect(self._handle_stop)
        self._reset_button.clicked.connect(self._handle_reset)

        for button in (self._start_button, self._stop_button, self._reset_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumWidth(100)

        controls_layout.addWidget(self._start_button)
        controls_layout.addWidget(self._stop_button)
        controls_layout.addWidget(self._reset_button)
        controls_layout.addStretch(1)
        layout.addLayout(controls_layout)

        self._apply_skin_to_ui()

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(60)
        self._ui_timer.timeout.connect(self._update_time_display)
        self._ui_timer.start()

        self.setCentralWidget(central)
        self.resize(720, 840)

        self._engine.set_mode(ChronographEngine.MODE_CLOCK)
        self._sync_control_state()
        self._update_time_display()

    def _on_mode_selected(self, button_id: int) -> None:
        if button_id == 0:
            self._engine.set_mode(ChronographEngine.MODE_CLOCK)
        else:
            self._engine.set_mode(ChronographEngine.MODE_STOPWATCH)
        self._analog_widget.update()
        self._sync_control_state()
        self._update_time_display()

    def _on_skin_selected(self, skin_name: str) -> None:
        skin = WATCH_SKINS.get(skin_name)
        if skin is None or skin == self._active_skin:
            return
        self._active_skin = skin
        self._analog_widget.set_skin(skin)
        self._apply_skin_to_ui()

    def _handle_start(self) -> None:
        self._engine.start_stopwatch()
        self._sync_control_state()

    def _handle_stop(self) -> None:
        self._engine.stop_stopwatch()
        self._sync_control_state()

    def _handle_reset(self) -> None:
        self._engine.reset_stopwatch()
        self._sync_control_state()
        self._update_time_display()
        self._analog_widget.update()

    def _apply_skin_to_ui(self) -> None:
        skin = self._active_skin
        mode_style = (
            f"QPushButton {{background-color: {MODE_BUTTON_IDLE_BACKGROUND}; color: {skin.time_text_color}; padding: 8px 18px; "
            f"border-radius: 14px; font-weight: 600;}}\n"
            f"QPushButton:checked {{background-color: {skin.highlight_color}; color: {skin.accent_text_color};}}"
        )
        self._mode_clock_button.setStyleSheet(mode_style)
        self._mode_stopwatch_button.setStyleSheet(mode_style)

        self._time_display.setStyleSheet(
            f"color: {skin.time_text_color}; background-color: {skin.time_background_rgba}; padding: 12px; border-radius: 16px;"
        )

        disabled_suffix = (
            "\nQPushButton:disabled {background-color: rgba(100, 116, 139, 120); color: rgba(226, 232, 240, 160);}"
        )
        self._start_button.setStyleSheet(
            f"QPushButton {{background-color: {skin.ui_accent_color}; color: {skin.ui_accent_text_color}; padding: 10px 16px; "
            f"border-radius: 12px; font-weight: 600;}}"
            f"{disabled_suffix}"
        )
        self._stop_button.setStyleSheet(
            "QPushButton {background-color: #dc2626; color: #fef2f2; padding: 10px 16px; border-radius: 12px; font-weight: 600;}"
            f"{disabled_suffix}"
        )
        self._reset_button.setStyleSheet(
            "QPushButton {background-color: #facc15; color: #0f172a; padding: 10px 16px; border-radius: 12px; font-weight: 600;}"
            f"{disabled_suffix}"
        )

        self._skin_label.setStyleSheet(f"color: {skin.time_text_color}; font-weight: 600;")
        combo_style = (
            f"QComboBox {{color: {skin.time_text_color}; background-color: rgba(15, 23, 42, 120); padding: 6px 12px; "
            f"border-radius: 12px; border: 2px solid {skin.highlight_color}; selection-background-color: {skin.highlight_color}; "
            f"selection-color: {skin.accent_text_color};}}\n"
            f"QComboBox QAbstractItemView {{background-color: rgba(15, 23, 42, 230); color: {skin.time_text_color}; "
            f"selection-background-color: {skin.highlight_color}; selection-color: {skin.accent_text_color}; border-radius: 8px;}}"
        )
        self._skin_selector.setStyleSheet(combo_style)

    def _sync_control_state(self) -> None:
        if self._engine.mode == ChronographEngine.MODE_CLOCK:
            self._start_button.setEnabled(False)
            self._stop_button.setEnabled(False)
            self._reset_button.setEnabled(False)
            self._start_button.setText("Start")
        else:
            running = self._engine.is_stopwatch_running()
            elapsed = self._engine.stopwatch_elapsed().total_seconds()
            self._start_button.setEnabled(not running)
            self._stop_button.setEnabled(running)
            self._reset_button.setEnabled(elapsed > 0.0)
            self._start_button.setText("Resume" if elapsed > 0.0 else "Start")

    def _update_time_display(self) -> None:
        if self._engine.mode == ChronographEngine.MODE_CLOCK:
            now = self._engine.current_time()
            self._time_display.setText(now.strftime("%H:%M:%S"))
        else:
            elapsed = self._engine.stopwatch_elapsed()
            total_seconds_float = elapsed.total_seconds()
            total_seconds = int(total_seconds_float)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            centiseconds = int((total_seconds_float - total_seconds) * 100)
            centiseconds = min(centiseconds, 99)
            self._time_display.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}")
