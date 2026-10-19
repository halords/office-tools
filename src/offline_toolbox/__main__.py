"""Application entry point and runtime bootstrap."""

import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from offline_toolbox.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Offline Toolbox")
    app.setOrganizationName("OfflineToolbox")

    # Set Windows App ID for proper taskbar grouping
    if sys.platform == "win32":
        try:
            import ctypes
            app_id = "offlinetoolbox.desktop.suite.v01"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
