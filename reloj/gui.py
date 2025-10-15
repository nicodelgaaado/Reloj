"""PySide6 front end for the chronograph clock."""

from __future__ import annotations

import math
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
    QRadialGradient,
)
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
        self.setAutoFillBackground(False)

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
        radius = size * 0.45

        painter.translate(center_x, center_y)

        self._draw_face(painter, radius)
        self._draw_hands(painter, radius * 0.9, self._snapshot)
        self._draw_center_cap(painter)

    def _draw_background(self, painter: QPainter) -> None:
        painter.save()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#0f172a"))
        gradient.setColorAt(0.45, QColor("#111b2c"))
        gradient.setColorAt(1.0, QColor("#1f2937"))
        painter.fillRect(self.rect(), gradient)

        vignette = QRadialGradient(QPointF(self.width() / 2.0, self.height() / 2.0), max(self.width(), self.height()) * 0.65)
        vignette.setColorAt(0.0, QColor(255, 255, 255, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 90))
        painter.fillRect(self.rect(), vignette)
        painter.restore()

    def _draw_face(self, painter: QPainter, radius: float) -> None:
        painter.save()
        case_gradient = QRadialGradient(QPointF(0, 0), radius * 1.05)
        case_gradient.setColorAt(0.0, QColor("#1f2937"))
        case_gradient.setColorAt(0.55, QColor("#101828"))
        case_gradient.setColorAt(1.0, QColor("#0b1120"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(case_gradient)
        painter.drawEllipse(QRectF(-radius, -radius, radius * 2, radius * 2))

        dial_radius = radius * 0.9
        dial_rect = QRectF(-dial_radius, -dial_radius, dial_radius * 2, dial_radius * 2)
        dial_gradient = QRadialGradient(QPointF(0, 0), dial_radius)
        dial_gradient.setColorAt(0.0, QColor("#f8fafc"))
        dial_gradient.setColorAt(0.65, QColor("#e2e8f0"))
        dial_gradient.setColorAt(1.0, QColor("#cbd5f5"))
        painter.setBrush(dial_gradient)
        painter.drawEllipse(dial_rect)

        highlight_pen = QPen(QColor("#38bdf8"))
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
            color = QColor("#38bdf8") if index % 3 == 0 else QColor("#1f2937")
            painter.setBrush(color)
            rect = QRectF(-marker_width / 2.0, -(radius * 0.78), marker_width, marker_length)
            painter.drawRoundedRect(rect, marker_width * 0.4, marker_width * 0.4)
            painter.restore()

        painter.setBrush(QColor("#94a3b8"))
        dot_radius = radius * 0.01
        for index in range(60):
            if index % 5 != 0:
                point = self._point_on_circle(radius * 0.78, index * 6.0)
                painter.drawEllipse(
                    QRectF(point.x() - dot_radius, point.y() - dot_radius, dot_radius * 2, dot_radius * 2)
                )

        inner_ring_pen = QPen(QColor("#d1d9e6"))
        inner_ring_pen.setWidthF(radius * 0.006)
        painter.setPen(inner_ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(-radius * 0.46, -radius * 0.46, radius * 0.92, radius * 0.92))

        painter.setPen(QPen(QColor("#0f172a")))
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
        painter.setBrush(QColor("#1f2937"))
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
        painter.setBrush(QColor("#0f172a"))
        painter.drawPath(minute_path)
        painter.restore()

        painter.save()
        painter.rotate(snapshot.seconds_angle)
        painter.setBrush(QColor("#38bdf8"))
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
        painter.setBrush(QColor("#0ea5e9"))
        painter.drawEllipse(QRectF(-counter_weight_radius, max_radius * 0.08, counter_weight_radius * 2, counter_weight_radius))
        painter.restore()

        painter.restore()

    def _draw_center_cap(self, painter: QPainter) -> None:
        painter.save()
        base_radius = min(self.width(), self.height()) * 0.032
        painter.setPen(QPen(QColor("#38bdf8"), base_radius * 0.18))
        painter.setBrush(QColor("#0f172a"))
        painter.drawEllipse(QRectF(-base_radius, -base_radius, base_radius * 2, base_radius * 2))

        cap_radius = base_radius * 0.55
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#38bdf8"))
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
