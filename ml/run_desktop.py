"""
Misinfo Shield - Always-On-Top Desktop App
============================================
Runs the Misinfo Shield panel as a native, borderless, always-on-top 
desktop window using PyQt6.

Usage:
    cd hack
    python run_desktop.py
"""

import sys
import subprocess
import time
import socket
from PyQt6.QtCore import Qt, QUrl, QPoint
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class FramelessWindow(QMainWindow):
    def __init__(self, api_process=None):
        super().__init__()
        self.api_process = api_process
        
        # Make the window frameless and always on top
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set dimensions matching the web panel CSS
        self.resize(430, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet(
            "#CentralWidget { background-color: #ffffff; border: 1px solid #d1d5da; border-radius: 8px; }"
        )
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Custom Title Bar (for dragging and closing)
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: #f6f8fa; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #d1d5da;")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(10, 0, 10, 0)
        
        lbl_title = QLabel("Misinfo Shield")
        lbl_title.setStyleSheet("color: #24292e; font-family: sans-serif; font-size: 12px; font-weight: 600;")
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("QPushButton { color: #586069; background: transparent; border: none; font-weight: bold; } QPushButton:hover { color: #d73a49; }")
        btn_close.clicked.connect(self.close)
        
        tb_layout.addWidget(lbl_title)
        tb_layout.addStretch()
        tb_layout.addWidget(btn_close)
        
        layout.addWidget(title_bar)
        
        # Web Engine View
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("http://localhost:8899"))
        layout.addWidget(self.browser)
        
        # Dragging variables
        self._is_dragging = False
        self._drag_pos = QPoint()
        
        # Make title bar grab mouse events for dragging
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move
        title_bar.mouseReleaseEvent = self._title_mouse_release

    def _title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_mouse_move(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _title_mouse_release(self, event):
        self._is_dragging = False
        event.accept()

    def closeEvent(self, event):
        """Ensure the API process is killed when the window closes."""
        if self.api_process:
            print("Shutting down API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
        super().closeEvent(event)


if __name__ == "__main__":
    api_proc = None
    
    # Check if port 8899 is already in use (maybe user ran api_server.py manually)
    if not is_port_in_use(8899):
        print("Starting local API server in background process...")
        # Start the FastAPI server as a completely separate background process
        # This prevents asyncio event loop conflicts with PyQt6
        api_proc = subprocess.Popen(
            [sys.executable, "api_server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a moment for uvicorn to bind the port
        retries = 20
        while retries > 0 and not is_port_in_use(8899):
            time.sleep(0.5)
            retries -= 1
    else:
        print("Port 8899 already in use. Assuming API server is already running.")
    
    # Start the PyQt Desktop App
    app = QApplication(sys.argv)
    window = FramelessWindow(api_process=api_proc)
    window.show()
    
    print("\n  ============================================================")
    print("  MISINFO SHIELD DESKTOP IS RUNNING")
    print("  Drag it by the top bar. It will always stay on top.")
    print("  Close the window to shut down the app and API.")
    print("  ============================================================\n")
    
    sys.exit(app.exec())
