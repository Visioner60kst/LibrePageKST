import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QFontComboBox, QColorDialog, QFormLayout, QGroupBox)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

class NumberPageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки нумерации")
        self.resize(350, 350)
        self.selected_color = QColor(0, 0, 0)  # Черный цвет по умолчанию
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        group_box = QGroupBox("Параметры нумерации")
        form_layout = QFormLayout(group_box)

        # 1. Выбор шрифта и размера
        self.font_combo = QFontComboBox()
        form_layout.addRow("Шрифт:", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 200)
        self.size_spin.setValue(12)
        form_layout.addRow("Размер шрифта:", self.size_spin)

        # 2. Выбор места: Сверху или Снизу
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Сверху", "Снизу"])
        form_layout.addRow("Расположение:", self.pos_combo)

        # 3. Отступы (в миллиметрах)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000, 1000)
        self.x_spin.setValue(10.0)
        self.x_spin.setSuffix(" мм")
        form_layout.addRow("Отступ слева:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000, 1000)
        self.y_spin.setValue(10.0)
        self.y_spin.setSuffix(" мм")
        form_layout.addRow("Отступ по вертикали:", self.y_spin)

        # 4. Выбор цвета
        self.btn_color = QPushButton("Выбрать цвет")
        self.btn_color.setStyleSheet("background-color: #000000; color: white; font-weight: bold;")
        self.btn_color.clicked.connect(self.choose_color)
        form_layout.addRow("Цвет:", self.btn_color)

        # 5. Угол наклона
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(0, 360)
        self.angle_spin.setValue(0)
        self.angle_spin.setSuffix(" °")
        form_layout.addRow("Угол наклона:", self.angle_spin)

        layout.addWidget(group_box)

        # Кнопки применения
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        self.btn_apply.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setStyleSheet("padding: 6px;")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)

    def choose_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Выберите цвет нумерации")
        if color.isValid():
            self.selected_color = color
            # Динамически меняем цвет текста на кнопке, чтобы он был читаемым на любом фоне
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