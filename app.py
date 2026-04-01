from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("PyQt6 kurulu degil. Once `python -m pip install -r requirements.txt` komutunu calistirin.")
        return 1

    from smart_league.professional_ui import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
