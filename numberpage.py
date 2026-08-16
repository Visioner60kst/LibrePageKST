import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QFontComboBox, QColorDialog, QFormLayout, QGroupBox)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

class NumberPageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Numbering settings")
        self.resize(350, 350)
        self.selected_color = QColor(0, 0, 0)  # Default color is black
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        group_box = QGroupBox("Numbering options")
        form_layout = QFormLayout(group_box)

        # 1. Selecting font and size
        self.font_combo = QFontComboBox()
        form_layout.addRow("Font:", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 200)
        self.size_spin.setValue(12)
        form_layout.addRow("Font size:", self.size_spin)

        # 2. Select location: Top or Bottom
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Above", "Bottom"])
        form_layout.addRow("Mood:", self.pos_combo)

        # 3. Indentations (in millimeters)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000, 1000)
        self.x_spin.setValue(10.0)
        self.x_spin.setSuffix(" mm")
        form_layout.addRow("Left indent:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000, 1000)
        self.y_spin.setValue(10.0)
        self.y_spin.setSuffix(" mm")
        form_layout.addRow("Vertical offset:", self.y_spin)

        # 4. Color selection
        self.btn_color = QPushButton("Select color")
        self.btn_color.setStyleSheet("background-color: #000000; color: white; font-weight: bold;")
        self.btn_color.clicked.connect(self.choose_color)
        form_layout.addRow("Color:", self.btn_color)

        # 5. Tilt angle
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(0, 360)
        self.angle_spin.setValue(0)
        self.angle_spin.setSuffix(" °")
        form_layout.addRow("Tilt angle:", self.angle_spin)

        layout.addWidget(group_box)

        # Application buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        self.btn_apply.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("padding: 6px;")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)

    def choose_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select numbering color")
        if color.isValid():
            self.selected_color = color
            # Dynamically change the color of the text on the button so that it is readable on any background
            text_color = "black" if color.lightness() > 128 else "white"
            self.btn_color.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; font-weight: bold;")

    def get_settings(self):
        return {
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.size_spin.value(),
            'position': self.pos_combo.currentText(),
            'offset_x': self.x_spin.value(),
            'offset_y': self.y_spin.value(),
            'color': self.selected_color,
            'angle': self.angle_spin.value()
        }