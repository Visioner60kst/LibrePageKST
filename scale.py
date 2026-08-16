from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDoubleSpinBox, QComboBox, QPushButton, QFormLayout
from PyQt6.QtCore import pyqtSignal

class ScalePageDialog(QDialog):
    # Сигнал для передачи параметров при немодальном или асинхронном вызове
    settings_applied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Changing the scale")
        self.resize(300, 250)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.spin_gen = QDoubleSpinBox()
        self.spin_gen.setRange(1, 500)
        self.spin_gen.setValue(100)
        self.spin_gen.setSuffix("%")
        
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(1, 500)
        self.spin_h.setValue(100)
        self.spin_h.setSuffix("%")
        
        self.spin_v = QDoubleSpinBox()
        self.spin_v.setRange(1, 500)
        self.spin_v.setValue(100)
        self.spin_v.setSuffix("%")
        
        form.addRow("Scale (general):", self.spin_gen)
        form.addRow("Horizontal scale:", self.spin_h)
        form.addRow("Vertical scale:", self.spin_v)
        
        layout.addLayout(form)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["All Pages", "Current Page", "Even Pages", "Odd Pages"])
        layout.addWidget(QLabel("Apply to:"))
        layout.addWidget(self.combo_mode)
        
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold;")
        self.btn_apply.clicked.connect(self._on_apply)
        layout.addWidget(self.btn_apply)

    def _on_apply(self):
        """Отправляет сигнал с настройками и закрывает диалог со статусом Accepted."""
        settings = self.get_settings()
        self.settings_applied.emit(settings)
        self.accept()
        
    def get_settings(self):
        return {
            "general": self.spin_gen.value(),
            "horiz": self.spin_h.value(),
            "vert": self.spin_v.value(),
            "mode": self.combo_mode.currentText()
        }

    # Методы совместимости для разных вариантов вызова из main.py
    def get_scale_settings(self):
        return self.get_settings()

    def get_values(self):
        return self.get_settings()