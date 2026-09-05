import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt

class CurvesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Текст в кривые")
        self.resize(350, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Выбор диапазона
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Применить к:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems([
            "Все страницы",
            "Текущая страница",
            "Четные страницы",
            "Нечетные страницы",
            "Указанные страницы"
        ])
        self.range_combo.currentTextChanged.connect(self.on_range_changed)
        range_layout.addWidget(self.range_combo)
        layout.addLayout(range_layout)

        # Поле для ввода определенных страниц (включается при выборе "Указанные страницы")
        self.custom_pages_input = QLineEdit()
        self.custom_pages_input.setPlaceholderText("Например: 1, 3, 5-7")
        self.custom_pages_input.setEnabled(False)
        layout.addWidget(self.custom_pages_input)

        # Кнопки действия
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_base_dir(self):
        """Определяет базовую директорию для работы программы"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_gs_path(self):
        """Определяет правильный исполняемый файл Ghostscript в зависимости от ОС"""
        base_dir = self.get_base_dir()
        bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
        
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            local_gs = os.path.join(bin_dir, "gs")
            if os.path.exists(local_gs):
                return local_gs
            # Если локального бинарника нет, используем системный
            return "gs" 
        else:
            # Для Windows
            return os.path.join(bin_dir, "gswin64c.exe")

    def on_range_changed(self, text):
        # Активируем поле ввода только если выбраны "Указанные страницы"
        self.custom_pages_input.setEnabled(text == "Указанные страницы")

    def get_settings(self):
        """Возвращает настройки после закрытия диалога"""
        return {
            'range': self.range_combo.currentText(),
            'custom_pages': self.custom_pages_input.text(),
            'gs_path': self.get_gs_path()  # Добавлен путь к Ghostscript
        }