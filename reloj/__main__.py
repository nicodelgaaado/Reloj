"""Entry point for the chronograph application."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .gui import ChronographWindow


def main() -> int:
    """Launch the PySide6 event loop and show the chronograph window."""
    app = QApplication(sys.argv)
    window = ChronographWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
