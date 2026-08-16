import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QFileDialog, QRadioButton,
                             QButtonGroup, QWidget, QSpinBox, QColorDialog,
                             QGroupBox, QMessageBox)
from PyQt6.QtGui import QColor

class BackgroundDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Background setting"))
        self.setMinimumWidth(400)

        self.bg_type = None  # 'pdf', 'jpg', 'color'
        self.file_path = ""
        self.current_rgb = (255, 255, 255) # White by default

        layout = QVBoxLayout(self)

        # --- File Usage Section ---
        file_group = QGroupBox(self.tr("Use image / PDF"))
        file_layout = QVBoxLayout()

        self.radio_file = QRadioButton(self.tr("Background from file"))
        self.radio_file.setChecked(True)
        file_layout.addWidget(self.radio_file)

        btn_layout = QHBoxLayout()
        self.btn_pdf = QPushButton(self.tr("Insert PDF"))
        self.btn_jpg = QPushButton(self.tr("Insert JPG"))
        self.btn_pdf.clicked.connect(self.load_pdf)
        self.btn_jpg.clicked.connect(self.load_jpg)
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_jpg)

        self.lbl_file = QLabel(self.tr("File not selected"))
        self.lbl_file.setWordWrap(True)

        file_layout.addLayout(btn_layout)
        file_layout.addWidget(self.lbl_file)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # --- Color Usage Section ---
        color_group = QGroupBox(self.tr("Use color fill"))
        color_layout = QVBoxLayout()

        self.radio_color = QRadioButton(self.tr("Background color"))
        color_layout.addWidget(self.radio_color)

        # Palette switcher
        palette_layout = QHBoxLayout()
        self.radio_rgb = QRadioButton(self.tr("Palette RGB"))
        self.radio_cmyk = QRadioButton(self.tr("Palette CMYK"))
        self.radio_rgb.setChecked(True)
        palette_layout.addWidget(self.radio_rgb)
        palette_layout.addWidget(self.radio_cmyk)
        color_layout.addLayout(palette_layout)

        # Settings RGB (system palette)
        self.rgb_widget = QWidget()
        rgb_lyt = QHBoxLayout(self.rgb_widget)
        rgb_lyt.setContentsMargins(0, 0, 0, 0)
        self.btn_choose_color = QPushButton(self.tr("Select color"))
        self.btn_choose_color.clicked.connect(self.choose_system_color)
        rgb_lyt.addWidget(self.btn_choose_color)

        self.lbl_rgb_preview = QLabel()
        self.lbl_rgb_preview.setFixedSize(30, 30)
        self.lbl_rgb_preview.setStyleSheet("background-color: rgb(255, 255, 255); border: 1px solid black;")
        rgb_lyt.addWidget(self.lbl_rgb_preview)
        color_layout.addWidget(self.rgb_widget)

        # Settings CMYK (direct interest entry)
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

        # Linking the switch
        self.radio_rgb.toggled.connect(self.toggle_palettes)
        self.radio_cmyk.toggled.connect(self.toggle_palettes)

        # Mutual exclusion of main radio buttons
        self.main_bg_group = QButtonGroup(self)
        self.main_bg_group.addButton(self.radio_file)
        self.main_bg_group.addButton(self.radio_color)
        self.radio_file.toggled.connect(self.update_ui_state)
        self.radio_color.toggled.connect(self.update_ui_state)

        # --- Selecting pages to apply ---
        self.combo_range = QComboBox()
        # Добавляем пары: (отображаемый текст с поддержкой перевода, скрытый неизменяемый ключ)
        self.combo_range.addItem(self.tr("All Pages"), "all")
        self.combo_range.addItem(self.tr("Current Page"), "current")
        self.combo_range.addItem(self.tr("Even Pages"), "even")
        self.combo_range.addItem(self.tr("Odd Pages"), "odd")
        
        layout.addWidget(QLabel(self.tr("Apply to:")))
        layout.addWidget(self.combo_range)

        # --- Application button ---
        self.btn_apply = QPushButton(self.tr("APPLY"))
        self.btn_apply.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

        # Initialize the interface
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
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Select PDF"), "", "PDF Files (*.pdf)")
        if path:
            self.file_path = path
            self.bg_type = 'pdf'
            self.lbl_file.setText(os.path.basename(path))
            self.radio_file.setChecked(True)

    def load_jpg(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Select JPG"), "", "JPEG Files (*.jpg *.jpeg)")
        if path:
            self.file_path = path
            self.bg_type = 'jpg'
            self.lbl_file.setText(os.path.basename(path))
            self.radio_file.setChecked(True)

    def choose_system_color(self):
        color = QColorDialog.getColor(QColor(*self.current_rgb), self, self.tr("Select background color"))
        if color.isValid():
            self.current_rgb = (color.red(), color.green(), color.blue())
            self.lbl_rgb_preview.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid black;")

    def get_settings(self):
        """Generates and returns settings for application"""
        settings = {
            'range': self.combo_range.currentData(),  # Возвращает 'all', 'current', 'even' или 'odd'
            'bg_type': None,
            'file_path': None,
            'color_value': None
        }

        if self.radio_file.isChecked():
            if not self.file_path:
                QMessageBox.warning(self, self.tr("Attention"), self.tr("Please select an image file or PDF."))
                return None
            settings['bg_type'] = self.bg_type
            settings['file_path'] = self.file_path
        else:
            settings['bg_type'] = 'color'
            if self.radio_rgb.isChecked():
                # PyMuPDF expects color components from 0.0 to 1.0 (for 3 values this is automatic RGB)
                settings['color_value'] = (self.current_rgb[0]/255.0, self.current_rgb[1]/255.0, self.current_rgb[2]/255.0)
            else:
                # 4 color components are automatically interpreted PyMuPDF How CMYK
                settings['color_value'] = (self.spin_c.value()/100.0, self.spin_m.value()/100.0, self.spin_y.value()/100.0, self.spin_k.value()/100.0)

        return settings