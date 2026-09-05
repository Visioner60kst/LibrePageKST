import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton)
from PyQt6.QtCore import Qt

class ConvertColorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Конвертация цветов")
        self.setFixedSize(450, 220)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)

        # 1. Диапазон страниц
        range_layout = QHBoxLayout()
        range_label = QLabel("Диапазон страниц:")
        range_label.setFixedWidth(130)
        range_layout.addWidget(range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.addItems([
            "Все страницы", 
            "Текущая страница", 
            "Четные страницы", 
            "Нечетные страницы"
        ])
        range_layout.addWidget(self.range_combo)
        self.layout.addLayout(range_layout)

        # 2. Выбор цветовой модели (Target)
        target_layout = QHBoxLayout()
        target_label = QLabel("Цветовая модель:")
        target_label.setFixedWidth(130)
        target_layout.addWidget(target_label)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["cmyk", "rgb", "grey"])
        target_layout.addWidget(self.target_combo)
        self.layout.addLayout(target_layout)

        # 3. Выбор ICC Профиля (Динамический)
        profile_layout = QHBoxLayout()
        profile_label = QLabel("ICC Профиль:")
        profile_label.setFixedWidth(130)
        profile_layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        profile_layout.addWidget(self.profile_combo)
        self.layout.addLayout(profile_layout)

        # Привязываем изменение модели к обновлению списка профилей
        self.target_combo.currentTextChanged.connect(self.update_profiles_list)
        
        # Инициализируем список профилей первый раз
        self.update_profiles_list(self.target_combo.currentText())

        # 4. Кнопки Ок/Отмена
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Применить")
        self.btn_ok.setStyleSheet("background-color: #9c27b0; color: white; font-weight: bold; padding: 6px;")
        self.btn_ok.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setStyleSheet("padding: 6px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(btn_layout)

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

    def update_profiles_list(self, target_color):
        """Загружает файлы профилей из соответствующей папки в resources"""
        self.profile_combo.clear()
        
        # Опция по умолчанию, когда встроенный GS берет свой базовый профиль
        self.profile_combo.addItem("По умолчанию (без профиля)", "")

        # Сопоставляем выбор пользователя с названием папки
        folder_map = {
            "cmyk": "CMYK",
            "rgb": "RGB",
            "grey": "GRAY",
        }
        
        folder_name = folder_map.get(target_color, "")
        if not folder_name:
            return

        base_dir = self.get_base_dir()
        profile_dir = os.path.join(base_dir, "resources", "profiles", folder_name)

        if os.path.exists(profile_dir) and os.path.isdir(profile_dir):
            for file_name in os.listdir(profile_dir):
                if file_name.lower().endswith(('.icc', '.icm')):
                    # Храним полный абсолютный путь к файлу в userData (для Ghostscript)
                    full_path = os.path.join(profile_dir, file_name)
                    # Выводим в список только название файла
                    self.profile_combo.addItem(file_name, full_path)

    def get_settings(self):
        """Возвращает настройки в main.py после нажатия 'Применить'"""
        return {
            'range': self.range_combo.currentText(),
            'target': self.target_combo.currentText(),
            # currentData() вернет полный путь к файлу профиля (или "" если выбрано "По умолчанию")
            'profile': self.profile_combo.currentData(),
            'gs_path': self.get_gs_path()  # Добавлен путь к Ghostscript
        }