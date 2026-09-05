import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QFileDialog, QRadioButton,
                             QButtonGroup, QWidget, QSpinBox, QColorDialog,
                             QGroupBox, QMessageBox)
from PyQt6.QtGui import QColor

class BackgroundDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка фона")
        self.setMinimumWidth(400)

        self.bg_type = None  # 'pdf', 'jpg', 'color'
        self.file_path = ""
        self.current_rgb = (255, 255, 255) # Белый по умолчанию

        layout = QVBoxLayout(self)

        # --- Секция использования файла ---
        file_group = QGroupBox("Использовать изображение / PDF")
        file_layout = QVBoxLayout()

        self.radio_file = QRadioButton("Фон из файла")
        self.radio_file.setChecked(True)
        file_layout.addWidget(self.radio_file)

        btn_layout = QHBoxLayout()
        self.btn_pdf = QPushButton("Вставить PDF")
        self.btn_jpg = QPushButton("Вставить JPG")
        self.btn_pdf.clicked.connect(self.load_pdf)
        self.btn_jpg.clicked.connect(self.load_jpg)
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_jpg)

        self.lbl_file = QLabel("Файл не выбран")
        self.lbl_file.setWordWrap(True)

        file_layout.addLayout(btn_layout)
        file_layout.addWidget(self.lbl_file)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # --- Секция использования цвета ---
        color_group = QGroupBox("Использовать заливку цветом")
        color_layout = QVBoxLayout()

        self.radio_color = QRadioButton("Фон цветом")
        color_layout.addWidget(self.radio_color)

        # Переключатель палитр
        palette_layout = QHBoxLayout()
        self.radio_rgb = QRadioButton("Палитра RGB")
        self.radio_cmyk = QRadioButton("Палитра CMYK")
        self.radio_rgb.setChecked(True)
        palette_layout.addWidget(self.radio_rgb)
        palette_layout.addWidget(self.radio_cmyk)
        color_layout.addLayout(palette_layout)

        # Настройки RGB (системная палитра)
        self.rgb_widget = QWidget()
        rgb_lyt = QHBoxLayout(self.rgb_widget)
        rgb_lyt.setContentsMargins(0, 0, 0, 0)
        self.btn_choose_color = QPushButton("Выбрать цвет")
        self.btn_choose_color.clicked.connect(self.choose_system_color)
        rgb_lyt.addWidget(self.btn_choose_color)

        self.lbl_rgb_preview = QLabel()
        self.lbl_rgb_preview.setFixedSize(30, 30)
        self.lbl_rgb_preview.setStyleSheet("background-color: rgb(255, 255, 255); border: 1px solid black;")
        rgb_lyt.addWidget(self.lbl_rgb_preview)
        color_layout.addWidget(self.rgb_widget)

        # Настройки CMYK (прямой ввод процентов)
        self.cmyk_widget = QWidget()
        cmyk_lyt = QHBoxLayout(self.cmyk_widget)
        cmyk_lyt.setContentsMargins(0, 0, 0, 0)
        
        self.spin_c = QSpinBox()
        self.spin_c.setRange(0, 100)
        self.spin_c.setPrefix("C: ")
        
        self.spin_m = QSpinBox()
        self.spin_m.setRange(0, 100)
        self.spin_m.setPrefix("M: ")
        
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 100)
        self.spin_y.setPrefix("Y: ")
        
        self.spin_k = QSpinBox()
        self.spin_k.setRange(0, 100)
        self.spin_k.setPrefix("K: ")
        
        cmyk_lyt.addWidget(self.spin_c)
        cmyk_lyt.addWidget(self.spin_m)
        cmyk_lyt.addWidget(self.spin_y)
        cmyk_lyt.addWidget(self.spin_k)
        self.cmyk_widget.setVisible(False)
        color_layout.addWidget(self.cmyk_widget)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Связываем переключение
        self.radio_rgb.toggled.connect(self.toggle_palettes)
        self.radio_cmyk.toggled.connect(self.toggle_palettes)

        # Взаимоисключение главных радиокнопок
        self.main_bg_group = QButtonGroup(self)
        self.main_bg_group.addButton(self.radio_file)
        self.main_bg_group.addButton(self.radio_color)
        self.radio_file.toggled.connect(self.update_ui_state)
        self.radio_color.toggled.connect(self.update_ui_state)

        # --- Выбор страниц для применения ---
        self.combo_range = QComboBox()
        self.combo_range.addItems(["Все страницы", "Текущая страница", "Четные страницы", "Нечетные страницы"])
        layout.addWidget(QLabel("Применить к:"))
        layout.addWidget(self.combo_range)

        # --- Кнопка применения ---
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

        # Инициализация интерфейса
        self.update_ui_state()

    def toggle_palettes(self):
        if self.radio_rgb.isChecked():
            self.rgb_widget.setVisible(True)
            self.cmyk_widget.setVisible(False)
        else:
            self.rgb_widget.setVisible(False)
            self.cmyk_widget.setVisible(True)

    def update_ui_state(self):
        is_file = self.radio_file.isChecked()
        self.btn_pdf.setEnabled(is_file)
        self.btn_jpg.setEnabled(is_file)

        is_color = self.radio_color.isChecked()
        self.btn_choose_color.setEnabled(is_color)
        self.radio_rgb.setEnabled(is_color)
        self.radio_cmyk.setEnabled(is_color)
        self.spin_c.setEnabled(is_color)
        self.spin_m.setEnabled(is_color)
        self.spin_y.setEnabled(is_color)
        self.spin_k.setEnabled(is_color)

    def load_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите PDF", "", "PDF Files (*.pdf)")
        if path:
            self.file_path = path
            self.bg_type = 'pdf'
            self.lbl_file.setText(os.path.basename(path))
            self.radio_file.setChecked(True)

    def load_jpg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите JPG", "", "JPEG Files (*.jpg *.jpeg)")
        if path:
            self.file_path = path
            self.bg_type = 'jpg'
            self.lbl_file.setText(os.path.basename(path))
            self.radio_file.setChecked(True)

    def choose_system_color(self):
        color = QColorDialog.getColor(QColor(*self.current_rgb), self, "Выберите цвет фона")
        if color.isValid():
            self.current_rgb = (color.red(), color.green(), color.blue())
            self.lbl_rgb_preview.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid black;")

    def get_settings(self):
        """Формирует и возвращает настройки для применения"""
        settings = {
            'range': self.combo_range.currentText(),
            'bg_type': None,
            'file_path': None,
            'color_value': None
        }

        if self.radio_file.isChecked():
            if not self.file_path:
                QMessageBox.warning(self, "Внимание", "Пожалуйста, выберите файл изображения или PDF.")
                return None
            settings['bg_type'] = self.bg_type
            settings['file_path'] = self.file_path
        else:
            settings['bg_type'] = 'color'
            if self.radio_rgb.isChecked():
                # PyMuPDF ожидает компоненты цвета от 0.0 до 1.0 (для 3 значений это автоматически RGB)
                settings['color_value'] = (self.current_rgb[0]/255.0, self.current_rgb[1]/255.0, self.current_rgb[2]/255.0)
            else:
                # 4 компоненты цвета автоматически трактуются PyMuPDF как CMYK
                settings['color_value'] = (self.spin_c.value()/100.0, self.spin_m.value()/100.0, self.spin_y.value()/100.0, self.spin_k.value()/100.0)

        return settings