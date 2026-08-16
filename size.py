from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QComboBox, QLineEdit, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator

class SizePageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RESIZE")
        self.resize(300, 350)
        
        self.standard_sizes = {
            "A6": (105, 148),
            "A5": (148, 210),
            "A4": (210, 297),
            "A3": (297, 420),
            "A2": (420, 594),
            "A1": (594, 841),
            "A0": (841, 1189),
            "Custom": (0, 0)
        }

        layout = QVBoxLayout(self)

        # Format selection
        layout.addWidget(QLabel("Select format:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(list(self.standard_sizes.keys()))
        self.size_combo.setCurrentText("A4")
        self.size_combo.currentIndexChanged.connect(self.on_size_changed)
        layout.addWidget(self.size_combo)

        # Input fields
        self.custom_w_input = QLineEdit()
        self.custom_w_input.setValidator(QDoubleValidator(1.0, 5000.0, 2))
        self.custom_w_input.setPlaceholderText("Width (mm)")
        
        self.custom_h_input = QLineEdit()
        self.custom_h_input.setValidator(QDoubleValidator(1.0, 5000.0, 2))
        self.custom_h_input.setPlaceholderText("Height (mm)")
        
        layout.addWidget(QLabel("Width (mm):"))
        layout.addWidget(self.custom_w_input)
        layout.addWidget(QLabel("Height (mm):"))
        layout.addWidget(self.custom_h_input)

        # Selection of application
        layout.addSpacing(10)
        self.radio_current = QRadioButton("Current page")
        self.radio_all = QRadioButton("All pages")
        self.radio_all.setChecked(True)
        
        self.group = QButtonGroup()
        self.group.addButton(self.radio_current)
        self.group.addButton(self.radio_all)
        
        layout.addWidget(self.radio_current)
        layout.addWidget(self.radio_all)

        # Button
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #e83e8c; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

        self.on_size_changed()

    def on_size_changed(self):
        val = self.size_combo.currentText()
        if val != "Custom":
            w, h = self.standard_sizes[val]
            self.custom_w_input.setText(str(w))
            self.custom_h_input.setText(str(h))
            self.custom_w_input.setEnabled(False)
            self.custom_h_input.setEnabled(False)
        else:
            self.custom_w_input.setEnabled(True)
            self.custom_h_input.setEnabled(True)

    def get_settings(self):
        return {
            'w_mm': float(self.custom_w_input.text().replace(',', '.')),
            'h_mm': float(self.custom_h_input.text().replace(',', '.')),
            'all': self.radio_all.isChecked()
        }