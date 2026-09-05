import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QRadioButton, QButtonGroup, 
                             QGroupBox)
from PyQt6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки экспорта")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Выбор формата
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPG", "TIFF"])
        fmt_layout.addWidget(self.format_combo)
        layout.addLayout(fmt_layout)
        
        # Выбор диапазона страниц
        self.group_range = QGroupBox("Диапазон страниц")
        range_layout = QVBoxLayout()
        self.rb_all = QRadioButton("Все страницы")
        self.rb_all.setChecked(True)
        self.rb_current = QRadioButton("Текущая страница")
        self.rb_even = QRadioButton("Четные страницы")
        self.rb_odd = QRadioButton("Нечетные страницы")
        
        self.range_group = QButtonGroup()
        self.range_group.addButton(self.rb_all)
        self.range_group.addButton(self.rb_current)
        self.range_group.addButton(self.rb_even)
        self.range_group.addButton(self.rb_odd)
        
        range_layout.addWidget(self.rb_all)
        range_layout.addWidget(self.rb_current)
        range_layout.addWidget(self.rb_even)
        range_layout.addWidget(self.rb_odd)
        self.group_range.setLayout(range_layout)
        layout.addWidget(self.group_range)
        
        # Выбор цветового пространства
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Цвет:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["RGB", "CMYK", "GRAY"])
        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)
        
        # Кнопка Применить
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)
        
        self.setLayout(layout)

    def get_settings(self):
        mode = ""
        if self.rb_all.isChecked(): mode = "Все страницы"
        elif self.rb_current.isChecked(): mode = "Текущая страница"
        elif self.rb_even.isChecked(): mode = "Четные страницы"
        elif self.rb_odd.isChecked(): mode = "Нечетные страницы"
        
        return {
            "format": self.format_combo.currentText(),
            "range": mode,
            "color": self.color_combo.currentText()
        }