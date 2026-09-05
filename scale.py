from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDoubleSpinBox, QComboBox, QPushButton, QFormLayout

class ScalePageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Изменение масштаба")
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
        
        form.addRow("Масштаб (общий):", self.spin_gen)
        form.addRow("Масштаб по горизонтали:", self.spin_h)
        form.addRow("Масштаб по вертикали:", self.spin_v)
        
        layout.addLayout(form)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Все страницы", "Текущая страница", "Четные страницы", "Нечетные страницы"])
        layout.addWidget(QLabel("Применить к:"))
        layout.addWidget(self.combo_mode)
        
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)
        
    def get_settings(self):
        return {
            "general": self.spin_gen.value(),
            "horiz": self.spin_h.value(),
            "vert": self.spin_v.value(),
            "mode": self.combo_mode.currentText()
        }