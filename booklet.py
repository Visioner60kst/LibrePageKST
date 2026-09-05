from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QComboBox, 
                             QPushButton, QLabel, QFormLayout, QDoubleSpinBox, QButtonGroup)
from PyQt6.QtCore import Qt

class BookletDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки буклета")
        self.setFixedWidth(350)
        
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("Настройки буклета")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Группа типов
        self.group_type = QButtonGroup(self)
        self.rad_one = QRadioButton("Одна тетрадь (весь файл)")
        self.rad_many = QRadioButton("Несколько тетрадей")
        self.rad_one.setChecked(True)
        self.group_type.addButton(self.rad_one)
        self.group_type.addButton(self.rad_many)
        
        layout.addWidget(self.rad_one)
        layout.addWidget(self.rad_many)
        
        # Выбор страниц в тетради
        form = QFormLayout()
        self.combo_pages = QComboBox()
        # Стандартные размеры тетрадей (кратные 4)
        pages = ["4", "8", "16", "24", "32", "40", "48", "64"]
        self.combo_pages.addItems(pages)
        form.addRow("Страниц в одной тетради:", self.combo_pages)
        
        # Смещения
        self.spin_inner = QDoubleSpinBox()
        self.spin_inner.setRange(0, 50)
        self.spin_inner.setSuffix(" мм")
        
        self.spin_outer = QDoubleSpinBox()
        self.spin_outer.setRange(0, 50)
        self.spin_outer.setSuffix(" мм")
        
        form.addRow("Смещение внутрь:", self.spin_inner)
        form.addRow("Смещение наружу:", self.spin_outer)
        
        layout.addLayout(form)
        
        # Кнопка
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

    def get_settings(self):
        return {
            "type": "one" if self.rad_one.isChecked() else "many",
            "pages": int(self.combo_pages.currentText()),
            "inner_offset": self.spin_inner.value(),
            "outer_offset": self.spin_outer.value()
        }