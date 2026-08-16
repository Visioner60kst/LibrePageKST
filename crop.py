from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QDoubleSpinBox, QComboBox, QGroupBox)
from PyQt6.QtCore import pyqtSignal

class CropPageDialog(QDialog):
    # Сигнал для передачи параметров в вызывающий модуль
    settings_applied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Framing (Trimming)")
        self.resize(300, 250)
        
        layout = QVBoxLayout(self)
        
        # Indent settings group
        margins_group = QGroupBox("Enter trim values ​​in mm")
        margins_layout = QVBoxLayout(margins_group)
        
        # Top
        h_top = QHBoxLayout()
        h_top.addWidget(QLabel("Above:"))
        self.spin_top = QDoubleSpinBox()
        self.spin_top.setRange(0, 1000)
        self.spin_top.setSuffix(" mm")
        h_top.addWidget(self.spin_top)
        margins_layout.addLayout(h_top)
        
        # Through
        h_bottom = QHBoxLayout()
        h_bottom.addWidget(QLabel("From below:"))
        self.spin_bottom = QDoubleSpinBox()
        self.spin_bottom.setRange(0, 1000)
        self.spin_bottom.setSuffix(" mm")
        h_bottom.addWidget(self.spin_bottom)
        margins_layout.addLayout(h_bottom)
        
        # Left
        h_left = QHBoxLayout()
        h_left.addWidget(QLabel("Left:"))
        self.spin_left = QDoubleSpinBox()
        self.spin_left.setRange(0, 1000)
        self.spin_left.setSuffix(" mm")
        h_left.addWidget(self.spin_left)
        margins_layout.addLayout(h_left)
        
        # Right
        h_right = QHBoxLayout()
        h_right.addWidget(QLabel("Right:"))
        self.spin_right = QDoubleSpinBox()
        self.spin_right.setRange(0, 1000)
        self.spin_right.setSuffix(" mm")
        h_right.addWidget(self.spin_right)
        margins_layout.addLayout(h_right)
        
        layout.addWidget(margins_group)
        
        # Selecting pages
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["All Pages", "Even Pages", "Odd Pages", "Current Page"])
        layout.addWidget(QLabel("Apply to:"))
        layout.addWidget(self.combo_mode)
        
        # Apply button
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold;")
        self.btn_apply.clicked.connect(self._on_apply)
        layout.addWidget(self.btn_apply)

    def _on_apply(self):
        """Передает данные через сигнал и закрывает диалог со статусом Accepted."""
        settings = self.get_settings()
        self.settings_applied.emit(settings)
        self.accept()

    def get_settings(self):
        return {
            'top': self.spin_top.value(),
            'bottom': self.spin_bottom.value(),
            'left': self.spin_left.value(),
            'right': self.spin_right.value(),
            'mode': self.combo_mode.currentText()
        }

    # Методы совместимости на случай, если в основном окне вызывается другое имя
    def get_crop_settings(self):
        return self.get_settings()

    def get_values(self):
        return self.get_settings()