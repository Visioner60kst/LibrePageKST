from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QLineEdit, QRadioButton,
    QButtonGroup, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator


class SizePageDialog(QDialog):
    def __init__(self, parent=None, current_w_mm=210.0, current_h_mm=297.0):
        super().__init__(parent)

        self.setWindowTitle("RESIZE")
        self.resize(300, 390)

        # Сохраняем реальные размеры текущей страницы PDF
        self.current_w = current_w_mm
        self.current_h = current_h_mm

        # Определяем ориентацию исходной страницы.
        # Если ширина больше высоты — исходник горизонтальный.
        self.is_landscape = self.current_w > self.current_h

        # Стандартные размеры A-серии.
        # ВАЖНО: ориентация автоматически берётся
        # от текущей страницы PDF.
        if self.is_landscape:
            self.standard_sizes = {
                "A6": (148, 105),
                "A5": (210, 148),
                "A4": (297, 210),
                "A3": (420, 297),
                "A2": (594, 420),
                "A1": (841, 594),
                "A0": (1189, 841),
                "Custom": (0, 0)
            }
        else:
            self.standard_sizes = {
                "A6": (105, 148),
                "A5": (148, 210),
                "A4": (210, 297),
                "A3": (297, 420),
                "A2": (420, 594),
                "A1": (594, 841),
                "A0": (841, 1189),
                "Custom": (0, 0)
            }

        layout = QVBoxLayout(self)

        # Информация о текущем размере
        orientation_text = "Landscape" if self.is_landscape else "Portrait"

        current_size_label = QLabel(
            f"Current Size: {self.current_w:.2f} x "
            f"{self.current_h:.2f} mm\n"
            f"Orientation: {orientation_text}"
        )
        current_size_label.setStyleSheet(
            "color: #666; font-style: italic; margin-bottom: 5px;"
        )
        layout.addWidget(current_size_label)

        # Выбор формата
        layout.addWidget(QLabel("Select format:"))

        self.size_combo = QComboBox()
        self.size_combo.addItems(list(self.standard_sizes.keys()))

        # Автоматически определяем формат текущего листа
        matched_format = "Custom"

        for fmt, (w, h) in self.standard_sizes.items():
            if fmt == "Custom":
                continue

            if abs(w - self.current_w) < 1.0 and abs(h - self.current_h) < 1.0:
                matched_format = fmt
                break

        self.size_combo.setCurrentText(matched_format)
        self.size_combo.currentIndexChanged.connect(self.on_size_changed)
        layout.addWidget(self.size_combo)

        # Поля произвольного размера
        self.custom_w_input = QLineEdit()
        self.custom_w_input.setValidator(
            QDoubleValidator(1.0, 5000.0, 2)
        )
        self.custom_w_input.setPlaceholderText("Width (mm)")

        self.custom_h_input = QLineEdit()
        self.custom_h_input.setValidator(
            QDoubleValidator(1.0, 5000.0, 2)
        )
        self.custom_h_input.setPlaceholderText("Height (mm)")

        layout.addWidget(QLabel("Width (mm):"))
        layout.addWidget(self.custom_w_input)
        layout.addWidget(QLabel("Height (mm):"))
        layout.addWidget(self.custom_h_input)

        # Масштабирование содержимого
        layout.addSpacing(5)

        self.check_scale = QCheckBox(
            "Proportional scale content"
        )
        self.check_scale.setChecked(True)
        layout.addWidget(self.check_scale)

        # Выбор страниц
        layout.addSpacing(10)

        self.radio_current = QRadioButton("Current page")
        self.radio_all = QRadioButton("All pages")
        self.radio_all.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.radio_current)
        self.group.addButton(self.radio_all)

        layout.addWidget(self.radio_current)
        layout.addWidget(self.radio_all)

        # Кнопка APPLY
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet(
            "background-color: #e83e8c; "
            "color: white; font-weight: bold;"
        )
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

        # Заполняем поля выбранного формата
        self.on_size_changed()

        # Если текущий формат нестандартный,
        # показываем реальные размеры страницы.
        if matched_format == "Custom":
            self.custom_w_input.setText(
                str(round(self.current_w, 2))
            )
            self.custom_h_input.setText(
                str(round(self.current_h, 2))
            )

    def on_size_changed(self):
        val = self.size_combo.currentText()

        if val != "Custom":
            w, h = self.standard_sizes[val]

            self.custom_w_input.setText(str(w))
            self.custom_h_input.setText(str(h))

            self.custom_w_input.setEnabled(False)
            self.custom_h_input.setEnabled(False)

        else:
            self.custom_w_input.setEnabled(True)
            self.custom_h_input.setEnabled(True)

            if not self.custom_w_input.text():
                self.custom_w_input.setText(
                    str(round(self.current_w, 2))
                )

            if not self.custom_h_input.text():
                self.custom_h_input.setText(
                    str(round(self.current_h, 2))
                )

    def get_settings(self):
        return {
            "w_mm": float(
                self.custom_w_input.text().replace(",", ".")
            ),
            "h_mm": float(
                self.custom_h_input.text().replace(",", ".")
            ),
            "all": self.radio_all.isChecked(),
            "scale": self.check_scale.isChecked(),
            "old_w_mm": self.current_w,
            "old_h_mm": self.current_h,
            "orientation": "landscape"
            if self.is_landscape
            else "portrait"
        }