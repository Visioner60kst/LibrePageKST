from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QLineEdit, QRadioButton,
                             QButtonGroup, QGridLayout, QCheckBox)
from PyQt6.QtGui import QDoubleValidator, QIntValidator


class MultiplyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DUPLICATE PAGES")
        self.resize(380, 470)

        self.standard_sizes = {
            "A0": (841, 1189),
            "A1": (594, 841),
            "A2": (420, 594),
            "A3": (297, 420),
            "A4": (210, 297),
            "A5": (148, 210),
            "A6": (105, 148),
            "A7": (74, 105),
            "Custom": (0, 0)
        }

        layout = QVBoxLayout(self)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Sheet size:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(list(self.standard_sizes.keys()))
        self.size_combo.setCurrentText("A3")
        self.size_combo.currentIndexChanged.connect(self.on_size_changed)
        size_layout.addWidget(self.size_combo)
        layout.addLayout(size_layout)

        self.custom_size_layout = QHBoxLayout()
        self.custom_w_input = QLineEdit()
        self.custom_w_input.setValidator(QDoubleValidator(1.0, 5000.0, 2))
        self.custom_h_input = QLineEdit()
        self.custom_h_input.setValidator(QDoubleValidator(1.0, 5000.0, 2))
        self.custom_size_layout.addWidget(self.custom_w_input)
        self.custom_size_layout.addWidget(QLabel("x"))
        self.custom_size_layout.addWidget(self.custom_h_input)
        layout.addLayout(self.custom_size_layout)

        orient_layout = QHBoxLayout()
        self.radio_portrait = QRadioButton("Book")
        self.radio_landscape = QRadioButton("Landscape")
        self.radio_landscape.setChecked(True)
        self.orient_group = QButtonGroup()
        self.orient_group.addButton(self.radio_portrait)
        self.orient_group.addButton(self.radio_landscape)
        orient_layout.addWidget(self.radio_portrait)
        orient_layout.addWidget(self.radio_landscape)
        layout.addLayout(orient_layout)

        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Copies per line:"), 0, 0)
        self.cols_input = QLineEdit("2")
        self.cols_input.setValidator(QIntValidator(1, 100))
        grid_layout.addWidget(self.cols_input, 0, 1)

        grid_layout.addWidget(QLabel("Copies per column:"), 1, 0)
        self.rows_input = QLineEdit("2")
        self.rows_input.setValidator(QIntValidator(1, 100))
        grid_layout.addWidget(self.rows_input, 1, 1)

        grid_layout.addWidget(QLabel("Distance between pages. (mm):"), 2, 0)
        self.spacing_input = QLineEdit("0")
        self.spacing_input.setValidator(QDoubleValidator(0.0, 500.0, 2))
        grid_layout.addWidget(self.spacing_input, 2, 1)

        layout.addLayout(grid_layout)

        self.check_crop_marks = QCheckBox("Place cutting marks (3 mm)")
        layout.addWidget(self.check_crop_marks)

        marks_layout = QGridLayout()
        marks_layout.addWidget(QLabel("Above (mm):"), 0, 0)
        self.crop_top_input = QLineEdit("3")
        self.crop_top_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        marks_layout.addWidget(self.crop_top_input, 0, 1)

        marks_layout.addWidget(QLabel("From below (mm):"), 1, 0)
        self.crop_bottom_input = QLineEdit("3")
        self.crop_bottom_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        marks_layout.addWidget(self.crop_bottom_input, 1, 1)

        marks_layout.addWidget(QLabel("Left (mm):"), 2, 0)
        self.crop_left_input = QLineEdit("3")
        self.crop_left_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        marks_layout.addWidget(self.crop_left_input, 2, 1)

        marks_layout.addWidget(QLabel("Right (mm):"), 3, 0)
        self.crop_right_input = QLineEdit("3")
        self.crop_right_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        marks_layout.addWidget(self.crop_right_input, 3, 1)

        layout.addLayout(marks_layout)

        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        self.on_size_changed()

    def on_size_changed(self):
        is_custom = self.size_combo.currentText() == "Custom"
        self.custom_w_input.setEnabled(is_custom)
        self.custom_h_input.setEnabled(is_custom)

        if not is_custom:
            w, h = self.standard_sizes[self.size_combo.currentText()]
            self.custom_w_input.setText(str(w))
            self.custom_h_input.setText(str(h))

    def get_settings(self):
        w = float(self.custom_w_input.text().replace(',', '.')) if self.custom_w_input.text() else 0.0
        h = float(self.custom_h_input.text().replace(',', '.')) if self.custom_h_input.text() else 0.0

        if self.radio_portrait.isChecked():
            target_w = min(w, h)
            target_h = max(w, h)
        else:
            target_w = max(w, h)
            target_h = min(w, h)

        return {
            'target_width_mm': target_w,
            'target_height_mm': target_h,
            'cols': int(self.cols_input.text()) if self.cols_input.text() else 1,
            'rows': int(self.rows_input.text()) if self.rows_input.text() else 1,
            'spacing_mm': float(self.spacing_input.text().replace(',', '.')) if self.spacing_input.text() else 0.0,
            'crop_marks': self.check_crop_marks.isChecked(),
            'crop_offset_top_mm': float(self.crop_top_input.text().replace(',', '.')) if self.crop_top_input.text() else 0.0,
            'crop_offset_bottom_mm': float(self.crop_bottom_input.text().replace(',', '.')) if self.crop_bottom_input.text() else 0.0,
            'crop_offset_left_mm': float(self.crop_left_input.text().replace(',', '.')) if self.crop_left_input.text() else 0.0,
            'crop_offset_right_mm': float(self.crop_right_input.text().replace(',', '.')) if self.crop_right_input.text() else 0.0,
        }
