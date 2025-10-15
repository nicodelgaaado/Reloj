"""PySide6 front end for the chronograph clock."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QMainWindow, QWidget

from .engine import ChronographEngine, ChronographSnapshot


class AnalogChronographWidget(QWidget):
    """Widget that renders an analog chronograph face."""

    def __init__(
        self,
        engine: Optional[ChronographEngine] = None,
        refresh_interval_ms: int = 16,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine or ChronographEngine()
        self._snapshot = self._engine.snapshot()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(refresh_interval_ms)
        self.setMinimumSize(360, 360)
        self.setAutoFillBackground(True)

    def _on_tick(self) -> None:
        self._snapshot = self._engine.snapshot()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        size = min(self.width(), self.height())
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        radius = size * 0.45

        painter.translate(center_x, center_y)

        self._draw_face(painter, radius)
        self._draw_hands(painter, radius * 0.9, self._snapshot)
        self._draw_center_cap(painter)

    def _draw_face(self, painter: QPainter, radius: float) -> None:
        painter.save()
        base_pen = QPen(QColor("#1f2933"))
        base_pen.setWidthF(radius * 0.02)
        painter.setPen(base_pen)
        painter.setBrush(QColor("#e5e9f0"))
        painter.drawEllipse(QRectF(-radius, -radius, radius * 2, radius * 2))

        # Chapter ring
        ring_pen = QPen(QColor("#111827"))
        ring_pen.setWidthF(radius * 0.04)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(-radius * 0.9, -radius * 0.9, radius * 1.8, radius * 1.8))

        # Tick marks for seconds and hours.
        painter.setPen(QPen(QColor("#111827"), radius * 0.01))
        for index in range(60):
            angle = index * 6.0
            outer = self._point_on_circle(radius * 0.92, angle)
            inner_length = radius * (0.74 if index % 5 == 0 else 0.82)
            inner = self._point_on_circle(inner_length, angle)
            pen_width = radius * (0.03 if index % 5 == 0 else 0.012)
            tick_pen = QPen(QColor("#111827"), pen_width)
            painter.setPen(tick_pen)
            painter.drawLine(inner, outer)

        painter.restore()

    def _draw_hands(self, painter: QPainter, max_radius: float, snapshot: ChronographSnapshot) -> None:
        painter.save()

        hour_pen = QPen(QColor("#111827"))
        hour_pen.setWidthF(max_radius * 0.08)
        painter.setPen(hour_pen)
        painter.drawLine(
            self._point_on_circle(max_radius * 0.05, snapshot.hours_angle + 180.0),
            self._point_on_circle(max_radius * 0.6, snapshot.hours_angle),
        )

        minute_pen = QPen(QColor("#111827"))
        minute_pen.setWidthF(max_radius * 0.05)
        painter.setPen(minute_pen)
        painter.drawLine(
            self._point_on_circle(max_radius * 0.07, snapshot.minutes_angle + 180.0),
            self._point_on_circle(max_radius * 0.8, snapshot.minutes_angle),
        )

        second_pen = QPen(QColor("#d90429"))
        second_pen.setWidthF(max_radius * 0.02)
        painter.setPen(second_pen)
        painter.drawLine(
            self._point_on_circle(max_radius * 0.1, snapshot.seconds_angle + 180.0),
            self._point_on_circle(max_radius * 0.88, snapshot.seconds_angle),
        )

        painter.restore()

    def _draw_center_cap(self, painter: QPainter) -> None:
        painter.save()
        cap_radius = min(self.width(), self.height()) * 0.02
        painter.setBrush(QColor("#d90429"))
        painter.setPen(QPen(QColor("#111827")))
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
        self.setCentralWidget(AnalogChronographWidget())
        self.resize(600, 600)
