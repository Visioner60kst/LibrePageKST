import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt

class CurvesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Text to curves")
        self.resize(350, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Range selection
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Apply to:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems([
            "All pages",
            "Current page",
            "Even pages",
            "Odd pages",
            "Specified pages"
        ])
        self.range_combo.currentTextChanged.connect(self.on_range_changed)
        range_layout.addWidget(self.range_combo)
        layout.addLayout(range_layout)

        # Field for entering specific pages (enabled when selecting "Specified pages"")
        self.custom_pages_input = QLineEdit()
        self.custom_pages_input.setPlaceholderText("For example: 1, 3, 5-7")
        self.custom_pages_input.setEnabled(False)
        layout.addWidget(self.custom_pages_input)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_base_dir(self):
        """Defines the base directory for the program to run"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_gs_path(self):
        """Identifies the correct executable file Ghostscript depending on OS"""
        base_dir = self.get_base_dir()
        bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
        
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            local_gs = os.path.join(bin_dir, "gs")
            if os.path.exists(local_gs):
                return local_gs
            # If there is no local binary, use the system one
            return "gs" 
        else:
            # For Windows
            return os.path.join(bin_dir, "gswin64c.exe")

    def on_range_changed(self, text):
        # We activate the input field only if “Specified pages” are selected"
        self.custom_pages_input.setEnabled(text == "Specified pages")

    def get_settings(self):
        """Returns settings after closing the dialog"""
        return {
            'range': self.range_combo.currentText(),
            'custom_pages': self.custom_pages_input.text(),
            'gs_path': self.get_gs_path()  # Added path to Ghostscript
        }